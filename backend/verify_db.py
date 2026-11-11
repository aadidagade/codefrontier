"""
Diagnostic script to verify PostgreSQL connectivity, database existence, and pgvector extension.

Requirements:
- Reads DATABASE_URL from backend/.env
- Connects using asyncpg
- Tests database responsiveness
- Verifies pgvector extension
- Tests vector arithmetic / vector type support
"""

import sys
import asyncio
from pathlib import Path
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).resolve().parent


def load_db_url() -> str:
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


async def verify():
    print("=" * 60)
    print("  PostgreSQL & pgvector Connectivity Diagnostics")
    print("=" * 60)

    db_url = load_db_url()
    if not db_url or "YOUR_PASSWORD" in db_url:
        print("\n[-] FAIL: DATABASE_URL is not configured with your actual PostgreSQL password.")
        print("    Please edit backend/.env:")
        print("    DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/knowledge_handover")
        sys.exit(1)

    # Convert sqlalchemy asyncpg url to asyncpg connection parameters
    # E.g. postgresql+asyncpg://user:pass@host:port/dbname -> postgresql://user:pass@host:port/dbname
    raw_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(raw_url)

    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or ""
    database = parsed.path.lstrip("/") or "knowledge_handover"

    print(f"[+] Connecting to PostgreSQL at {host}:{port} as user '{user}'...")
    print(f"[+] Target database: '{database}'")

    try:
        import asyncpg
    except ImportError:
        print("[-] FAIL: asyncpg is not installed. Run: pip install asyncpg")
        sys.exit(1)

    # 1. Test server connection (connecting to postgres default db if knowledge_handover doesn't exist yet)
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )
        print(f"[+] Successfully connected to database '{database}'.")
    except asyncpg.InvalidCatalogNameError:
        print(f"[-] Database '{database}' does not exist yet.")
        print(f"[+] Attempting to create database '{database}' automatically...")
        try:
            admin_conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database="postgres",
            )
            await admin_conn.execute(f'CREATE DATABASE "{database}";')
            await admin_conn.close()
            print(f"[+] Successfully created database '{database}'!")
            # Reconnect
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
            )
        except Exception as create_err:
            print(f"[-] Could not automatically create database '{database}': {create_err}")
            print("    Please run this manual command in PowerShell:")
            print(f'    psql -U {user} -c "CREATE DATABASE {database};"')
            sys.exit(1)
    except Exception as e:
        print(f"[-] Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("  1. Verify your PostgreSQL service is running (Start -> Services -> postgresql).")
        print("  2. Verify your password in backend/.env matches your PostgreSQL superuser password.")
        print("  3. Default port is 5432.")
        sys.exit(1)

    # 2. Check PostgreSQL version
    pg_version = await conn.fetchval("SELECT version();")
    print(f"[+] PostgreSQL Version: {pg_version.split(',')[0]}")

    # 3. Check pgvector extension
    print("\n[+] Checking pgvector extension...")
    vector_ext = await conn.fetchval(
        "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
    )

    if not vector_ext:
        print("[-] pgvector extension not yet enabled in this database. Attempting to enable...")
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            vector_ext = await conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
            )
            print(f"[+] Successfully enabled pgvector extension (version: {vector_ext})!")
        except Exception as ext_err:
            print(f"[-] Could not enable pgvector automatically: {ext_err}")
            print("\n    To install pgvector on Windows:")
            print("    Option A: If using EnterpriseDB PostgreSQL installer, install pgvector using:")
            print("              https://github.com/pgvector/pgvector#windows")
            print("    Option B: If using Docker:")
            print("              docker run -d --name pgvector -e POSTGRES_PASSWORD=postgres -p 5432:5432 pgvector/pgvector:pg16")
            print(f'    Option C: In psql: psql -U {user} -d {database} -c "CREATE EXTENSION vector;"')
            await conn.close()
            sys.exit(1)
    else:
        print(f"[+] pgvector extension is active (version: {vector_ext}).")

    # 4. Test vector operations
    print("[+] Testing vector type & arithmetic...")
    try:
        sample_vector = await conn.fetchval("SELECT '[0.1, 0.2, 0.3]'::vector;")
        distance = await conn.fetchval(
            "SELECT '[1, 0, 0]'::vector <-> '[0, 1, 0]'::vector AS euclidean_dist;"
        )
        print(f"[+] Vector cast test passed: {sample_vector}")
        print(f"[+] Vector distance calculation passed: {distance:.4f}")
    except Exception as v_err:
        print(f"[-] Vector operation test failed: {v_err}")
        await conn.close()
        sys.exit(1)

    await conn.close()
    print("\n" + "=" * 60)
    print("  [SUCCESS] PostgreSQL and pgvector verified successfully!")
    print(f"  - Database : {database}")
    print(f"  - pgvector : {vector_ext} operational")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(verify())
