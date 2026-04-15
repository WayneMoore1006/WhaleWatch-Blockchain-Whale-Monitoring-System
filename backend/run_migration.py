import os
from sqlalchemy import text
from app.core.database import SessionLocal

def run_migration():
    with open("migration_v2.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    db = SessionLocal()
    # SQL Server GO separator logic
    batches = [b for b in sql.split("GO") if b.strip()]
    if not batches:
        batches = [sql] # If no GO statements

    try:
        if batches == [sql]:
            for stmt in sql.split(';'):
                if stmt.strip():
                    db.execute(text(stmt))
        else:
            for batch in batches:
                db.execute(text(batch))
        db.commit()
        print("Migration applied successfully!")
    except Exception as e:
        db.rollback()
        with open("migration_error.txt", "w", encoding="utf-8") as err_f:
            err_f.write(str(e))
        print("Migration error written to file")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
