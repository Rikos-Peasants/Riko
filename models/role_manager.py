import discord
from typing import Optional
from config import Config

class RoleManager:
    """Handles role-related operations and validations"""
    
    @staticmethod
    def has_banned_role(member: discord.Member) -> bool:
        """Check if member has the banned role"""
        banned_role = discord.utils.get(member.roles, id=Config.BANNED_ROLE_ID)
        return banned_role is not None
    
    @staticmethod
    def can_access_restricted_role(member: discord.Member) -> bool:
        """Check if member can access the restricted role"""
        return not RoleManager.has_banned_role(member)
    
    @staticmethod
    def get_restricted_role(guild: discord.Guild) -> Optional[discord.Role]:
        """Get the restricted role from the guild"""
        return discord.utils.get(guild.roles, id=Config.RESTRICTED_ROLE_ID)
    
    @staticmethod
    def get_banned_role(guild: discord.Guild) -> Optional[discord.Role]:
        """Get the banned role from the guild"""
        return discord.utils.get(guild.roles, id=Config.BANNED_ROLE_ID) 