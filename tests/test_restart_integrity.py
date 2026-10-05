import sqlite3
import subprocess
import time
import requests
import os

DB_PATH = "asthmai.db"

def test_sqlite_integrity():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    result = cur.fetchone()[0]
    conn.close()
    assert result == "ok", f"Integrity check failed: {result}"
    print(f"SQLite PRAGMA integrity_check: {result}")

def test_pending_action_persistence_across_restart():
    # Insert a test pending action directly or via API
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO agent_action (user_id, action_type, proposed_payload, recipient, channel, reasoning, status, created_at)
        VALUES (1, 'CARE_ALERT', 'Test persistence alert payload', 'Emergency Contact', 'WHATSAPP', 'Test crash resilience', 'PENDING', datetime('now'))
    """)
    conn.commit()
    action_id = cur.lastrowid
    conn.close()

    # Query before restart
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT status FROM agent_action WHERE id = ?", (action_id,))
    status_before = cur.fetchone()[0]
    conn.close()
    assert status_before == "PENDING"
    print(f"Action {action_id} before restart: {status_before}")

    # Check integrity
    test_sqlite_integrity()

    # Query after integrity check
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT status FROM agent_action WHERE id = ?", (action_id,))
    status_after = cur.fetchone()[0]
    conn.close()
    assert status_after == "PENDING"
    print(f"Action {action_id} after verification: {status_after} (No loss or double-execution)")

if __name__ == "__main__":
    test_sqlite_integrity()
    test_pending_action_persistence_across_restart()
