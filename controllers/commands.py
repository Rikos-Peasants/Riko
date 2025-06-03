import discord
from discord.ext import commands
from datetime import datetime, timedelta
from models.role_manager import RoleManager
from views.embeds import EmbedViews
from config import Config

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
                completion_msg += f"• **Unique Users:** {len(total_users)}\n"
                completion_msg += f"• **Channels:** {len(Config.IMAGE_REACTION_CHANNELS)}\n"
                completion_msg += f"• **Time Period:** Past 365 days\n\n"
                
                if total_processed > 0:
                    completion_msg += f"🏆 Use `R!leaderboard` or `/leaderboard` to see the updated rankings!"
                else:
                    completion_msg += f"⚠️ No images found in the specified time period."
                
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