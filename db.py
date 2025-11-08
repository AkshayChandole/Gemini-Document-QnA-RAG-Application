from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import text
from pgvector.sqlalchemy import Vector
from dotenv import load_dotenv
import urllib.parse
import os

# Load environment variables
load_dotenv()

# Supabase database credentials
POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME")  
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD") 
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "postgres")

# Encode password (for special characters)
encoded_password = urllib.parse.quote_plus(POSTGRES_PASSWORD)

# Construct Supabase database URL
database_url = (
    f"postgresql://{POSTGRES_USERNAME}:{encoded_password}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{DATABASE_NAME}?sslmode=require"
)

# Create SQLAlchemy engine
engine = create_engine(database_url, echo=False, future=True)

# Session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Define models
Base = declarative_base()

class File(Base):
    __tablename__ = "files"
    file_id = Column(Integer, primary_key=True)
    file_name = Column(String(255))
    file_content = Column(Text)

class FileChunk(Base):
    __tablename__ = "file_chunks"
    chunk_id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.file_id"))
    chunk_text = Column(Text)
    embedding_vector = Column(Vector(384))

# Ensure pgvector extension exists (safe to run multiple times)
with engine.begin() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

# Create tables (if not exist)
try:
    Base.metadata.create_all(engine)
    print("✅ Tables created successfully in Supabase")
except Exception as e:
    print(f"❌ Error creating tables: {e}")
