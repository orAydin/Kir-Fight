import random
import json
from datetime import datetime, date
from typing import Optional, List, Tuple, Dict, Any
from database import db_manager
from models import User, Quest, UserQuest, Challenge
from config import config
import logging

logger = logging.getLogger(__name__)

class UserService:
    @staticmethod
    def get_or_create_user(user_id: str, group_id: str, username: str) -> User:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM users WHERE user_id = ? AND group_id = ?",
                (user_id, group_id)
            )
            user_data = cursor.fetchone()
            
            if not user_data:
                cursor.execute("""
                    INSERT INTO users (user_id, group_id, username, length, last_growth)
                    VALUES (?, ?, ?, 0, NULL)
                """, (user_id, group_id, username))
                conn.commit()
                
                return User(user_id=user_id, group_id=group_id, username=username)
            else:
                # Update username if changed
                if user_data['username'] != username:
                    cursor.execute(
                        "UPDATE users SET username = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND group_id = ?",
                        (username, user_id, group_id)
                    )
                    conn.commit()
                
                return User(**dict(user_data))
    
    @staticmethod
    def can_grow_today(user: User) -> bool:
        today = str(date.today())
        return user.last_growth != today
    
    @staticmethod
    def grow_user(user_id: str, group_id: str, username: str) -> Tuple[bool, str, int, int]:
        user = UserService.get_or_create_user(user_id, group_id, username)
        
        if not UserService.can_grow_today(user):
            return False, "⚠️ تو امروز کیرتو بزرگ کردی! فردا دوباره بیا", 0, user.length
        
        growth = random.randint(config.min_daily_growth, config.max_daily_growth)
        new_length = user.length + growth
        today = str(date.today())
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET length = ?, last_growth = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND group_id = ?
            """, (new_length, today, user_id, group_id))
            conn.commit()
        
        # Check for quest progress
        QuestService.update_quest_progress(user_id, group_id, 'daily_growth', 1)
        QuestService.update_quest_progress(user_id, group_id, 'total_length', new_length)
        
        return True, f"🌱 کیرت {growth} سانتی‌متر بزرگ شد!\n📏 طول جدید: {new_length} سانتی‌متر", growth, new_length
    
    @staticmethod
    def get_leaderboard(group_id: str, limit: int = None) -> List[User]:
        limit = limit or config.leaderboard_limit
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM users WHERE group_id = ? 
                ORDER BY length DESC LIMIT ?
            """, (group_id, limit))
            
            return [User(**dict(row)) for row in cursor.fetchall()]
    
    @staticmethod
    def get_user_stats(user_id: str, group_id: str) -> Optional[User]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE user_id = ? AND group_id = ?",
                (user_id, group_id)
            )
            row = cursor.fetchone()
            return User(**dict(row)) if row else None

class ChallengeService:
    @staticmethod
    def can_challenge(challenger_id: str, opponent_id: str, group_id: str, amount: int) -> Tuple[bool, str]:
        if challenger_id == opponent_id:
            return False, "⚠️ نمیتونی با خودت چالش کنی"
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE (user_id = ? OR user_id = ?) AND group_id = ?",
                (challenger_id, opponent_id, group_id)
            )
            users = {row['user_id']: dict(row) for row in cursor.fetchall()}
        
        if len(users) != 2:
            return False, "⚠️ هر دو کاربر باید در مسابقه شرکت کرده باشند"
        
        challenger = users.get(challenger_id)
        opponent = users.get(opponent_id)
        
        if challenger['length'] < amount:
            return False, f"⚠️ {challenger['username']} به اندازه کافی سانتی‌متر برای چالش نداری!"
        
        if opponent['length'] < amount:
            return False, f"⚠️ {opponent['username']} به اندازه کافی سانتی‌متر برای چالش نداره!"
        
        return True, "OK"
    
    @staticmethod
    def execute_challenge(challenger_id: str, opponent_id: str, group_id: str, amount: int) -> Tuple[str, str, int, int]:
        winner_id = random.choice([challenger_id, opponent_id])
        loser_id = opponent_id if winner_id == challenger_id else challenger_id
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current user data
            cursor.execute(
                "SELECT * FROM users WHERE (user_id = ? OR user_id = ?) AND group_id = ?",
                (challenger_id, opponent_id, group_id)
            )
            users = {row['user_id']: dict(row) for row in cursor.fetchall()}
            
            winner_new_length = users[winner_id]['length'] + amount
            loser_new_length = max(0, users[loser_id]['length'] - amount)
            
            # Update lengths and stats
            cursor.execute("""
                UPDATE users SET 
                    length = ?, 
                    total_challenges = total_challenges + 1,
                    challenges_won = challenges_won + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND group_id = ?
            """, (winner_new_length, 1, winner_id, group_id))
            
            cursor.execute("""
                UPDATE users SET 
                    length = ?, 
                    total_challenges = total_challenges + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND group_id = ?
            """, (loser_new_length, loser_id, group_id))
            
            # Record challenge history
            cursor.execute("""
                INSERT INTO challenge_history (challenger_id, opponent_id, group_id, amount, winner_id)
                VALUES (?, ?, ?, ?, ?)
            """, (challenger_id, opponent_id, group_id, amount, winner_id))
            
            conn.commit()
            
            # Update quest progress
            QuestService.update_quest_progress(winner_id, group_id, 'challenges_won', 1)
            QuestService.update_quest_progress(loser_id, group_id, 'challenges_participated', 1)
            QuestService.update_quest_progress(winner_id, group_id, 'challenges_participated', 1)
            
            return winner_id, loser_id, winner_new_length, loser_new_length

class QuestService:
    @staticmethod
    def get_active_quests(group_id: str) -> List[Quest]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM quests WHERE group_id = ? AND is_active = 1",
                (group_id,)
            )
            return [Quest(**dict(row)) for row in cursor.fetchall()]
    
    @staticmethod
    def get_user_quest_progress(user_id: str, group_id: str) -> Dict[int, UserQuest]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_quests WHERE user_id = ? AND group_id = ?",
                (user_id, group_id)
            )
            return {row['quest_id']: UserQuest(**dict(row)) for row in cursor.fetchall()}
    
    @staticmethod
    def update_quest_progress(user_id: str, group_id: str, quest_type: str, value: int):
        active_quests = QuestService.get_active_quests(group_id)
        
        for quest in active_quests:
            if quest.quest_type == quest_type:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Get or create user quest progress
                    cursor.execute(
                        "SELECT * FROM user_quests WHERE user_id = ? AND group_id = ? AND quest_id = ?",
                        (user_id, group_id, quest.quest_id)
                    )
                    user_quest = cursor.fetchone()
                    
                    if not user_quest:
                        cursor.execute("""
                            INSERT INTO user_quests (user_id, group_id, quest_id, progress)
                            VALUES (?, ?, ?, ?)
                        """, (user_id, group_id, quest.quest_id, value))
                    else:
                        new_progress = user_quest['progress'] + value
                        completed = new_progress >= quest.target_value
                        
                        cursor.execute("""
                            UPDATE user_quests SET 
                                progress = ?, 
                                completed = ?,
                                completed_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE completed_at END
                            WHERE user_id = ? AND group_id = ? AND quest_id = ?
                        """, (new_progress, completed, completed, user_id, group_id, quest.quest_id))
                        
                        # Award quest reward if completed
                        if completed and not user_quest['completed']:
                            cursor.execute("""
                                UPDATE users SET length = length + ?, updated_at = CURRENT_TIMESTAMP
                                WHERE user_id = ? AND group_id = ?
                            """, (quest.reward, user_id, group_id))
                    
                    conn.commit()
    
    @staticmethod
    def create_default_quests(group_id: str):
        default_quests = [
            {
                'title': 'رشد روزانه',
                'description': 'پنج روز متوالی کیرت رو بزرگ کن',
                'reward': 25,
                'quest_type': 'daily_growth',
                'target_value': 5,
                'requirements': json.dumps({'consecutive_days': True})
            },
            {
                'title': 'قهرمان چالش',
                'description': 'در ۳ چالش پیروز شو',
                'reward': 30,
                'quest_type': 'challenges_won',
                'target_value': 3,
                'requirements': json.dumps({})
            },
            {
                'title': 'کیر کلفت',
                'description': 'به طول ۱۰۰ سانتی‌متر برس',
                'reward': 50,
                'quest_type': 'total_length',
                'target_value': 100,
                'requirements': json.dumps({})
            }
        ]
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            for quest_data in default_quests:
                cursor.execute("""
                    INSERT OR IGNORE INTO quests 
                    (group_id, title, description, reward, quest_type, target_value, requirements)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    group_id, quest_data['title'], quest_data['description'],
                    quest_data['reward'], quest_data['quest_type'],
                    quest_data['target_value'], quest_data['requirements']
                ))
            conn.commit()
