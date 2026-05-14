"""
Update admin_notifications table to add reply functionality
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def update_schema():
    """Add admin_reply and replied_at columns to admin_notifications table"""
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("🔄 Updating admin_notifications table schema...")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='admin_notifications' 
            AND column_name IN ('admin_reply', 'replied_at')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add admin_reply column if it doesn't exist
        if 'admin_reply' not in existing_columns:
            cursor.execute("""
                ALTER TABLE admin_notifications 
                ADD COLUMN admin_reply TEXT
            """)
            print("✅ Added admin_reply column")
        else:
            print("ℹ️  admin_reply column already exists")
        
        # Add replied_at column if it doesn't exist
        if 'replied_at' not in existing_columns:
            cursor.execute("""
                ALTER TABLE admin_notifications 
                ADD COLUMN replied_at TIMESTAMP
            """)
            print("✅ Added replied_at column")
        else:
            print("ℹ️  replied_at column already exists")
        
        conn.commit()
        print("✅ Schema update completed successfully!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Admin Notifications Schema Update")
    print("=" * 50)
    update_schema()
