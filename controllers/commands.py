import discord
from discord.ext import commands
from datetime import datetime, timedelta
import logging
from models.role_manager import RoleManager
from views.embeds import EmbedViews
from config import Config

logger = logging.getLogger(__name__)

class CommandsController:
    """Controller for handling bot commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.utcnow()
    
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
                bot_user_id = self.bot.user.id
                
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
                                if await self.bot.leaderboard_manager.image_message_exists(str(message.id)):
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
                                    await self.bot.leaderboard_manager.store_image_message(
                                        message=message,
                                        image_url=image_url,
                                        initial_score=net_score
                                    )
                                    
                                    # Update the image message score with current reactions
                                    await self.bot.leaderboard_manager.update_image_message_score(
                                        message_id=str(message.id),
                                        thumbs_up=thumbs_up,
                                        thumbs_down=thumbs_down
                                    )
                                
                                # Add to leaderboard (this will create or update the user)
                                self.bot.leaderboard_manager.add_image_post(
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
                
                # Get the date range for the past week
                now = datetime.now()
                end_date = now
                start_date = now - timedelta(days=7)
                
                # Use the scheduler controller to post the best image
                await self.bot.scheduler_controller._post_best_image("week", start_date, end_date)
                
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
                
                # Get the date range for the past month
                now = datetime.now()
                end_date = now
                start_date = now.replace(day=1)  # First day of current month
                
                # Use the scheduler controller to post the best image
                await self.bot.scheduler_controller._post_best_image("month", start_date, end_date)
                
                # Send response based on command type
                if hasattr(ctx, 'followup'):
                    await ctx.followup.send("✅ Best image of the month has been posted to each image channel!", ephemeral=True)
                else:
                    await ctx.send("✅ Best image of the month has been posted to each image channel!")
                
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
                await self.bot.scheduler_controller._post_best_image("year", start_date, end_date)
                
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
                leaderboard_data = self.bot.leaderboard_manager.get_leaderboard(limit=10)
                
                # Create and send embed
                embed = EmbedViews.leaderboard_embed(leaderboard_data, "all time")
                
                # Add stats summary
                stats = self.bot.leaderboard_manager.get_stats_summary()
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
        async def stats_command(ctx, user: discord.Member = None):
            """Show stats for yourself or another user"""
            try:
                target_user = user if user else ctx.author
                
                # Get user stats
                stats = self.bot.leaderboard_manager.get_user_stats(target_user.id)
                
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
                stats = self.bot.leaderboard_manager.get_stats_summary()
                
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
                if await self.bot.leaderboard_manager.is_nsfwban_user(user.id):
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
                success = await self.bot.leaderboard_manager.add_nsfwban_user(
                    user_id=user.id,
                    user_name=user.display_name,
                    banned_by_id=ctx.author.id,
                    banned_by_name=ctx.author.display_name,
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
                if not await self.bot.leaderboard_manager.is_nsfwban_user(user.id):
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
                success = await self.bot.leaderboard_manager.remove_nsfwban_user(user.id)
                
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
                warning_result = await self.bot.leaderboard_manager.add_warning(
                    guild_id=ctx.guild.id,
                    user_id=user.id,
                    user_name=user.display_name,
                    moderator_id=ctx.author.id,
                    moderator_name=ctx.author.display_name,
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
                    log_channel_id = await self.bot.leaderboard_manager.get_warning_log_channel(ctx.guild.id)
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
                warnings = await self.bot.leaderboard_manager.get_user_warnings(ctx.guild.id, user.id)
                warning_count = await self.bot.leaderboard_manager.get_warning_count(ctx.guild.id, user.id)
                
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
                cleared_count = await self.bot.leaderboard_manager.clear_user_warnings(ctx.guild.id, user.id)
                
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
                    log_channel_id = await self.bot.leaderboard_manager.get_warning_log_channel(ctx.guild.id)
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
                if not hasattr(self.bot, 'events_controller') or not self.bot.events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Quest system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = self.bot.events_controller.quest_manager
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
        async def achievements_command(ctx, user: discord.Member = None):
            """View achievements for yourself or another user"""
            try:
                # Check if quest manager is available
                if not hasattr(self.bot, 'events_controller') or not self.bot.events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Achievement system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = self.bot.events_controller.quest_manager
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
        async def streaks_command(ctx, user: discord.Member = None):
            """View streaks for yourself or another user"""
            try:
                # Check if quest manager is available
                if not hasattr(self.bot, 'events_controller') or not self.bot.events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Streak system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = self.bot.events_controller.quest_manager
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
                if not hasattr(self.bot, 'events_controller') or not self.bot.events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Events system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = self.bot.events_controller.quest_manager
                
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
                if not hasattr(self.bot, 'events_controller') or not self.bot.events_controller.quest_manager:
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
                
                quest_manager = self.bot.events_controller.quest_manager
                
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
                if not hasattr(self.bot, 'events_controller') or not self.bot.events_controller.quest_manager:
                    error_embed = EmbedViews.error_embed("Events system is not available at the moment.")
                    await ctx.send(embed=error_embed, ephemeral=True)
                    return
                
                quest_manager = self.bot.events_controller.quest_manager
                
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
                result = await quest_manager.end_event(
                    event_id=str(target_event['_id']),
                    leaderboard_manager=self.bot.leaderboard_manager
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
        async def setlogchannel_command(ctx, channel: discord.TextChannel = None):
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
                    current_channel_id = await self.bot.leaderboard_manager.get_warning_log_channel(ctx.guild.id)
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
                success = await self.bot.leaderboard_manager.set_warning_log_channel(ctx.guild.id, channel.id)
                
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