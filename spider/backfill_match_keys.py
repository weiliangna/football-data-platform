"""One-off legacy match_key repair, intentionally separate from statistics."""

from __future__ import annotations

import os
import sys

import pymysql

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common.match_utils import build_match_key
from database.mysql import get_conn


def backfill_match_keys(cursor):
    """Repair only missing keys; existing keys and result data are untouched."""

    cursor.execute("SELECT id,match_name FROM order_matches WHERE match_key IS NULL OR match_key=''" )
    for row in cursor.fetchall():
        cursor.execute(
            "UPDATE order_matches SET match_key=%s WHERE id=%s",
            (build_match_key(match_name=row.get("match_name")), row["id"]),
        )

    cursor.execute(
        "SELECT id,match_name,home_team,away_team FROM match_results WHERE match_key IS NULL OR match_key=''"
    )
    for row in cursor.fetchall():
        cursor.execute(
            "UPDATE match_results SET match_key=%s WHERE id=%s",
            (
                build_match_key(
                    home_team=row.get("home_team"),
                    away_team=row.get("away_team"),
                    match_name=row.get("match_name"),
                ),
                row["id"],
            ),
        )


def main():
    conn = get_conn()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        backfill_match_keys(cursor)
        conn.commit()
        print("match_key backfill complete")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
