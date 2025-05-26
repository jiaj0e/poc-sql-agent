from os import getenv
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
import time

# Load local environment variables
load_dotenv()

def test_db_connection(engine, max_retries=3, delay=2):
    """Test database connection with retries"""
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                result = conn.execute(sqlalchemy.text("SELECT 1")).scalar()
                print(f"Database connection successful! Test query result: {result}")
                return True
        except SQLAlchemyError as e:
            print(f"Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise
    return False

# Database configuration
DB_PASSWORD = getenv('DB_PASSWORD', 'postgres')
DB_USER = getenv('DB_USER', 'postgres')
DB_ENDPOINT = getenv('DB_ENDPOINT', 'localhost')
DB_PORT = getenv('DB_PORT', '5432')
DB_NAME = getenv('DB_NAME', 'test')

# Construct database URL
__db_url = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_ENDPOINT}:{DB_PORT}/{DB_NAME}'
print(f'Connecting to database: {__db_url}')

# Create engine with connection pooling
ENGINE = sqlalchemy.create_engine(
    __db_url,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30
)

# Test the connection
test_db_connection(ENGINE)