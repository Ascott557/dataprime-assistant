-- DataPrime Assistant - Database Initialization Script
-- PostgreSQL 15+

-- Create tables for the DataPrime Assistant application

-- Feedback table for user ratings and comments
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    user_input TEXT NOT NULL,
    generated_query TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    trace_id VARCHAR(32),  -- W3C trace ID format (32 hex chars)
    span_id VARCHAR(16),   -- W3C span ID format (16 hex chars)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_trace_id ON feedback(trace_id);
CREATE INDEX IF NOT EXISTS idx_feedback_metadata ON feedback USING GIN(metadata);

-- Query history table
CREATE TABLE IF NOT EXISTS query_history (
    id SERIAL PRIMARY KEY,
    user_input TEXT NOT NULL,
    generated_query TEXT NOT NULL,
    intent VARCHAR(100),
    intent_confidence FLOAT,
    validation_score FLOAT,
    is_valid BOOLEAN,
    execution_time_ms INTEGER,
    trace_id VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_history_intent ON query_history(intent);
CREATE INDEX IF NOT EXISTS idx_query_history_trace_id ON query_history(trace_id);

-- Background jobs table
CREATE TABLE IF NOT EXISTS background_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    job_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    payload JSONB,
    result JSONB,
    error_message TEXT,
    trace_id VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_background_jobs_job_id ON background_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_background_jobs_status ON background_jobs(status);
CREATE INDEX IF NOT EXISTS idx_background_jobs_created_at ON background_jobs(created_at DESC);

-- Demo performance data table (for slow database demo)
CREATE TABLE IF NOT EXISTS demo_performance_data (
    id SERIAL PRIMARY KEY,
    operation_type VARCHAR(100) NOT NULL,
    duration_ms INTEGER NOT NULL,
    trace_id VARCHAR(32),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_demo_performance_created_at ON demo_performance_data(created_at DESC);

-- Insert some sample data for demo purposes
INSERT INTO demo_performance_data (operation_type, duration_ms, metadata) VALUES
    ('query_generation', 250, '{"model": "gpt-4", "tokens": 150}'::jsonb),
    ('validation', 50, '{"syntax_check": true}'::jsonb),
    ('external_api_call', 500, '{"api": "coralogix", "endpoint": "/v1/dataprime"}'::jsonb)
ON CONFLICT DO NOTHING;

-- Create a view for analytics
CREATE OR REPLACE VIEW feedback_analytics AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total_feedback,
    AVG(rating) as avg_rating,
    COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback,
    COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback
FROM feedback
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

-- Grant permissions (if needed for specific users)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dataprime;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dataprime;

-- Output success message
DO $$
BEGIN
    RAISE NOTICE 'DataPrime Assistant database initialized successfully!';
    RAISE NOTICE 'Tables created: feedback, query_history, background_jobs, demo_performance_data';
    RAISE NOTICE 'View created: feedback_analytics';
END $$;

