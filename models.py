from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json

@dataclass
class User:
    user_id: str
    group_id: str
    username: str
    length: int = 0
    last_growth: Optional[str] = None
    total_challenges: int = 0
    challenges_won: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def win_rate(self) -> float:
        if self.total_challenges == 0:
            return 0.0
        return (self.challenges_won / self.total_challenges) * 100

@dataclass
class Quest:
    quest_id: int
    group_id: str
    title: str
    description: str
    reward: int
    requirements: str
    quest_type: str = 'manual'
    target_value: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    @property
    def requirements_dict(self) -> Dict[str, Any]:
        try:
            return json.loads(self.requirements) if self.requirements else {}
        except json.JSONDecodeError:
            return {}

@dataclass
class UserQuest:
    user_id: str
    group_id: str
    quest_id: int
    progress: int = 0
    completed: bool = False
    completed_at: Optional[datetime] = None
    
    @property
    def progress_percentage(self) -> float:
        return min(100.0, (self.progress / max(1, self.target_value)) * 100)

@dataclass
class Challenge:
    challenge_id: int
    challenger_id: str
    opponent_id: str
    group_id: str
    amount: int
    winner_id: Optional[str] = None
    created_at: Optional[datetime] = None
