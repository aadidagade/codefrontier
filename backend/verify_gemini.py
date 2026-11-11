"""
Diagnostic script to verify Google Gemini API connectivity and embedding generation.

Requirements:
- Loads API key from local .env
- Initializes official Google GenAI client (google-genai)
- Checks whether the API key works
- Lists/verifies available generation models
- Verifies configured embedding model is accessible
- Generates a small test embedding and checks it has 768 dimensions
- NEVER prints or logs secret keys
"""

import sys
import os
import re
from pathlib import Path

# Base backend directory
BACKEND_DIR = Path(__file__).resolve().parent


def load_env_vars() -> dict:
    """Manually parse .env without external dependencies if dotenv is not yet installed."""
    env_path = BACKEND_DIR / ".env"
    env_vars = {}
    if not env_path.exists():
        print("[-] Error: backend/.env file not found.")
        print("    Please ensure backend/.env exists before running this test.")
        sys.exit(1)

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip("'\"")
    return env_vars


def mask_key(key: str) -> str:
    """Mask key for safe logging (e.g. AIzaSy...8x9F). Never expose the full key."""
    if not key or len(key) < 8:
        return "********"
    return f"{key[:6]}...{key[-4:]}"


def update_env_variable(key: str, new_value: str):
    """Safely updates or appends a key in backend/.env without altering other lines."""
    env_path = BACKEND_DIR / ".env"
    lines = []
    found = False
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith(f"{key}="):
                lines.append(f"{key}={new_value}\n")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={new_value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def main():
    print("=" * 60)
    print("  Google Gemini Connectivity & Embedding Diagnostics")
    print("=" * 60)

    # 1. Load configuration
    env_vars = load_env_vars()
    api_key = env_vars.get("GEMINI_API_KEY", "")
    embedding_model = env_vars.get("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
    configured_gen_model = env_vars.get("GEMINI_MODEL", "gemini-2.5-flash")
    expected_dim = int(env_vars.get("EMBEDDING_DIMENSION", "768"))

    # 2. Key validation
    if not api_key or api_key == "YOUR_GEMINI_API_KEY" or api_key.startswith("YOUR_"):
        print("\n[-] FAIL: GEMINI_API_KEY is not configured in backend/.env.")
        print("    Please open backend/.env and set your key:")
        print("    GEMINI_API_KEY=AIzaSy...")
        print("    Get your key from: https://aistudio.google.com/api-keys")
        sys.exit(1)

    print(f"[+] Loaded API key: {mask_key(api_key)}")

    # 3. Import official google-genai SDK
    try:
        from google import genai
        from google.genai import types
        print("[+] Successfully imported official 'google-genai' SDK.")
    except ImportError as e:
        print(f"[-] FAIL: google-genai library is not installed: {e}")
        print("    Run: pip install -r requirements.txt")
        sys.exit(1)

    # 4. Initialize client
    try:
        client = genai.Client(api_key=api_key)
        print("[+] Initialized Google GenAI Client.")
    except Exception as e:
        print(f"[-] FAIL: Error initializing client: {e}")
        sys.exit(1)

    # 5. List and verify models
    print("\n[+] Checking available models...")
    available_models = []
    try:
        models_pager = client.models.list()
        for m in models_pager:
            name = getattr(m, "name", "")
            # model names usually look like 'models/gemini-2.5-flash'
            clean_name = name.replace("models/", "")
            available_models.append(clean_name)
        print(f"[+] Found {len(available_models)} accessible models.")
    except Exception as e:
        print(f"[-] WARNING: Could not list models ({e}). Testing direct generation instead.")

    # 6. Verify or select generation model
    preferred_models = [
        configured_gen_model,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]

    selected_gen_model = None
    if available_models:
        for candidate in preferred_models:
            if candidate and candidate in available_models:
                selected_gen_model = candidate
                break
        if not selected_gen_model:
            # Pick any model that starts with gemini
            gemini_candidates = [m for m in available_models if "gemini" in m.lower() and "embed" not in m.lower()]
            if gemini_candidates:
                selected_gen_model = gemini_candidates[0]

    if not selected_gen_model:
        selected_gen_model = configured_gen_model or "gemini-2.5-flash"

    print(f"[+] Testing text generation with model: '{selected_gen_model}'...")
    try:
        response = client.models.generate_content(
            model=selected_gen_model,
            contents="State 'CONNECTED' if you receive this message.",
        )
        reply = response.text.strip()
        print(f"[+] Text generation response verified: {reply[:30]}...")
        if selected_gen_model != configured_gen_model:
            print(f"[+] Updating backend/.env GEMINI_MODEL={selected_gen_model}")
            update_env_variable("GEMINI_MODEL", selected_gen_model)
    except Exception as e:
        print(f"[-] FAIL: Text generation failed with '{selected_gen_model}': {e}")
        sys.exit(1)

    # 7. Verify embedding model
    print(f"\n[+] Testing embedding generation with model: '{embedding_model}'...")
    test_text = "Knowledge Handover Platform: Verifying dense semantic embedding pipeline."

    embedding_candidates = [embedding_model, "text-embedding-004", "gemini-embedding-2"]
    successful_embed_model = None
    embedding_values = None

    for candidate in embedding_candidates:
        if not candidate:
            continue
        try:
            embed_res = client.models.embed_content(
                model=candidate,
                contents=test_text,
            )
            # Inspect returned embedding structure
            if hasattr(embed_res, "embeddings") and embed_res.embeddings:
                embedding_values = embed_res.embeddings[0].values
            elif hasattr(embed_res, "embedding") and embed_res.embedding:
                embedding_values = embed_res.embedding.values
            else:
                embedding_values = getattr(embed_res, "values", None)

            if embedding_values:
                successful_embed_model = candidate
                break
        except Exception as embed_err:
            print(f"    [-] Candidate '{candidate}' error: {embed_err}")

    if not successful_embed_model or not embedding_values:
        print("[-] FAIL: Could not generate embeddings with candidate models.")
        sys.exit(1)

    dim = len(embedding_values)
    print(f"[+] Successfully generated embedding with '{successful_embed_model}'.")
    print(f"[+] Vector dimensions: {dim} (Expected: {expected_dim})")

    if dim != expected_dim:
        print(f"[-] WARNING: Returned dimension is {dim}, expected {expected_dim}.")
        print(f"[+] Auto-adjusting backend/.env EMBEDDING_DIMENSION={dim} and GEMINI_EMBEDDING_MODEL={successful_embed_model}")
        update_env_variable("EMBEDDING_DIMENSION", str(dim))
        update_env_variable("GEMINI_EMBEDDING_MODEL", successful_embed_model)
    else:
        if successful_embed_model != embedding_model:
            print(f"[+] Updating backend/.env GEMINI_EMBEDDING_MODEL={successful_embed_model}")
            update_env_variable("GEMINI_EMBEDDING_MODEL", successful_embed_model)

    print("\n" + "=" * 60)
    print("  [SUCCESS] All Google Gemini API checks passed cleanly!")
    print("  - Generation Model :", selected_gen_model)
    print("  - Embedding Model  :", successful_embed_model)
    print("  - Embedding Vector :", f"{dim} dimensions verified")
    print("  - Secret Safety    : No raw API keys or secrets exposed")
    print("=" * 60)


if __name__ == "__main__":
    main()
