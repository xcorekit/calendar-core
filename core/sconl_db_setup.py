#!/usr/bin/env python3
# sconl_db_setup.py
# Creates ~/.local/share/sconl/sconl.db with full schema + migrates TSV data.
# Safe to re-run — uses CREATE TABLE IF NOT EXISTS + INSERT OR IGNORE.
#
# Usage:
#   python3 sconl_db_setup.py              # create schema only
#   python3 sconl_db_setup.py --migrate    # schema + migrate TSVs
#   python3 sconl_db_setup.py --verify     # print row counts per table
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
import csv
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

HOME        = Path.home()
DB_PATH     = HOME / ".local/share/sconl/sconl.db"
DATA_DIR    = HOME / ".local/share/sconl/data"   # unified compat symlink dir
TENANT_FILE = HOME / ".config/sconl/tenant.toml"
TENANT_ID   = ""  # auto-read from tenant.toml below

# ── Helpers ───────────────────────────────────────────────────────────────────

def now():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def read_tenant_id():
    """Read tenant ID from tenant.toml without requiring tomllib."""
    if not TENANT_FILE.exists():
        return "local"
    for line in TENANT_FILE.read_text().splitlines():
        if line.strip().startswith("id"):
            parts = line.split("=", 1)
            if len(parts) == 2:
                return parts[1].strip().strip('"').strip("'")
    return "local"


def load_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def header(msg):
    print(f"\n  {msg}")
    print(f"  {'─' * len(msg)}")


# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = """
-- ── Scope ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scope_inbox (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '',
    body        TEXT DEFAULT '',
    status      TEXT DEFAULT 'new',
    source      TEXT DEFAULT 'isconl',
    captured_at TEXT,
    eq_year     INTEGER,
    eq_cycle    INTEGER,
    eq_day      INTEGER,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS scope_tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '',
    status      TEXT DEFAULT 'backlog',
    priority    TEXT DEFAULT 'med',
    project_id  TEXT DEFAULT '',
    carry_fwd   INTEGER DEFAULT 0,
    due_date    TEXT DEFAULT '-',
    energy      TEXT DEFAULT 'medium',
    created_at  TEXT,
    updated_at  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS scope_goals (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '',
    kpi         TEXT DEFAULT '',
    target      REAL DEFAULT 1,
    current     REAL DEFAULT 0,
    level       TEXT DEFAULT 'cycle',
    status      TEXT DEFAULT 'active',
    weight      INTEGER DEFAULT 1,
    created_at  TEXT,
    updated_at  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS scope_projects (
    id          TEXT PRIMARY KEY,
    goal_id     TEXT DEFAULT '',
    title       TEXT NOT NULL DEFAULT '',
    status      TEXT DEFAULT 'active',
    dod         TEXT DEFAULT '',
    created_at  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS scope_cycles (
    id          TEXT PRIMARY KEY,
    eq_year     INTEGER,
    cycle_num   INTEGER,
    theme       TEXT,
    start_date  TEXT,
    end_date    TEXT,
    status      TEXT DEFAULT 'active',
    obj1        TEXT DEFAULT '',
    obj2        TEXT DEFAULT '',
    obj3        TEXT DEFAULT '',
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS scope_reflections (
    date        TEXT NOT NULL,
    mood        TEXT DEFAULT '',
    energy      INTEGER DEFAULT 0,
    has_content INTEGER DEFAULT 0,
    tenant_id   TEXT NOT NULL DEFAULT 'local',
    PRIMARY KEY (date, tenant_id)
);

-- ── Space ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS space_spaces (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL DEFAULT '',
    type          TEXT DEFAULT '',
    status        TEXT DEFAULT 'active',
    health        INTEGER DEFAULT 5,
    description   TEXT DEFAULT '',
    emoji         TEXT DEFAULT '',
    created_at    TEXT,
    last_reviewed TEXT,
    tenant_id     TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS space_projects (
    id          TEXT PRIMARY KEY,
    space_id    TEXT DEFAULT '',
    title       TEXT NOT NULL DEFAULT '',
    status      TEXT DEFAULT 'active',
    created_at  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS space_contacts (
    id           TEXT PRIMARY KEY,
    space_id     TEXT DEFAULT '',
    name         TEXT NOT NULL DEFAULT '',
    role         TEXT DEFAULT '',
    last_contact TEXT DEFAULT '-',
    created_at   TEXT,
    tenant_id    TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS space_kpi_defs (
    id        TEXT PRIMARY KEY,
    space_id  TEXT DEFAULT '',
    name      TEXT NOT NULL DEFAULT '',
    unit      TEXT DEFAULT '',
    target    REAL DEFAULT 0,
    tenant_id TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS space_kpi_log (
    id          TEXT PRIMARY KEY,
    kpi_id      TEXT DEFAULT '',
    space_id    TEXT DEFAULT '',
    name        TEXT DEFAULT '',
    value       REAL DEFAULT 0,
    unit        TEXT DEFAULT '',
    measured_at TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS space_events (
    id          TEXT PRIMARY KEY,
    space_id    TEXT DEFAULT '',
    type        TEXT DEFAULT '',
    title       TEXT NOT NULL DEFAULT '',
    event_date  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

-- ── Spark ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS spark_ideas (
    id          TEXT PRIMARY KEY,
    stage       TEXT DEFAULT 'captured',
    type        TEXT DEFAULT 'general',
    body        TEXT DEFAULT '',
    title       TEXT NOT NULL DEFAULT '',
    created_at  TEXT,
    updated_at  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS spark_learning (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '',
    type        TEXT DEFAULT 'book',
    status      TEXT DEFAULT 'backlog',
    progress    INTEGER DEFAULT 0,
    author      TEXT DEFAULT '',
    created_at  TEXT,
    updated_at  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS spark_dia (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL DEFAULT '',
    role         TEXT DEFAULT '',
    type         TEXT DEFAULT '',
    depth        TEXT DEFAULT '',
    last_contact TEXT DEFAULT '-',
    trajectory   TEXT DEFAULT '',
    created_at   TEXT,
    tenant_id    TEXT NOT NULL DEFAULT 'local'
);

-- ── Event bus ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sconl_events (
    id          TEXT PRIMARY KEY,
    source      TEXT DEFAULT 'isconl',
    type        TEXT NOT NULL DEFAULT '',
    payload     TEXT DEFAULT '{}',
    created_at  TEXT,
    consumed_by TEXT DEFAULT '',
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

-- ── Finance ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS finance_accounts (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    type        TEXT DEFAULT 'bank',
    currency    TEXT DEFAULT 'KES',
    balance     REAL DEFAULT 0,
    created_at  TEXT,
    updated_at  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS finance_transactions (
    id          TEXT PRIMARY KEY,
    account_id  TEXT NOT NULL DEFAULT '',
    date        TEXT,
    amount      REAL DEFAULT 0,
    type        TEXT DEFAULT 'expense',
    category    TEXT DEFAULT '',
    note        TEXT DEFAULT '',
    created_at  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS finance_budgets (
    id          TEXT PRIMARY KEY,
    category    TEXT NOT NULL DEFAULT '',
    amount      REAL DEFAULT 0,
    period      TEXT DEFAULT 'monthly',
    created_at  TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local'
);

-- ── Metadata ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sconl_meta (
    key         TEXT NOT NULL,
    value       TEXT,
    tenant_id   TEXT NOT NULL DEFAULT 'local',
    updated_at  TEXT,
    PRIMARY KEY (key, tenant_id)
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_inbox_status    ON scope_inbox(status, tenant_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status    ON scope_tasks(status, tenant_id);
CREATE INDEX IF NOT EXISTS idx_goals_status    ON scope_goals(status, tenant_id);
CREATE INDEX IF NOT EXISTS idx_spaces_status   ON space_spaces(status, tenant_id);
CREATE INDEX IF NOT EXISTS idx_ideas_stage     ON spark_ideas(stage, tenant_id);
CREATE INDEX IF NOT EXISTS idx_events_type     ON sconl_events(type, tenant_id);
CREATE INDEX IF NOT EXISTS idx_events_consumed ON sconl_events(consumed_by, tenant_id);
CREATE INDEX IF NOT EXISTS idx_finance_account ON finance_transactions(account_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_finance_date    ON finance_transactions(date, tenant_id);
"""

# ── Migration ─────────────────────────────────────────────────────────────────

def migrate_tsv(conn, tenant_id):
    """Migrate flat TSV files into SQLite. Idempotent (INSERT OR IGNORE)."""
    total = 0

    def ins(table, row):
        nonlocal total
        keys = list(row.keys())
        vals = [row[k] if row[k] not in ('', '-') else None for k in keys]
        placeholders = ",".join(["?"] * len(keys))
        try:
            conn.execute(
                f"INSERT OR IGNORE INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
                vals
            )
            total += 1
        except Exception as e:
            print(f"    ! {table} row error: {e}")

    # scope_inbox
    for r in load_tsv(DATA_DIR / "scope/inbox.tsv"):
        ins("scope_inbox", {
            "id": r.get("ID"), "title": r.get("TITLE",""),
            "body": r.get("BODY",""), "status": r.get("STATUS","new"),
            "source": r.get("SOURCE","isconl"), "captured_at": r.get("CAPTURED_AT"),
            "eq_year": r.get("EQ_YEAR"), "eq_cycle": r.get("EQ_CYCLE"),
            "eq_day": r.get("EQ_DAY"), "tenant_id": tenant_id,
        })

    # scope_tasks
    for r in load_tsv(DATA_DIR / "scope/tasks.tsv"):
        ins("scope_tasks", {
            "id": r.get("ID"), "title": r.get("TITLE",""),
            "status": r.get("STATUS","backlog"), "priority": r.get("PRIORITY","med"),
            "project_id": r.get("PROJECT_ID",""), "carry_fwd": r.get("CARRY_FWD",0),
            "due_date": r.get("DUE_DATE","-"), "energy": r.get("ENERGY","medium"),
            "created_at": r.get("CREATED_AT"), "updated_at": r.get("UPDATED_AT"),
            "tenant_id": tenant_id,
        })

    # scope_goals
    for r in load_tsv(DATA_DIR / "scope/goals.tsv"):
        ins("scope_goals", {
            "id": r.get("ID"), "title": r.get("TITLE",""),
            "kpi": r.get("KPI",""), "target": r.get("TARGET",1),
            "current": r.get("CURRENT",0), "level": r.get("LEVEL","cycle"),
            "status": r.get("STATUS","active"), "weight": r.get("WEIGHT",1),
            "created_at": r.get("CREATED_AT"), "updated_at": r.get("UPDATED_AT"),
            "tenant_id": tenant_id,
        })

    # scope_reflections
    for r in load_tsv(DATA_DIR / "scope/reflections.tsv"):
        ins("scope_reflections", {
            "date": r.get("DATE"), "mood": r.get("MOOD",""),
            "energy": r.get("ENERGY",0), "has_content": r.get("HAS_CONTENT",0),
            "tenant_id": tenant_id,
        })

    # space_spaces
    for r in load_tsv(DATA_DIR / "space/spaces.tsv"):
        ins("space_spaces", {
            "id": r.get("ID"), "name": r.get("NAME",""),
            "type": r.get("TYPE",""), "status": r.get("STATUS","active"),
            "health": r.get("HEALTH",5), "description": r.get("DESCRIPTION",""),
            "emoji": r.get("EMOJI",""), "created_at": r.get("CREATED_AT"),
            "last_reviewed": r.get("LAST_REVIEWED"), "tenant_id": tenant_id,
        })

    # space_contacts
    for r in load_tsv(DATA_DIR / "space/contacts.tsv"):
        ins("space_contacts", {
            "id": r.get("ID"), "space_id": r.get("SPACE_ID",""),
            "name": r.get("NAME",""), "role": r.get("ROLE",""),
            "last_contact": r.get("LAST_CONTACT","-"),
            "created_at": r.get("CREATED_AT"), "tenant_id": tenant_id,
        })

    # space_kpi_defs
    for r in load_tsv(DATA_DIR / "space/kpi_defs.tsv"):
        ins("space_kpi_defs", {
            "id": r.get("ID"), "space_id": r.get("SPACE_ID",""),
            "name": r.get("NAME",""), "unit": r.get("UNIT",""),
            "target": r.get("TARGET",0), "tenant_id": tenant_id,
        })

    # space_kpi_log
    for r in load_tsv(DATA_DIR / "space/kpi_log.tsv"):
        ins("space_kpi_log", {
            "id": r.get("ID"), "kpi_id": r.get("KPI_ID",""),
            "space_id": r.get("SPACE_ID",""), "name": r.get("NAME",""),
            "value": r.get("VALUE",0), "unit": r.get("UNIT",""),
            "measured_at": r.get("MEASURED_AT"), "tenant_id": tenant_id,
        })

    # space_events
    for r in load_tsv(DATA_DIR / "space/events.tsv"):
        ins("space_events", {
            "id": r.get("ID"), "space_id": r.get("SPACE_ID",""),
            "type": r.get("TYPE",""), "title": r.get("TITLE",""),
            "event_date": r.get("EVENT_DATE"), "tenant_id": tenant_id,
        })

    # spark_ideas
    for r in load_tsv(DATA_DIR / "spark/ideas.tsv"):
        ins("spark_ideas", {
            "id": r.get("ID"), "stage": r.get("STAGE","captured"),
            "type": r.get("TYPE","general"), "body": r.get("BODY",""),
            "title": r.get("TITLE",""), "created_at": r.get("CREATED_AT"),
            "updated_at": r.get("UPDATED_AT"), "tenant_id": tenant_id,
        })

    # spark_learning
    for r in load_tsv(DATA_DIR / "spark/learning.tsv"):
        ins("spark_learning", {
            "id": r.get("ID"), "title": r.get("TITLE",""),
            "type": r.get("TYPE","book"), "status": r.get("STATUS","backlog"),
            "progress": r.get("PROGRESS",0), "author": r.get("AUTHOR",""),
            "created_at": r.get("CREATED_AT"), "updated_at": r.get("UPDATED_AT"),
            "tenant_id": tenant_id,
        })

    # spark_dia
    for r in load_tsv(DATA_DIR / "spark/dia.tsv"):
        ins("spark_dia", {
            "id": r.get("ID"), "name": r.get("NAME",""),
            "role": r.get("ROLE",""), "type": r.get("TYPE",""),
            "depth": r.get("DEPTH",""), "last_contact": r.get("LAST_CONTACT","-"),
            "trajectory": r.get("TRAJECTORY",""),
            "created_at": r.get("CREATED_AT"), "tenant_id": tenant_id,
        })

    # sconl_events
    for r in load_tsv(DATA_DIR / "scope/../events.tsv") + \
             load_tsv(HOME / "_/engineer-systems/Systems/iSconl/hub/core/events.tsv"):
        if not r.get("ID"): continue
        ins("sconl_events", {
            "id": r.get("ID"), "source": r.get("SOURCE","isconl"),
            "type": r.get("TYPE",""), "payload": r.get("PAYLOAD","{}"),
            "created_at": r.get("CREATED_AT"), "consumed_by": r.get("CONSUMED_BY",""),
            "tenant_id": tenant_id,
        })

    conn.commit()
    return total


# ── Verify ────────────────────────────────────────────────────────────────────

def verify(conn, tenant_id):
    tables = [
        "scope_inbox", "scope_tasks", "scope_goals", "scope_reflections",
        "scope_projects", "scope_cycles",
        "space_spaces", "space_projects", "space_contacts",
        "space_kpi_defs", "space_kpi_log", "space_events",
        "spark_ideas", "spark_learning", "spark_dia",
        "sconl_events",
        "finance_accounts", "finance_transactions", "finance_budgets",
        "sconl_meta",
    ]
    header("Table row counts")
    for t in tables:
        try:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {t} WHERE tenant_id=?", (tenant_id,)
            ).fetchone()[0]
            marker = "✓" if count >= 0 else "!"
            print(f"    {marker}  {t:<30} {count} rows")
        except Exception as e:
            print(f"    !  {t:<30} ERROR: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="sconl SQLite database setup")
    p.add_argument("--migrate", action="store_true", help="Migrate TSV data into SQLite")
    p.add_argument("--verify",  action="store_true", help="Print row counts and exit")
    args = p.parse_args()

    global TENANT_ID
    TENANT_ID = read_tenant_id()

    print(f"\n  sconl db setup")
    print(f"  ──────────────")
    print(f"  db:     {DB_PATH}")
    print(f"  tenant: {TENANT_ID}")

    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")    # safe for concurrent reads (Flutter app)
    conn.execute("PRAGMA foreign_keys=ON")

    if args.verify:
        verify(conn, TENANT_ID)
        conn.close()
        return

    # Create schema
    header("Creating schema")
    conn.executescript(SCHEMA)
    conn.commit()
    print("    ✓  All tables created (or already exist)")

    # Write meta
    conn.execute(
        "INSERT OR REPLACE INTO sconl_meta (key, value, tenant_id, updated_at) VALUES (?,?,?,?)",
        ("schema_version", "1.0.0", TENANT_ID, now())
    )
    conn.execute(
        "INSERT OR REPLACE INTO sconl_meta (key, value, tenant_id, updated_at) VALUES (?,?,?,?)",
        ("created_at", now(), TENANT_ID, now())
    )
    conn.commit()

    if args.migrate:
        header("Migrating TSV data")
        total = migrate_tsv(conn, TENANT_ID)
        print(f"    ✓  {total} rows migrated")

    # Always verify after setup
    verify(conn, TENANT_ID)

    size = DB_PATH.stat().st_size
    print(f"\n  ✓  Done — {DB_PATH}")
    print(f"     Size: {size:,} bytes\n")
    conn.close()


if __name__ == "__main__":
    main()
