#!/usr/bin/env python3
"""
Diagnostic script for Riko Discord Bot
Use this to test and troubleshoot bot issues
"""
import asyncio
import discord
from discord.ext import commands
from config import Config
import logging

# Set up logging to see more details
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def diagnose_bot():
    """Run comprehensive bot diagnostics"""
    print("🔍 Riko Bot Diagnostic Tool")
    print("=" * 50)
    
    try:
        # Create bot instance with same settings as main bot
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        bot = commands.Bot(
            command_prefix='R!',
            intents=intents,
            case_insensitive=True
        )
        
        # Add a simple test command
        @bot.hybrid_command(name="test", description="Test command to verify bot functionality")
        async def test_command(ctx):
            await ctx.send("✅ Bot is working! Both text and slash commands are functional.")
        
        # Add another test command
        @bot.command(name="texttest")
        async def text_test_command(ctx):
            await ctx.send("✅ Text-only command working!")
        
        @bot.event
        async def on_ready():
            print(f"✅ Bot connected as: {bot.user}")
            print(f"📊 Bot ID: {bot.user.id}")
            print(f"🏠 Guilds: {len(bot.guilds)}")
            
            for guild in bot.guilds:
                print(f"   - {guild.name} (ID: {guild.id})")
            
            # Check bot permissions
            target_guild = bot.get_guild(Config.GUILD_ID)
            if target_guild:
                bot_member = target_guild.get_member(bot.user.id)
                if bot_member:
                    perms = bot_member.guild_permissions
                    print(f"\n🔐 Bot permissions in {target_guild.name}:")
                    print(f"   - Send Messages: {perms.send_messages}")
                    print(f"   - Use Slash Commands: {perms.use_slash_commands}")
                    print(f"   - Add Reactions: {perms.add_reactions}")
                    print(f"   - Read Message History: {perms.read_message_history}")
                    print(f"   - Embed Links: {perms.embed_links}")
                    print(f"   - Attach Files: {perms.attach_files}")
            
            # Generate proper invite URL
            invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=268437568&scope=bot%20applications.commands"
            
            print(f"\n🔗 CRITICAL: Use this invite URL to fix slash commands:")
            print(f"{invite_url}")
            print("\n⚠️  If slash commands show 'Unknown integration', the bot needs to be")
            print("⚠️  re-invited with the 'applications.commands' scope using the URL above!")
            
            # Test command registration
            print(f"\n📝 Registered Commands:")
            print(f"   - Text commands: {len(bot.commands)}")
            for cmd in bot.commands:
                print(f"     * R!{cmd.name}")
            
            print(f"   - App commands (slash): {len(bot.tree.get_commands())}")
            for cmd in bot.tree.get_commands():
                print(f"     * /{cmd.name}")
            
            # Try to sync commands
            print(f"\n🔄 Testing command sync...")
            try:
                # Test guild sync
                guild_obj = discord.Object(id=Config.GUILD_ID)
                synced_guild = await bot.tree.sync(guild=guild_obj)
                print(f"✅ Guild sync successful: {len(synced_guild)} commands")
                
                # Test global sync
                synced_global = await bot.tree.sync()
                print(f"✅ Global sync successful: {len(synced_global)} commands")
                
                if len(synced_global) == 0:
                    print("❌ NO COMMANDS SYNCED!")
                    print("❌ This means the bot is missing 'applications.commands' scope")
                    print("❌ Use the invite URL above to fix this!")
                
            except discord.Forbidden:
                print("❌ Sync failed: Missing 'applications.commands' scope")
                print("❌ The bot MUST be re-invited with the URL above!")
            except Exception as e:
                print(f"❌ Sync error: {e}")
            
            print(f"\n📋 Troubleshooting Steps:")
            print(f"1. Copy the invite URL above")
            print(f"2. Kick the current bot from your server")
            print(f"3. Use the new invite URL to re-add the bot")
            print(f"4. Make sure to approve both 'bot' and 'applications.commands' scopes")
            print(f"5. Test with 'R!test' (text) and '/test' (slash)")
            
            print(f"\n🔧 If text commands (R!test) still don't work:")
            print(f"   - Check if the bot can see your messages")
            print(f"   - Make sure Message Content Intent is enabled in Discord Developer Portal")
            print(f"   - Verify the bot has 'Send Messages' permission")
            
            # Close the bot after diagnostics
            await bot.close()
        
        @bot.event
        async def on_command_error(ctx, error):
            print(f"❌ Command error: {error}")
            if isinstance(error, commands.CommandNotFound):
                print(f"❌ Command '{ctx.invoked_with}' not found")
                print(f"❌ This suggests text commands aren't registering properly")
        
        @bot.event
        async def on_message(message):
            if message.author == bot.user:
                return
            
            if message.content.startswith('R!'):
                print(f"📨 Received text command: {message.content}")
            
            await bot.process_commands(message)
        
        # Start the bot
        print("🚀 Starting diagnostic bot...")
        await bot.start(Config.TOKEN)
        
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")

if __name__ == "__main__":
    print("🤖 Running bot diagnostics...")
    asyncio.run(diagnose_bot()) 