"""
Alembic migration environment for BLACKSITE.

SQLCipher integration note:
  `app.models` patches sys.modules["sqlite3"] → pysqlcipher3.dbapi2 at import time
  when BLACKSITE_DB_KEY is set.  SQLAlchemy's pysqlite dialect calls
  `from sqlite3 import dbapi2` during engine initialization, which fails against
  the pysqlcipher3 module.

  Fix: capture real sqlite3 *before* importing app.models, restore it while
  SQLAlchemy builds the dialect + engine, then re-apply the patch.  Actual
  connections still go through pysqlcipher3 via our creator= function.

Usage:
  BLACKSITE_DB_KEY=<key> alembic current
  BLACKSITE_DB_KEY=<key> alembic upgrade head
  BLACKSITE_DB_KEY=<key> alembic stamp head          # mark existing DB as current
  BLACKSITE_DB_KEY=<key> alembic revision --autogenerate -m "describe change"
  BLACKSITE_DB_KEY=<key> alembic downgrade -1
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context

# ── Project root on sys.path ──────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# ── Capture real sqlite3 BEFORE app.models patches sys.modules["sqlite3"] ────
_real_sqlite3 = sys.modules.get("sqlite3")
if _real_sqlite3 is None:
    import sqlite3 as _real_sqlite3  # type: ignore[assignment]
    _real_sqlite3 = sys.modules["sqlite3"]

# ── Import models — triggers pysqlcipher3 patch if BLACKSITE_DB_KEY is set ───
from app.models import Base  # noqa: E402

_patched_sqlite3 = sys.modules.get("sqlite3")  # pysqlcipher3 module, or real sqlite3

# ── Read config.yaml for db.path ─────────────────────────────────────────────
import yaml as _yaml

try:
    with open(_PROJECT_ROOT / "config.yaml") as _f:
        _APP_CONFIG = _yaml.safe_load(_f) or {}
except FileNotFoundError:
    _APP_CONFIG = {}

_DB_PATH_REL = _APP_CONFIG.get("db", {}).get("path", "blacksite.db")
_DB_PATH = str(_PROJECT_ROOT / _DB_PATH_REL) if not Path(_DB_PATH_REL).is_absolute() else _DB_PATH_REL
_DB_KEY  = os.environ.get("BLACKSITE_DB_KEY", "")

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _make_connection():
    """
    Raw connection factory.  Opens the SQLite/SQLCipher DB directly via
    pysqlcipher3 when a key is set, or stdlib sqlite3 when not.
    Applies PRAGMA key + standard performance pragmas.
    """
    if _DB_KEY:
        import pysqlcipher3.dbapi2 as _sc

        class _Shim:
            """python 3.8+ create_function compat shim (same as in app/models.py)."""
            __slots__ = ("_c",)
            def __init__(self, c):       object.__setattr__(self, "_c", c)
            def create_function(self, n, a, f, deterministic=False):
                                         object.__getattribute__(self, "_c").create_function(n, a, f)
            def __getattr__(self, n):    return getattr(object.__getattribute__(self, "_c"), n)
            def __setattr__(self, n, v):
                if n == "_c": object.__setattr__(self, n, v)
                else:         setattr(object.__getattribute__(self, "_c"), n, v)

        raw  = _sc.connect(_DB_PATH)
        conn = _Shim(raw)
        conn.execute(f"PRAGMA key='{_DB_KEY}'")
    else:
        import sqlite3 as _sq3
        conn = _sq3.connect(_DB_PATH)

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-20000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _get_engine():
    from sqlalchemy import create_engine, pool

    if db_url := os.environ.get("DATABASE_URL"):
        return create_engine(
            db_url.replace("+asyncpg", "").replace("+aiosqlite", ""),
            poolclass=pool.NullPool,
        )

    # Temporarily restore real sqlite3 so SQLAlchemy's pysqlite dialect can
    # call `from sqlite3 import dbapi2` without hitting the pysqlcipher3 patch.
    sys.modules["sqlite3"] = _real_sqlite3
    try:
        engine = create_engine(
            "sqlite://",
            creator=_make_connection,
            poolclass=pool.StaticPool,
        )
    finally:
        # Re-apply the pysqlcipher3 patch for the rest of the process.
        sys.modules["sqlite3"] = _patched_sqlite3

    return engine


def run_migrations_offline() -> None:
    url = os.environ.get("DATABASE_URL", f"sqlite:///{_DB_PATH}").replace("+asyncpg", "").replace("+aiosqlite", "")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = _get_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,   # Required for SQLite ALTER COLUMN (copy-rename)
            compare_type=True,      # Detect column type changes in autogenerate
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
