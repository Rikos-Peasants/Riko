import discord
from discord.ext import commands
from datetime import datetime, timedelta
from models.role_manager import RoleManager
from views.embeds import EmbedViews

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
        async def leaderboard_command(ctx, period: str = "all"):
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
                
                # Determine time period
                start_date = None
                end_date = datetime.now()
                period_name = "all time"
                
                if period.lower() in ["week", "weekly"]:
                    start_date = end_date - timedelta(days=7)
                    period_name = "this week"
                elif period.lower() in ["month", "monthly"]:
                    start_date = end_date.replace(day=1)
                    period_name = "this month"
                elif period.lower() in ["year", "yearly"]:
                    start_date = end_date.replace(month=1, day=1)
                    period_name = "this year"
                
                # Generate leaderboard data
                leaderboard_data = await self.bot.scheduler_controller.generate_leaderboard(guild, start_date, end_date)
                
                # Create and send embed
                embed = EmbedViews.leaderboard_embed(leaderboard_data, period_name)
                
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
        
        # Store references to prevent garbage collection
        self.debug_command = debug_command
        self.uptime_command = uptime_command
        self.best_week_command = best_week_command
        self.best_month_command = best_month_command
        self.best_year_command = best_year_command
        self.leaderboard_command = leaderboard_command 