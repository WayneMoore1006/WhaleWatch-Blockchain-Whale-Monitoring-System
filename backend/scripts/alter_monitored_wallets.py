import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal

def alter_schema():
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(text("""
            SELECT count(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'monitored_wallets' 
            AND COLUMN_NAME = 'sort_index'
        """))
        exists = result.scalar() > 0
        if not exists:
            db.execute(text("ALTER TABLE monitored_wallets ADD sort_index INT DEFAULT 0"))
            db.commit()
            print("Successfully added sort_index to monitored_wallets")
        else:
            print("sort_index already exists")
    except Exception as e:
        print(f"Error altering schema: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    alter_schema()
