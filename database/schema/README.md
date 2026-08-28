# Production database schema coverage

## Reference snapshot

`football_data_schema.sql` is copied from the production read-only structure export generated with:

```bash
mysqldump --no-data --skip-comments --skip-triggers --no-tablespaces football_data
```

The reference file was read and inspected without connecting to the database. Its source SHA-256 is:

```text
7f0dd1a3163da2dac1d6e60eb44e784de822d0341d51262843388ac296610042
```

Static safety checks found:

- 22 `CREATE TABLE` statements.
- 22 matching `DROP TABLE` statements.
- 84 session-level `SET` statements emitted by mysqldump.
- No `INSERT`, `REPLACE`, `LOAD DATA`, `UPDATE`, or `DELETE` statements.
- No views, triggers, routines, or `DEFINER` clauses.
- No password, token, cookie, authorization, JWT, or private-key material.
- 17 DDL `AUTO_INCREMENT` table counters. These are table options from the no-data export, not row data.

The snapshot contains schema DDL only. It must not be confused with a database migration and was not executed during repository preparation.

## Actual production tables

The production snapshot contains these 22 tables:

1. `daily_report`
2. `expert_profile`
3. `expert_rank`
4. `expert_score`
5. `match_results`
6. `matches`
7. `order_matches`
8. `order_sync_log`
9. `orders`
10. `platform_config`
11. `platforms`
12. `settlement_logs`
13. `spider_logs`
14. `sync_log`
15. `team_aliases`
16. `user_daily_stats`
17. `user_grade_overrides`
18. `user_profiles_ext`
19. `user_rank`
20. `user_statistics`
21. `users`
22. `users_statistics`

## Current code dependencies

Static inspection of all Python SQL calls found direct dependencies on these production tables:

- `expert_profile`
- `expert_rank`
- `match_results`
- `matches`
- `order_matches`
- `orders`
- `platform_config`
- `platforms`
- `settlement_logs`
- `spider_logs`
- `sync_log`
- `team_aliases`
- `user_grade_overrides`
- `user_profiles_ext`
- `user_statistics`
- `users`

The following production tables were not referenced by the current Python SQL scan and appear to belong to historical or external workflows:

- `daily_report`
- `expert_score`
- `order_sync_log`
- `user_daily_stats`
- `user_rank`
- `users_statistics`

This absence of a static reference does not authorize deleting those production tables.

## Migration coverage

The repository migrations contain complete `CREATE TABLE` statements for:

| Table | Migration |
|---|---|
| `user_statistics` | `scripts/migrate_v3.py` |
| `settlement_logs` | `scripts/migrate_v3.py` |
| `spider_logs` | `scripts/migrate_v3.py`, `scripts/migrate_hub_v4.py` |
| `platform_config` | `scripts/migrate_v3.py`, `scripts/migrate_hub_v4.py` |
| `user_grade_overrides` | `scripts/migrate_hub_v4.py` |
| `user_profiles_ext` | `scripts/migrate_v6.py` |
| `team_aliases` | `scripts/migrate_v6.py` |

The migrations do not contain the base `CREATE TABLE` definition for these current-code dependencies:

- `orders`
- `order_matches`
- `match_results`
- `matches`
- `users`
- `expert_profile`
- `expert_rank`
- `sync_log`
- `platforms`

Their production definitions are now documented by the reviewed no-data snapshot, but they still cannot be created by running the repository migrations alone.

## Optional Last Known Good snapshots

The API can persist successful read-model responses in an optional `api_snapshots`
table.  The application treats this table as best-effort and continues using
its in-process cache when the table has not been provisioned.  A DBA may create
the table separately with the following fields (no business rows are required):

`snapshot_key` (primary key), `payload_json`, `updated_at`, `source_updated_at`,
and `status`.

## Migration differences from production

The static comparison found:

- Every column and index that `migrate_v3.py`, `migrate_hub_v4.py`, and `migrate_v6.py` add to `orders`, `order_matches`, and `match_results` is present in production.
- Production `orders.platform_bonus` is `DECIMAL(12,2)`, while `migrate_v3.py` declares `DECIMAL(16,2)` for a newly added column.
- Production `orders.commission_total` is `DECIMAL(12,2)`, while `migrate_v3.py` declares `DECIMAL(16,2)` for a newly added column.
- Production `user_statistics.recent_results` is `VARCHAR(100)`, while `migrate_v3.py` creates it as `VARCHAR(150)`.
- Production `user_statistics` has additional indexes named `idx_platform`, `idx_score`, `idx_profit`, `idx_roi`, and `idx_hit` that are not created by the inspected migrations.
- Production contains six tables with no current Python SQL reference: `daily_report`, `expert_score`, `order_sync_log`, `user_daily_stats`, `user_rank`, and `users_statistics`.
- The production dump includes MySQL-normalized nullability, collation, defaults, engine options, and current auto-increment table options. These may differ textually from hand-written migration SQL even when the logical column is otherwise equivalent.

No database structure was changed as part of this comparison.
