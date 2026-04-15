
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

# SQL Server Connection Config
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME", "WhaleWatch")

connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"Trusted_Connection=yes;"
)

def migrate():
    try:
        print(f"Connecting to database {DB_NAME} on {DB_SERVER}...")
        conn = pyodbc.connect(connection_string, autocommit=True)
        cursor = conn.cursor()
        
        print("Migrating [monitored_wallets]...")
        cursor.execute("ALTER TABLE monitored_wallets ALTER COLUMN label NVARCHAR(100)")
        
        print("Migrating [wallet_token_holdings]...")
        cursor.execute("ALTER TABLE wallet_token_holdings ALTER COLUMN token_symbol NVARCHAR(50)")
        cursor.execute("ALTER TABLE wallet_token_holdings ALTER COLUMN token_name NVARCHAR(200)")
        
        print("Migrating [alerts]...")
        cursor.execute("ALTER TABLE alerts ALTER COLUMN title NVARCHAR(200)")
        cursor.execute("ALTER TABLE alerts ALTER COLUMN description NVARCHAR(MAX)")
        
        print("Migration completed successfully!")
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
