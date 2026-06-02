import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "finance.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 1. Table for tracking manual/WhatsApp expenses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            sender TEXT,
            raw_text TEXT,
            amount REAL,
            category TEXT,
            clean_description TEXT
        )
    """)
    # 2. Table for storing uploaded Zerodha positions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            symbol TEXT PRIMARY KEY,
            quantity INTEGER,
            avg_cost REAL,
            current_value REAL,
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_expense(sender, raw_text, amount, category, clean_description):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO expenses (timestamp, sender, raw_text, amount, category, clean_description)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, sender, raw_text, amount, category, clean_description))
    conn.commit()
    conn.close()

def save_portfolio_row(symbol, qty, avg_cost, curr_val):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO portfolio (symbol, quantity, avg_cost, current_value, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            quantity=excluded.quantity,
            avg_cost=excluded.avg_cost,
            current_value=excluded.current_value,
            last_updated=excluded.last_updated
    """, (symbol, qty, avg_cost, curr_val, timestamp))
    conn.commit()
    conn.close()

def get_all_expenses():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM expenses", conn)
    conn.close()
    return df

def get_portfolio():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM portfolio", conn)
    conn.close()
    return df

init_db()