"""Best-effort Last Known Good API snapshot storage.

The snapshot table is intentionally optional.  A deployment can roll out the
application before the table migration is applied; reads and writes then
degrade to the in-process cache without breaking the request path.
"""

from __future__ import annotations

import json
from datetime import datetime
from time import time

import pymysql

from database.mysql import get_conn


SNAPSHOT_TABLE = "api_snapshots"
_snapshot_unavailable = False


def _json_payload(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def _parse_payload(value):
    try:
        payload = json.loads(value or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _row_meta(row):
    updated = row.get("updated_at") if row else None
    if isinstance(updated, datetime):
        age = max(0.0, time() - updated.timestamp())
        updated_text = updated.isoformat()
    else:
        age = None
        updated_text = str(updated) if updated else None
    return {
        "freshness": row.get("status") if row else "degraded",
        "updated_at": updated_text,
        "age_seconds": round(age, 3) if age is not None else None,
        "refreshing": False,
    }


def load_snapshot(snapshot_key):
    """Return ``(payload, meta)`` or ``(None, None)`` when unavailable."""

    global _snapshot_unavailable
    if _snapshot_unavailable:
        return None, None
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """
            SELECT snapshot_key,payload_json,updated_at,source_updated_at,status
            FROM api_snapshots
            WHERE snapshot_key=%s
            LIMIT 1
            """,
            (str(snapshot_key),),
        )
        row = cursor.fetchone()
        if not row:
            return None, None
        payload = _parse_payload(row.get("payload_json"))
        if payload is None:
            return None, None
        return payload, _row_meta(row)
    except Exception:
        _snapshot_unavailable = True
        return None, None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def save_snapshot(snapshot_key, payload, status="fresh", source_updated_at=None):
    """Persist a successful response when the optional table is available."""

    global _snapshot_unavailable
    if _snapshot_unavailable or not isinstance(payload, dict):
        return False
    conn = cursor = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO api_snapshots
                (snapshot_key,payload_json,updated_at,source_updated_at,status)
            VALUES (%s,%s,NOW(),%s,%s)
            ON DUPLICATE KEY UPDATE
                payload_json=VALUES(payload_json),
                updated_at=VALUES(updated_at),
                source_updated_at=VALUES(source_updated_at),
                status=VALUES(status)
            """,
            (
                str(snapshot_key),
                _json_payload(payload),
                source_updated_at,
                str(status or "fresh"),
            ),
        )
        conn.commit()
        return True
    except Exception:
        _snapshot_unavailable = True
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def attach_meta(payload, *, freshness="fresh", updated_at=None, age_seconds=None,
                refreshing=False):
    """Add compatibility metadata without changing the existing data shape."""

    result = dict(payload or {})
    result["meta"] = {
        "freshness": freshness,
        "updated_at": updated_at,
        "age_seconds": age_seconds,
        "refreshing": bool(refreshing),
    }
    return result
