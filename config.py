import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class BotConfig:
    token: str
    db_file: str = 'dick_competition.db'
    port: int = 10000
    log_level: str = 'INFO'
    max_daily_growth: int = 18
    min_daily_growth: int = 1
    max_challenge_amount: int = 20
    min_challenge_amount: int = 1
    leaderboard_limit: int = 10
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        token = os.getenv('BOT_TOKEN')
        if not token:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        return cls(
            token=token,
            port=int(os.getenv('PORT', 10000)),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            max_daily_growth=int(os.getenv('MAX_DAILY_GROWTH', 18)),
            min_daily_growth=int(os.getenv('MIN_DAILY_GROWTH', 1)),
            max_challenge_amount=int(os.getenv('MAX_CHALLENGE_AMOUNT', 20)),
            min_challenge_amount=int(os.getenv('MIN_CHALLENGE_AMOUNT', 1)),
            leaderboard_limit=int(os.getenv('LEADERBOARD_LIMIT', 10))
        )

config = BotConfig.from_env()
