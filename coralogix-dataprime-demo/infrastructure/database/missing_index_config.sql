-- =============================================================================
-- Black Friday Demo: Missing Index Scenario
-- =============================================================================
--
-- SCENARIO: Database team forgot to create indexes on the products table
-- before Black Friday launch. This is a common production issue.
--
-- EXPECTED IMPACT:
--   - Product category queries will perform full table scans
--   - Query duration will increase from ~50ms to 2500ms+
--   - Database CPU utilization will spike to 80-90%
--   - P95 latency will degrade significantly
--   - Users will experience slow page loads
--
-- TIMELINE:
--   - Minutes 0-10: Queries slow but tolerable (500ms)
--   - Minutes 10-15: Noticeable degradation (1000ms)
--   - Minutes 15+: Critical slowness (2500ms+)
--
-- =============================================================================

-- Drop the category index (causes full table scans)
DROP INDEX IF EXISTS idx_products_category;

-- Drop the stock quantity index (inventory queries affected)
DROP INDEX IF EXISTS idx_products_stock_quantity;

-- Show confirmation
SELECT 'Missing index configuration applied - indexes dropped' AS status;

-- Verify indexes are gone
SELECT 
    schemaname, 
    tablename, 
    indexname 
FROM pg_indexes 
WHERE tablename = 'products' 
  AND schemaname = 'public';

-- =============================================================================
-- TO RESTORE (for cleanup after demo):
-- =============================================================================
--
-- CREATE INDEX idx_products_category ON products(category);
-- CREATE INDEX idx_products_stock_quantity ON products(stock_quantity);
--
-- Expected restoration time: ~500ms for both indexes
-- =============================================================================

