
import sys
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def scrub():
    print("=== Whale Watching Intelligence Scrubber ===")
    print("This script will wipe all monitored wallets, transactions, and token holdings from your LOCAL database.")
    print("Use this BEFORE generating a SQL dump or pushing to GitHub to protect your 'intelligence'.\n")
    
    server = os.getenv("DB_SERVER", "localhost")
    database = os.getenv("DB_NAME", "WhaleWatch")
    
    # Using Windows Auth for safety/ease
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"Trusted_Connection=yes;"
    )
    
    confirm = input("Are you sure you want to WIPE all wallet data? (y/n): ")
    if confirm.lower() != 'y':
        print("Scrubbing cancelled.")
        return

    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        print("Cleaning monitored_wallets (and cascading to transactions/holdings)...")
        # Assuming CASCADE is set on Foreign Keys (as in migration_v2)
        # If not, we wipe them individually
        cursor.execute("DELETE FROM wallet_token_holdings")
        cursor.execute("DELETE FROM wallet_transactions")
        cursor.execute("DELETE FROM wallet_daily_stats")
        cursor.execute("DELETE FROM alerts")
        cursor.execute("DELETE FROM monitored_wallets")
        
        print("✅ Success: All intelligence data has been scrubbed from the local DB.")
        print("Your database schema is now clean and safe to share.")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error during scrubbing: {e}")

if __name__ == "__main__":
    scrub()
