-- Migration 002: Add index for api_usage_log and fix gap in sequence
CREATE INDEX IF NOT EXISTS idx_api_usage_provider ON api_usage_log(provider, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_request_id ON api_usage_log(request_id);
