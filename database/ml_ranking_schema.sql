-- ML-Based Ranking Schema
-- Tracks user selections for machine learning

CREATE TABLE IF NOT EXISTS user_selections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Session tracking
    session_id UUID NOT NULL,
    user_id UUID,  -- Optional user ID if authenticated
    
    -- Query context
    query_text TEXT,
    query_type VARCHAR(50),  -- 'search', 'recommendation', 'alternative'
    
    -- Results shown
    results_shown UUID[],  -- Array of part IDs shown to user
    result_count INTEGER,
    
    -- User selection
    selected_part_id UUID REFERENCES parts(id),
    selection_rank INTEGER,  -- Position in results (1-indexed)
    
    -- Interaction metadata
    time_to_select_seconds INTEGER,
    clicked_alternatives BOOLEAN DEFAULT FALSE,
    clicked_documentation BOOLEAN DEFAULT FALSE,
    
    -- Feedback
    explicit_feedback INTEGER,  -- 1-5 star rating (optional)
    feedback_text TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Part reference
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    
    -- Extracted features for ML
    feature_vector JSONB,  -- Flexible feature storage
    
    -- Precomputed features
    cost_score DECIMAL(5, 2),
    availability_score DECIMAL(5, 2),
    popularity_score DECIMAL(5, 2),
    spec_completeness_score DECIMAL(5, 2),
    
    -- Metadata
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Model identification
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50),  -- 'lightgbm', 'xgboost', 'neural_net'
    
    -- Model binary
    model_data BYTEA,  -- Serialized model
    
    -- Performance metrics
    training_samples INTEGER,
    validation_accuracy DECIMAL(5, 4),
    ndcg_score DECIMAL(5, 4),  -- Normalized Discounted Cumulative Gain
    
    -- Feature importance
    feature_importance JSONB,
    
    -- Status
    is_active BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_selections_session ON user_selections(session_id);
CREATE INDEX IF NOT EXISTS idx_user_selections_part ON user_selections(selected_part_id);
CREATE INDEX IF NOT EXISTS idx_user_selections_created ON user_selections(created_at);
CREATE INDEX IF NOT EXISTS idx_ml_features_part ON ml_features(part_id);
CREATE INDEX IF NOT EXISTS idx_ml_models_active ON ml_models(is_active) WHERE is_active = TRUE;

-- Comments
COMMENT ON TABLE user_selections IS 'User selection tracking for ML training';
COMMENT ON TABLE ml_features IS 'Precomputed ML features for parts';
COMMENT ON TABLE ml_models IS 'Trained ML models for ranking';
COMMENT ON COLUMN user_selections.selection_rank IS 'Position of selected part in results (1 = first)';
COMMENT ON COLUMN ml_models.ndcg_score IS 'Ranking quality metric (higher is better)';
