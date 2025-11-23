#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Shared span attributes for consistent Flow Alert triggering.
Ensures all services use identical attribute names for OpenTelemetry spans.
"""

import time
import os
import structlog

logger = structlog.get_logger()


class DemoSpanAttributes:
    """Consistent span attribute setters for Flow Alert compatibility."""
    
    @staticmethod
    def set_slow_query(span, duration_ms, missing_index, rows_scanned=10000):
        """
        Set slow query attributes for Flow Alert detection.
        
        These exact attribute names are required for Flow Alerts to trigger:
        - db.slow_query: Boolean flag
        - db.duration_ms: Query duration
        - db.full_table_scan: Boolean for full scan detection
        - db.missing_index: Name of missing index
        - db.rows_scanned: Number of rows examined
        """
        span.set_attribute("db.slow_query", True)
        span.set_attribute("db.duration_ms", duration_ms)
        span.set_attribute("db.full_table_scan", True)
        span.set_attribute("db.missing_index", missing_index)
        span.set_attribute("db.rows_scanned", rows_scanned)
        
        logger.warning(
            "demo_slow_query_triggered",
            duration_ms=duration_ms,
            missing_index=missing_index,
            rows_scanned=rows_scanned
        )
    
    @staticmethod
    def set_pool_exhausted(span, max_conn, wait_ms, rejected_count=0):
        """
        Set connection pool exhaustion attributes for Flow Alert.
        
        Critical attributes:
        - db.connection.pool.exhausted: Boolean flag
        - db.connection.pool.size: Max pool size
        - db.connection.pool.wait_time_ms: Timeout duration
        - db.connection.pool.rejected_count: Number of rejections
        """
        span.set_attribute("db.connection.pool.exhausted", True)
        span.set_attribute("db.connection.pool.size", max_conn)
        span.set_attribute("db.connection.pool.wait_time_ms", wait_ms)
        span.set_attribute("db.connection.pool.rejected_count", rejected_count)
        
        logger.error(
            "demo_pool_exhaustion",
            max_connections=max_conn,
            wait_time_ms=wait_ms,
            rejected_count=rejected_count
        )
    
    @staticmethod
    def set_checkout_failed(span, order_id, user_id, total, failure_reason):
        """
        Set checkout failure attributes for business impact tracking.
        
        Attributes:
        - checkout.failed: Boolean flag
        - checkout.failure_reason: Root cause
        - checkout.order_id: Failed order ID
        - checkout.user_id: Affected user
        - checkout.total: Revenue lost
        - checkout.cart_abandoned: Boolean flag
        """
        span.set_attribute("checkout.failed", True)
        span.set_attribute("checkout.failure_reason", failure_reason)
        span.set_attribute("checkout.order_id", order_id)
        span.set_attribute("checkout.user_id", user_id)
        span.set_attribute("checkout.total", total)
        span.set_attribute("checkout.cart_abandoned", True)
        
        logger.error(
            "demo_checkout_failed",
            order_id=order_id,
            user_id=user_id,
            total=total,
            reason=failure_reason
        )


def calculate_demo_minute():
    """
    Calculate elapsed minutes using Unix timestamp (more reliable than string parsing).
    
    Uses DEMO_START_TIMESTAMP environment variable (Unix epoch seconds).
    This avoids issues with:
    - Date changes (e.g., demo crossing midnight)
    - Timezone differences
    - String parsing errors
    """
    demo_mode = os.getenv('DEMO_MODE', 'off')
    if demo_mode != 'blackfriday':
        return 0
    
    try:
        # Use Unix timestamp instead of string time parsing
        demo_start_ts = os.getenv('DEMO_START_TIMESTAMP', '')
        if not demo_start_ts:
            logger.warning("demo_start_timestamp_missing")
            return 0
        
        start = float(demo_start_ts)
        elapsed = time.time() - start
        return max(0, int(elapsed / 60))
    except Exception as e:
        logger.warning("demo_minute_calculation_error", error=str(e))
        return 0


def is_demo_mode():
    """Check if running in Black Friday demo mode."""
    return os.getenv('DEMO_MODE', 'off') == 'blackfriday'


def get_demo_phase(demo_minute):
    """
    Get current demo phase name.
    
    Phases:
    - ramp (0-10 min): Traffic increasing
    - peak (10-15 min): Normal operations at peak load
    - degradation (15-20 min): Database issues emerging
    - critical (20-30 min): Full failure mode
    """
    if demo_minute < 10:
        return "ramp"
    elif demo_minute < 15:
        return "peak"
    elif demo_minute < 20:
        return "degradation"
    else:
        return "critical"

