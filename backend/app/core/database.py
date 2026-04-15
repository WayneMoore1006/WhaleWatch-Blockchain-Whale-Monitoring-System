import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# SQL Server Connection Config
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME", "WhaleWatch")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")

# Connection string for SQL Server (using mssql+pyodbc with Windows Auth)
connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"Trusted_Connection=yes;"
    f"MARS_Connection=yes;"
)

# Use create_url for SQLAlchemy compatibility
connection_url = f"mssql+pyodbc:///?odbc_connect={connection_string}"

engine = create_engine(
    connection_url,
    echo=False,
    fast_executemany=True,   # 提升大量寫入效能
    pool_size=10,           # 常駐連線數
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
