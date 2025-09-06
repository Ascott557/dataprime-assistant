#!/usr/bin/env python3
import sqlite3
import os
import sys

# Add path for telemetry
sys.path.append('.')
from shared_telemetry_working import ensure_telemetry_initialized
from opentelemetry import trace

print('🔍 DEBUGGING SQLITE INSTRUMENTATION')
print('='*50)

# Initialize telemetry like the storage service does
print('1. Initializing telemetry...')
telemetry_success = ensure_telemetry_initialized()
print(f'   Telemetry initialized: {telemetry_success}')

# Get tracer
tracer = trace.get_tracer(__name__)

print('\n2. Testing SQLite operations with tracing...')

# Test if SQLite operations create spans
with tracer.start_as_current_span('test_sqlite_operations') as root_span:
    print('   Created root span')
    
    # Open database connection
    conn = sqlite3.connect('test_debug.db')
    cursor = conn.cursor()
    
    print('   Opened SQLite connection')
    
    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            data TEXT
        )
    ''')
    print('   Executed CREATE TABLE')
    
    # Insert data
    cursor.execute('INSERT INTO test_table (data) VALUES (?)', ('test_data',))
    print('   Executed INSERT')
    
    # Select data
    cursor.execute('SELECT * FROM test_table')
    results = cursor.fetchall()
    print(f'   Executed SELECT, got {len(results)} rows')
    
    conn.commit()
    conn.close()
    print('   Closed connection')

print('\n3. Analysis:')
print('   If SQLite3Instrumentor was working, we should see separate spans for:')
print('   - CREATE TABLE operation')
print('   - INSERT operation') 
print('   - SELECT operation')

print('\n4. Possible issues:')
print('   - SQLite3Instrumentor may not be actually instrumenting connections')
print('   - May need to use specific SQLite connection methods')
print('   - Instrumentation might only work with certain SQLite usage patterns')
print('   - Storage service might not be using traced SQLite calls')

# Clean up
if os.path.exists('test_debug.db'):
    os.remove('test_debug.db')
    print('\n   Cleaned up test database')
