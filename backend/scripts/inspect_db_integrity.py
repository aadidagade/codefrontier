"""
Database Integrity Inspector Script for CodeFrontier Knowledge Handover Platform.
Performs read-only validation of live tables in backend/app.db:
- Checks table existence and row counts
- Checks for orphaned foreign keys
- Checks for NULL integrity violations
- Checks for duplicate records on unique constraints
"""

import sqlite3
import sys

def main():
    db_path = "backend/app.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"=== Auditing Live Database: {db_path} ===")
    
    # 1. PRAGMA foreign_key_check
    cursor.execute("PRAGMA foreign_key_check;")
    fk_violations = cursor.fetchall()
    print(f"Foreign Key Violations Count: {len(fk_violations)}")
    if fk_violations:
        for v in fk_violations:
            print(f"  [FK Violation] Table: {v[0]}, Rowid: {v[1]}, Target: {v[2]}, FK index: {v[3]}")
    else:
        print("  -> PASSED: Zero foreign key violations across all tables.")

    # 2. PRAGMA integrity_check
    cursor.execute("PRAGMA integrity_check;")
    integrity = cursor.fetchall()
    print(f"SQLite Integrity Check: {integrity[0][0]}")

    # 3. List all tables and row counts
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"\nFound {len(tables)} tables:")
    for t in sorted(tables):
        cursor.execute(f"SELECT COUNT(*) FROM \"{t}\";")
        cnt = cursor.fetchone()[0]
        print(f"  - {t:<30}: {cnt} rows")

    # 4. Specific Checks for Orphaned Records
    print("\n=== Checking for Specific Orphaned Records ===")
    
    # Documents without Project
    cursor.execute("""
        SELECT COUNT(*) FROM documents d 
        LEFT JOIN projects p ON d.project_id = p.id 
        WHERE p.id IS NULL;
    """)
    orphaned_docs = cursor.fetchone()[0]
    print(f"Orphaned documents (missing project): {orphaned_docs}")

    # Chunks without Document
    cursor.execute("""
        SELECT COUNT(*) FROM document_chunks c 
        LEFT JOIN documents d ON c.document_id = d.id 
        WHERE d.id IS NULL;
    """)
    orphaned_chunks = cursor.fetchone()[0]
    print(f"Orphaned document chunks (missing document): {orphaned_chunks}")

    # Handovers without Project
    cursor.execute("""
        SELECT COUNT(*) FROM handovers h 
        LEFT JOIN projects p ON h.project_id = p.id 
        WHERE p.id IS NULL;
    """)
    orphaned_handovers = cursor.fetchone()[0]
    print(f"Orphaned handovers (missing project): {orphaned_handovers}")

    # Sections without Handover
    cursor.execute("""
        SELECT COUNT(*) FROM handover_sections s 
        LEFT JOIN handovers h ON s.handover_id = h.id 
        WHERE h.id IS NULL;
    """)
    orphaned_sections = cursor.fetchone()[0]
    print(f"Orphaned handover sections (missing handover): {orphaned_sections}")

    # Tasks without Project
    cursor.execute("""
        SELECT COUNT(*) FROM tasks t 
        LEFT JOIN projects p ON t.project_id = p.id 
        WHERE p.id IS NULL;
    """)
    orphaned_tasks = cursor.fetchone()[0]
    print(f"Orphaned tasks (missing project): {orphaned_tasks}")

    # Conflicts without Project
    cursor.execute("""
        SELECT COUNT(*) FROM conflicts c 
        LEFT JOIN projects p ON c.project_id = p.id 
        WHERE p.id IS NULL;
    """)
    orphaned_conflicts = cursor.fetchone()[0]
    print(f"Orphaned conflicts (missing project): {orphaned_conflicts}")

    # 5. Check unique constraint on user emails
    cursor.execute("SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;")
    dup_emails = cursor.fetchall()
    print(f"Duplicate user emails: {len(dup_emails)}")

    # 6. Check unique constraint on project members (project_id, user_id)
    cursor.execute("SELECT project_id, user_id, COUNT(*) FROM project_members GROUP BY project_id, user_id HAVING COUNT(*) > 1;")
    dup_members = cursor.fetchall()
    print(f"Duplicate project memberships: {len(dup_members)}")

    conn.close()
    print("\nDatabase integrity inspection complete.")

if __name__ == "__main__":
    main()
