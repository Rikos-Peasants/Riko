import os
from dotenv import load_dotenv
from typing import Optional, List

# Load environment variables
load_dotenv()

def get_int_env(key: str, default: Optional[int] = None) -> int:
    """Get an integer from environment variables with proper error handling"""
    value = os.getenv(key)
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"Environment variable {key} is required but not set")
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable {key} must be a valid integer, got: {value}")

class Config:
    TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD_ID = get_int_env('GUILD_ID')
    BANNED_ROLE_ID = get_int_env('BANNED_ROLE_ID')
    RESTRICTED_ROLE_ID = get_int_env('RESTRICTED_ROLE_ID')
    MONGO_URI = os.getenv('MONGO_URI')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # For YouTube video announcements
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')  # For YouTube Data API
    
    # NSFWBAN system role IDs
    NSFWBAN_MODERATOR_ROLE_ID = 1372477845997359244  # Role that can use nsfwban commands
    NSFWBAN_BANNED_ROLE_ID = get_int_env('BANNED_ROLE_ID')  # Role given to NSFWBAN'd users (same as BANNED_ROLE_ID)
    
    # Image reaction channels
    IMAGE_REACTION_CHANNELS = [
        1282209034916855809,
        1378693276206370969
    ]
    
    # Chat channels for redirecting conversations
    CHAT_CHANNELS = [
        1278117139428933647,
        1278117139428933649
    ]
    
    # Warning log channel (can be configured with /setlogchannel)
    WARNING_LOG_CHANNEL_ID: Optional[int] = None  # Will be set dynamically
    
    @classmethod
    def validate(cls):
        """Validate that all required environment variables are set"""
        required_vars = [
            ('DISCORD_TOKEN', cls.TOKEN),
            ('GUILD_ID', cls.GUILD_ID),
            ('BANNED_ROLE_ID', cls.BANNED_ROLE_ID),
            ('RESTRICTED_ROLE_ID', cls.RESTRICTED_ROLE_ID),
            ('MONGO_URI', cls.MONGO_URI)
        ]
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}") 