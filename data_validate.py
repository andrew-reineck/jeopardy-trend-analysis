import sqlite3
import pandas as pd

def run_data_quality_checks(db_path: str = "jeopardy.db") -> bool:
    conn = sqlite3.connect(db_path)
    passed = True

    print("==================================================")
    print("      RUNNING DATA QUALITY & INTEGRITY CHECKS     ")
    print("==================================================\n")

    # 1. Null Checks on Dimensions
    null_cat_query = "SELECT COUNT(*) as cnt FROM Dim_Category WHERE category_name IS NULL OR parent_subject IS NULL"
    null_cats = pd.read_sql_query(null_cat_query, conn).iloc[0]['cnt']
    if null_cats > 0:
        print(f"[FAIL] Found {null_cats} NULL entries in Dim_Category.")
        passed = False
    else:
        print("[PASS] Dim_Category contains zero NULL values.")

    # 2. Foreign Key Integrity Check (Orphans)
    orphan_query = """
    SELECT COUNT(*) as orphan_cnt
    FROM Fact_Category_Appearances f
    LEFT JOIN Dim_Category c ON f.category_id = c.category_id
    WHERE c.category_id IS NULL;
    """
    orphans = pd.read_sql_query(orphan_query, conn).iloc[0]['orphan_cnt']
    if orphans > 0:
        print(f"[FAIL] Found {orphans} orphaned category foreign keys in Fact table.")
        passed = False
    else:
        print("[PASS] Fact_Category_Appearances passes foreign key integrity check.")

    # 3. Value Range & Sanity Check
    len_check_query = "SELECT MIN(category_char_count) as min_len, MAX(category_char_count) as max_len FROM Fact_Category_Appearances"
    lens = pd.read_sql_query(len_check_query, conn).iloc[0]
    if lens['min_len'] <= 0:
        print(f"[WARN] Fact table contains records with non-positive character counts.")
        passed = False
    else:
        print(f"[PASS] Character counts are within valid bounds (Min: {lens['min_len']}, Max: {lens['max_len']}).")

    conn.close()
    
    print("\n--------------------------------------------------")
    if passed:
        print("RESULT: ALL DATA QUALITY CHECKS PASSED SUCCESSFULLY.")
    else:
        print("RESULT: DATA QUALITY CHECKS FAILED - REVIEW LOGS.")
    print("==================================================\n")
    
    return passed

if __name__ == "__main__":
    run_data_quality_checks()