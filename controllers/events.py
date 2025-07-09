import discord
from discord.ext import commands
from models.role_manager import RoleManager
from models.quest_manager import QuestManager
from views.embeds import EmbedViews
from config import Config
import logging
from typing import List

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
        async def on_member_remove(member: discord.Member):
            await self._handle_member_leave(member)
        
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
        """Handle member join events to reapply NSFWBAN role if needed and send welcome message"""
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
            
            # Send welcome message if enabled
            await self._send_welcome_message(member)
                    
        except Exception as e:
            logger.error(f"Error handling member join for NSFWBAN reapplication: {e}")
    
    async def _handle_member_leave(self, member: discord.Member):
        """Handle member leave events and send leave message"""
        # Only process events from the configured guild
        if member.guild.id != Config.GUILD_ID:
            return
        
        try:
            # Send leave message if enabled
            await self._send_leave_message(member)
        except Exception as e:
            logger.error(f"Error handling member leave: {e}")
    
    async def _send_welcome_message(self, member: discord.Member):
        """Send welcome message to configured channel"""
        try:
            # Check if welcome system is enabled
            if not await self.bot.leaderboard_manager.is_welcome_enabled(member.guild.id):
                return
            
            # Get welcome channel
            welcome_channel_id = await self.bot.leaderboard_manager.get_welcome_channel(member.guild.id)
            if not welcome_channel_id:
                return
            
            welcome_channel = member.guild.get_channel(welcome_channel_id)
            if not welcome_channel:
                logger.warning(f"Welcome channel {welcome_channel_id} not found")
                return
            
            # Get welcome message template
            welcome_message_data = await self.bot.leaderboard_manager.get_welcome_message(member.guild.id)
            if not welcome_message_data:
                # Default welcome message
                welcome_message_data = {
                    "content": "Welcome {usermention}! 🎉"
                }
            
            # Process message with placeholders
            processed_message = await self._process_welcome_leave_message(welcome_message_data, member, "welcome")
            
            # Send the message
            await welcome_channel.send(**processed_message)
            logger.info(f"Sent welcome message for {member.display_name} in #{welcome_channel.name}")
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
    
    async def _send_leave_message(self, member: discord.Member):
        """Send leave message to configured channel"""
        try:
            # Check if leave system is enabled
            if not await self.bot.leaderboard_manager.is_leave_enabled(member.guild.id):
                return
            
            # Get leave channel
            leave_channel_id = await self.bot.leaderboard_manager.get_leave_channel(member.guild.id)
            if not leave_channel_id:
                return
            
            leave_channel = member.guild.get_channel(leave_channel_id)
            if not leave_channel:
                logger.warning(f"Leave channel {leave_channel_id} not found")
                return
            
            # Get leave message template
            leave_message_data = await self.bot.leaderboard_manager.get_leave_message(member.guild.id)
            if not leave_message_data:
                # Default leave message
                leave_message_data = {
                    "content": "Goodbye {displayname}! 👋"
                }
            
            # Process message with placeholders
            processed_message = await self._process_welcome_leave_message(leave_message_data, member, "leave")
            
            # Send the message
            await leave_channel.send(**processed_message)
            logger.info(f"Sent leave message for {member.display_name} in #{leave_channel.name}")
            
        except Exception as e:
            logger.error(f"Error sending leave message: {e}")
    
    async def _process_welcome_leave_message(self, message_data: dict, member: discord.Member, message_type: str) -> dict:
        """Process welcome/leave message with placeholders"""
        import copy
        processed_data = copy.deepcopy(message_data)
        
        # Define placeholders
        placeholders = {
            "{usermention}": member.mention,
            "{displayname}": member.display_name,
            "{username}": member.name,
            "{userid}": str(member.id),
            "{userurl}": f"https://discord.com/users/{member.id}",
            "{useravatar}": str(member.display_avatar.url) if member.display_avatar else "",
            "{membercount}": str(member.guild.member_count),
            "{guildname}": member.guild.name,
            "{guildid}": str(member.guild.id)
        }
        
        def replace_placeholders(text):
            """Replace placeholders in text"""
            if not isinstance(text, str):
                return text
            for placeholder, value in placeholders.items():
                text = text.replace(placeholder, value)
            return text
        
        # Process content
        if "content" in processed_data:
            processed_data["content"] = replace_placeholders(processed_data["content"])
        
        # Process embeds
        if "embeds" in processed_data:
            for embed_data in processed_data["embeds"]:
                # Process embed fields
                for field_name in ["title", "description"]:
                    if field_name in embed_data:
                        embed_data[field_name] = replace_placeholders(embed_data[field_name])
                
                # Process embed author
                if "author" in embed_data:
                    for author_field in ["name", "url", "icon_url"]:
                        if author_field in embed_data["author"]:
                            embed_data["author"][author_field] = replace_placeholders(embed_data["author"][author_field])
                
                # Process embed footer
                if "footer" in embed_data:
                    for footer_field in ["text", "icon_url"]:
                        if footer_field in embed_data["footer"]:
                            embed_data["footer"][footer_field] = replace_placeholders(embed_data["footer"][footer_field])
                
                # Process embed fields
                if "fields" in embed_data:
                    for field in embed_data["fields"]:
                        if "name" in field:
                            field["name"] = replace_placeholders(field["name"])
                        if "value" in field:
                            field["value"] = replace_placeholders(field["value"])
                
                # Process embed image and thumbnail
                for image_field in ["image", "thumbnail"]:
                    if image_field in embed_data and "url" in embed_data[image_field]:
                        embed_data[image_field]["url"] = replace_placeholders(embed_data[image_field]["url"])
            
            # Convert embed data to discord.Embed objects
            embeds = []
            for embed_data in processed_data["embeds"]:
                embed = discord.Embed()
                
                # Set basic embed properties
                if "title" in embed_data:
                    embed.title = embed_data["title"]
                if "description" in embed_data:
                    embed.description = embed_data["description"]
                if "color" in embed_data:
                    embed.color = embed_data["color"]
                if "url" in embed_data:
                    embed.url = embed_data["url"]
                if "timestamp" in embed_data:
                    embed.timestamp = embed_data["timestamp"]
                
                # Set embed author
                if "author" in embed_data:
                    author = embed_data["author"]
                    author_kwargs = {"name": author.get("name", "")}
                    if "url" in author and author["url"]:
                        author_kwargs["url"] = author["url"]
                    if "icon_url" in author and author["icon_url"]:
                        author_kwargs["icon_url"] = author["icon_url"]
                    embed.set_author(**author_kwargs)
                
                # Set embed footer
                if "footer" in embed_data:
                    footer = embed_data["footer"]
                    footer_kwargs = {"text": footer.get("text", "")}
                    if "icon_url" in footer and footer["icon_url"]:
                        footer_kwargs["icon_url"] = footer["icon_url"]
                    embed.set_footer(**footer_kwargs)
                
                # Add embed fields
                if "fields" in embed_data:
                    for field in embed_data["fields"]:
                        embed.add_field(
                            name=field.get("name", ""),
                            value=field.get("value", ""),
                            inline=field.get("inline", False)
                        )
                
                # Set embed image
                if "image" in embed_data and "url" in embed_data["image"]:
                    embed.set_image(url=embed_data["image"]["url"])
                
                # Set embed thumbnail
                if "thumbnail" in embed_data and "url" in embed_data["thumbnail"]:
                    embed.set_thumbnail(url=embed_data["thumbnail"]["url"])
                
                embeds.append(embed)
            
            processed_data["embeds"] = embeds
        
        return processed_data
    
    async def _handle_member_join_message(self, message: discord.Message):
        """Handle Discord system messages for member joins and reply with sticker"""
        try:
            # Check if this is a system message for member join
            if message.type == discord.MessageType.new_member:
                # Get the sticker by ID from the guild
                sticker_id = 1391462726781505536
                
                # Try to get the sticker from the guild first
                sticker = None
                if message.guild:
                    sticker = discord.utils.get(message.guild.stickers, id=sticker_id)
                
                if sticker:
                    # Send the sticker as a reply to the member join message
                    await message.reply(stickers=[sticker])
                    logger.info(f"Sent welcome sticker for member join message in #{getattr(message.channel, 'name', 'DM')}")
                else:
                    logger.warning(f"Could not find guild sticker with ID {sticker_id}")
                    
        except discord.Forbidden:
            logger.error("Missing permission to send sticker messages for member joins")
        except discord.HTTPException as e:
            logger.error(f"HTTP error sending sticker for member join message: {e}")
        except Exception as e:
            logger.error(f"Error handling member join message: {e}")
    
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
        """Handle new messages for image reactions and member join stickers"""
        # Check for member join system messages FIRST (before ignoring bot messages)
        if message.guild and message.guild.id == Config.GUILD_ID:
            await self._handle_member_join_message(message)
        
        # Ignore bot messages for regular processing
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
        
        # Check if message is in help channel
        if message.channel.id == Config.HELP_CHANNEL_ID:
            await self._handle_help_channel_message(message)
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
                await message.add_reaction('🔖')  # Bookmark emoji
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
    
    async def _handle_help_channel_message(self, message: discord.Message):
        """Handle messages in the help channel by creating a thread with resources"""
        try:
            # Create a public thread for the help request
            thread_name = f"Help - {message.author.display_name}"
            thread = await message.create_thread(name=thread_name, auto_archive_duration=60)
            
            # Create the help response message
            help_content = f"""Hey {message.author.mention}! 👋

Here are some useful resources to help you:

**📂 Channel with all projects of rayen:**
<#{Config.PROJECTS_CHANNEL_ID}>

**💻 Riko's Code:**
<https://github.com/rayenfeng/riko_project>

**🎬 Rayen's YouTube:**
<https://www.youtube.com/@JustRayen>

<@&{Config.HELP_ROLE_ID}>"""
            
            # Send the help message in the thread
            await thread.send(help_content)
            
            logger.info(f"Created help thread for {message.author.display_name} in #{message.channel.name}")
            
        except discord.Forbidden:
            logger.error(f"Missing permission to create thread in #{message.channel.name}")
        except Exception as e:
            logger.error(f"Error handling help channel message: {e}")
    

    
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
        
        # Basic guild checks
        if not hasattr(reaction.message, 'guild') or not reaction.message.guild:
            return
        
        if reaction.message.guild.id != Config.GUILD_ID:
            return
        
        # Handle bookmark reactions FIRST (works in any channel with images)
        emoji_str = str(reaction.emoji)
        logger.info(f"Reaction detected: '{emoji_str}' (repr: {repr(emoji_str)}) by {user.display_name}")
        
        # Check for bookmark emoji (multiple possible variants)
        bookmark_emojis = ['🔖', '📑', '📌', '🏷️']
        if emoji_str in bookmark_emojis:
            logger.info(f"Processing bookmark reaction '{emoji_str}' by {user.display_name}")
            await self._handle_bookmark_reaction(reaction, user, added)
            return
        
        # Only track scoring reactions in designated image channels
        if reaction.message.channel.id not in Config.IMAGE_REACTION_CHANNELS:
            return
        
        # Only track thumbs up and thumbs down for scoring
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
        
        # Track the user reaction
        await self.bot.leaderboard_manager.track_user_reaction(
            user_id=user.id,
            message_id=str(message.id),
            emoji=str(reaction.emoji),
            added=added
        )
        
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
    
    async def _handle_bookmark_reaction(self, reaction: discord.Reaction, user: discord.User, added: bool):
        """Handle bookmark emoji reactions"""
        try:
            message = reaction.message
            
            # Check if the message has images
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
            
            if added:
                # Add bookmark
                success = await self.bot.leaderboard_manager.add_bookmark(
                    user.id, 
                    str(message.id), 
                    user.display_name
                )
                
                if success:
                    # Send ephemeral confirmation
                    try:
                        embed = discord.Embed(
                            title="🔖 Bookmark Added",
                            description=f"Successfully bookmarked [this image]({message.jump_url})!",
                            color=0x3498db
                        )
                        embed.set_footer(text="Use /bookmarks to view all your bookmarks")
                        await user.send(embed=embed)
                    except discord.Forbidden:
                        # User has DMs disabled, that's okay
                        pass
                    
                    logger.info(f"User {user.display_name} bookmarked message {message.id}")
                else:
                    # Already bookmarked or failed
                    try:
                        embed = discord.Embed(
                            title="📌 Already Bookmarked",
                            description="This image is already in your bookmarks!",
                            color=0xf39c12
                        )
                        await user.send(embed=embed)
                    except discord.Forbidden:
                        pass
            else:
                # Remove bookmark
                success = await self.bot.leaderboard_manager.remove_bookmark(user.id, str(message.id))
                
                if success:
                    try:
                        embed = discord.Embed(
                            title="🗑️ Bookmark Removed",
                            description="Bookmark removed successfully!",
                            color=0xe74c3c
                        )
                        await user.send(embed=embed)
                    except discord.Forbidden:
                        pass
                    
                    logger.info(f"User {user.display_name} removed bookmark for message {message.id}")
                
        except Exception as e:
            logger.error(f"Error handling bookmark reaction: {e}")
    
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