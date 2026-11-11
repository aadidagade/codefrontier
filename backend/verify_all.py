"""
Unified verification runner that checks:
1. Environment variables and secrets safety
2. PostgreSQL connection and pgvector extension
3. Google Gemini API connectivity, model availability, and embedding dimensions
"""

import sys
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def main():
    print("*" * 65)
    print("  KNOWLEDGE HANDOVER PLATFORM - ENVIRONMENT VERIFICATION")
    print("*" * 65)

    py_exe = sys.executable

    # 1. Verify Database
    print("\n>>> STEP 1: VERIFYING POSTGRESQL & PGVECTOR...")
    db_script = BACKEND_DIR / "verify_db.py"
    db_result = subprocess.run([py_exe, str(db_script)])
    if db_result.returncode != 0:
        print("\n[-] PostgreSQL verification encountered issues (see above).")
    else:
        print("\n[+] PostgreSQL & pgvector check passed!")

    # 2. Verify Gemini
    print("\n>>> STEP 2: VERIFYING GOOGLE GEMINI AI CLIENT & EMBEDDINGS...")
    gemini_script = BACKEND_DIR / "verify_gemini.py"
    gemini_result = subprocess.run([py_exe, str(gemini_script)])
    if gemini_result.returncode != 0:
        print("\n[-] Gemini verification encountered issues (see above).")
    else:
        print("\n[+] Google Gemini check passed!")

    if db_result.returncode == 0 and gemini_result.returncode == 0:
        print("\n" + "*" * 65)
        print("  ALL SYSTEM CHECKS PASSED SUCCESSFULLY!")
        print("  Backend environment is fully prepared for Phase 2.")
        print("*" * 65)
    else:
        print("\n" + "*" * 65)
        print("  One or more checks requires manual action (see instructions above).")
        print("*" * 65)


if __name__ == "__main__":
    main()
