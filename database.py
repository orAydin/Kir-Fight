import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from config import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_file: str = None):
        self.db_file = db_file or config.db_file
        
    @contextmanager
    def get_connection(self):
        connection = None
        try:
            connection = sqlite3.connect(self.db_file)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
        except sqlite3.Error as e:
            if connection:
                connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def initialize_database(self):
        """Initialize all database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT,
                    group_id TEXT,
                    username TEXT,
                    length INTEGER DEFAULT 0,
                    last_growth DATE,
                    total_challenges INTEGER DEFAULT 0,
                    challenges_won INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, group_id)
                )
            """)
            
            # Quests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quests (
                    quest_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    reward INTEGER NOT NULL,
                    requirements TEXT,
                    quest_type TEXT DEFAULT 'manual',
                    target_value INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User quests progress
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_quests (
                    user_id TEXT,
                    group_id TEXT,
                    quest_id INTEGER,
                    progress INTEGER DEFAULT 0,
                    completed BOOLEAN DEFAULT 0,
                    completed_at TIMESTAMP,
                    PRIMARY KEY (user_id, group_id, quest_id),
                    FOREIGN KEY (quest_id) REFERENCES quests(quest_id) ON DELETE CASCADE
                )
            """)
            
            # Challenge history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS challenge_history (
                    challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenger_id TEXT,
                    opponent_id TEXT,
                    group_id TEXT,
                    amount INTEGER,
                    winner_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Group settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_settings (
                    group_id TEXT PRIMARY KEY,
                    group_name TEXT,
                    daily_growth_enabled BOOLEAN DEFAULT 1,
                    challenges_enabled BOOLEAN DEFAULT 1,
                    quests_enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def migrate_database(self):
        """Handle database migrations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check and add missing columns
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            migrations = [
                ("total_challenges", "ALTER TABLE users ADD COLUMN total_challenges INTEGER DEFAULT 0"),
                ("challenges_won", "ALTER TABLE users ADD COLUMN challenges_won INTEGER DEFAULT 0"),
                ("updated_at", "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            ]
            
            for column_name, migration_sql in migrations:
                if column_name not in columns:
                    try:
                        cursor.execute(migration_sql)
                        logger.info(f"Added {column_name} column to users table")
                    except sqlite3.Error as e:
                        logger.error(f"Migration error for {column_name}: {e}")
            
            conn.commit()

# Global database manager instance
db_manager = DatabaseManager()
