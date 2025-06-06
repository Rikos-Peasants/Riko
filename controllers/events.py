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
        async def on_member_join(member: discord.Member):
            await self._handle_member_join(member)
        
        @self.bot.event
        async def on_member_update(before: discord.Member, after: discord.Member):
            await self._handle_member_update(before, after)
        
        @self.bot.event
        async def on_message(message: discord.Message):
            await self._handle_message(message)
        
        @self.bot.event
        async def on_message_delete(message: discord.Message):
            await self._handle_message_delete(message)
        
        @self.bot.event
        async def on_command_error(ctx: commands.Context, error: commands.CommandError):
            await self._handle_command_error(ctx, error)
        
        @self.bot.event
        async def on_command(ctx: commands.Context):
            """Log when commands are successfully invoked"""
            logger.info(f"Command '{ctx.command.name}' invoked by {ctx.author.display_name} in #{ctx.channel.name}")
        
        @self.bot.event
        async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
            await self._handle_reaction_change(reaction, user, added=True)
        
        @self.bot.event
        async def on_reaction_remove(reaction: discord.Reaction, user: discord.User):
            await self._handle_reaction_change(reaction, user, added=False)
    
    async def _handle_member_join(self, member: discord.Member):
        """Handle member join events to reapply NSFWBAN role if needed"""
        # Only process events from the configured guild
        if member.guild.id != Config.GUILD_ID:
            return
        
        try:
            # Check if the user is in the NSFWBAN database
            if await self.bot.leaderboard_manager.is_nsfwban_user(member.id):
                # Get the NSFWBAN banned role (the role applied to banned users)
                nsfwban_role = discord.utils.get(member.guild.roles, id=Config.NSFWBAN_BANNED_ROLE_ID)
                
                if nsfwban_role:
                    # Add the role back to the user
                    await member.add_roles(nsfwban_role, reason="Reapplying NSFWBAN role on rejoin")
                    logger.info(f"Reapplied NSFWBAN role to {member.display_name} on rejoin")
                    
                    # Get ban info for DM
                    ban_info = await self.bot.leaderboard_manager.get_nsfwban_user_info(member.id)
                    reason = ban_info.get('reason', 'No reason provided') if ban_info else 'No reason provided'
                    
                    # Send DM notification
                    try:
                        dm_embed = EmbedViews.nsfwban_dm_embed(reason, member.guild.name)
                        await member.send(embed=dm_embed)
                    except discord.Forbidden:
                        # User has DMs disabled, that's okay
                        pass
                    except Exception as e:
                        logger.error(f"Failed to send NSFWBAN rejoin DM to {member.display_name}: {e}")
                else:
                    logger.error(f"NSFWBAN role not found when trying to reapply to {member.display_name}")
                    
        except Exception as e:
            logger.error(f"Error handling member join for NSFWBAN reapplication: {e}")
    
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
        
        # Log message if it starts with command prefix
        if message.content.startswith('R!'):
            logger.info(f"Received command: {message.content} from {message.author.display_name}")
        
        # IMPORTANT: Process commands first for text commands to work
        await self.bot.process_commands(message)
        
        # Only process messages from the configured guild
        if not message.guild or message.guild.id != Config.GUILD_ID:
            return
        
        # Check if message is in image reaction channels
        if message.channel.id not in Config.IMAGE_REACTION_CHANNELS:
            return
        
        # Check if message has images
        has_image = False
        image_url = None
        
        # Check for attachments (uploaded images)
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                has_image = True
                image_url = attachment.url
                break
        
        # Check for embedded images (links)
        if not has_image:
            for embed in message.embeds:
                if embed.image:
                    has_image = True
                    image_url = embed.image.url
                    break
                elif embed.thumbnail:
                    has_image = True
                    image_url = embed.thumbnail.url
                    break
        
        # React with thumbs up and thumbs down if image found
        if has_image and image_url:
            try:
                await message.add_reaction('👍')
                await message.add_reaction('👎')
                logger.info(f"Added reactions to image in {message.channel.name} by {message.author.display_name}")
                
                # Store the image message in MongoDB
                await self.bot.leaderboard_manager.store_image_message(
                    message=message,
                    image_url=image_url,
                    initial_score=0
                )
                
                # Track the image post in leaderboard
                self.bot.leaderboard_manager.add_image_post(
                    user_id=message.author.id,
                    user_name=message.author.display_name,
                    initial_score=0  # Start with 0, will be updated when reactions happen
                )
                
            except discord.Forbidden:
                logger.error(f"Missing permission to add reactions in {message.channel.name}")
            except Exception as e:
                logger.error(f"Error adding reactions to message: {e}")
    
    async def _handle_message_delete(self, message: discord.Message):
        """Handle message deletions to clean up image tracking"""
        # Only process messages from image channels
        if not message.guild or message.guild.id != Config.GUILD_ID:
            return
            
        if message.channel.id not in Config.IMAGE_REACTION_CHANNELS:
            return
            
        # Delete the image message from MongoDB if it exists
        await self.bot.leaderboard_manager.delete_image_message(str(message.id))
    
    async def _handle_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            logger.debug(f"Unknown command: {ctx.invoked_with}")
            return
        elif isinstance(error, commands.MissingPermissions):
            logger.warning(f"Missing permissions for command {ctx.command.name}: {error}")
            await ctx.send("❌ You don't have permission to use this command.", ephemeral=True)
        elif isinstance(error, commands.NotOwner):
            logger.warning(f"Non-owner tried to use owner command {ctx.command.name}: {ctx.author}")
            await ctx.send("❌ This command is only available to bot owners.", ephemeral=True)
        else:
            logger.error(f"Command error in {ctx.command.name}: {error}")
            await ctx.send(f"❌ An error occurred: {str(error)}", ephemeral=True)
    
    async def _handle_reaction_change(self, reaction: discord.Reaction, user: discord.User, added: bool):
        """Handle reaction additions and removals for leaderboard tracking"""
        # Ignore bot reactions
        if user.bot:
            return
        
        # Only track reactions in image channels
        if not hasattr(reaction.message, 'guild') or not reaction.message.guild:
            return
        
        if reaction.message.guild.id != Config.GUILD_ID:
            return
        
        if reaction.message.channel.id not in Config.IMAGE_REACTION_CHANNELS:
            return
        
        # Only track thumbs up and thumbs down
        if str(reaction.emoji) not in ['👍', '👎']:
            return
        
        # Check if the message has images
        message = reaction.message
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
        
        if not has_image:
            return
        
        # Calculate score change
        score_change = 0
        if str(reaction.emoji) == '👍':
            score_change = 1 if added else -1
        elif str(reaction.emoji) == '👎':
            score_change = -1 if added else 1
        
        # Update the leaderboard for the image author
        if score_change != 0:
            self.bot.leaderboard_manager.update_image_score(
                user_id=message.author.id,
                user_name=message.author.display_name,
                score_change=score_change
            )
            
            # Update the image message score in MongoDB
            thumbs_up = sum(1 for r in message.reactions if str(r.emoji) == '👍')
            thumbs_down = sum(1 for r in message.reactions if str(r.emoji) == '👎')
            
            await self.bot.leaderboard_manager.update_image_message_score(
                message_id=str(message.id),
                thumbs_up=thumbs_up,
                thumbs_down=thumbs_down
            )
            
            action = "added" if added else "removed"
            logger.debug(f"Reaction {action}: {reaction.emoji} on {message.author.display_name}'s image (score change: {score_change:+d})") 