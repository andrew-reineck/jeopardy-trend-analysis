import sqlite3
import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

def train_and_track_model(db_path: str = "jeopardy.db", experiment_name: str = "Jeopardy_Predictor"):
    # 1. Set up MLflow
    mlflow.set_experiment(experiment_name)

    # 2. Extract analytical dataset from Star Schema via SQL JOIN
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        c.parent_subject,
        r.round_name,
        f.category_char_count,
        f.category_word_count
    FROM Fact_Category_Appearances f
    JOIN Dim_Category c ON f.category_id = c.category_id
    JOIN Dim_Round r ON f.round_id = r.round_id
    WHERE r.round_name IN ('Jeopardy', 'Double Jeopardy', 'Final Jeopardy');
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("No valid records returned from database.")
        return

    # Features & Target
    X = df[['parent_subject', 'category_char_count', 'category_word_count']]
    y = df['round_name']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Model Hyperparameters
    n_estimators = 100
    max_depth = 10
    random_state = 42

    # 3. Start MLflow Run
    with mlflow.start_run():
        print("Logging run to MLflow...")

        # Log Parameters
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("max_depth", max_depth)
        mlflow.log_param("test_size", 0.2)
        mlflow.log_param("model_type", "RandomForestClassifier")

        # Define Feature Preprocessing Pipeline
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OneHotEncoder(handle_unknown='ignore'), ['parent_subject']),
                ('num', 'passthrough', ['category_char_count', 'category_word_count'])
            ]
        )

        model_pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', RandomForestClassifier(
                n_estimators=n_estimators, 
                max_depth=max_depth, 
                random_state=random_state
            ))
        ])

        # Train Model
        model_pipeline.fit(X_train, y_train)

        # Predict & Evaluate
        y_pred = model_pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')

        # Log Metrics
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1_score", f1)

        # Log Scikit-Learn Model Artifact
        mlflow.sklearn.log_model(sk_model=model_pipeline, name="jeopardy_round_classifier", skops_trusted_types=["sklearn.tree._tree.Tree"])

        print(f"\n--- Model Training & Tracking Complete ---")
        print(f"Accuracy:  {acc:.4f}")
        print(f"F1-Score:  {f1:.4f}")

if __name__ == "__main__":
    train_and_track_model()