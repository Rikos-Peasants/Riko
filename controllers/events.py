import discord
from discord.ext import commands
from models.role_manager import RoleManager
from models.quest_manager import QuestManager
from views.embeds import EmbedViews
from config import Config
import logging

logger = logging.getLogger(__name__)

class EventsController:
    """Controller for handling Discord events"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.spam_channel_message_count = 0  # Track messages in spam channel
        self.quest_manager = None  # Will be initialized when bot is ready
    
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
        
        # Check for spam channel flood detection
        await self._check_spam_channel_flood(message)
        
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
                
                # Update quest progress and check achievements
                await self._update_quest_progress_and_achievements(message.author, message)
                
            except discord.Forbidden:
                logger.error(f"Missing permission to add reactions in {message.channel.name}")
            except Exception as e:
                logger.error(f"Error adding reactions to message: {e}")
        else:
            # This is a text message in an image channel, check if we need to send a reminder
            await self._check_for_chat_reminder(message)
    
    async def _check_for_chat_reminder(self, message: discord.Message):
        """Check if the last 10 messages are text messages and send a chat reminder"""
        try:
            # Get the last 10 messages from the channel
            messages = []
            async for msg in message.channel.history(limit=10):
                messages.append(msg)
            
            # Check if all 10 messages are text messages (no images)
            text_message_count = 0
            for msg in messages:
                # Skip bot messages
                if msg.author.bot:
                    continue
                
                # Check if message has images
                has_image = False
                
                # Check for attachments (uploaded images)
                for attachment in msg.attachments:
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                        has_image = True
                        break
                
                # Check for embedded images (links)
                if not has_image:
                    for embed in msg.embeds:
                        if embed.image or embed.thumbnail:
                            has_image = True
                            break
                
                if not has_image and msg.content.strip():  # Text message with content
                    text_message_count += 1
                else:
                    break  # Found an image or empty message, reset count
            
            # If we have 10 consecutive text messages, send a reminder
            if text_message_count >= 10:
                # Check if we recently sent a reminder (to avoid spam)
                recent_bot_messages = []
                async for msg in message.channel.history(limit=20):
                    if msg.author == self.bot.user:
                        recent_bot_messages.append(msg)
                
                # Check if we already sent a chat reminder in the last 20 messages
                for bot_msg in recent_bot_messages:
                    if "this isn't exactly the channel to chat" in bot_msg.content.lower():
                        return  # Already sent a reminder recently
                
                # Format chat channel mentions
                chat_mentions = []
                for channel_id in Config.CHAT_CHANNELS:
                    chat_mentions.append(f"<#{channel_id}>")
                
                chat_channels_text = " or ".join(chat_mentions)
                
                reminder_message = f"Umm Sorry guys, this isn't exactly the channel to chat about stuff, please move over to {chat_channels_text} 💬"
                
                await message.channel.send(reminder_message)
                logger.info(f"Sent chat reminder in #{message.channel.name} after {text_message_count} consecutive text messages")
                
        except Exception as e:
            logger.error(f"Error checking for chat reminder: {e}")
    
    async def _check_spam_channel_flood(self, message: discord.Message):
        """Check for message flooding in the spam channel"""
        # Specific channel ID for spam detection
        SPAM_CHANNEL_ID = 1373806584748314634
        
        # Only check messages in the specified spam channel
        if message.channel.id != SPAM_CHANNEL_ID:
            return
        
        # Don't count bot messages or webhook messages
        if message.author.bot or message.webhook_id:
            return
        
        # Don't count empty messages
        if not message.content.strip():
            return
        
        try:
            # Increment message count
            self.spam_channel_message_count += 1
            logger.debug(f"Spam channel message count: {self.spam_channel_message_count}")
            
            # Check if we've reached 10 messages
            if self.spam_channel_message_count >= 10:
                # Send the "nap" message with enhanced spelling
                nap_message = "Shut up, people! I'm trying to nap here. I couldn't care less that you're all flooding my spam channel. 😴💤"
                
                await message.channel.send(nap_message)
                logger.info(f"Sent nap message in #{message.channel.name} after {self.spam_channel_message_count} messages")
                
                # Reset counter to prevent spam
                self.spam_channel_message_count = 0
                
        except Exception as e:
            logger.error(f"Error in spam channel flood detection: {e}")
    
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
            # Count actual human reactions, excluding bot reactions
            thumbs_up = 0
            thumbs_down = 0
            
            for r in message.reactions:
                if str(r.emoji) == '👍':
                    thumbs_up = r.count
                    # Subtract 1 if bot reacted (bot reactions shouldn't count)
                    async for u in r.users():
                        if u.bot:
                            thumbs_up = max(0, thumbs_up - 1)
                            break
                elif str(r.emoji) == '👎':
                    thumbs_down = r.count
                    # Subtract 1 if bot reacted (bot reactions shouldn't count)
                    async for u in r.users():
                        if u.bot:
                            thumbs_down = max(0, thumbs_down - 1)
                            break
            
            await self.bot.leaderboard_manager.update_image_message_score(
                message_id=str(message.id),
                thumbs_up=thumbs_up,
                thumbs_down=thumbs_down
            )
            
            # Update quest progress for earning likes (for image author)
            if str(reaction.emoji) == '👍' and added:
                await self._update_quest_progress_likes(message.author)
            
            # Update quest progress for rating images (for the person who reacted)
            await self._update_quest_progress_rating(user)
            
            action = "added" if added else "removed"
            logger.info(f"Reaction {action}: {reaction.emoji} on {message.author.display_name}'s image (score change: {score_change:+d}), thumbs_up: {thumbs_up}, thumbs_down: {thumbs_down}")
    
    def initialize_quest_manager(self):
        """Initialize the quest manager (called from bot.py when ready)"""
        try:
            self.quest_manager = QuestManager()
            logger.info("Quest Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Quest Manager: {e}")
    
    async def _update_quest_progress_and_achievements(self, user: discord.User, message: discord.Message):
        """Update quest progress and check achievements when user posts an image"""
        if not self.quest_manager:
            return
            
        try:
            # Update quest progress for posting images
            completed_quests = await self.quest_manager.update_quest_progress(
                user_id=user.id,
                quest_type="post_images",
                count=1
            )
            
            # Update posting streak
            post_streak = await self.quest_manager.update_post_streak(user.id)
            
            # Send notifications for completed quests
            for quest in completed_quests:
                try:
                    embed = EmbedViews.quest_completed_embed(quest)
                    await user.send(embed=embed)
                except discord.Forbidden:
                    # User has DMs disabled
                    pass
            
            # Check for new achievements (including streak achievements)
            new_achievements = await self.quest_manager.check_achievements(
                user_id=user.id,
                leaderboard_manager=self.bot.leaderboard_manager
            )
            
            # Send notifications for new achievements
            for achievement in new_achievements:
                try:
                    embed = EmbedViews.achievement_earned_embed(achievement)
                    await user.send(embed=embed)
                except discord.Forbidden:
                    # User has DMs disabled
                    pass
            
            # Add to active events as contestant
            await self.quest_manager.add_event_contestant(
                message_id=str(message.id),
                user_id=user.id,
                user_name=user.display_name
            )
            
        except Exception as e:
            logger.error(f"Error updating quest progress and achievements: {e}")
    
    async def _update_quest_progress_likes(self, user: discord.User):
        """Update quest progress for earning likes"""
        if not self.quest_manager:
            return
            
        try:
            completed_quests = await self.quest_manager.update_quest_progress(
                user_id=user.id,
                quest_type="earn_likes",
                count=1
            )
            
            # Send notifications for completed quests
            for quest in completed_quests:
                try:
                    embed = EmbedViews.quest_completed_embed(quest)
                    await user.send(embed=embed)
                except discord.Forbidden:
                    pass
                    
        except Exception as e:
            logger.error(f"Error updating quest progress for likes: {e}")
    
    async def _update_quest_progress_rating(self, user: discord.User):
        """Update quest progress for rating images"""
        if not self.quest_manager or user.bot:
            return
            
        try:
            # Update the stat for tracking achievements
            await self.quest_manager.update_user_stat(user.id, "ratings_given", 1)
            
            completed_quests = await self.quest_manager.update_quest_progress(
                user_id=user.id,
                quest_type="rate_images",
                count=1
            )
            
            # Send notifications for completed quests
            for quest in completed_quests:
                try:
                    embed = EmbedViews.quest_completed_embed(quest)
                    await user.send(embed=embed)
                except discord.Forbidden:
                    pass
                    
        except Exception as e:
            logger.error(f"Error updating quest progress for rating: {e}") 