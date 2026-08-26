import json
from datetime import date, datetime
from pathlib import Path

from common.match_identity import (
    build_match_identity,
    load_team_aliases,
    supports_identity_v2,
    table_columns,
)


PENDING_RESULT = "待开奖"
SETTLED_RESULTS = {"赢", "输"}


class PlatformOrderCollision(RuntimeError):
    pass


def as_float(value, default=0.0):
    if value in (None, "", "-", "--"):
        return default

    try:
        return float(str(value).replace("%", "").strip())
    except (TypeError, ValueError):
        return default


def as_int(value, default=0):
    if value in (None, "", "-", "--"):
        return default

    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def parse_datetime(value):
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    text = str(value).strip()

    if text.isdigit() and len(text) == 14:
        try:
            return datetime.strptime(text, "%Y%m%d%H%M%S")
        except ValueError:
            return None

    for format_text in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y%m%d",
    ):
        try:
            return datetime.strptime(text, format_text)
        except ValueError:
            continue

    return None


def parse_epoch_milliseconds(value):
    if value in (None, ""):
        return None

    try:
        return datetime.fromtimestamp(int(value) / 1000)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def load_json_file(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8-sig")
    )


def load_detail_map(path):
    raw = load_json_file(path)

    if not isinstance(raw, dict):
        raise ValueError("详情 JSON 必须是订单 ID 到响应对象的映射")

    return {
        str(key): value
        for key, value in raw.items()
    }


def preview_repository():
    class PreviewRepository:
        def __init__(self):
            self.records = {}

        def save(self, record):
            key = (
                record.get("platform_id"),
                record.get("platform_order_id"),
            )
            inserted_order = key not in self.records
            self.records[key] = record
            return {
                "order_id": None,
                "inserted_order": inserted_order,
                "inserted_legs": len(record.get("legs") or []),
                "updated_legs": 0,
                "saved_results": 0,
                "skipped_results": len(
                    record.get("match_results") or []
                ),
            }

    return PreviewRepository()


def _default_connection_factory():
    from database.mysql import get_conn

    return get_conn()


def _row_value(row, key, index=0):
    if isinstance(row, dict):
        return row.get(key)
    if isinstance(row, (tuple, list)) and len(row) > index:
        return row[index]
    return None


class DatabaseRepository:
    def __init__(self, connection_factory=None):
        self.connection_factory = (
            connection_factory or _default_connection_factory
        )

    def save(self, record):
        conn = self.connection_factory()
        cursor = conn.cursor()

        try:
            alias_map = load_team_aliases(cursor)
            order_match_columns = table_columns(
                cursor,
                "order_matches",
            )
            match_result_columns = table_columns(
                cursor,
                "match_results",
            )
            order_match_identity_v2 = supports_identity_v2(
                order_match_columns
            )
            match_result_identity_v2 = supports_identity_v2(
                match_result_columns
            )

            self._save_user(cursor, record)
            local_order_id, inserted_order = self._save_order(
                cursor,
                record,
            )
            leg_stats = self._save_legs(
                cursor,
                local_order_id,
                record,
                alias_map,
                order_match_identity_v2,
            )
            result_stats = self._save_match_results(
                cursor,
                record,
                alias_map,
                match_result_identity_v2,
            )
            conn.commit()
            return {
                "order_id": local_order_id,
                "inserted_order": inserted_order,
                **leg_stats,
                **result_stats,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def _save_user(self, cursor, record):
        user = record.get("user") or {}
        platform_id = int(record["platform_id"])
        user_id = user.get("user_id")
        nickname = str(user.get("nickname") or "").strip()

        if user_id in (None, "", 0):
            raise ValueError("订单缺少可验证的平台用户 ID")

        cursor.execute(
            """
            INSERT INTO users
            (platform_id,platform_user_id,username,nickname,total_orders)
            VALUES(%s,%s,%s,%s,0)
            ON DUPLICATE KEY UPDATE
                username=VALUES(username),
                nickname=CASE
                    WHEN VALUES(nickname)<>'' THEN VALUES(nickname)
                    ELSE nickname
                END
            """,
            (
                platform_id,
                user_id,
                str(user_id),
                nickname,
            ),
        )

        avatar_url = str(user.get("avatar_url") or "").strip()

        if not avatar_url:
            return

        cursor.execute(
            """
            INSERT INTO user_profiles_ext
            (platform_id,user_id,nickname,avatar_url,source)
            VALUES(%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                nickname=CASE
                    WHEN VALUES(nickname)<>'' THEN VALUES(nickname)
                    ELSE nickname
                END,
                avatar_url=CASE
                    WHEN VALUES(avatar_url)<>'' THEN VALUES(avatar_url)
                    ELSE avatar_url
                END,
                source=VALUES(source),
                updated_time=NOW()
            """,
            (
                platform_id,
                user_id,
                nickname,
                avatar_url,
                str(user.get("avatar_source") or "platform_response"),
            ),
        )

    def _save_order(self, cursor, record):
        order = record.get("order") or {}
        platform_id = int(record["platform_id"])
        platform_order_id = str(
            order.get("platform_order_id") or ""
        ).strip()

        if not platform_order_id:
            raise ValueError("订单缺少可验证的平台订单 ID")

        cursor.execute(
            """
            SELECT id,platform_id,result,profit,platform_bonus,
                   commission_total,settlement_status,settled_time
            FROM orders
            WHERE platform_order_id=%s
            LIMIT 1
            FOR UPDATE
            """,
            (platform_order_id,),
        )
        existing = cursor.fetchone()

        if existing:
            existing_platform = as_int(
                _row_value(existing, "platform_id", 1),
                0,
            )

            if existing_platform != platform_id:
                raise PlatformOrderCollision(
                    "platform_order_id 已被其他平台占用；"
                    "当前 schema 的全局唯一键不允许安全写入"
                )

        incoming_result = str(
            order.get("result") or PENDING_RESULT
        ).strip()
        incoming_settled = incoming_result in SETTLED_RESULTS

        if existing and not incoming_settled:
            result = _row_value(existing, "result", 2) or PENDING_RESULT
            profit = _row_value(existing, "profit", 3) or 0
            platform_bonus = (
                _row_value(existing, "platform_bonus", 4) or 0
            )
            commission_total = (
                _row_value(existing, "commission_total", 5) or 0
            )
            settlement_status = (
                _row_value(existing, "settlement_status", 6) or ""
            )
            settled_time = _row_value(existing, "settled_time", 7)
        else:
            result = incoming_result
            profit = as_float(order.get("profit"), 0)
            platform_bonus = as_float(
                order.get("platform_bonus"),
                0,
            )
            commission_total = as_float(
                order.get("commission_total"),
                0,
            )
            settlement_status = str(
                order.get("settlement_status") or ""
            )
            settled_time = order.get("settled_time")

        values = (
            order.get("user_id"),
            str(order.get("nickname") or ""),
            order.get("match_id"),
            order.get("match_name"),
            order.get("league"),
            order.get("play_type"),
            order.get("pass_summary"),
            order.get("selection"),
            order.get("bet_code"),
            order.get("odds_text"),
            as_float(order.get("stake"), 0),
            result,
            profit,
            order.get("publish_time"),
            order.get("declaration"),
            as_float(order.get("hit_rate"), 0),
            as_float(order.get("profitability"), 0),
            as_int(order.get("follow_num"), 0),
            as_int(order.get("handicap"), 0),
            platform_bonus,
            commission_total,
            settlement_status,
            settled_time,
            as_float(order.get("expected_bonus"), 0),
        )

        if existing:
            local_order_id = as_int(
                _row_value(existing, "id", 0),
                0,
            )
            cursor.execute(
                """
                UPDATE orders SET
                    user_id=%s,nickname=%s,match_id=%s,match_name=%s,
                    league=%s,play_type=%s,pass_summary=%s,
                    selection=%s,bet_code=%s,odds_text=%s,stake=%s,
                    result=%s,profit=%s,publish_time=%s,declaration=%s,
                    hit_rate=%s,profitability=%s,follow_num=%s,
                    handicap=%s,platform_bonus=%s,commission_total=%s,
                    settlement_status=%s,settled_time=%s,
                    expected_bonus=%s
                WHERE id=%s
                """,
                values + (local_order_id,),
            )
            return local_order_id, False

        cursor.execute(
            """
            INSERT INTO orders
            (
                platform_id,user_id,nickname,platform_order_id,
                match_id,match_name,league,play_type,pass_summary,
                selection,bet_code,odds_text,stake,result,profit,
                publish_time,declaration,hit_rate,profitability,
                follow_num,handicap,platform_bonus,commission_total,
                settlement_status,settled_time,expected_bonus
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
            """,
            (
                platform_id,
                order.get("user_id"),
                str(order.get("nickname") or ""),
                platform_order_id,
            ) + values[2:],
        )
        return int(cursor.lastrowid), True

    def _find_leg(
        self,
        cursor,
        order_id,
        leg,
        identity,
        identity_v2,
    ):
        play_type = str(leg.get("play_type") or "")
        handicap = as_int(leg.get("handicap"), 0)
        source_code = identity["source_match_code"]

        if identity_v2 and identity["match_date"] and source_code:
            cursor.execute(
                """
                SELECT id,result,profit
                FROM order_matches
                WHERE order_id=%s AND platform_id=%s
                  AND match_date=%s AND match_code=%s
                  AND play_type=%s AND IFNULL(handicap,0)=%s
                ORDER BY id LIMIT 1 FOR UPDATE
                """,
                (
                    order_id,
                    identity["platform_id"],
                    identity["match_date"],
                    source_code,
                    play_type,
                    handicap,
                ),
            )
            found = cursor.fetchone()
            if found:
                return found

        if identity_v2 and source_code and identity["match_key"]:
            cursor.execute(
                """
                SELECT id,result,profit
                FROM order_matches
                WHERE order_id=%s AND platform_id=%s
                  AND match_code=%s AND match_key=%s
                  AND play_type=%s AND IFNULL(handicap,0)=%s
                ORDER BY id LIMIT 1 FOR UPDATE
                """,
                (
                    order_id,
                    identity["platform_id"],
                    source_code,
                    identity["match_key"],
                    play_type,
                    handicap,
                ),
            )
            found = cursor.fetchone()
            if found:
                return found

        cursor.execute(
            """
            SELECT id,result,profit
            FROM order_matches
            WHERE order_id=%s AND match_name=%s
              AND play_type=%s AND IFNULL(handicap,0)=%s
            ORDER BY id LIMIT 1 FOR UPDATE
            """,
            (
                order_id,
                leg.get("match_name"),
                play_type,
                handicap,
            ),
        )
        return cursor.fetchone()

    def _save_legs(
        self,
        cursor,
        order_id,
        record,
        alias_map,
        identity_v2,
    ):
        inserted = 0
        updated = 0

        for leg in record.get("legs") or []:
            identity = build_match_identity(
                record["platform_id"],
                match_date=leg.get("match_date"),
                source_match_code=(
                    leg.get("source_match_code")
                    or leg.get("match_code")
                ),
                match_name=leg.get("match_name"),
                home_team=leg.get("home_team"),
                away_team=leg.get("away_team"),
                alias_map=alias_map,
            )
            existing = self._find_leg(
                cursor,
                order_id,
                leg,
                identity,
                identity_v2,
            )
            incoming_result = str(
                leg.get("result") or PENDING_RESULT
            )

            if existing and incoming_result == PENDING_RESULT:
                result = _row_value(existing, "result", 1) or PENDING_RESULT
                profit = _row_value(existing, "profit", 2) or 0
            else:
                result = incoming_result
                profit = as_float(leg.get("profit"), 0)

            common_values = (
                identity["source_match_code"],
                leg.get("match_name"),
                identity["match_key"],
                leg.get("league"),
                leg.get("play_type"),
                leg.get("selection"),
                json.dumps(
                    leg.get("option_detail") or [],
                    ensure_ascii=False,
                ),
                as_int(leg.get("handicap"), 0),
                leg.get("deadline_time"),
                result,
                profit,
            )

            if existing:
                local_leg_id = as_int(
                    _row_value(existing, "id", 0),
                    0,
                )
                if identity_v2:
                    cursor.execute(
                        """
                        UPDATE order_matches SET
                            platform_id=%s,match_code=%s,
                            match_name=%s,match_key=%s,match_date=%s,
                            normalized_home=%s,normalized_away=%s,
                            match_identity=%s,identity_quality=%s,
                            league=%s,play_type=%s,selection=%s,
                            option_detail=%s,handicap=%s,
                            deadline_time=%s,result=%s,profit=%s
                        WHERE id=%s
                        """,
                        (
                            identity["platform_id"],
                            common_values[0],
                            common_values[1],
                            common_values[2],
                            identity["match_date"],
                            identity["normalized_home"],
                            identity["normalized_away"],
                            identity["match_identity"],
                            identity["identity_quality"],
                        ) + common_values[3:] + (local_leg_id,),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE order_matches SET
                            match_code=%s,match_name=%s,match_key=%s,
                            league=%s,play_type=%s,selection=%s,
                            option_detail=%s,handicap=%s,
                            deadline_time=%s,result=%s,profit=%s
                        WHERE id=%s
                        """,
                        common_values + (local_leg_id,),
                    )
                updated += 1
                continue

            if identity_v2:
                cursor.execute(
                    """
                    INSERT INTO order_matches
                    (
                        order_id,platform_id,match_code,match_name,
                        match_key,match_date,normalized_home,
                        normalized_away,match_identity,identity_quality,
                        league,play_type,selection,option_detail,handicap,
                        deadline_time,result,profit
                    )
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                     %s,%s,%s,%s)
                    """,
                    (
                        order_id,
                        identity["platform_id"],
                        common_values[0],
                        common_values[1],
                        common_values[2],
                        identity["match_date"],
                        identity["normalized_home"],
                        identity["normalized_away"],
                        identity["match_identity"],
                        identity["identity_quality"],
                    ) + common_values[3:],
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO order_matches
                    (
                        order_id,match_code,match_name,match_key,
                        league,play_type,selection,option_detail,
                        handicap,deadline_time,result,profit
                    )
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (order_id,) + common_values,
                )
            inserted += 1

        return {
            "inserted_legs": inserted,
            "updated_legs": updated,
        }

    def _save_match_results(
        self,
        cursor,
        record,
        alias_map,
        identity_v2,
    ):
        saved = 0
        skipped = 0

        for result in record.get("match_results") or []:
            identity = build_match_identity(
                record["platform_id"],
                match_date=result.get("match_date"),
                source_match_code=(
                    result.get("source_match_code")
                    or result.get("match_code")
                ),
                match_name=result.get("match_name"),
                home_team=result.get("home_team"),
                away_team=result.get("away_team"),
                alias_map=alias_map,
            )

            if (
                not identity_v2
                or not identity["match_date"]
                or not identity["source_match_code"]
            ):
                skipped += 1
                continue

            cursor.execute(
                """
                SELECT id,platform_id
                FROM match_results
                WHERE match_name=%s
                LIMIT 1 FOR UPDATE
                """,
                (result.get("match_name"),),
            )
            name_collision = cursor.fetchone()

            if name_collision and as_int(
                _row_value(name_collision, "platform_id", 1),
                0,
            ) not in (0, int(record["platform_id"])):
                skipped += 1
                continue

            cursor.execute(
                """
                SELECT id
                FROM match_results
                WHERE platform_id=%s AND match_date=%s
                  AND match_code=%s
                ORDER BY id LIMIT 1 FOR UPDATE
                """,
                (
                    record["platform_id"],
                    identity["match_date"],
                    identity["source_match_code"],
                ),
            )
            existing = cursor.fetchone() or name_collision
            values = (
                record["platform_id"],
                identity["match_date"],
                identity["source_match_code"],
                identity["match_key"],
                identity["normalized_home"],
                identity["normalized_away"],
                identity["match_identity"],
                identity["identity_quality"],
                result.get("match_name"),
                result.get("league"),
                identity["home_team"],
                identity["away_team"],
                as_int(result.get("home_score"), 0),
                as_int(result.get("away_score"), 0),
                as_int(result.get("half_home_score"), 0),
                as_int(result.get("half_away_score"), 0),
                "已结束",
                result.get("finished_time"),
                str(result.get("source") or record["platform_name"]),
            )

            if existing:
                cursor.execute(
                    """
                    UPDATE match_results SET
                        platform_id=%s,match_date=%s,match_code=%s,
                        match_key=%s,normalized_home=%s,
                        normalized_away=%s,match_identity=%s,
                        identity_quality=%s,match_name=%s,league=%s,
                        home_team=%s,away_team=%s,home_score=%s,
                        away_score=%s,half_home_score=%s,
                        half_away_score=%s,status=%s,finished_time=%s,
                        source=%s
                    WHERE id=%s
                    """,
                    values + (
                        as_int(_row_value(existing, "id", 0), 0),
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO match_results
                    (
                        platform_id,match_date,match_code,match_key,
                        normalized_home,normalized_away,match_identity,
                        identity_quality,match_name,league,home_team,
                        away_team,home_score,away_score,half_home_score,
                        half_away_score,status,finished_time,source
                    )
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                     %s,%s,%s,%s,%s)
                    """,
                    values,
                )
            saved += 1

        return {
            "saved_results": saved,
            "skipped_results": skipped,
        }


def save_sync_status(record, connection_factory=None):
    factory = connection_factory or _default_connection_factory
    conn = factory()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO sync_log
            (platform_id,platform_name,new_count,duplicate_count,
             status,cost_time,created_time)
            VALUES(%s,%s,%s,%s,%s,%s,NOW())
            """,
            (
                record["platform_id"],
                record["platform_name"],
                record.get("new_count", 0),
                record.get("duplicate_count", 0),
                record["status"],
                record.get("cost_time", 0),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def ingest_records(
    list_items,
    detail_fetcher,
    record_builder,
    platform_id,
    platform_name,
    repository,
    status_recorder=None,
):
    summary = {
        "platform_id": int(platform_id),
        "platform_name": platform_name,
        "total_count": 0,
        "new_count": 0,
        "duplicate_count": 0,
        "failed_count": 0,
        "failed": [],
        "issues": [],
    }

    for item in list_items or []:
        summary["total_count"] += 1
        source_id = None

        try:
            source_id, detail = detail_fetcher(item)
            record = record_builder(item, detail)
            result = repository.save(record)
            if result.get("inserted_order"):
                summary["new_count"] += 1
            else:
                summary["duplicate_count"] += 1
            summary["issues"].extend(record.get("issues") or [])
        except Exception as exc:
            summary["failed_count"] += 1
            summary["failed"].append(
                {
                    "source_id": str(source_id or ""),
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    if summary["failed_count"] == 0:
        status = "success"
    elif summary["new_count"] or summary["duplicate_count"]:
        status = "partial"
    else:
        status = "failed"

    summary["status"] = status

    if status_recorder is not None:
        status_recorder(
            {
                "platform_id": int(platform_id),
                "platform_name": platform_name,
                "new_count": summary["new_count"],
                "duplicate_count": summary["duplicate_count"],
                "status": status,
                "cost_time": 0,
            }
        )

    return summary
