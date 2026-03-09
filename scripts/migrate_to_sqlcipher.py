#!/usr/bin/env python3
"""
BLACKSITE — SQLCipher migration script.
Encrypts an existing plaintext SQLite database using SQLCipher AES-256.

Usage:
    python scripts/migrate_to_sqlcipher.py [--db data/blacksite.db] [--key-env BLACKSITE_DB_KEY]

The encryption key is read from the environment variable BLACKSITE_DB_KEY.
If not set, a random 32-byte key is generated, printed, and must be saved to config.yaml.
"""
import argparse
import os
import sys
import shutil
import secrets
from pathlib import Path


def migrate(db_path: str, key: str) -> None:
    try:
        from pysqlcipher3 import dbapi2 as sqlcipher
    except ImportError:
        print("ERROR: pysqlcipher3 not installed. Run: pip install pysqlcipher3")
        sys.exit(1)

    db = Path(db_path)
    if not db.exists():
        print(f"ERROR: Database not found: {db}")
        sys.exit(1)

    backup = db.with_suffix(".db.unencrypted-backup")
    encrypted = db.with_suffix(".db.encrypted-new")

    print(f"Source:  {db}")
    print(f"Backup:  {backup}")
    print(f"Output:  {encrypted}")

    # Step 1 — back up original
    shutil.copy2(str(db), str(backup))
    print(f"[1/4] Backup created: {backup}")

    # Step 2 — open plaintext DB with SQLCipher (no key = plaintext mode)
    conn = sqlcipher.connect(str(db))
    conn.execute("PRAGMA key=''")  # empty key = treat as plaintext
    conn.execute(f"PRAGMA cipher_plaintext_header_size=0")

    # Step 3 — attach encrypted destination and export
    conn.execute(f"ATTACH DATABASE '{encrypted}' AS encrypted KEY '{key}'")
    conn.execute("SELECT sqlcipher_export('encrypted')")
    conn.execute("DETACH DATABASE encrypted")
    conn.close()
    print(f"[2/4] Encrypted copy created: {encrypted}")

    # Step 4 — verify encrypted DB opens correctly
    try:
        vconn = sqlcipher.connect(str(encrypted))
        vconn.execute(f"PRAGMA key='{key}'")
        tables = vconn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        vconn.close()
        print(f"[3/4] Verification: {tables} tables readable with provided key ✓")
    except Exception as e:
        print(f"ERROR: Verification failed — {e}")
        encrypted.unlink(missing_ok=True)
        sys.exit(1)

    # Step 5 — replace original
    shutil.move(str(encrypted), str(db))
    print(f"[4/4] Original replaced with encrypted database ✓")
    print()
    print("Migration complete. Add to config.yaml:")
    print("  security:")
    print("    db_encryption: true")
    print(f"    db_encryption_key_env: BLACKSITE_DB_KEY")
    print()
    print(f"Set environment variable: export BLACKSITE_DB_KEY='{key}'")
    print("Or add to the systemd service unit: Environment=BLACKSITE_DB_KEY=<key>")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate BLACKSITE DB to SQLCipher encryption")
    parser.add_argument("--db", default="data/blacksite.db")
    parser.add_argument("--key-env", default="BLACKSITE_DB_KEY",
                        help="Environment variable containing the encryption key")
    args = parser.parse_args()

    key = os.environ.get(args.key_env, "")
    if not key:
        key = secrets.token_hex(32)
        print(f"No key found in ${args.key_env}. Generated new key:")
        print(f"  {key}")
        print("Save this key — it cannot be recovered if lost.")
        print()

    migrate(args.db, key)
