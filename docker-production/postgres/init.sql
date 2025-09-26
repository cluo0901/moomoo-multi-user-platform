-- PostgreSQL initialization script for production moomoo platform
-- Creates additional production configurations

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create additional indexes for performance
-- These will be created after tables are created by the application

-- Set production-optimized settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Create monitoring user for Prometheus
CREATE USER prometheus_user WITH PASSWORD 'prometheus_monitor_password';
GRANT pg_monitor TO prometheus_user;

-- Select the database to be sure
SELECT current_database();