import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            sslmode="require"  # Important for AWS RDS
        )
        assert conn is not None
        conn.close()
        
        print("✅ Connection successful!")
        conn.close()

    except Exception as e:
        print("❌ Connection failed:")
        print(e)


if __name__ == "__main__":
    test_connection()