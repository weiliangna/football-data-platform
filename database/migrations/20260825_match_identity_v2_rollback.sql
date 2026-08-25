-- Match Identity v2 rollback.
--
-- This rollback is intentionally guarded.  It aborts if post-migration
-- data contains duplicate legacy match_name/match_id values because
-- restoring the former UNIQUE constraints would otherwise fail midway.
-- Take a backup first: dropping v2 columns discards identity metadata.

SELECT 'ROLLBACK PRECHECK match_results duplicate names' AS check_name;
SELECT match_name,COUNT(*) AS duplicate_count
FROM match_results
WHERE match_name IS NOT NULL AND match_name<>''
GROUP BY match_name
HAVING COUNT(*)>1
ORDER BY duplicate_count DESC,match_name
LIMIT 100;

SELECT 'ROLLBACK PRECHECK matches duplicate source codes' AS check_name;
SELECT match_id,COUNT(*) AS duplicate_count
FROM matches
WHERE match_id IS NOT NULL AND match_id<>''
GROUP BY match_id
HAVING COUNT(*)>1
ORDER BY duplicate_count DESC,match_id
LIMIT 100;

DELIMITER $$

DROP PROCEDURE IF EXISTS rollback_match_identity_v2$$

CREATE PROCEDURE rollback_match_identity_v2()
BEGIN
    IF EXISTS (
        SELECT 1
        FROM match_results
        WHERE match_name IS NOT NULL AND match_name<>''
        GROUP BY match_name
        HAVING COUNT(*)>1
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT='Rollback blocked: duplicate match_results.match_name values exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM matches
        WHERE match_id IS NOT NULL AND match_id<>''
        GROUP BY match_id
        HAVING COUNT(*)>1
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT='Rollback blocked: duplicate matches.match_id values exist';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND INDEX_NAME='idx_om_identity_code'
    ) THEN
        ALTER TABLE order_matches DROP INDEX idx_om_identity_code;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND INDEX_NAME='idx_om_identity_teams'
    ) THEN
        ALTER TABLE order_matches DROP INDEX idx_om_identity_teams;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND INDEX_NAME='idx_om_identity_value'
    ) THEN
        ALTER TABLE order_matches DROP INDEX idx_om_identity_value;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='idx_mr_identity_code'
    ) THEN
        ALTER TABLE match_results DROP INDEX idx_mr_identity_code;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='idx_mr_identity_teams'
    ) THEN
        ALTER TABLE match_results DROP INDEX idx_mr_identity_teams;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='idx_mr_identity_value'
    ) THEN
        ALTER TABLE match_results DROP INDEX idx_mr_identity_value;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='idx_matches_identity_code'
    ) THEN
        ALTER TABLE matches DROP INDEX idx_matches_identity_code;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='idx_matches_identity_teams'
    ) THEN
        ALTER TABLE matches DROP INDEX idx_matches_identity_teams;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='idx_matches_identity_value'
    ) THEN
        ALTER TABLE matches DROP INDEX idx_matches_identity_value;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='identity_quality'
    ) THEN
        ALTER TABLE order_matches DROP COLUMN identity_quality;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='match_identity'
    ) THEN
        ALTER TABLE order_matches DROP COLUMN match_identity;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='normalized_away'
    ) THEN
        ALTER TABLE order_matches DROP COLUMN normalized_away;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='normalized_home'
    ) THEN
        ALTER TABLE order_matches DROP COLUMN normalized_home;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='match_date'
    ) THEN
        ALTER TABLE order_matches DROP COLUMN match_date;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='order_matches'
          AND COLUMN_NAME='platform_id'
    ) THEN
        ALTER TABLE order_matches DROP COLUMN platform_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='identity_quality'
    ) THEN
        ALTER TABLE match_results DROP COLUMN identity_quality;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='match_identity'
    ) THEN
        ALTER TABLE match_results DROP COLUMN match_identity;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='normalized_away'
    ) THEN
        ALTER TABLE match_results DROP COLUMN normalized_away;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='normalized_home'
    ) THEN
        ALTER TABLE match_results DROP COLUMN normalized_home;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='match_date'
    ) THEN
        ALTER TABLE match_results DROP COLUMN match_date;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND COLUMN_NAME='platform_id'
    ) THEN
        ALTER TABLE match_results DROP COLUMN platform_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='identity_quality'
    ) THEN
        ALTER TABLE matches DROP COLUMN identity_quality;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='match_identity'
    ) THEN
        ALTER TABLE matches DROP COLUMN match_identity;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='normalized_away'
    ) THEN
        ALTER TABLE matches DROP COLUMN normalized_away;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='normalized_home'
    ) THEN
        ALTER TABLE matches DROP COLUMN normalized_home;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='match_date'
    ) THEN
        ALTER TABLE matches DROP COLUMN match_date;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND COLUMN_NAME='platform_id'
    ) THEN
        ALTER TABLE matches DROP COLUMN platform_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='idx_mr_match_name'
    ) THEN
        ALTER TABLE match_results DROP INDEX idx_mr_match_name;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='match_results'
          AND INDEX_NAME='uk_match'
    ) THEN
        ALTER TABLE match_results
            ADD UNIQUE INDEX uk_match (match_name);
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='idx_matches_source_code'
    ) THEN
        ALTER TABLE matches DROP INDEX idx_matches_source_code;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE()
          AND TABLE_NAME='matches'
          AND INDEX_NAME='match_id'
    ) THEN
        ALTER TABLE matches
            ADD UNIQUE INDEX match_id (match_id);
    END IF;
END$$

CALL rollback_match_identity_v2()$$
DROP PROCEDURE rollback_match_identity_v2$$

DELIMITER ;

SELECT 'ROLLBACK POSTCHECK v2 columns remaining' AS check_name;
SELECT TABLE_NAME,COLUMN_NAME
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA=DATABASE()
  AND TABLE_NAME IN ('matches','order_matches','match_results')
  AND COLUMN_NAME IN (
      'platform_id',
      'match_date',
      'normalized_home',
      'normalized_away',
      'match_identity',
      'identity_quality'
  )
ORDER BY TABLE_NAME,COLUMN_NAME;
