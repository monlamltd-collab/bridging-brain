#!/usr/bin/env python3
"""
Database setup - imports lender data from Excel questionnaire
"""

import pandas as pd
import sqlite3
import json
import re

def clean_column_name(col):
    """Convert Excel column names to clean database column names"""
    col = str(col).lower().strip()
    col = re.sub(r'[^a-z0-9_]', '_', col)
    col = re.sub(r'_+', '_', col)
    col = col.strip('_')
    if len(col) > 60:
        col = col[:60]
    return col

def setup_database(excel_path, db_path='lenders.db'):
    """Import lender data from Excel to SQLite"""
    
    print(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"Found {len(df)} lenders with {len(df.columns)} columns")
    
    # Create column mapping with unique names
    new_columns = []
    seen_names = {}
    for col in df.columns:
        clean_name = clean_column_name(col)
        # Handle duplicates by adding suffix
        if clean_name in seen_names:
            seen_names[clean_name] += 1
            unique_name = f"{clean_name}_{seen_names[clean_name]}"
        else:
            seen_names[clean_name] = 0
            unique_name = clean_name
        new_columns.append(unique_name)
    
    df.columns = new_columns
    
    # Ensure we have a name column
    name_cols = [c for c in df.columns if 'name' in c and 'lender' in c]
    if name_cols:
        df = df.rename(columns={name_cols[0]: 'name'})
    elif 'name_of_lender' in df.columns:
        df = df.rename(columns={'name_of_lender': 'name'})
    
    # Drop rows without a lender name
    if 'name' in df.columns:
        df = df.dropna(subset=['name'])
    
    # Create database
    conn = sqlite3.connect(db_path)
    
    # Store lenders
    df.to_sql('lenders', conn, if_exists='replace', index=False)
    
    # Create feedback table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lender_name TEXT,
            deal_type TEXT,
            rating INTEGER,
            feedback_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create conversations table for memory
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # Print column info
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(lenders)")
    columns = cursor.fetchall()
    
    print(f"\nDatabase created: {db_path}")
    print(f"Lenders table: {len(df)} rows, {len(columns)} columns")
    print("\nColumn names:")
    for i, col in enumerate(columns):
        print(f"  {i+1:3d}. {col[1]}")
    
    conn.close()
    return db_path

if __name__ == "__main__":
    import sys
    excel_path = sys.argv[1] if len(sys.argv) > 1 else "Bridging_Lenders_Questionnaire_Responses_1.xlsx"
    setup_database(excel_path)
