#!/usr/bin/env python3
"""
Test script to check PostgreSQL database connection
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_database_connection():
    """Test the database connection"""
    
    # Get database URL from environment or use default
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:password@localhost:5432/resume_matcher"
    )
    
    print(f"Testing connection to: {DATABASE_URL}")
    print("-" * 50)
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version_row = result.fetchone()
            if version_row:
                version = version_row[0]
                print(f"✅ Database connection successful!")
                print(f"📊 PostgreSQL version: {version}")
            else:
                print(f"✅ Database connection successful!")
                print(f"📊 PostgreSQL version: Unknown")
            
            # Test if our tables exist
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Existing tables: {tables}")
            
            return True
            
    except SQLAlchemyError as e:
        print(f"❌ Database connection failed!")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1) 