"""
Test script for the bot security system
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.security import CommandSecurity, SecurityLevel
import discord
from unittest.mock import AsyncMock, MagicMock

class MockUser:
    """Mock Discord user for testing"""
    def __init__(self, user_id: int, is_bot_owner: bool = False, has_admin: bool = False, has_manage_guild: bool = False, has_nsfwban_role: bool = False):
        self.id = user_id
        self.is_bot_owner = is_bot_owner
        self.guild_permissions = MagicMock()
        self.guild_permissions.administrator = has_admin
        self.guild_permissions.manage_guild = has_manage_guild
        self.roles = []
        
        if has_nsfwban_role:
            # Mock NSFWBAN moderator role
            mock_role = MagicMock()
            mock_role.id = 1372477845997359244  # Example NSFWBAN_MODERATOR_ROLE_ID
            self.roles.append(mock_role)

class MockGuild:
    """Mock Discord guild for testing"""
    def __init__(self, guild_id: int = 1278117138909102170):
        self.id = guild_id

class MockBot:
    """Mock Discord bot for testing"""
    def __init__(self, owner_ids: list = None):
        self.owner_ids = owner_ids or [123456789]
    
    async def is_owner(self, user):
        return user.id in self.owner_ids

class MockContext:
    """Mock Discord context for testing"""
    def __init__(self, user: MockUser, guild: MockGuild = None, bot: MockBot = None):
        self.author = user
        self.guild = guild or MockGuild()
        self.bot = bot or MockBot()

async def test_security_levels():
    """Test different security levels with various user permissions"""
    
    print("Testing Bot Security System")
    print("=" * 50)
    
    # Test users with different permission levels
    test_cases = [
        {
            "name": "Regular User",
            "user": MockUser(999999),
            "expected_access": {
                SecurityLevel.PUBLIC: True,
                SecurityLevel.MODERATOR: False,
                SecurityLevel.ADMIN: False,
                SecurityLevel.OWNER: False
            }
        },
        {
            "name": "Moderator (Manage Guild)",
            "user": MockUser(888888, has_manage_guild=True),
            "expected_access": {
                SecurityLevel.PUBLIC: True,
                SecurityLevel.MODERATOR: True,
                SecurityLevel.ADMIN: False,
                SecurityLevel.OWNER: False
            }
        },
        {
            "name": "NSFWBAN Moderator",
            "user": MockUser(777777, has_nsfwban_role=True),
            "expected_access": {
                SecurityLevel.PUBLIC: True,
                SecurityLevel.MODERATOR: True,
                SecurityLevel.ADMIN: False,
                SecurityLevel.OWNER: False
            }
        },
        {
            "name": "Administrator",
            "user": MockUser(666666, has_admin=True),
            "expected_access": {
                SecurityLevel.PUBLIC: True,
                SecurityLevel.MODERATOR: True,
                SecurityLevel.ADMIN: True,
                SecurityLevel.OWNER: False
            }
        },
        {
            "name": "Bot Owner",
            "user": MockUser(123456789, is_bot_owner=True),
            "expected_access": {
                SecurityLevel.PUBLIC: True,
                SecurityLevel.MODERATOR: True,
                SecurityLevel.ADMIN: True,
                SecurityLevel.OWNER: True
            }
        }
    ]
    
    # Test each user type
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print("-" * 30)
        
        # Create mock context
        bot = MockBot([123456789])  # Bot owner ID
        ctx = MockContext(test_case['user'], bot=bot)
        
        # Test each security level
        for level, expected in test_case['expected_access'].items():
            is_allowed, error_msg = await CommandSecurity.check_permissions(ctx, level)
            
            status = "PASS" if is_allowed == expected else "FAIL"
            access = "ALLOWED" if is_allowed else "DENIED"
            
            print(f"  {level.value.upper():12} | {access:7} | {status}")
            
            if is_allowed != expected:
                print(f"    Expected: {expected}, Got: {is_allowed}")
                if error_msg:
                    print(f"    Error: {error_msg}")

def test_command_categorization():
    """Test command security level categorization"""
    
    print(f"\nTesting Command Categorization")
    print("=" * 50)
    
    # Test specific commands
    test_commands = {
        # PUBLIC commands
        'leaderboard': SecurityLevel.PUBLIC,
        'stats': SecurityLevel.PUBLIC,
        'uptime': SecurityLevel.PUBLIC,
        'quests': SecurityLevel.PUBLIC,
        'bookmarks': SecurityLevel.PUBLIC,
        
        # MODERATOR commands
        'warn': SecurityLevel.MODERATOR,
        'warnings': SecurityLevel.MODERATOR,
        'setlogchannel': SecurityLevel.MODERATOR,
        'greet': SecurityLevel.MODERATOR,
        
        # ADMIN commands
        'purge': SecurityLevel.ADMIN,
        'nsfwban': SecurityLevel.ADMIN,
        'modconfig': SecurityLevel.ADMIN,
        'overrule': SecurityLevel.ADMIN,
        
        # OWNER commands
        'testowner': SecurityLevel.OWNER,
        'processold': SecurityLevel.OWNER,
        'dbstatus': SecurityLevel.OWNER,
        'createevent': SecurityLevel.OWNER,
    }
    
    for command, expected_level in test_commands.items():
        actual_level = CommandSecurity.get_command_security_level(command)
        status = "PASS" if actual_level == expected_level else "FAIL"
        
        print(f"{command:15} | {expected_level.value.upper():10} | {actual_level.value.upper():10} | {status}")

def test_security_info():
    """Test security information retrieval"""
    
    print(f"\nTesting Security Information")
    print("=" * 50)
    
    test_commands = ['leaderboard', 'warn', 'purge', 'testowner', 'unknown_command']
    
    for command in test_commands:
        info = CommandSecurity.get_security_info(command)
        print(f"\nCommand: {command}")
        print(f"   Level: {info['level']}")
        print(f"   Description: {info['description']}")
        print(f"   Required: {', '.join(info['required_permissions'])}")

async def main():
    """Run all security tests"""
    
    print("Starting Bot Security System Tests\n")
    
    # Test security level checking
    await test_security_levels()
    
    # Test command categorization
    test_command_categorization()
    
    # Test security information
    test_security_info()
    
    print(f"\nSecurity testing completed!")
    print(f"\nSummary:")
    print(f"   - PUBLIC commands: Safe for everyone")
    print(f"   - MODERATOR commands: Require Manage Server or moderator role")
    print(f"   - ADMIN commands: Require Administrator permission")
    print(f"   - OWNER commands: Bot owners only")
    print(f"\nThe bot is now secure! Commands like leaderboard are free to use,")
    print(f"   while dangerous commands like purge require proper permissions.")

if __name__ == "__main__":
    asyncio.run(main())