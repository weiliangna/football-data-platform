
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `daily_report`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `daily_report` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `report_date` date DEFAULT NULL,
  `total_orders` int DEFAULT '0',
  `total_profit` decimal(12,2) DEFAULT '0.00',
  `avg_hit_rate` decimal(5,2) DEFAULT '0.00',
  `top_user` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `top_profit_user` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `expert_profile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `expert_profile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int NOT NULL,
  `user_id` bigint NOT NULL,
  `nickname` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `total_order` int DEFAULT '0',
  `win_order` int DEFAULT '0',
  `lose_order` int DEFAULT '0',
  `pending_order` int DEFAULT '0',
  `win_rate` decimal(5,2) DEFAULT '0.00',
  `current_streak` int DEFAULT '0',
  `max_streak` int DEFAULT '0',
  `total_amount` decimal(12,2) DEFAULT '0.00',
  `total_profit` decimal(12,2) DEFAULT '0.00',
  `avg_profitability` decimal(10,2) DEFAULT '0.00',
  `risk_level` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `expert_level` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `avatar` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `fans` int DEFAULT '0',
  `source_hit_rate` decimal(5,2) DEFAULT '0.00',
  `source_profit_rate` decimal(5,2) DEFAULT '0.00',
  `month_profit` decimal(12,2) DEFAULT '0.00',
  `last_ten` varchar(1000) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=217 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `expert_rank`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `expert_rank` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int NOT NULL,
  `user_id` bigint NOT NULL,
  `nickname` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `order_count` int DEFAULT '0',
  `total_amount` decimal(12,2) DEFAULT '0.00',
  `avg_hit_rate` decimal(5,2) DEFAULT '0.00',
  `avg_profitability` decimal(12,2) DEFAULT '0.00',
  `avg_follow` int DEFAULT '0',
  `expert_score` decimal(6,2) DEFAULT '0.00',
  `level` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '普通',
  `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `expert_score`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `expert_score` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int DEFAULT NULL,
  `user_id` bigint DEFAULT NULL,
  `nickname` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `accuracy_score` decimal(5,2) DEFAULT NULL,
  `profit_score` decimal(5,2) DEFAULT NULL,
  `capital_score` decimal(5,2) DEFAULT NULL,
  `stability_score` decimal(5,2) DEFAULT NULL,
  `risk_score` decimal(5,2) DEFAULT NULL,
  `total_score` decimal(5,2) DEFAULT NULL,
  `level` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=186 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `match_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `match_results` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `match_name` varchar(200) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `league` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `home_team` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `away_team` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `home_score` int DEFAULT '0',
  `away_score` int DEFAULT '0',
  `half_home_score` int DEFAULT '0',
  `half_away_score` int DEFAULT '0',
  `status` varchar(20) COLLATE utf8mb4_general_ci DEFAULT '未结束',
  `finished_time` datetime DEFAULT NULL,
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `match_code` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '周一001等场次',
  `match_key` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '标准比赛键',
  `source` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '赛果来源',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_match` (`match_name`),
  KEY `idx_mr_match_key` (`match_key`),
  KEY `idx_mr_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=557 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `matches`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `matches` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `match_id` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `league` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '赛事',
  `home_team` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '主队',
  `away_team` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客队',
  `match_time` datetime DEFAULT NULL COMMENT '比赛时间',
  `home_score` int DEFAULT NULL COMMENT '主队比分',
  `away_score` int DEFAULT NULL COMMENT '客队比分',
  `status` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '未结束' COMMENT '比赛状态',
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `match_id` (`match_id`)
) ENGINE=InnoDB AUTO_INCREMENT=375 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `order_matches`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_matches` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `order_id` bigint NOT NULL,
  `match_name` varchar(200) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `league` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `play_type` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `selection` text COLLATE utf8mb4_general_ci,
  `result` varchar(20) COLLATE utf8mb4_general_ci DEFAULT '待开奖',
  `profit` decimal(12,2) DEFAULT '0.00',
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `handicap` int DEFAULT '0',
  `match_code` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '周一001等比赛编号',
  `option_detail` text COLLATE utf8mb4_general_ci COMMENT '选项及赔率JSON',
  `match_key` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '标准比赛键',
  `deadline_time` datetime DEFAULT NULL COMMENT '比赛/销售截止时间',
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`),
  KEY `idx_match_name` (`match_name`),
  KEY `idx_om_match_key` (`match_key`),
  KEY `idx_om_result` (`result`),
  KEY `idx_om_order_play` (`order_id`,`play_type`),
  KEY `idx_om_match_name` (`match_name`),
  KEY `idx_om_deadline` (`deadline_time`),
  KEY `idx_om_code` (`match_code`)
) ENGINE=InnoDB AUTO_INCREMENT=1378 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `order_sync_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_sync_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int DEFAULT NULL,
  `platform_order_id` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `sync_time` datetime DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orders` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int NOT NULL COMMENT '平台ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `match_id` bigint DEFAULT NULL COMMENT '比赛ID',
  `match_name` varchar(200) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '比赛名称',
  `league` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '赛事',
  `play_type` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '玩法类型',
  `pass_summary` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `pass_composition` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `bet_count` int DEFAULT NULL,
  `lot_multi` decimal(12,2) DEFAULT NULL,
  `selection` text COLLATE utf8mb4_general_ci,
  `bet_code` text COLLATE utf8mb4_general_ci,
  `odds` decimal(6,2) DEFAULT NULL COMMENT '赔率',
  `odds_text` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `stake` decimal(12,2) DEFAULT '0.00' COMMENT '投注金额',
  `result` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '待开奖' COMMENT '赛果',
  `profit` decimal(12,2) DEFAULT '0.00' COMMENT '盈亏',
  `publish_time` datetime DEFAULT NULL COMMENT '发单时间',
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `platform_order_id` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '平台订单ID',
  `nickname` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '发单用户昵称',
  `declaration` text COLLATE utf8mb4_general_ci COMMENT '发单说明',
  `hit_rate` decimal(5,2) DEFAULT NULL COMMENT '命中率',
  `profitability` decimal(5,2) DEFAULT NULL COMMENT '盈利能力',
  `follow_num` int DEFAULT '0' COMMENT '跟单人数',
  `handicap` int DEFAULT '0',
  `platform_bonus` decimal(12,2) DEFAULT '0.00' COMMENT '平台实际派奖金额',
  `commission_total` decimal(12,2) DEFAULT '0.00' COMMENT '平台实际佣金',
  `settlement_status` varchar(30) COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '平台结算状态',
  `settled_time` datetime DEFAULT NULL COMMENT '平台结算同步时间',
  `expected_bonus` decimal(16,2) DEFAULT '0.00' COMMENT '预计回报',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_order` (`platform_order_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_platform` (`platform_id`),
  KEY `idx_match` (`match_id`),
  KEY `idx_orders_platform_user` (`platform_id`,`user_id`),
  KEY `idx_orders_result` (`result`),
  KEY `idx_orders_created` (`created_time`),
  KEY `idx_orders_platform_time` (`platform_id`,`publish_time`)
) ENGINE=InnoDB AUTO_INCREMENT=259 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `platform_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `platform_config` (
  `platform_id` int NOT NULL,
  `name` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `enabled` tinyint DEFAULT '1',
  `spider_enabled` tinyint DEFAULT '1',
  `result_enabled` tinyint DEFAULT '1',
  `settlement_enabled` tinyint DEFAULT '1',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`platform_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `platforms`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `platforms` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `url` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `status` tinyint DEFAULT '1',
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `settlement_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `settlement_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `order_id` bigint NOT NULL,
  `order_match_id` bigint NOT NULL,
  `match_name` varchar(200) COLLATE utf8mb4_general_ci DEFAULT '',
  `play_type` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '',
  `selection` text COLLATE utf8mb4_general_ci,
  `handicap` int DEFAULT '0',
  `home_score` int DEFAULT NULL,
  `away_score` int DEFAULT NULL,
  `half_home_score` int DEFAULT NULL,
  `half_away_score` int DEFAULT NULL,
  `old_result` varchar(30) COLLATE utf8mb4_general_ci DEFAULT '',
  `new_result` varchar(30) COLLATE utf8mb4_general_ci DEFAULT '',
  `reason` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '',
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_settlement_order` (`order_id`,`id`),
  KEY `idx_settlement_match` (`match_name`,`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `spider_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `spider_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int DEFAULT '0',
  `spider_name` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `started_time` datetime DEFAULT NULL,
  `finished_time` datetime DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_general_ci DEFAULT '',
  `exit_code` int DEFAULT '0',
  `message` text COLLATE utf8mb4_general_ci,
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_spider_name` (`spider_name`,`id`),
  KEY `idx_spider_platform` (`platform_id`,`id`)
) ENGINE=InnoDB AUTO_INCREMENT=445 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `sync_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sync_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int DEFAULT '0',
  `platform_name` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `new_count` int DEFAULT '0',
  `duplicate_count` int DEFAULT '0',
  `status` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `cost_time` float DEFAULT '0',
  `created_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3553 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `team_aliases`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `team_aliases` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int DEFAULT '0',
  `canonical_name` varchar(120) COLLATE utf8mb4_general_ci NOT NULL,
  `alias_name` varchar(120) COLLATE utf8mb4_general_ci NOT NULL,
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_alias` (`platform_id`,`alias_name`),
  KEY `idx_team_canonical` (`canonical_name`)
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_daily_stats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_daily_stats` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `nickname` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户昵称',
  `stat_date` date NOT NULL COMMENT '统计日期',
  `platform_id` int NOT NULL COMMENT '平台ID',
  `order_count` int DEFAULT '0' COMMENT '发单数量',
  `total_amount` decimal(12,2) DEFAULT '0.00' COMMENT '发单金额',
  `avg_hit_rate` decimal(5,2) DEFAULT '0.00' COMMENT '平均命中率',
  `avg_profitability` decimal(12,2) DEFAULT '0.00' COMMENT '平均盈利能力',
  `win_count` int DEFAULT '0' COMMENT '中奖数量',
  `lose_count` int DEFAULT '0' COMMENT '失败数量',
  `pending_count` int DEFAULT '0' COMMENT '未开奖数量',
  `win_rate` decimal(5,2) DEFAULT '0.00' COMMENT '胜率',
  `profit` decimal(12,2) DEFAULT '0.00' COMMENT '当日盈亏',
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_date` (`user_id`,`stat_date`),
  KEY `idx_user` (`user_id`),
  KEY `idx_date` (`stat_date`)
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_grade_overrides`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_grade_overrides` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int NOT NULL,
  `user_id` bigint NOT NULL,
  `grade` varchar(1) COLLATE utf8mb4_general_ci NOT NULL,
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_grade_user` (`platform_id`,`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_profiles_ext`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_profiles_ext` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int NOT NULL,
  `user_id` bigint NOT NULL,
  `nickname` varchar(100) COLLATE utf8mb4_general_ci DEFAULT '',
  `avatar_url` text COLLATE utf8mb4_general_ci,
  `source` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '',
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_user` (`platform_id`,`user_id`),
  KEY `idx_profile_nickname` (`nickname`)
) ENGINE=InnoDB AUTO_INCREMENT=67 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_rank`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_rank` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `period_type` varchar(20) COLLATE utf8mb4_general_ci NOT NULL COMMENT '周期（日/周/月/总）',
  `rank_date` date NOT NULL COMMENT '统计日期',
  `order_count` int DEFAULT '0' COMMENT '发单数量',
  `win_count` int DEFAULT '0' COMMENT '盈利数量',
  `win_rate` decimal(5,2) DEFAULT '0.00' COMMENT '胜率',
  `profit` decimal(12,2) DEFAULT '0.00' COMMENT '盈利金额',
  `rank_score` decimal(12,2) DEFAULT '0.00' COMMENT '综合评分',
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_period` (`period_type`),
  KEY `idx_date` (`rank_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_statistics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_statistics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` int NOT NULL,
  `user_id` bigint NOT NULL,
  `nickname` varchar(100) COLLATE utf8mb4_general_ci DEFAULT '',
  `total_orders` int DEFAULT '0',
  `settled_orders` int DEFAULT '0',
  `win_orders` int DEFAULT '0',
  `lose_orders` int DEFAULT '0',
  `pending_orders` int DEFAULT '0',
  `hit_rate` decimal(8,2) DEFAULT '0.00',
  `total_stake` decimal(16,2) DEFAULT '0.00',
  `total_profit` decimal(16,2) DEFAULT '0.00',
  `roi` decimal(10,2) DEFAULT '0.00',
  `follow_num` bigint DEFAULT '0',
  `current_streak` int DEFAULT '0',
  `max_win_streak` int DEFAULT '0',
  `recent_results` varchar(100) COLLATE utf8mb4_general_ci DEFAULT '',
  `expert_score` decimal(10,2) DEFAULT '0.00',
  `last_order_time` datetime DEFAULT NULL,
  `updated_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_user` (`platform_id`,`user_id`),
  KEY `idx_platform` (`platform_id`),
  KEY `idx_score` (`expert_score`),
  KEY `idx_profit` (`total_profit`),
  KEY `idx_roi` (`roi`),
  KEY `idx_hit` (`hit_rate`)
) ENGINE=InnoDB AUTO_INCREMENT=2706 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `platform_id` int NOT NULL COMMENT '所属平台ID',
  `username` varchar(100) COLLATE utf8mb4_general_ci NOT NULL COMMENT '平台用户名',
  `nickname` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户昵称',
  `level` varchar(50) COLLATE utf8mb4_general_ci DEFAULT '普通' COMMENT '用户等级',
  `total_orders` int DEFAULT '0' COMMENT '累计发单数量',
  `win_count` int DEFAULT '0' COMMENT '命中数量',
  `lose_count` int DEFAULT '0' COMMENT '失败数量',
  `pending_count` int DEFAULT '0' COMMENT '待开奖数量',
  `win_rate` decimal(5,2) DEFAULT '0.00' COMMENT '胜率',
  `total_profit` decimal(12,2) DEFAULT '0.00' COMMENT '累计盈亏',
  `last_order_time` datetime DEFAULT NULL COMMENT '最近发单时间',
  `created_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `last_update_time` datetime DEFAULT NULL COMMENT '最后统计时间',
  `platform_user_id` bigint DEFAULT NULL COMMENT '平台用户ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_user` (`platform_id`,`platform_user_id`),
  KEY `idx_platform` (`platform_id`),
  KEY `idx_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=9267 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `users_statistics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users_statistics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint DEFAULT NULL,
  `nickname` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `total_orders` int DEFAULT '0',
  `win_orders` int DEFAULT '0',
  `lose_orders` int DEFAULT '0',
  `win_rate` decimal(5,2) DEFAULT '0.00',
  `total_profit` decimal(12,2) DEFAULT '0.00',
  `recent_results` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `ranking` int DEFAULT NULL,
  `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

