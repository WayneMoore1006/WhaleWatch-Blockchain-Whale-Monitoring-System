
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME", "WhaleWatch")

connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"Trusted_Connection=yes;"
)

def run_sql(sql):
    try:
        conn = pyodbc.connect(connection_string, autocommit=True)
        cursor = conn.cursor()
        print(f"Executing: {sql}")
        cursor.execute(sql)
        print("Success!")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Already done monitored_wallets.label
    run_sql("ALTER TABLE wallet_token_holdings ALTER COLUMN token_symbol NVARCHAR(50)")
    run_sql("ALTER TABLE wallet_token_holdings ALTER COLUMN token_name NVARCHAR(200)")
    run_sql("ALTER TABLE alerts ALTER COLUMN title NVARCHAR(200)")
    run_sql("ALTER TABLE alerts ALTER COLUMN description NVARCHAR(MAX)")
