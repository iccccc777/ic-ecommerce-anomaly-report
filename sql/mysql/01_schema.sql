SET NAMES utf8mb4;
SET time_zone = '+00:00';

DROP VIEW IF EXISTS behavior_clean;
DROP TABLE IF EXISTS dim_category;
DROP TABLE IF EXISTS dim_item;
DROP TABLE IF EXISTS dim_user;
DROP TABLE IF EXISTS behavior;

CREATE TABLE behavior (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    item_id BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    behavior_type VARCHAR(8) NOT NULL,
    timestamps BIGINT NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE VIEW behavior_clean AS
SELECT
    id,
    user_id,
    item_id,
    category_id,
    behavior_type,
    timestamps,
    DATE_FORMAT(
        DATE_ADD(FROM_UNIXTIME(timestamps), INTERVAL 8 HOUR),
        '%Y-%m-%d'
    ) AS event_day,
    HOUR(DATE_ADD(FROM_UNIXTIME(timestamps), INTERVAL 8 HOUR)) AS event_hour
FROM behavior
WHERE DATE(DATE_ADD(FROM_UNIXTIME(timestamps), INTERVAL 8 HOUR))
      BETWEEN '2017-11-25' AND '2017-12-03';

CREATE TABLE dim_user (
    user_id BIGINT NOT NULL,
    behavior_count BIGINT NOT NULL,
    active_days INT NOT NULL,
    first_ts BIGINT NOT NULL,
    last_ts BIGINT NOT NULL,
    PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE dim_item (
    item_id BIGINT NOT NULL,
    behavior_count BIGINT NOT NULL,
    user_count BIGINT NOT NULL,
    PRIMARY KEY (item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE dim_category (
    category_id BIGINT NOT NULL,
    behavior_count BIGINT NOT NULL,
    user_count BIGINT NOT NULL,
    PRIMARY KEY (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
