import discord
from discord.ext import commands
from models.role_manager import RoleManager
from views.embeds import EmbedViews
from config import Config
import logging

logger = logging.getLogger(__name__)

class EventsController:
    """Controller for handling Discord events"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def register_events(self):
        """Register all Discord events"""
        
        @self.bot.event
        async def on_member_update(before: discord.Member, after: discord.Member):
            await self._handle_member_update(before, after)
        
        @self.bot.event
        async def on_message(message: discord.Message):
            await self._handle_message(message)
    
    async def _handle_member_update(self, before: discord.Member, after: discord.Member):
        """Handle member role updates"""
        # Only process events from the configured guild
        if after.guild.id != Config.GUILD_ID:
            return
        
        # Get role changes
        roles_added = set(after.roles) - set(before.roles)
        
        # Check if the restricted role was added
        restricted_role = RoleManager.get_restricted_role(after.guild)
        if restricted_role in roles_added:
            # Check if user has banned role
            if RoleManager.has_banned_role(after):
                try:
                    # Remove the restricted role
                    await after.remove_roles(restricted_role, reason="User is banned from this role")
                    
                    # Send DM with access denied embed
                    embed = EmbedViews.access_denied_embed()
                    try:
                        await after.send(embed=embed)
                    except discord.Forbidden:
                        # If DM fails, we could log this or send to a mod channel
                        pass
                        
                except discord.Forbidden:
                    # Bot doesn't have permission to remove roles
                    print(f"Failed to remove role from {after.display_name}: Missing permissions")
                except Exception as e:
                    print(f"Error handling role update for {after.display_name}: {e}")
    
    async def _handle_message(self, message: discord.Message):
        """Handle new messages for image reactions"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Only process messages from the configured guild
        if not message.guild or message.guild.id != Config.GUILD_ID:
            return
        
        # Check if message is in image reaction channels
        if message.channel.id not in Config.IMAGE_REACTION_CHANNELS:
            return
        
        # Check if message has images
        has_image = False
        
        # Check for attachments (uploaded images)
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                has_image = True
                break
        
        # Check for embedded images (links)
        if not has_image:
            for embed in message.embeds:
                if embed.image or embed.thumbnail:
                    has_image = True
                    break
        
        # React with thumbs up and thumbs down if image found
        if has_image:
            try:
                await message.add_reaction('👍')
                await message.add_reaction('👎')
                logger.info(f"Added reactions to image in {message.channel.name} by {message.author.display_name}")
            except discord.Forbidden:
                logger.error(f"Missing permission to add reactions in {message.channel.name}")
            except Exception as e:
                logger.error(f"Error adding reactions to message: {e}") 