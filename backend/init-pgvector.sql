-- 🔍 Initialize pgvector extension for PostgreSQL
-- This script runs automatically when container starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create operator classes if they don't exist (they should be included with pgvector)
-- These are for vector similarity operations

-- Verify extension is installed
SELECT 
    extname as extension_name, 
    extversion as version,
    extowner as owner
FROM pg_extension 
WHERE extname = 'vector';

-- Test vector functionality
DO $$
DECLARE
    test_vector vector(3);
BEGIN
    -- Create a test vector to verify functionality
    test_vector := '[1.0, 2.0, 3.0]';
    
    RAISE NOTICE 'pgvector extension successfully enabled and tested';
    RAISE NOTICE 'Test vector created: %', test_vector;
    RAISE NOTICE 'Vector operations available: cosine distance (<=>), L2 distance (<->), inner product (<#>)';
END $$;
