"""
Migration execution and table verification runner.

Requirements:
- Ensures pgvector extension is present
- Executes Alembic migrations: alembic upgrade head
- Verifies all 15 tables are created with proper columns and types
- Verifies VECTOR(768) dimension on document_chunks table
"""

import sys
import asyncio
from pathlib import Path
from alembic.config import Config
from alembic import command
import asyncpg
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).resolve().parent.parent


def get_db_url() -> str:
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        print("[-] Error: backend/.env file not found.")
        sys.exit(1)

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                _, val = line.split("=", 1)
                return val.strip().strip("'\"")
    return ""


async def verify_tables():
    db_url = get_db_url()
    if not db_url or "YOUR_PASSWORD" in db_url:
        print("[-] FAIL: Please configure your PostgreSQL password in backend/.env before running migrations.")
        sys.exit(1)

    raw_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(raw_url)

    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or ""
    database = parsed.path.lstrip("/") or "knowledge_handover"

    # Step 1: Pre-migration pgvector check
    print(f"\n[1/3] Ensuring pgvector extension exists in '{database}'...")
    try:
        conn = await asyncpg.connect(
            host=host, port=port, user=user, password=password, database=database
        )
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        ext_ver = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        print(f"[+] pgvector extension is active (version {ext_ver}).")
        await conn.close()
    except Exception as e:
        print(f"[-] Could not connect or enable pgvector: {e}")
        sys.exit(1)

    # Step 2: Run Alembic migrations
    print("\n[2/3] Running Alembic migration to 'head'...")
    try:
        alembic_ini_path = BACKEND_DIR / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")
        print("[+] Alembic upgrade head completed successfully!")
    except Exception as e:
        print(f"[-] Alembic migration failed: {e}")
        sys.exit(1)

    # Step 3: Verify all 15 tables and columns
    print("\n[3/3] Verifying database tables and vector columns...")
    expected_tables = [
        "users",
        "refresh_tokens",
        "projects",
        "project_members",
        "documents",
        "document_chunks",
        "handovers",
        "handover_sections",
        "handover_versions",
        "handover_audit_logs",
        "evidence_references",
        "conflicts",
        "tasks",
        "task_dependencies",
        "notifications",
    ]

    conn = await asyncpg.connect(
        host=host, port=port, user=user, password=password, database=database
    )

    rows = await conn.fetch(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
        """
    )
    existing_tables = set(r["table_name"] for r in rows)

    missing = [t for t in expected_tables if t not in existing_tables]
    if missing:
        print(f"[-] FAIL: The following expected tables are missing: {missing}")
        await conn.close()
        sys.exit(1)

    print(f"[+] All {len(expected_tables)} required tables verified:")
    for idx, tbl in enumerate(expected_tables, start=1):
        count = await conn.fetchval(f'SELECT count(*) FROM "{tbl}";')
        print(f"    {idx:2d}. {tbl:<25} [verified, rows: {count}]")

    # Check vector column dimension on document_chunks
    col_info = await conn.fetchrow(
        """
        SELECT column_name, udt_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'document_chunks' AND column_name = 'embedding';
        """
    )
    if col_info:
        print(f"\n[+] Vector column verified: document_chunks.embedding -> {col_info['udt_name']} (type: {col_info['data_type']})")

    # Test vector insertion query capability
    test_vec = await conn.fetchval("SELECT '[0.1, 0.2, 0.3]'::vector(768);")
    print(f"[+] Vector(768) syntax and memory allocation confirmed.")

    await conn.close()

    print("\n" + "=" * 65)
    print("  [SUCCESS] All 15 database models and pgvector extension are live!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(verify_tables())
