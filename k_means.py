import sqlite3
import pandas as pd
from sentence_transformers import SentenceTransformer, util

def classify_and_populate_db(csv_path: str, db_path: str = "jeopardy.db"):
    # 1. Load raw data and extract unique categories
    df = pd.read_csv(csv_path)
    unique_categories = df['category'].dropna().astype(str).unique()
    print(f"Loaded {len(unique_categories)} unique categories.")

    # 2. Define Anchor Target Subjects
    anchor_subjects = [
        "Pop Culture, Movies, Television, and Music",
        "World and US History, Politics, and Royalty",
        "Science, Nature, Technology, and Medicine",
        "Geography, Countries, World Capitals, and Landmarks",
        "Wordplay, Puns, Spelling, and Language Games",
        "Literature, Authors, Fine Arts, and Theatre",
        "Sports, Games, and Hobbies"
    ]

    # 3. Load Sentence Transformer Model
    print("Loading sentence-transformers model 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 4. Generate Embeddings for Categories AND Anchors
    print("Generating dense semantic embeddings...")
    category_embeddings = model.encode(unique_categories, show_progress_bar=True, convert_to_tensor=True)
    anchor_embeddings = model.encode(anchor_subjects, convert_to_tensor=True)

    # 5. Compute Cosine Similarity & Assign Parent Subject
    print("Classifying categories to nearest anchor subject...")
    similarity_matrix = util.cos_sim(category_embeddings, anchor_embeddings)
    best_match_indices = similarity_matrix.argmax(dim=1).cpu().numpy()

    # Map results
    assigned_subjects = [anchor_subjects[idx] for idx in best_match_indices]

    cat_df = pd.DataFrame({
        'category_name': unique_categories,
        'cluster_id': best_match_indices,
        'parent_subject': assigned_subjects
    })

    # 6. Database DDL & Ingestion
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Dim_Category (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE,
        cluster_id INTEGER,
        parent_subject TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Dim_Round (
        round_id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_name TEXT UNIQUE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Fact_Category_Appearances (
        appearance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        show_num INTEGER,
        air_date TEXT,
        category_id INTEGER,
        round_id INTEGER,
        category_char_count INTEGER,
        category_word_count INTEGER,
        FOREIGN KEY (category_id) REFERENCES Dim_Category(category_id),
        FOREIGN KEY (round_id) REFERENCES Dim_Round(round_id)
    );
    """)
    conn.commit()

    # Populate Dim_Category
    for _, row in cat_df.iterrows():
        cursor.execute("""
            INSERT OR IGNORE INTO Dim_Category (category_name, cluster_id, parent_subject)
            VALUES (?, ?, ?)
        """, (row['category_name'], int(row['cluster_id']), row['parent_subject']))

    # Populate Dim_Round
    for round_name in df['round'].dropna().drop_duplicates():
        cursor.execute("INSERT OR IGNORE INTO Dim_Round (round_name) VALUES (?)", (round_name,))

    conn.commit()

    # Build Foreign Key Lookups
    cat_map = pd.read_sql_query("SELECT category_id, category_name FROM Dim_Category", conn).set_index('category_name')['category_id'].to_dict()
    round_map = pd.read_sql_query("SELECT round_id, round_name FROM Dim_Round", conn).set_index('round_name')['round_id'].to_dict()

    # Populate Fact Table
    fact_records = []
    for _, row in df.iterrows():
        cat_str = str(row['category']) if pd.notnull(row['category']) else ""
        fact_records.append((
            int(row['game_id']) if pd.notnull(row['game_id']) else None,
            int(row['show_num']) if pd.notnull(row['show_num']) else None,
            str(row['air_date']),
            cat_map.get(row['category']),
            round_map.get(row['round']),
            len(cat_str),
            len(cat_str.split())
        ))

    cursor.executemany("""
        INSERT INTO Fact_Category_Appearances 
        (game_id, show_num, air_date, category_id, round_id, category_char_count, category_word_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, fact_records)

    conn.commit()
    conn.close()

    print("\n--- Distribution of Categories Across Parent Subjects ---")
    print(cat_df['parent_subject'].value_counts())
    print(f"\nDatabase populated successfully at '{db_path}'.")

if __name__ == "__main__":
    classify_and_populate_db("jeopardy_data.csv")