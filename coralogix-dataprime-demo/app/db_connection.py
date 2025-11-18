#!/usr/bin/env python3
"""
Database Connection Pool Manager for E-commerce Product Service

Provides PostgreSQL connection pool with:
- 100 max connections (matches demo requirements)
- 3-second connection timeout (matches demo error messages)
- Connection health tracking
- Manual instrumentation of pooled connections
"""

import os
import psycopg2
from psycopg2 import pool
import logging

logger = logging.getLogger(__name__)

# Global connection pool instance
_db_pool = None

def initialize_db_pool():
    """
    Initialize the PostgreSQL connection pool.
    
    Configuration matches demo requirements:
    - Max connections: 100 (Scene 10: "capacity of 100 connections")
    - Timeout: 3 seconds (Scene 10: "within 3000ms")
    """
    global _db_pool
    
    if _db_pool is not None:
        logger.info("Database pool already initialized")
        return _db_pool
    
    try:
        _db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=5,
            maxconn=int(os.getenv("DB_MAX_CONNECTIONS", "100")),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "productcatalog"),
            user=os.getenv("DB_USER", "dbadmin"),
            password=os.getenv("DB_PASSWORD", "demo_password"),
            connect_timeout=3  # 3-second timeout for demo
        )
        
        logger.info(
            f"✅ Database pool initialized: "
            f"min={_db_pool.minconn}, max={_db_pool.maxconn}, "
            f"host={os.getenv('DB_HOST')}"
        )
        
        return _db_pool
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database pool: {e}")
        raise


def get_db_pool():
    """Get the global database pool instance."""
    if _db_pool is None:
        return initialize_db_pool()
    return _db_pool


def get_connection():
    """
    Get a connection from the pool.
    
    NOTE: We use MANUAL OpenTelemetry spans in the service layer (not auto-instrumentation).
    This matches the proven SQLite pattern - explicit spans with comprehensive attributes.
    
    Raises:
        Exception: "ConnectionError: Could not acquire connection within 3000ms"
                   if pool is exhausted or timeout occurs
    """
    try:
        pool_instance = get_db_pool()
        conn = pool_instance.getconn()
        
        if conn is None:
            # Pool exhausted - matches demo Scene 10 error message
            raise Exception("ConnectionError: Could not acquire connection within 3000ms")
        
        return conn
        
    except psycopg2.pool.PoolError as e:
        # Pool exhausted or other pool-related error
        logger.error(f"Pool error: {e}")
        raise Exception("ConnectionError: Could not acquire connection within 3000ms")
        
    except Exception as e:
        # Connection timeout or other errors
        logger.error(f"Connection error: {e}")
        raise Exception(f"ConnectionError: Could not acquire connection within 3000ms")


def return_connection(conn):
    """
    Return a connection to the pool.
    
    Args:
        conn: Database connection to return
    """
    if conn is not None:
        try:
            pool_instance = get_db_pool()
            pool_instance.putconn(conn)
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")


def get_pool_stats():
    """
    Get current pool statistics.
    
    Returns:
        dict: Pool statistics including active connections and utilization
    """
    try:
        pool_instance = get_db_pool()
        
        # Access pool internals (ThreadedConnectionPool tracks these)
        active = len([c for c in pool_instance._used.values() if c is not None])
        max_conn = pool_instance.maxconn
        utilization = (active / max_conn * 100) if max_conn > 0 else 0
        
        return {
            "active_connections": active,
            "max_connections": max_conn,
            "utilization_percent": round(utilization, 2),
            "available_connections": max_conn - active
        }
        
    except Exception as e:
        logger.error(f"Error getting pool stats: {e}")
        return {
            "active_connections": 0,
            "max_connections": 100,
            "utilization_percent": 0,
            "available_connections": 100,
            "error": str(e)
        }


def close_all_connections():
    """Close all connections in the pool (for cleanup)."""
    global _db_pool
    
    if _db_pool is not None:
        try:
            _db_pool.closeall()
            logger.info("✅ All database connections closed")
            _db_pool = None
        except Exception as e:
            logger.error(f"Error closing connections: {e}")


