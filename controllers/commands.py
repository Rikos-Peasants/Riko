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
                await ctx.defer()  # This might take a while
                
                # Get the date range for the past week
                now = datetime.now()
                end_date = now
                start_date = now - timedelta(days=7)
                
                # Use the scheduler controller to post the best image
                await self.bot.scheduler_controller._post_best_image("week", start_date, end_date)
                
                await ctx.followup.send("✅ Best image of the week has been posted!", ephemeral=True)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to post best image: {str(e)}")
                await ctx.followup.send(embed=error_embed, ephemeral=True)
        
        @self.bot.hybrid_command(name="bestmonth", description="Manually post the best image of this month (Bot owners only)")
        @commands.is_owner()
        async def best_month_command(ctx):
            """Manually trigger best image of the month post"""
            try:
                await ctx.defer()  # This might take a while
                
                # Get the date range for the past month
                now = datetime.now()
                end_date = now
                start_date = now.replace(day=1)  # First day of current month
                
                # Use the scheduler controller to post the best image
                await self.bot.scheduler_controller._post_best_image("month", start_date, end_date)
                
                await ctx.followup.send("✅ Best image of the month has been posted!", ephemeral=True)
                
            except Exception as e:
                error_embed = EmbedViews.error_embed(f"Failed to post best image: {str(e)}")
                await ctx.followup.send(embed=error_embed, ephemeral=True)
        
        # Store references to prevent garbage collection
        self.uptime_command = uptime_command
        self.best_week_command = best_week_command
        self.best_month_command = best_month_command 