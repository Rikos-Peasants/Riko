import discord
from discord.ext import commands
from datetime import datetime, timedelta
import logging
from typing import Optional, Union
from models.role_manager import RoleManager
from views.embeds import EmbedViews
from config import Config

logger = logging.getLogger(__name__)

class CommandsController:
    """Controller for handling bot commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.utcnow()
    
    def get_bot_attr(self, attr_name: str) -> Optional[object]:
        """Safely get bot attribute"""
        return getattr(self.bot, attr_name, None) if hasattr(self.bot, attr_name) else None
    
    def get_leaderboard_manager(self):
        """Safely get leaderboard manager"""
        return getattr(self.bot, 'leaderboard_manager', None)
    
    def get_scheduler_controller(self):
        """Safely get scheduler controller"""
        return getattr(self.bot, 'scheduler_controller', None)
    
    def get_events_controller(self):
        """Safely get events controller"""
        return getattr(self.bot, 'events_controller', None)
    
    def get_random_announcer(self):
        """Safely get random announcer"""
        return getattr(self.bot, 'random_announcer', None)
    
    def register_commands(self):
        """Register all hybrid commands (both text and slash)"""
        
        # Add a simple debug command for testing
        @self.bot.command(name="debug")
        async def debug_command(ctx):
            """Simple debug command to test text commands"""
            await ctx.send("🔧 Debug: Text commands are working!")
        
        # Add a simple owner test command
        @self.bot.hybrid_command(name="testowner", description="Test if you're a bot owner")
        @commands.is_owner()
        async def test_owner_command(ctx):
            """Test command to verify bot owner status"""
            await ctx.send("✅ You are verified as a bot owner! Owner commands should work for you.")
        
        # Define the hybrid command
        @self.bot.hybrid_command(name="uptime", description="Check how long the bot has been running")
        async def uptime_command(ctx):
            """Check how long the bot has been running"""
            try:
                current_time = datetime.utcnow()
                uptime_duration = current_time - self.start_time
                
                # Format uptime string
                days = uptime_duration.days
                hours, remainder = divmod(uptime_duration.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
                
                embed = EmbedViews.uptime_embed(uptime_str)
                
                # Add footer to show both command formats
                embed.set_footer(text="💡 Use R!uptime or /uptime")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to get uptime: {str(e)}")
                await ctx.send(embed=error_embed, ephemeral=True)
        
        @self.bot.hybrid_command(name="processold", description="Process old images from the past year (Bot owners only)")
        @commands.is_owner()
        async def process_old_command(ctx):
            """Process old images from the past year and add them to the leaderboard"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()  # This will take a while
                
                guild = ctx.guild
                if not guild or guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Check if leaderboard manager is available
                leaderboard_manager = getattr(self.bot, 'leaderboard_manager', None)
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Send initial status
                status_msg = "🔄 Processing old images from the past year...\nThis may take several minutes..."
                if hasattr(ctx, 'followup'):
                    status_response = await ctx.followup.send(status_msg)
                else:
                    status_response = await ctx.send(status_msg)
                
                # Process images from the past year
                one_year_ago = datetime.now() - timedelta(days=365)
                total_processed = 0
                total_skipped = 0
                total_users = set()
                
                # Get bot user ID to exclude bot reactions
                bot_user_id = self.bot.user.id if self.bot.user else 0
                
                for channel_id in Config.IMAGE_REACTION_CHANNELS:
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        print(f"⚠️ Could not find channel {channel_id}")
                        continue
                    
                    print(f"🔍 Processing channel #{channel.name} (ID: {channel_id})")
                    channel_count = 0
                    
                    try:
                        # Count total messages first for progress
                        message_count = 0
                        async for message in channel.history(limit=None, after=one_year_ago):
                            message_count += 1
                            if message_count % 100 == 0:
                                print(f"   Counting messages... {message_count}")
                        
                        print(f"   Found {message_count} total messages to scan")
                        
                        # Now process messages
                        processed_messages = 0
                        async for message in channel.history(limit=None, after=one_year_ago):
                            processed_messages += 1
                            
                            # Skip bot messages
                            if message.author.bot:
                                continue
                            
                            # Progress indicator
                            if processed_messages % 50 == 0:
                                print(f"   Progress: {processed_messages}/{message_count} messages")
                            
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
                            
                            if has_image:
                                # Check if this message is already processed to avoid duplicates
                                if hasattr(leaderboard_manager, 'image_message_exists'):
                                    if await leaderboard_manager.image_message_exists(str(message.id)):
                                        print(f"   ⏭️ Skipping already processed image from {message.author.display_name}")
                                        total_skipped += 1
                                        continue
                                
                                # Extract image URL for database storage
                                image_url = None
                                
                                # Check for attachments (uploaded images)
                                for attachment in message.attachments:
                                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                                        image_url = attachment.url
                                        break
                                
                                # Check for embedded images (links) if no attachment found
                                if not image_url:
                                    for embed in message.embeds:
                                        if embed.image:
                                            image_url = embed.image.url
                                            break
                                        elif embed.thumbnail:
                                            image_url = embed.thumbnail.url
                                            break
                                
                                # Calculate current score
                                thumbs_up = 0
                                thumbs_down = 0
                                
                                for reaction in message.reactions:
                                    if str(reaction.emoji) == '👍':
                                        thumbs_up = reaction.count
                                        # Check if bot reacted and subtract 1
                                        async for user in reaction.users():
                                            if user.id == bot_user_id:
                                                thumbs_up = max(0, thumbs_up - 1)
                                                break
                                    elif str(reaction.emoji) == '👎':
                                        thumbs_down = reaction.count
                                        # Check if bot reacted and subtract 1
                                        async for user in reaction.users():
                                            if user.id == bot_user_id:
                                                thumbs_down = max(0, thumbs_down - 1)
                                                break
                                
                                net_score = thumbs_up - thumbs_down
                                
                                # Store the image message in MongoDB database
                                if image_url:
                                    await leaderboard_manager.store_image_message(
                                        message=message,
                                        image_url=image_url,
                                        initial_score=net_score
                                    )
                                    
                                    # Update the image message score with current reactions
                                    await leaderboard_manager.update_image_message_score(
                                        message_id=str(message.id),
                                        thumbs_up=thumbs_up,
                                        thumbs_down=thumbs_down
                                    )
                                
                                # Add to leaderboard (this will create or update the user)
                                leaderboard_manager.add_image_post(
                                    user_id=message.author.id,
                                    user_name=message.author.display_name,
                                    initial_score=net_score
                                )
                                
                                channel_count += 1
                                total_users.add(message.author.id)
                                
                                # Debug info for all images (not just first 3)
                                print(f"   📸 Image {channel_count}: {message.author.display_name} ({message.created_at.strftime('%Y-%m-%d')}) - {thumbs_up}👍 {thumbs_down}👎 = {net_score} net")
                    
                    except Exception as e:
                        print(f"❌ Error processing channel #{channel.name}: {e}")
                        continue
                    
                    total_processed += channel_count
                    print(f"✅ Processed {channel_count} images from #{channel.name}")
                
                # Send completion message
                completion_msg = f"✅ **Processing Complete!**\n\n"
                completion_msg += f"📊 **Results:**\n"
                completion_msg += f"• **Images Processed:** {total_processed}\n"
                completion_msg += f"• **Images Skipped:** {total_skipped} (already in database)\n"
                completion_msg += f"• **Unique Users:** {len(total_users)}\n"
                completion_msg += f"• **Channels:** {len(Config.IMAGE_REACTION_CHANNELS)}\n"
                completion_msg += f"• **Time Period:** Past 365 days\n\n"
                
                if total_processed > 0:
                    completion_msg += f"🏆 Use `R!leaderboard` or `/leaderboard` to see the updated rankings!\n"
                    completion_msg += f"💾 All processed images have been stored in the database for best image tracking."
                else:
                    completion_msg += f"⚠️ No new images found in the specified time period."
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(completion_msg)
                else:
                    await status_response.edit(content=completion_msg)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to process old images: {str(e)}")
                print(f"❌ Error in processold command: {e}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)
        
        @self.bot.hybrid_command(name="bestweek", description="Manually post the best image of this week (Bot owners only)")
        @commands.is_owner()
        async def best_week_command(ctx):
            """Manually trigger best image of the week post"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()  # This might take a while
                
                # Get the date range for the PREVIOUS complete week (Monday to Sunday)
                now = datetime.now()
                # If it's Sunday, show last week. Otherwise show the current week so far.
                if now.weekday() == 6:  # Sunday
                    end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)  # Start of today (Sunday)
                    start_date = end_date - timedelta(days=6)  # Monday of last week
                else:
                    # For other days, show current week from Monday to now
                    days_since_monday = now.weekday()  # Monday is 0
                    start_date = now - timedelta(days=days_since_monday)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = now
                
                # Use the scheduler controller to post the best image
                scheduler_controller = getattr(self.bot, 'scheduler_controller', None)
                if scheduler_controller:
                    await scheduler_controller._post_best_image("week", start_date, end_date)
                else:
                    error_msg = "Scheduler controller is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Send response based on command type
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send("✅ Best image of the week has been posted to each image channel!", ephemeral=True)
                else:
                    await ctx.send("✅ Best image of the week has been posted to each image channel!")
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to post best image: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)
        
        @self.bot.hybrid_command(name="bestmonth", description="Manually post the best image of this month (Bot owners only)")
        @commands.is_owner()
        async def best_month_command(ctx):
            """Manually trigger best image of the month post"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()  # This might take a while
                
                # Get the date range for the PREVIOUS complete month
                now = datetime.now()
                # If it's the 1st of the month, show last month. Otherwise show current month so far.
                if now.day == 1:
                    end_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)  # Start of current month
                    # Go back to the first day of last month
                    if now.month == 1:
                        start_date = now.replace(year=now.year-1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
                    else:
                        start_date = now.replace(month=now.month-1, day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    # For other days, show current month from 1st to now
                    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    end_date = now
                
                # Use the scheduler controller to post the best image
                scheduler_controller = self.get_scheduler_controller()
                if scheduler_controller:
                    await scheduler_controller._post_best_image("month", start_date, end_date)
                    
                    # Send response based on command type
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send("✅ Best image of the month has been posted to each image channel!", ephemeral=True)
                    else:
                        await ctx.send("✅ Best image of the month has been posted to each image channel!")
                else:
                    error_msg = "Scheduler controller is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to post best image: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)
        
        @self.bot.hybrid_command(name="bestyear", description="Manually post the best image of this year (Bot owners only)")
        @commands.is_owner()
        async def best_year_command(ctx):
            """Manually trigger best image of the year post"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()  # This might take a while
                
                # Get the date range for the current year
                now = datetime.now()
                end_date = now
                start_date = now.replace(month=1, day=1)  # First day of current year
                
                # Use the scheduler controller to post the best image
                scheduler_controller = self.get_scheduler_controller()
                if scheduler_controller:
                    await scheduler_controller._post_best_image("year", start_date, end_date)
                else:
                    error_msg = "Scheduler controller is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Send response based on command type
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send("✅ Best image of the year has been posted to each image channel!", ephemeral=True)
                else:
                    await ctx.send("✅ Best image of the year has been posted to each image channel!")
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to post best image: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)
        
        @self.bot.hybrid_command(name="leaderboard", description="Show the image upvote leaderboard")
        async def leaderboard_command(ctx):
            """Show leaderboard of users by image upvotes"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()  # This might take a while
                
                guild = ctx.guild
                if not guild or guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Get leaderboard data from JSON file (fast!)
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                leaderboard_data = leaderboard_manager.get_leaderboard(limit=10)
                
                # Create and send embed
                embed = EmbedViews.leaderboard_embed(leaderboard_data, "all time")
                
                # Add stats summary
                stats = leaderboard_manager.get_stats_summary()
                embed.add_field(
                    name="📊 Server Stats",
                    value=f"**Total Users:** {stats['total_users']}\n"
                          f"**Total Images:** {stats['total_images']}\n"
                          f"**Average Score:** {stats['average_score']}",
                    inline=False
                )
                
                # Send response based on command type
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to generate leaderboard: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)
        
        @self.bot.hybrid_command(name="stats", description="Show your image posting statistics")
        async def stats_command(ctx, user: Optional[discord.Member] = None):
            """Show stats for yourself or another user"""
            try:
                target_user = user if user else ctx.author
                
                # Get user stats
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                stats = leaderboard_manager.get_user_stats(target_user.id)
                
                if not stats:
                    message = f"No image posting stats found for {target_user.display_name}."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(message, ephemeral=True)
                    else:
                        await ctx.send(message)
                    return
                
                # Calculate average
                avg_score = stats['total_score'] / stats['image_count'] if stats['image_count'] > 0 else 0
                
                # Create embed
                embed = discord.Embed(
                    title=f"📊 Image Stats for {target_user.display_name}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name="🏆 Total Score",
                    value=str(stats['total_score']),
                    inline=True
                )
                
                embed.add_field(
                    name="📸 Images Posted",
                    value=str(stats['image_count']),
                    inline=True
                )
                
                embed.add_field(
                    name="📈 Average Score",
                    value=f"{avg_score:.1f}",
                    inline=True
                )
                
                embed.set_thumbnail(url=target_user.display_avatar.url if target_user.display_avatar else None)
                embed.set_footer(text="Based on net upvotes (👍 - 👎)")
                
                # Send response
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to get stats: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)
        
        @self.bot.hybrid_command(name="dbstatus", description="Check MongoDB connection status (Bot owners only)")
        @commands.is_owner()
        async def db_status_command(ctx):
            """Check MongoDB connection and show database statistics"""
            try:
                if hasattr(ctx, 'defer'):
                    await ctx.defer(ephemeral=True)
                
                # Test MongoDB connection and get stats
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                stats = leaderboard_manager.get_stats_summary()
                
                embed = discord.Embed(
                    title="🗄️ MongoDB Status",
                    description="Database connection and statistics",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name="📊 Database Stats",
                    value=f"**Users:** {stats['total_users']}\n"
                          f"**Images:** {stats['total_images']}\n"
                          f"**Total Score:** {stats['total_score']}\n"
                          f"**Average:** {stats['average_score']}",
                    inline=False
                )
                
                embed.add_field(
                    name="🔗 Connection",
                    value="✅ MongoDB Connected",
                    inline=True
                )
                
                embed.add_field(
                    name="🏢 Database",
                    value="Riko",
                    inline=True
                )
                
                embed.add_field(
                    name="📋 Collection",
                    value="images",
                    inline=True
                )
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed, ephemeral=True)
                else:
                    await ctx.send(embed=embed)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"MongoDB connection failed: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)
        
        # Custom permission check for NSFWBAN commands
        def can_use_nsfwban():
            """Check if user can use NSFWBAN commands"""
            async def predicate(ctx):
                # Bot owners can always use the command
                if await ctx.bot.is_owner(ctx.author):
                    return True
                
                # Check if user has administrator permissions
                if ctx.author.guild_permissions.administrator:
                    return True
                
                # Check if user has the specific NSFWBAN moderator role
                nsfwban_moderator_role = discord.utils.get(ctx.author.roles, id=Config.NSFWBAN_MODERATOR_ROLE_ID)
                if nsfwban_moderator_role:
                    return True
                
                return False
            return commands.check(predicate)

        @self.bot.hybrid_command(name="nsfwban", description="Ban a user from NSFW content (Admins/NSFWBAN role only)")
        @can_use_nsfwban()
        async def nsfwban_command(ctx, user: discord.Member, *, reason: str = "No reason provided"):
            """Ban a user from NSFW content"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                # Validate guild
                if not ctx.guild or ctx.guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Check if user is trying to ban themselves
                if user.id == ctx.author.id:
                    error_msg = "❌ You cannot NSFWBAN yourself!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Check if user is trying to ban a bot owner
                if await ctx.bot.is_owner(user):
                    error_msg = "❌ You cannot NSFWBAN a bot owner!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Check if user is already NSFWBAN'd
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                if await leaderboard_manager.is_nsfwban_user(user.id):
                    error_msg = f"❌ {user.display_name} is already NSFWBAN'd!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Get the NSFWBAN banned role (the role applied to banned users)
                nsfwban_role = discord.utils.get(ctx.guild.roles, id=Config.NSFWBAN_BANNED_ROLE_ID)
                if not nsfwban_role:
                    error_msg = f"❌ NSFWBAN role not found! (ID: {Config.NSFWBAN_BANNED_ROLE_ID})"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Add the role to the user
                try:
                    await user.add_roles(nsfwban_role, reason=f"NSFWBAN by {ctx.author.display_name}: {reason}")
                except discord.Forbidden:
                    error_msg = "❌ I don't have permission to manage roles!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                except discord.HTTPException as e:
                    error_msg = f"❌ Failed to add role: {str(e)}"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Add user to database
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                success = await leaderboard_manager.add_nsfwban_user(
                    user_id=user.id,
                    user_name=user.display_name,
                    banned_by_id=ctx.author.id,
                    banned_by_name=ctx.author.display_name,
                    guild_id=ctx.guild.id,
                    reason=reason
                )
                
                if not success:
                    error_msg = "❌ Failed to save ban to database!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Send success embed
                embed = EmbedViews.nsfwban_success_embed(user, reason, ctx.author)
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                
                # Send DM to the banned user
                try:
                    dm_embed = EmbedViews.nsfwban_dm_embed(reason, ctx.guild.name)
                    await user.send(embed=dm_embed)
                except discord.Forbidden:
                    # User has DMs disabled, that's okay
                    pass
                except Exception as e:
                    logger.error(f"Failed to send NSFWBAN DM to {user.display_name}: {e}")
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to execute NSFWBAN: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @self.bot.hybrid_command(name="nsfwunban", description="Remove NSFW ban from a user (Admins/NSFWBAN role only)")
        @can_use_nsfwban()
        async def nsfwunban_command(ctx, user: discord.Member):
            """Remove NSFW ban from a user"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                # Validate guild
                if not ctx.guild or ctx.guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Check if user is NSFWBAN'd
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                if not await leaderboard_manager.is_nsfwban_user(user.id):
                    error_msg = f"❌ {user.display_name} is not NSFWBAN'd!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Get the NSFWBAN banned role (the role applied to banned users)
                nsfwban_role = discord.utils.get(ctx.guild.roles, id=Config.NSFWBAN_BANNED_ROLE_ID)
                if not nsfwban_role:
                    error_msg = f"❌ NSFWBAN role not found! (ID: {Config.NSFWBAN_BANNED_ROLE_ID})"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Remove the role from the user
                try:
                    await user.remove_roles(nsfwban_role, reason=f"NSFWUNBAN by {ctx.author.display_name}")
                except discord.Forbidden:
                    error_msg = "❌ I don't have permission to manage roles!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                except discord.HTTPException as e:
                    error_msg = f"❌ Failed to remove role: {str(e)}"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Remove user from database
                success = await leaderboard_manager.remove_nsfwban_user(user.id)
                
                if not success:
                    error_msg = "❌ Failed to remove ban from database!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Send success embed
                embed = EmbedViews.nsfwunban_success_embed(user, ctx.author)
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                
                # Send DM to the unbanned user
                try:
                    dm_embed = EmbedViews.nsfwunban_dm_embed(ctx.guild.name)
                    await user.send(embed=dm_embed)
                except discord.Forbidden:
                    # User has DMs disabled, that's okay
                    pass
                except Exception as e:
                    logger.error(f"Failed to send NSFWUNBAN DM to {user.display_name}: {e}")
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to execute NSFWUNBAN: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        # Warning system commands
        def can_warn():
            """Check if user can use warning commands (needs manage_guild permission)"""
            async def predicate(ctx):
                # Bot owners can always use the command
                if await ctx.bot.is_owner(ctx.author):
                    return True
                
                # Check if the user has manage_guild permission
                if not ctx.author.guild_permissions.manage_guild:
                    return False
                
                return True
            return commands.check(predicate)

        @self.bot.hybrid_command(name="warn", description="Issue a warning to a user (Manage Server permission required)")
        @can_warn()
        async def warn_command(ctx, user: discord.Member, *, reason: str = "No reason provided"):
            """Issue a warning to a user with automatic escalation"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                # Validate guild
                if not ctx.guild or ctx.guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Check if user is trying to warn themselves
                if user.id == ctx.author.id:
                    error_msg = "❌ You cannot warn yourself!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Check if user is trying to warn a bot
                if user.bot:
                    error_msg = "❌ You cannot warn bots!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Check if user is trying to warn a bot owner
                if await ctx.bot.is_owner(user):
                    error_msg = "❌ You cannot warn a bot owner!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Add the warning to database
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                warning_result = await leaderboard_manager.add_warning(
                    guild_id=ctx.guild.id,
                    user_id=user.id,
                    user_name=user.display_name,
                    warned_by_id=ctx.author.id,
                    warned_by_name=ctx.author.display_name,
                    reason=reason
                )
                
                warning_count = warning_result.get("warning_count", 0)
                action = warning_result.get("action", "none")
                
                # Apply automatic escalation
                try:
                    if action == "timeout_1h":
                        timeout_until = discord.utils.utcnow() + timedelta(hours=1)
                        await user.timeout(timeout_until, reason=f"Automated warning escalation: {reason}")
                    elif action == "timeout_4h":
                        timeout_until = discord.utils.utcnow() + timedelta(hours=4)
                        await user.timeout(timeout_until, reason=f"Automated warning escalation: {reason}")
                    elif action == "timeout_1w":
                        timeout_until = discord.utils.utcnow() + timedelta(weeks=1)
                        await user.timeout(timeout_until, reason=f"Automated warning escalation: {reason}")
                    elif action == "kick":
                        await user.kick(reason=f"Automated warning escalation (5th warning): {reason}")
                except discord.Forbidden:
                    error_msg = "⚠️ Warning logged, but I don't have permission to apply timeout/kick!"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                except discord.HTTPException as e:
                    error_msg = f"⚠️ Warning logged, but failed to apply action: {str(e)}"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                
                # Send warning embed
                embed = EmbedViews.warning_embed(user, ctx.author, reason, warning_count, action)
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                
                # Send log message to configured log channel
                try:
                    leaderboard_manager = self.get_leaderboard_manager()
                    if leaderboard_manager:
                        log_channel_id = await leaderboard_manager.get_warning_log_channel(ctx.guild.id)
                        if log_channel_id:
                            log_channel = ctx.guild.get_channel(log_channel_id)
                            if log_channel:
                                log_embed = EmbedViews.warning_log_embed(user, ctx.author, reason, warning_count, action)
                                await log_channel.send(embed=log_embed)
                                logger.info(f"Warning logged to #{log_channel.name} for {user.display_name}")
                            else:
                                logger.warning(f"Warning log channel {log_channel_id} not found in guild {ctx.guild.name}")
                except Exception as e:
                    logger.error(f"Failed to send warning log: {e}")
                
                # Send DM to the warned user (if not kicked)
                if action != "kick":
                    try:
                        dm_embed = discord.Embed(
                            title="⚠️ You have been warned",
                            description=f"You have received a warning in **{ctx.guild.name}**.",
                            color=discord.Color.orange(),
                            timestamp=discord.utils.utcnow()
                        )
                        dm_embed.add_field(name="📝 Reason", value=reason, inline=False)
                        dm_embed.add_field(name="⚠️ Warning Count", value=f"{warning_count}/5", inline=True)
                        dm_embed.add_field(name="👮 Warned by", value=ctx.author.display_name, inline=True)
                        
                        if action != "warning":
                            action_text = {
                                "timeout_1h": "You have been timed out for 1 hour.",
                                "timeout_4h": "You have been timed out for 4 hours.",
                                "timeout_1w": "You have been timed out for 1 week."
                            }
                            dm_embed.add_field(name="⚡ Action Taken", value=action_text.get(action), inline=False)
                        
                        dm_embed.set_footer(text="Please follow the server rules to avoid further warnings.")
                        await user.send(embed=dm_embed)
                    except discord.Forbidden:
                        # User has DMs disabled, that's okay
                        pass
                    except Exception as e:
                        logger.error(f"Failed to send warning DM to {user.display_name}: {e}")
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to issue warning: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @self.bot.hybrid_command(name="warnings", description="View warnings for a user (Manage Server permission required)")
        @can_warn()
        async def warnings_command(ctx, user: discord.Member):
            """View warnings for a specific user"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                # Validate guild
                if not ctx.guild or ctx.guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Get warnings for the user
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                warnings = await leaderboard_manager.get_user_warnings(ctx.guild.id, user.id)
                warning_count = await leaderboard_manager.get_warning_count(ctx.guild.id, user.id)
                
                # Create and send embed
                embed = EmbedViews.user_warnings_embed(user, warnings, warning_count)
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to retrieve warnings: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @self.bot.hybrid_command(name="clearwarnings", description="Clear all warnings for a user (Manage Server permission required)")
        @can_warn()
        async def clearwarnings_command(ctx, user: discord.Member):
            """Clear all warnings for a user"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                # Validate guild
                if not ctx.guild or ctx.guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Clear warnings for the user
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                cleared_count = await leaderboard_manager.clear_user_warnings(ctx.guild.id, user.id)
                
                if cleared_count == 0:
                    error_msg = f"❌ {user.display_name} has no active warnings to clear."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Create and send embed
                embed = EmbedViews.warning_cleared_embed(user, cleared_count, ctx.author)
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                
                # Send log message to configured log channel
                try:
                    leaderboard_manager = self.get_leaderboard_manager()
                    if leaderboard_manager:
                        log_channel_id = await leaderboard_manager.get_warning_log_channel(ctx.guild.id)
                    if log_channel_id:
                        log_channel = ctx.guild.get_channel(log_channel_id)
                        if log_channel:
                            log_embed = discord.Embed(
                                title="🧹 Warnings Cleared",
                                description=f"All warnings have been cleared for {user.mention}",
                                color=discord.Color.green(),
                                timestamp=discord.utils.utcnow()
                            )
                            log_embed.add_field(name="👤 User", value=f"{user.mention}\n`{user.name}` ({user.id})", inline=True)
                            log_embed.add_field(name="👮 Cleared by", value=f"{ctx.author.mention}\n`{ctx.author.name}`", inline=True)
                            log_embed.add_field(name="📊 Warnings Cleared", value=f"**{cleared_count}** warnings", inline=True)
                            log_embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
                            log_embed.set_footer(text="Warning System Log", icon_url=ctx.author.display_avatar.url if ctx.author.display_avatar else None)
                            await log_channel.send(embed=log_embed)
                            logger.info(f"Warning clear logged to #{log_channel.name} for {user.display_name}")
                        else:
                            logger.warning(f"Warning log channel {log_channel_id} not found in guild {ctx.guild.name}")
                except Exception as e:
                    logger.error(f"Failed to send warning clear log: {e}")
                
                # Send DM to the user
                try:
                    dm_embed = discord.Embed(
                        title="🧹 Your warnings have been cleared",
                        description=f"All your warnings in **{ctx.guild.name}** have been cleared by a moderator.",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    dm_embed.add_field(name="👮 Cleared by", value=ctx.author.display_name, inline=True)
                    dm_embed.add_field(name="📊 Warnings Cleared", value=str(cleared_count), inline=True)
                    dm_embed.set_footer(text="You now have a clean slate! Please continue following the rules.")
                    await user.send(embed=dm_embed)
                except discord.Forbidden:
                    # User has DMs disabled, that's okay
                    pass
                except Exception as e:
                    logger.error(f"Failed to send warning clear DM to {user.display_name}: {e}")
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to clear warnings: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @self.bot.hybrid_command(name="quests", description="View your daily quests")
        async def quests_command(ctx):
            """View or generate daily quests for the user"""
            try:
                # Check if quest manager is available
                events_controller = self.get_events_controller()
                if not events_controller or not events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Quest system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = events_controller.quest_manager
                user_id = ctx.author.id
                
                # Get or generate daily quests
                quests = await quest_manager.get_user_daily_quests(user_id)
                if not quests:
                    quests = await quest_manager.generate_daily_quests(user_id)
                
                # Create and send embed
                embed = EmbedViews.daily_quests_embed(quests, ctx.author.display_name)
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in quests command: {e}")
                error_embed = EmbedViews.error_embed(f"Failed to get quests: {str(e)}")
                await ctx.send(embed=error_embed, ephemeral=True)
        
        @self.bot.hybrid_command(name="achievements", description="View your achievements")
        async def achievements_command(ctx, user: Optional[discord.Member] = None):
            """View achievements for yourself or another user"""
            try:
                # Check if quest manager is available
                events_controller = self.get_events_controller()
                if not events_controller or not events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Achievement system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = events_controller.quest_manager
                target_user = user or ctx.author
                
                # Get user achievements
                achievements = await quest_manager.get_user_achievements(target_user.id)
                
                # Create and send embed
                embed = EmbedViews.achievements_embed(achievements, target_user.display_name)
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in achievements command: {e}")
                error_embed = EmbedViews.error_embed(f"Failed to get achievements: {str(e)}")
                await ctx.send(embed=error_embed, ephemeral=True)
        
        @self.bot.hybrid_command(name="streaks", description="View your streaks and consistency stats")
        async def streaks_command(ctx, user: Optional[discord.Member] = None):
            """View streaks for yourself or another user"""
            try:
                # Check if quest manager is available
                events_controller = self.get_events_controller()
                if not events_controller or not events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Streak system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = events_controller.quest_manager
                target_user = user or ctx.author
                
                # Get user streaks
                streaks = await quest_manager.get_user_streaks(target_user.id)
                
                # Create and send embed
                embed = EmbedViews.streaks_embed(streaks, target_user.display_name)
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in streaks command: {e}")
                error_embed = EmbedViews.error_embed(f"Failed to get streaks: {str(e)}")
                await ctx.send(embed=error_embed, ephemeral=True)
        
        @self.bot.hybrid_command(name="events", description="View active image contest events")
        async def events_command(ctx):
            """View all active image contest events"""
            try:
                # Check if quest manager is available
                events_controller = self.get_events_controller()
                if not events_controller or not events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Events system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = events_controller.quest_manager
                
                # Get active events
                events = await quest_manager.get_active_events()
                
                # Create and send embed
                embed = EmbedViews.active_events_embed(events)
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in events command: {e}")
                error_embed = EmbedViews.error_embed(f"Failed to get events: {str(e)}")
                await ctx.send(embed=error_embed, ephemeral=True)
        
        @self.bot.hybrid_command(name="createevent", description="Create a new image contest event (Bot owners only)")
        @commands.is_owner()
        async def create_event_command(ctx, name: str, description: str, duration_hours: int = 24):
            """Create a new image contest event"""
            try:
                # Check if quest manager is available
                events_controller = self.get_events_controller()
                if not events_controller or not events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Events system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                # Validate inputs
                if len(name) > 100:
                    error_embed = EmbedViews.error_embed("Event name must be 100 characters or less.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                if len(description) > 500:
                    error_embed = EmbedViews.error_embed("Event description must be 500 characters or less.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                if duration_hours < 1 or duration_hours > 168:  # Max 1 week
                    error_embed = EmbedViews.error_embed("Duration must be between 1 and 168 hours (1 week).")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                events_controller = self.get_events_controller()
                if not events_controller or not events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Events system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = events_controller.quest_manager
                
                # Calculate start and end dates
                from datetime import datetime, timedelta
                start_date = datetime.now()
                end_date = start_date + timedelta(hours=duration_hours)
                
                # Create the event
                event_id = await quest_manager.create_event(
                    name=name,
                    description=description,
                    start_date=start_date,
                    end_date=end_date,
                    created_by_id=ctx.author.id,
                    created_by_name=ctx.author.display_name
                )
                
                if not event_id:
                    error_embed = EmbedViews.error_embed("Failed to create event.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                # Create event data for embed
                event_data = {
                    "name": name,
                    "description": description,
                    "start_date": start_date,
                    "end_date": end_date,
                    "created_by_name": ctx.author.display_name
                }
                
                # Send success embed
                embed = EmbedViews.event_created_embed(event_data)
                await ctx.send(embed=embed)
                
                logger.info(f"Created event '{name}' by {ctx.author.display_name}")
                
            except Exception as e:
                logger.error(f"Error in create event command: {e}")
                error_embed = EmbedViews.error_embed(f"Failed to create event: {str(e)}")
                await ctx.send(embed=error_embed, ephemeral=True)
        
        @self.bot.hybrid_command(name="endevent", description="End an active event and announce winner (Bot owners only)")
        @commands.is_owner()
        async def end_event_command(ctx, event_name: str):
            """End an active event and announce the winner"""
            try:
                # Check if quest manager is available
                events_controller = self.get_events_controller()
                if not events_controller or not events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Events system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = events_controller.quest_manager
                
                # Find the event by name
                active_events = await quest_manager.get_active_events()
                target_event = None
                
                for event in active_events:
                    if event['name'].lower() == event_name.lower():
                        target_event = event
                        break
                
                if not target_event:
                    error_embed = EmbedViews.error_embed(f"No active event found with name '{event_name}'")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                # End the event
                leaderboard_manager = self.get_leaderboard_manager()
                result = await quest_manager.end_event(
                    event_id=str(target_event['_id']),
                    leaderboard_manager=leaderboard_manager
                )
                
                if not result:
                    error_embed = EmbedViews.error_embed("Failed to end event.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                # Send winner announcement
                embed = EmbedViews.event_winner_embed(result['event'], result['winner'])
                await ctx.send(embed=embed)
                
                logger.info(f"Ended event '{event_name}' by {ctx.author.display_name}")
                
            except Exception as e:
                logger.error(f"Error in end event command: {e}")
                error_embed = EmbedViews.error_embed(f"Failed to end event: {str(e)}")
                await ctx.send(embed=error_embed, ephemeral=True)

        @self.bot.hybrid_command(name="setlogchannel", description="Set the channel for warning logs (Manage Server permission required)")
        @can_warn()
        async def setlogchannel_command(ctx, channel: Optional[discord.TextChannel] = None):
            """Set or view the warning log channel"""
            try:
                # Check if this is a slash command (has defer) or text command
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                # Validate guild
                if not ctx.guild or ctx.guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # If no channel provided, show current setting
                if channel is None:
                    leaderboard_manager = self.get_leaderboard_manager()
                    if not leaderboard_manager:
                        error_msg = "Leaderboard manager is not available."
                        if hasattr(ctx, 'followup'):
                            await ctx.followup.send(error_msg, ephemeral=True)
                        else:
                            await ctx.send(error_msg)
                        return
                    
                    current_channel_id = await leaderboard_manager.get_warning_log_channel(ctx.guild.id)
                    if current_channel_id:
                        current_channel = ctx.guild.get_channel(current_channel_id)
                        if current_channel:
                            embed = discord.Embed(
                                title="📋 Warning Log Channel",
                                description=f"Warnings are currently logged to {current_channel.mention}",
                                color=discord.Color.blue(),
                                timestamp=discord.utils.utcnow()
                            )
                            embed.add_field(name="Channel", value=f"#{current_channel.name}", inline=True)
                            embed.add_field(name="Channel ID", value=str(current_channel_id), inline=True)
                            embed.set_footer(text="Use /setlogchannel #channel to change")
                        else:
                            embed = discord.Embed(
                                title="⚠️ Warning Log Channel",
                                description="Warning log channel is set but the channel no longer exists!",
                                color=discord.Color.orange(),
                                timestamp=discord.utils.utcnow()
                            )
                            embed.add_field(name="Missing Channel ID", value=str(current_channel_id), inline=False)
                            embed.set_footer(text="Use /setlogchannel #channel to set a new channel")
                    else:
                        embed = discord.Embed(
                            title="📋 Warning Log Channel",
                            description="No warning log channel is currently set.",
                            color=discord.Color.light_grey(),
                            timestamp=discord.utils.utcnow()
                        )
                        embed.add_field(name="ℹ️ Info", value="Warnings will not be logged until a channel is set.", inline=False)
                        embed.set_footer(text="Use /setlogchannel #channel to set one")
                    
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(embed=embed)
                    else:
                        await ctx.send(embed=embed)
                    return
                
                # Set the new log channel
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                success = await leaderboard_manager.set_warning_log_channel(ctx.guild.id, channel.id)
                
                if success:
                    embed = discord.Embed(
                        title="✅ Warning Log Channel Set",
                        description=f"Warning logs will now be sent to {channel.mention}",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(name="Channel", value=f"#{channel.name}", inline=True)
                    embed.add_field(name="Set by", value=ctx.author.mention, inline=True)
                    embed.set_footer(text="All future warnings will be logged here")
                    
                    # Send a test log message
                    try:
                        test_embed = discord.Embed(
                            title="🔧 Warning Log Channel Configured",
                            description=f"This channel has been set as the warning log channel by {ctx.author.mention}.",
                            color=discord.Color.blue(),
                            timestamp=discord.utils.utcnow()
                        )
                        test_embed.add_field(name="📋 What gets logged here:", value="• Warning issued\n• User timeouts\n• User kicks\n• Warning clears", inline=False)
                        test_embed.set_footer(text="Warning System Configuration")
                        await channel.send(embed=test_embed)
                    except discord.Forbidden:
                        embed.add_field(name="⚠️ Warning", value="I don't have permission to send messages in that channel!", inline=False)
                    
                else:
                    embed = discord.Embed(
                        title="❌ Error",
                        description="Failed to set the warning log channel. Please try again.",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to set log channel: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @self.bot.hybrid_command(name="testbest", description="Test best image functionality with custom date range (Bot owners only)")
        @commands.is_owner()
        async def test_best_command(ctx, days_back: int = 7, channel_id: Optional[int] = None):
            """Test best image functionality with custom parameters"""
            try:
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                guild = ctx.guild
                if not guild or guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Calculate date range
                now = datetime.now()
                end_date = now
                start_date = now - timedelta(days=days_back)
                
                # Use provided channel or current channel
                test_channel_id = channel_id if channel_id else ctx.channel.id
                
                # Check if it's an image channel
                if test_channel_id not in Config.IMAGE_REACTION_CHANNELS:
                    error_msg = f"Channel {test_channel_id} is not configured as an image reaction channel."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Get the best image
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                best_image = await leaderboard_manager.get_best_image(
                    channel_id=str(test_channel_id),
                    start_date=start_date,
                    end_date=end_date
                )
                
                if not best_image:
                    response = f"❌ No images found in the last {days_back} days in channel {test_channel_id}"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(response)
                    else:
                        await ctx.send(response)
                    return
                
                # Create response embed
                embed = discord.Embed(
                    title="🔍 Debug: Best Image Found",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(name="📅 Date Range", value=f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", inline=False)
                embed.add_field(name="📺 Channel ID", value=str(test_channel_id), inline=True)
                embed.add_field(name="💬 Message ID", value=best_image['message_id'], inline=True)
                embed.add_field(name="👤 Author", value=best_image['author_name'], inline=True)
                embed.add_field(name="🏆 Score", value=str(best_image['score']), inline=True)
                embed.add_field(name="👍 Thumbs Up", value=str(best_image['thumbs_up']), inline=True)
                embed.add_field(name="👎 Thumbs Down", value=str(best_image['thumbs_down']), inline=True)
                embed.add_field(name="📅 Posted", value=best_image['created_at'].strftime('%Y-%m-%d %H:%M:%S'), inline=False)
                embed.add_field(name="🔗 Jump URL", value=f"[Original Message]({best_image['jump_url']})", inline=False)
                
                if best_image.get('image_url'):
                    embed.set_image(url=best_image['image_url'])
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to test best image: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @self.bot.hybrid_command(name="updatescore", description="Update scores for recent images by re-scanning reactions (Bot owners only)")
        @commands.is_owner()
        async def update_score_command(ctx, days_back: int = 7, channel_id: Optional[int] = None):
            """Update scores for recent images by re-scanning their reactions"""
            try:
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                guild = ctx.guild
                if not guild or guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Calculate date range
                now = datetime.now()
                start_date = now - timedelta(days=days_back)
                
                # Use provided channel or current channel
                test_channel_id = channel_id if channel_id else ctx.channel.id
                
                # Check if it's an image channel
                if test_channel_id not in Config.IMAGE_REACTION_CHANNELS:
                    error_msg = f"Channel {test_channel_id} is not configured as an image reaction channel."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                channel = guild.get_channel(test_channel_id)
                if not channel:
                    error_msg = f"Could not find channel {test_channel_id}"
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Get all images from the database in this time period
                leaderboard_manager = self.get_leaderboard_manager()
                if not leaderboard_manager:
                    error_msg = "Leaderboard manager is not available."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                images_in_db = list(leaderboard_manager.images_collection.find({
                    "channel_id": str(test_channel_id),
                    "created_at": {"$gte": start_date}
                }))
                
                updated_count = 0
                errors = 0
                
                for image_data in images_in_db:
                    try:
                        # Get the actual Discord message
                        message = await channel.fetch_message(int(image_data['message_id']))
                        
                        # Count reactions, excluding bot reactions
                        thumbs_up = 0
                        thumbs_down = 0
                        
                        for reaction in message.reactions:
                            if str(reaction.emoji) == '👍':
                                thumbs_up = reaction.count
                                # Check if bot reacted and subtract 1
                                async for user in reaction.users():
                                    if user.bot:
                                        thumbs_up = max(0, thumbs_up - 1)
                                        break
                            elif str(reaction.emoji) == '👎':
                                thumbs_down = reaction.count
                                # Check if bot reacted and subtract 1
                                async for user in reaction.users():
                                    if user.bot:
                                        thumbs_down = max(0, thumbs_down - 1)
                                        break
                        
                        # Update the database
                        await leaderboard_manager.update_image_message_score(
                            message_id=str(message.id),
                            thumbs_up=thumbs_up,
                            thumbs_down=thumbs_down
                        )
                        
                        updated_count += 1
                        
                        if updated_count % 10 == 0:
                            status = f"Updated {updated_count}/{len(images_in_db)} images..."
                            logger.info(status)
                    
                    except discord.NotFound:
                        # Message was deleted
                        logger.info(f"Message {image_data['message_id']} was deleted, removing from database")
                        await leaderboard_manager.delete_image_message(image_data['message_id'])
                        errors += 1
                    except Exception as e:
                        logger.error(f"Error updating message {image_data['message_id']}: {e}")
                        errors += 1
                
                # Create response embed
                embed = discord.Embed(
                    title="✅ Score Update Complete",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(name="📊 Updated Images", value=str(updated_count), inline=True)
                embed.add_field(name="❌ Errors", value=str(errors), inline=True)
                embed.add_field(name="📅 Days Back", value=str(days_back), inline=True)
                embed.add_field(name="📺 Channel", value=f"<#{test_channel_id}>", inline=False)
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to update scores: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @self.bot.hybrid_command(name="debugreactions", description="Debug reaction tracking setup (Bot owners only)")
        @commands.is_owner()
        async def debug_reactions_command(ctx):
            """Debug reaction tracking configuration and test setup"""
            try:
                embed = discord.Embed(
                    title="🔍 Reaction Tracking Debug",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                # Show current channel info
                current_channel = ctx.channel.id
                embed.add_field(
                    name="📍 Current Channel",
                    value=f"<#{current_channel}> (ID: {current_channel})",
                    inline=False
                )
                
                # Show configured channels
                channel_list = []
                for channel_id in Config.IMAGE_REACTION_CHANNELS:
                    channel = ctx.guild.get_channel(channel_id)
                    if channel:
                        status = "✅ Found" if current_channel == channel_id else "📍 Other"
                        channel_list.append(f"{status} <#{channel_id}> (#{channel.name})")
                    else:
                        channel_list.append(f"❌ Missing Channel ID: {channel_id}")
                
                embed.add_field(
                    name="⚙️ Configured Image Channels",
                    value="\n".join(channel_list) if channel_list else "None configured",
                    inline=False
                )
                
                # Check if current channel is valid for reactions
                is_valid_channel = current_channel in Config.IMAGE_REACTION_CHANNELS
                embed.add_field(
                    name="🎯 Reaction Tracking Status",
                    value="✅ ENABLED in this channel" if is_valid_channel else "❌ DISABLED in this channel",
                    inline=False
                )
                
                # Add testing instructions
                if is_valid_channel:
                    embed.add_field(
                        name="🧪 To Test",
                        value="1. Post an image in this channel\n2. React with 👍 or 👎\n3. Check bot logs for reaction messages",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🧪 To Test",
                        value="Switch to one of the configured image channels above, then:\n1. Post an image\n2. React with 👍 or 👎\n3. Check bot logs",
                        inline=False
                    )
                
                # Add guild info
                embed.add_field(
                    name="🏠 Guild Info",
                    value=f"Current: {ctx.guild.id}\nConfigured: {Config.GUILD_ID}\nMatch: {'✅ Yes' if ctx.guild.id == Config.GUILD_ID else '❌ No'}",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to debug reactions: {str(e)}")
                await ctx.send(embed=error_embed)

        # YouTube monitoring command group
        @self.bot.hybrid_group(name="youtube", description="Manage YouTube video monitoring")
        @commands.is_owner()
        async def youtube_group(ctx):
            """Base group for YouTube monitoring commands"""
            if ctx.invoked_subcommand is None:
                await ctx.send_help(youtube_group)

        @youtube_group.command(name="list", description="Show all monitored YouTube channels")
        async def youtube_list(ctx):
            """List all monitored YouTube channels"""
            try:
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                guild = ctx.guild
                if not guild or guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                youtube_monitor = getattr(self.bot, 'youtube_monitor', None)
                if not youtube_monitor:
                    error_msg = "YouTube monitoring is not initialized."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                channels = await youtube_monitor.get_monitored_channels_list()
                
                embed = discord.Embed(
                    title="📺 YouTube Monitoring Status",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                if channels:
                    for i, channel in enumerate(channels[:10], 1):  # Limit to 10
                        discord_channel = guild.get_channel(channel.get('discord_channel_id'))
                        channel_name = discord_channel.name if discord_channel else "Unknown"
                        
                        embed.add_field(
                            name=f"{i}. {channel.get('channel_name', 'Unknown')}",
                            value=f"**ID:** `{channel.get('youtube_channel_id')}`\n"
                                  f"**Posts to:** #{channel_name}\n"
                                  f"**Status:** {'🟢 Active' if channel.get('enabled') else '🔴 Disabled'}",
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="No Channels Monitored",
                        value="Use `/youtube add` to start monitoring channels",
                        inline=False
                    )
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to list YouTube channels: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @youtube_group.command(name="add", description="Add a YouTube channel to monitor")
        async def youtube_add(ctx, youtube_channel_id: str, discord_channel: discord.TextChannel):
            """Add a YouTube channel to monitor"""
            try:
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                guild = ctx.guild
                if not guild or guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                youtube_monitor = getattr(self.bot, 'youtube_monitor', None)
                if not youtube_monitor:
                    error_msg = "YouTube monitoring is not initialized."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                success = await youtube_monitor.add_monitored_channel(
                    youtube_channel_id=youtube_channel_id,
                    discord_channel_id=discord_channel.id,
                    guild_id=guild.id
                )
                
                if success:
                    channel_info = await youtube_monitor.get_channel_info(youtube_channel_id)
                    embed = discord.Embed(
                        title="✅ YouTube Monitor Added",
                        description=f"Now monitoring **{channel_info.get('title', 'Unknown')}** for new videos",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="YouTube Channel", value=youtube_channel_id, inline=True)
                    embed.add_field(name="Discord Channel", value=discord_channel.mention, inline=True)
                    embed.add_field(name="Character", value="Ino will announce new videos", inline=False)
                else:
                    embed = EmbedViews.error_embed("Failed to add YouTube monitor. Check if the channel ID is valid.")
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to add YouTube monitor: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @youtube_group.command(name="remove", description="Remove a YouTube channel from monitoring")
        async def youtube_remove(ctx, youtube_channel_id: str):
            """Remove a YouTube channel from monitoring"""
            try:
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                guild = ctx.guild
                if not guild or guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                youtube_monitor = getattr(self.bot, 'youtube_monitor', None)
                if not youtube_monitor:
                    error_msg = "YouTube monitoring is not initialized."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                success = await youtube_monitor.remove_monitored_channel(youtube_channel_id)
                
                if success:
                    embed = discord.Embed(
                        title="✅ YouTube Monitor Removed",
                        description=f"No longer monitoring channel `{youtube_channel_id}`",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                else:
                    embed = EmbedViews.error_embed("Channel not found in monitoring list.")
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to remove YouTube monitor: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @youtube_group.command(name="test", description="Test Ino's response to a YouTube channel's latest video")
        async def youtube_test(ctx, youtube_channel_id: str):
            """Test Ino's response generation for a YouTube channel"""
            try:
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                guild = ctx.guild
                if not guild or guild.id != Config.GUILD_ID:
                    error_msg = "This command can only be used in the configured guild."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                youtube_monitor = getattr(self.bot, 'youtube_monitor', None)
                if not youtube_monitor:
                    error_msg = "YouTube monitoring is not initialized."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Get latest video and generate response
                videos = await youtube_monitor.get_recent_videos(youtube_channel_id)
                if videos:
                    latest_video = videos[0]
                    ino_response = await youtube_monitor.generate_ino_response(latest_video)
                    
                    embed = discord.Embed(
                        title="🧪 Test Ino Response",
                        color=discord.Color.purple(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="Latest Video", value=latest_video.get('title', 'Unknown'), inline=False)
                    embed.add_field(name="Video Link", value=latest_video.get('link', 'N/A'), inline=False)
                    embed.add_field(name="Ino's Response", value=ino_response or "Failed to generate response", inline=False)
                else:
                    embed = EmbedViews.error_embed("No videos found for this channel.")
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to test YouTube response: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @youtube_group.command(name="help", description="Show YouTube monitoring help and setup guide")
        async def youtube_help(ctx):
            """Show help for YouTube monitoring commands"""
            try:
                embed = discord.Embed(
                    title="📺 YouTube Monitor Help",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(
                    name="Available Commands",
                    value="• `/youtube list` - Show monitored channels\n"
                          "• `/youtube add <channel_id> <discord_channel>` - Add monitoring\n"
                          "• `/youtube remove <channel_id>` - Remove monitoring\n"
                          "• `/youtube test <channel_id>` - Test Ino response",
                    inline=False
                )
                embed.add_field(
                    name="How to find YouTube Channel ID",
                    value="**Method 1:** Go to the channel → View page source (Ctrl+U) → Search for `channelId`\n"
                          "**Method 2:** Use a browser extension like 'YouTube Channel ID'\n"
                          "**Method 3:** Go to channel → About tab → Copy channel ID (if available)",
                    inline=False
                )
                embed.add_field(
                    name="Setup Requirements",
                    value="• `GEMINI_API_KEY` must be set in `.env` file\n"
                          "• Bot needs access to the Discord channel\n"
                          "• YouTube channel must be public",
                    inline=False
                )
                embed.add_field(
                    name="How It Works",
                    value="Ino checks for new videos every 10 minutes and posts character-appropriate announcements using AI",
                    inline=False
                )
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to show help: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        @youtube_group.command(name="validate", description="Validate a YouTube channel ID without adding it")
        async def youtube_validate(ctx, youtube_channel_id: str):
            """Validate a YouTube channel ID without adding it to monitoring"""
            try:
                if hasattr(ctx, 'defer'):
                    await ctx.defer()
                
                youtube_monitor = getattr(self.bot, 'youtube_monitor', None)
                if not youtube_monitor:
                    error_msg = "YouTube monitoring is not initialized."
                    if hasattr(ctx, 'followup'):
                        await ctx.followup.send(error_msg, ephemeral=True)
                    else:
                        await ctx.send(error_msg)
                    return
                
                # Test the channel validation
                channel_info = await youtube_monitor.get_channel_info(youtube_channel_id)
                
                if channel_info:
                    embed = discord.Embed(
                        title="✅ YouTube Channel Valid",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="Channel ID", value=youtube_channel_id, inline=True)
                    embed.add_field(name="Channel Name", value=channel_info.get('title', 'Unknown'), inline=True)
                    embed.add_field(name="Description", value=channel_info.get('description', 'No description')[:100] + '...', inline=False)
                    embed.add_field(name="Channel Link", value=channel_info.get('link', 'N/A'), inline=False)
                    
                    if channel_info.get('latest_video'):
                        latest = channel_info['latest_video']
                        embed.add_field(name="Latest Video", value=f"[{latest.get('title', 'Unknown')}]({latest.get('link', '')})", inline=False)
                else:
                    embed = discord.Embed(
                        title="❌ YouTube Channel Invalid",
                        description=f"Could not validate channel ID: `{youtube_channel_id}`\n\n**Possible issues:**\n• Channel doesn't exist\n• Channel is private\n• Invalid channel ID format\n• Network/API issues",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(
                        name="How to find correct Channel ID",
                        value="1. Go to the YouTube channel\n2. Click 'About' tab\n3. Look for 'Channel ID' or use browser extension\n4. Should start with 'UC' and be 24 characters long",
                        inline=False
                    )
                
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=embed)
                else:
                    await ctx.send(embed=embed)
                    
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to validate YouTube channel: {str(e)}")
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await ctx.send(embed=error_embed)

        # Store references to prevent garbage collection
        self.debug_command = debug_command
        self.test_owner_command = test_owner_command
        self.uptime_command = uptime_command 
        self.process_old_command = process_old_command
        self.best_week_command = best_week_command
        self.best_month_command = best_month_command
        self.best_year_command = best_year_command
        self.leaderboard_command = leaderboard_command
        self.stats_command = stats_command 
        self.db_status_command = db_status_command
        self.nsfwban_command = nsfwban_command
        self.nsfwunban_command = nsfwunban_command
        self.warn_command = warn_command
        self.warnings_command = warnings_command
        self.clearwarnings_command = clearwarnings_command
        self.setlogchannel_command = setlogchannel_command
        self.youtube_group = youtube_group
        self.youtube_list = youtube_list
        self.youtube_add = youtube_add
        self.youtube_remove = youtube_remove
        self.youtube_test = youtube_test
        self.youtube_help = youtube_help
        self.youtube_validate = youtube_validate
        self.debug_reactions_command = debug_reactions_command

        # TEMPORARY RESEARCH COMMANDS FOR RANDOM ANNOUNCEMENTS
        @self.bot.hybrid_command(name='start_announcements', description='Start random announcements (RESEARCH)')
        @commands.is_owner()
        async def start_announcements_cmd(ctx):
            """Start the random announcement system"""
            random_announcer = self.get_random_announcer()
            if not random_announcer:
                await ctx.send("❌ Random announcer is not initialized!")
                return
            
            if random_announcer.random_announcement_task.is_running():
                await ctx.send("⚠️ Random announcements are already running!")
                return
            
            random_announcer.start_announcements()
            await ctx.send("✅ Started random announcement system! Announcements will be posted every 15 minutes.")

        @self.bot.hybrid_command(name='stop_announcements', description='Stop random announcements (RESEARCH)')
        @commands.is_owner()
        async def stop_announcements_cmd(ctx):
            """Stop the random announcement system"""
            random_announcer = self.get_random_announcer()
            if not random_announcer:
                await ctx.send("❌ Random announcer is not initialized!")
                return
            
            if not random_announcer.random_announcement_task.is_running():
                await ctx.send("⚠️ Random announcements are not running!")
                return
            
            random_announcer.stop_announcements()
            await ctx.send("🛑 Stopped random announcement system!")

        @self.bot.hybrid_command(name='test_announcement', description='Test a specific personality announcement (RESEARCH)')
        @commands.is_owner()
        async def test_announcement_cmd(ctx, personality: str = 'tame'):
            """Test an announcement with a specific personality"""
            random_announcer = self.get_random_announcer()
            if not random_announcer:
                await ctx.send("❌ Random announcer is not initialized!")
                return
            
            valid_personalities = list(random_announcer.personality_variations.keys())
            if personality not in valid_personalities:
                await ctx.send(f"❌ Invalid personality! Valid options: {', '.join(valid_personalities)}")
                return
            
            await ctx.send(f"🧪 Testing {personality} personality...")
            
            # Generate and post test announcement
            announcement = await random_announcer.generate_random_announcement(personality)
            if announcement:
                await random_announcer.post_announcement(announcement, personality)
                await ctx.send(f"✅ Posted test announcement with {personality} personality!")
            else:
                await ctx.send("❌ Failed to generate test announcement!")

        @self.bot.hybrid_command(name='announcement_stats', description='Get feedback statistics (RESEARCH)')
        @commands.is_owner()
        async def announcement_stats_cmd(ctx, days: int = 7):
            """Get feedback statistics for random announcements"""
            random_announcer = self.get_random_announcer()
            if not random_announcer:
                await ctx.send("❌ Random announcer is not initialized!")
                return
            
            stats = await random_announcer.get_feedback_stats(days)
            
            if not stats:
                await ctx.send(f"📊 No feedback data found for the last {days} days.")
                return
            
            embed = discord.Embed(
                title=f"📊 Announcement Feedback Stats ({days} days)",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            for personality, data in stats.items():
                likes = data.get('likes', 0)
                dislikes = data.get('dislikes', 0)
                total = likes + dislikes
                
                if total > 0:
                    percentage = (likes / total) * 100
                    embed.add_field(
                        name=f"🎭 {personality.title()}",
                        value=f"👍 {likes} | 👎 {dislikes}\n📈 {percentage:.1f}% positive",
                        inline=True
                    )
            
            embed.set_footer(text="Research data for personality optimization")
            await ctx.send(embed=embed)