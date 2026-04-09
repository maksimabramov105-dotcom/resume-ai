#!/usr/bin/env python3
"""
setup_linkedin_creds.py — Securely store LinkedIn credentials
Usage: python3 setup_linkedin_creds.py

Stores encrypted credentials in credentials.json.
Encryption key stored in .env file (LINKEDIN_FERNET_KEY).
"""
import os
import json
import getpass
import sys

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("cryptography library not installed.")
    print("   Run: pip install cryptography")
    sys.exit(1)

CREDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
ENV_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def get_or_create_key() -> bytes:
    """Get existing Fernet key from .env, or generate and persist a new one."""
    key = None
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("LINKEDIN_FERNET_KEY="):
                    key = line.split("=", 1)[1].encode()
                    break
    if not key:
        key = Fernet.generate_key()
        with open(ENV_FILE, "a", encoding="utf-8") as f:
            f.write(f"\nLINKEDIN_FERNET_KEY={key.decode()}\n")
        print("  New encryption key generated and saved to .env")
    return key


def save_credentials(email: str, password: str) -> None:
    """Encrypt and save LinkedIn credentials to credentials.json."""
    key    = get_or_create_key()
    fernet = Fernet(key)
    creds  = {
        "linkedin_email":    fernet.encrypt(email.encode()).decode(),
        "linkedin_password": fernet.encrypt(password.encode()).decode(),
    }
    with open(CREDS_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)


def load_credentials() -> tuple[str, str]:
    """
    Load and decrypt LinkedIn credentials.
    Used by linkedin_applicator.py and any automated job application module.

    Returns:
        (email, password) as plaintext strings.

    Raises:
        ValueError: if LINKEDIN_FERNET_KEY is not set in environment.
        FileNotFoundError: if credentials.json does not exist.
    """
    key_val = os.getenv("LINKEDIN_FERNET_KEY", "").encode()
    if not key_val:
        raise ValueError(
            "LINKEDIN_FERNET_KEY not set in environment. "
            "Run python3 setup_linkedin_creds.py first."
        )
    fernet = Fernet(key_val)
    if not os.path.exists(CREDS_FILE):
        raise FileNotFoundError(
            f"credentials.json not found at {CREDS_FILE}. "
            "Run python3 setup_linkedin_creds.py first."
        )
    with open(CREDS_FILE, encoding="utf-8") as f:
        creds = json.load(f)
    email    = fernet.decrypt(creds["linkedin_email"].encode()).decode()
    password = fernet.decrypt(creds["linkedin_password"].encode()).decode()
    return email, password


if __name__ == "__main__":
    print("LinkedIn Credential Setup")
    print("=" * 40)
    print("Your credentials will be encrypted with Fernet (AES-128-CBC).")
    print("The encryption key is stored in .env — never commit that file.")
    print()

    # Check if already set
    if os.path.exists(CREDS_FILE):
        overwrite = input("credentials.json already exists. Overwrite? [y/N]: ").strip().lower()
        if overwrite != 'y':
            print("Aborted. Existing credentials unchanged.")
            sys.exit(0)

    email    = input("LinkedIn email: ").strip()
    if not email:
        print("Error: email cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("LinkedIn password: ")
    if not password:
        print("Error: password cannot be empty.")
        sys.exit(1)

    save_credentials(email, password)

    print()
    print("Credentials saved securely to credentials.json")
    print("   Encryption key stored in .env (LINKEDIN_FERNET_KEY)")
    print()
    print("IMPORTANT — add these to .gitignore if not already there:")
    print("   credentials.json")
    print("   .env")
    print()
    print("Test decryption now...")
    try:
        # Must load key from env since we just wrote it
        key_val = None
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                if line.startswith("LINKEDIN_FERNET_KEY="):
                    key_val = line.strip().split("=", 1)[1]
        if key_val:
            os.environ["LINKEDIN_FERNET_KEY"] = key_val
        e, _ = load_credentials()
        print(f"   Decryption OK — email: {e}")
    except Exception as ex:
        print(f"   Decryption test failed: {ex}")
