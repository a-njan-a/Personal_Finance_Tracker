import os
import urllib.parse as urlparse
import psycopg2
import pandas as pd
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Establishes a secure connection to the cloud PostgreSQL database."""
    # Parse the connection URL to ensure compatibility with all hosting environments
    url = urlparse.urlparse(DATABASE_URL)
    dbname = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
        sslmode="require" # Neon requires SSL encryption for connections
    )

def init_db():
    """Initializes tables using PostgreSQL data types (SERIAL instead of AUTOINCREMENT)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Expense logs table configuration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            sender TEXT,
            raw_text TEXT,
            amount REAL,
            category TEXT,
            clean_description TEXT
        )
    """)
    
    # Portfolio holdings table configuration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            symbol TEXT PRIMARY KEY,
            quantity INTEGER,
            avg_cost REAL,
            current_value REAL,
            last_updated TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def insert_expense(sender, raw_text, amount, category, clean_description, timestamp=datetime.now()):
    conn = get_connection()
    cursor = conn.cursor()
    # timestamp = datetime.now()
    cursor.execute("""
        INSERT INTO expenses (timestamp, sender, raw_text, amount, category, clean_description)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (timestamp, sender, raw_text, amount, category, clean_description))
    conn.commit()
    cursor.close()
    conn.close()

def save_portfolio_row(symbol, qty, avg_cost, curr_val):
    """Saves or updates investment assets using PostgreSQL upsert syntax (ON CONFLICT)."""
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now()
    cursor.execute("""
        INSERT INTO portfolio (symbol, quantity, avg_cost, current_value, last_updated)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (symbol) DO UPDATE SET
            quantity = EXCLUDED.quantity,
            avg_cost = EXCLUDED.avg_cost,
            current_value = EXCLUDED.current_value,
            last_updated = EXCLUDED.last_updated
    """, (symbol, qty, avg_cost, curr_val, timestamp))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_expenses():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM expenses", conn)
    conn.close()
    return df

def get_portfolio():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM portfolio", conn)
    conn.close()
    return df

# Initialize cloud structures on runtime import
init_db()