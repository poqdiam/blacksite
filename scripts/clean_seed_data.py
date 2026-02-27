#!/usr/bin/env python3
"""
clean_seed_data.py — Alias for: python scripts/seed_test_data.py --clean

Removes all [SEED] prefixed records from the BLACKSITE database.
No production data is touched.

Usage:
    python scripts/clean_seed_data.py
    python scripts/clean_seed_data.py --db /path/to/other.db
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_SCRIPT = os.path.join(SCRIPT_DIR, "seed_test_data.py")

args = [sys.executable, SEED_SCRIPT, "--clean"] + sys.argv[1:]
sys.exit(subprocess.call(args))
