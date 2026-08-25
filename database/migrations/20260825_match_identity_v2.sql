-- Match Identity v2 forward migration.
--
-- Safety properties:
--   * No rows are deleted.
--   * New identity columns are nullable so legacy rows remain valid.
--   * No new UNIQUE constraint is created in this phase.
--   * Existing match_name/match_id UNIQUE constraints are replaced by
--     ordinary indexes because those values are not globally unique.
--   * Historical dates are not inferred from names, week codes,
--     order expiration, deadline_time, or kickoff proxies.
--
-- Run only after reviewing every PRECHECK result and taking a backup.

SELECT 'PRECHECK required tables' AS check_name;
SELECT TABLE_NAME
FROM information_schema.TABLES
WHERE TABLE_SCHEMA=DATABASE()
  AND TABLE_NAME IN (
      'matches',
      'orders',
      'order_matches',
      'match_results',
      'team_aliases'
  )
ORDER BY TABLE_NAME;

SELECT 'PRECHECK legacy match_results duplicate names' AS check_name;
SELECT match_name,COUNT(*) AS duplicate_count
FROM match_results
WHERE match_name IS NOT NULL AND match_name<>''
GROUP BY match_name
HAVING COUNT(*)>1
ORDER BY duplicate_count DESC,match_name
LIMIT 100;

SELECT 'PRECHECK legacy matches duplicate source codes' AS check_name;
SELECT match_id,COUNT(*) AS duplicate_count
FROM matches
WHERE match_id IS NOT NULL AND match_id<>''
GROUP BY match_id
HAVING COUNT(*)>1
ORDER BY duplicate_count DESC,match_id
LIMIT 100;

DELIMITER $$

DROP PROCEDURE IF EXISTS migrate_match_identity_v2$$

CREATE PROCEDURE migrate_match_identity_v2()
BEGIN
    IF (
        SELECT COUNT(*)
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME IN (
              'matches',
              'orders',
              'order_matches',
              'match_results',
              'team_aliases'
          )
    ) <> 5 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT='Match Identity v2 required tables are missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='platform_id'
    ) THEN
        ALTER TABLE order_matches
            ADD COLUMN platform_id INT NULL
            COMMENT 'Source platform; nullable for legacy rows';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='match_date'
    ) THEN
        ALTER TABLE order_matches
            ADD COLUMN match_date DATE NULL
            COMMENT 'Verified source match date; never inferred from deadline';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='normalized_home'
    ) THEN
        ALTER TABLE order_matches
            ADD COLUMN normalized_home VARCHAR(120) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='normalized_away'
    ) THEN
        ALTER TABLE order_matches
            ADD COLUMN normalized_away VARCHAR(120) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='match_identity'
    ) THEN
        ALTER TABLE order_matches
            ADD COLUMN match_identity VARCHAR(255) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='identity_quality'
    ) THEN
        ALTER TABLE order_matches
            ADD COLUMN identity_quality VARCHAR(20) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='platform_id'
    ) THEN
        ALTER TABLE match_results
            ADD COLUMN platform_id INT NULL
            COMMENT 'Source platform; nullable for legacy rows';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='match_date'
    ) THEN
        ALTER TABLE match_results
            ADD COLUMN match_date DATE NULL
            COMMENT 'Verified source match date; NULL when unknown';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='normalized_home'
    ) THEN
        ALTER TABLE match_results
            ADD COLUMN normalized_home VARCHAR(120) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='normalized_away'
    ) THEN
        ALTER TABLE match_results
            ADD COLUMN normalized_away VARCHAR(120) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='match_identity'
    ) THEN
        ALTER TABLE match_results
            ADD COLUMN match_identity VARCHAR(255) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='identity_quality'
    ) THEN
        ALTER TABLE match_results
            ADD COLUMN identity_quality VARCHAR(20) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='platform_id'
    ) THEN
        ALTER TABLE matches
            ADD COLUMN platform_id INT NULL
            COMMENT 'Source platform; nullable for legacy rows';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='match_date'
    ) THEN
        ALTER TABLE matches
            ADD COLUMN match_date DATE NULL
            COMMENT 'Verified source match date; NULL when unknown';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='normalized_home'
    ) THEN
        ALTER TABLE matches
            ADD COLUMN normalized_home VARCHAR(120) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='normalized_away'
    ) THEN
        ALTER TABLE matches
            ADD COLUMN normalized_away VARCHAR(120) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='match_identity'
    ) THEN
        ALTER TABLE matches
            ADD COLUMN match_identity VARCHAR(255) NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='identity_quality'
    ) THEN
        ALTER TABLE matches
            ADD COLUMN identity_quality VARCHAR(20) NULL;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='uk_match'
          AND NON_UNIQUE=0
    ) THEN
        ALTER TABLE match_results DROP INDEX uk_match;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='match_id'
          AND NON_UNIQUE=0
    ) THEN
        ALTER TABLE matches DROP INDEX match_id;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='idx_mr_match_name'
    ) THEN
        ALTER TABLE match_results
            ADD INDEX idx_mr_match_name (match_name);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='idx_matches_source_code'
    ) THEN
        ALTER TABLE matches
            ADD INDEX idx_matches_source_code (match_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND INDEX_NAME='idx_om_identity_code'
    ) THEN
        ALTER TABLE order_matches
            ADD INDEX idx_om_identity_code
                (platform_id,match_date,match_code);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND INDEX_NAME='idx_om_identity_teams'
    ) THEN
        ALTER TABLE order_matches
            ADD INDEX idx_om_identity_teams
                (platform_id,match_date,normalized_home,normalized_away);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND INDEX_NAME='idx_om_identity_value'
    ) THEN
        ALTER TABLE order_matches
            ADD INDEX idx_om_identity_value (match_identity);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='idx_mr_identity_code'
    ) THEN
        ALTER TABLE match_results
            ADD INDEX idx_mr_identity_code
                (platform_id,match_date,match_code);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='idx_mr_identity_teams'
    ) THEN
        ALTER TABLE match_results
            ADD INDEX idx_mr_identity_teams
                (platform_id,match_date,normalized_home,normalized_away);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='idx_mr_identity_value'
    ) THEN
        ALTER TABLE match_results
            ADD INDEX idx_mr_identity_value (match_identity);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='idx_matches_identity_code'
    ) THEN
        ALTER TABLE matches
            ADD INDEX idx_matches_identity_code
                (platform_id,match_date,match_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='idx_matches_identity_teams'
    ) THEN
        ALTER TABLE matches
            ADD INDEX idx_matches_identity_teams
                (platform_id,match_date,normalized_home,normalized_away);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='idx_matches_identity_value'
    ) THEN
        ALTER TABLE matches
            ADD INDEX idx_matches_identity_value (match_identity);
    END IF;
END$$

CALL migrate_match_identity_v2()$$
DROP PROCEDURE migrate_match_identity_v2$$

DELIMITER ;

-- Deterministic historical backfill: order platform ownership is known.
UPDATE order_matches om
INNER JOIN orders o ON o.id=om.order_id
SET om.platform_id=o.platform_id
WHERE om.platform_id IS NULL;

-- Build identities only for rows whose date and normalized teams have
-- already been populated from verified source data.  This deliberately
-- leaves legacy rows NULL instead of guessing a date.
UPDATE order_matches
SET match_identity=CASE
        WHEN match_code IS NOT NULL AND match_code<>'' THEN
            CONCAT(platform_id,'|',DATE_FORMAT(match_date,'%Y-%m-%d'),'|',match_code)
        WHEN normalized_home IS NOT NULL AND normalized_home<>''
         AND normalized_away IS NOT NULL AND normalized_away<>'' THEN
            CONCAT(platform_id,'|',DATE_FORMAT(match_date,'%Y-%m-%d'),'|',normalized_home,'|',normalized_away)
        ELSE NULL
    END,
    identity_quality=CASE
        WHEN match_code IS NOT NULL AND match_code<>'' THEN 'exact'
        WHEN normalized_home IS NOT NULL AND normalized_home<>''
         AND normalized_away IS NOT NULL AND normalized_away<>'' THEN 'secondary'
        ELSE identity_quality
    END
WHERE platform_id IS NOT NULL
  AND match_date IS NOT NULL
  AND (match_identity IS NULL OR match_identity='');

UPDATE match_results
SET match_identity=CASE
        WHEN match_code IS NOT NULL AND match_code<>'' THEN
            CONCAT(platform_id,'|',DATE_FORMAT(match_date,'%Y-%m-%d'),'|',match_code)
        WHEN normalized_home IS NOT NULL AND normalized_home<>''
         AND normalized_away IS NOT NULL AND normalized_away<>'' THEN
            CONCAT(platform_id,'|',DATE_FORMAT(match_date,'%Y-%m-%d'),'|',normalized_home,'|',normalized_away)
        ELSE NULL
    END,
    identity_quality=CASE
        WHEN match_code IS NOT NULL AND match_code<>'' THEN 'exact'
        WHEN normalized_home IS NOT NULL AND normalized_home<>''
         AND normalized_away IS NOT NULL AND normalized_away<>'' THEN 'secondary'
        ELSE identity_quality
    END
WHERE platform_id IS NOT NULL
  AND match_date IS NOT NULL
  AND (match_identity IS NULL OR match_identity='');

UPDATE matches
SET match_identity=CASE
        WHEN match_id IS NOT NULL AND match_id<>'' THEN
            CONCAT(platform_id,'|',DATE_FORMAT(match_date,'%Y-%m-%d'),'|',match_id)
        WHEN normalized_home IS NOT NULL AND normalized_home<>''
         AND normalized_away IS NOT NULL AND normalized_away<>'' THEN
            CONCAT(platform_id,'|',DATE_FORMAT(match_date,'%Y-%m-%d'),'|',normalized_home,'|',normalized_away)
        ELSE NULL
    END,
    identity_quality=CASE
        WHEN match_id IS NOT NULL AND match_id<>'' THEN 'exact'
        WHEN normalized_home IS NOT NULL AND normalized_home<>''
         AND normalized_away IS NOT NULL AND normalized_away<>'' THEN 'secondary'
        ELSE identity_quality
    END
WHERE platform_id IS NOT NULL
  AND match_date IS NOT NULL
  AND (match_identity IS NULL OR match_identity='');

SELECT 'POSTCHECK exact identity duplicates' AS check_name;
SELECT 'order_matches' AS table_name,match_identity,COUNT(*) AS duplicate_count
FROM order_matches
WHERE identity_quality='exact' AND match_identity IS NOT NULL
GROUP BY match_identity
HAVING COUNT(*)>1
UNION ALL
SELECT 'match_results',match_identity,COUNT(*)
FROM match_results
WHERE identity_quality='exact' AND match_identity IS NOT NULL
GROUP BY match_identity
HAVING COUNT(*)>1
UNION ALL
SELECT 'matches',match_identity,COUNT(*)
FROM matches
WHERE identity_quality='exact' AND match_identity IS NOT NULL
GROUP BY match_identity
HAVING COUNT(*)>1;

SELECT 'POSTCHECK NULL identity inventory' AS check_name;
SELECT 'order_matches' AS table_name,COUNT(*) AS null_identity_rows
FROM order_matches
WHERE match_identity IS NULL OR match_identity=''
UNION ALL
SELECT 'match_results',COUNT(*)
FROM match_results
WHERE match_identity IS NULL OR match_identity=''
UNION ALL
SELECT 'matches',COUNT(*)
FROM matches
WHERE match_identity IS NULL OR match_identity='';
