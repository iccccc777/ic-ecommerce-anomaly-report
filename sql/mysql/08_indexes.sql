CREATE INDEX idx_behavior_user
    ON behavior (user_id, timestamps);

CREATE INDEX idx_behavior_category
    ON behavior (category_id, timestamps);

CREATE INDEX idx_behavior_category_user
    ON behavior (category_id, user_id);

CREATE INDEX idx_behavior_item_user
    ON behavior (item_id, user_id);

CREATE INDEX idx_behavior_time
    ON behavior (timestamps);

CREATE INDEX idx_behavior_type_time
    ON behavior (behavior_type, timestamps);

CREATE INDEX idx_behavior_type_user
    ON behavior (behavior_type, user_id);
