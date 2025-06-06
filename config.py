import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD_ID = int(os.getenv('GUILD_ID'))
    BANNED_ROLE_ID = int(os.getenv('BANNED_ROLE_ID'))
    RESTRICTED_ROLE_ID = int(os.getenv('RESTRICTED_ROLE_ID'))
    MONGO_URI = os.getenv('MONGO_URI')
    
    # NSFWBAN system role IDs
    NSFWBAN_MODERATOR_ROLE_ID = 1372477845997359244  # Role that can use nsfwban commands
    NSFWBAN_BANNED_ROLE_ID = int(os.getenv('BANNED_ROLE_ID'))  # Role given to NSFWBAN'd users (same as BANNED_ROLE_ID)
    
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
    
    @classmethod
    def validate(cls):
        """Validate that all required environment variables are set"""
        if not cls.TOKEN:
            raise ValueError("DISCORD_TOKEN is not set in environment variables")
        if not cls.GUILD_ID:
            raise ValueError("GUILD_ID is not set in environment variables")
        if not cls.BANNED_ROLE_ID:
            raise ValueError("BANNED_ROLE_ID is not set in environment variables")
        if not cls.RESTRICTED_ROLE_ID:
            raise ValueError("RESTRICTED_ROLE_ID is not set in environment variables")
        if not cls.MONGO_URI:
            raise ValueError("MONGO_URI is not set in environment variables") 