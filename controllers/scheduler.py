import discord
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from config import Config
from views.embeds import EmbedViews

logger = logging.getLogger(__name__)

class SchedulerController:
    """Controller for handling scheduled tasks like best image posts"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def start_tasks(self):
        """Start all scheduled tasks"""
        logger.info("Starting scheduled tasks...")
        
        # Start weekly and monthly tasks
        if not self.weekly_best_image.is_running():
            self.weekly_best_image.start()
        
        if not self.monthly_best_image.is_running():
            self.monthly_best_image.start()
    
    def stop_tasks(self):
        """Stop all scheduled tasks"""
        logger.info("Stopping scheduled tasks...")
        
        if self.weekly_best_image.is_running():
            self.weekly_best_image.cancel()
        
        if self.monthly_best_image.is_running():
            self.monthly_best_image.cancel()
    
    @tasks.loop(hours=24)  # Check daily
    async def weekly_best_image(self):
        """Post the best image of the week every Sunday"""
        try:
            now = datetime.now()
            # Check if it's Sunday (weekday 6)
            if now.weekday() == 6:  # Sunday
                logger.info("Starting weekly best image selection...")
                
                # Get the date range for the past week
                end_date = now
                start_date = now - timedelta(days=7)
                
                await self._post_best_image("week", start_date, end_date)
                
        except Exception as e:
            logger.error(f"Error in weekly best image task: {e}")
    
    @tasks.loop(hours=24)  # Check daily
    async def monthly_best_image(self):
        """Post the best image of the month on the first day of each month"""
        try:
            now = datetime.now()
            # Check if it's the first day of the month
            if now.day == 1:
                logger.info("Starting monthly best image selection...")
                
                # Get the date range for the past month
                end_date = now
                # Go back to the first day of last month
                if now.month == 1:
                    start_date = now.replace(year=now.year-1, month=12, day=1)
                else:
                    start_date = now.replace(month=now.month-1, day=1)
                
                await self._post_best_image("month", start_date, end_date)
                
        except Exception as e:
            logger.error(f"Error in monthly best image task: {e}")
    
    async def _post_best_image(self, period: str, start_date: datetime, end_date: datetime):
        """Find and post the best image for the given period"""
        try:
            # Check if best image channel is configured
            if not Config.BEST_IMAGE_CHANNEL_ID:
                logger.warning(f"BEST_IMAGE_CHANNEL_ID not configured, skipping {period}ly best image post")
                return
            
            guild = self.bot.get_guild(Config.GUILD_ID)
            if not guild:
                logger.error(f"Could not find guild {Config.GUILD_ID}")
                return
            
            best_image_channel = guild.get_channel(Config.BEST_IMAGE_CHANNEL_ID)
            if not best_image_channel:
                logger.error(f"Could not find best image channel {Config.BEST_IMAGE_CHANNEL_ID}")
                return
            
            # Find the best image from both channels
            best_message, best_score = await self._find_best_image_in_period(guild, start_date, end_date)
            
            if not best_message:
                logger.info(f"No images found for {period}ly best image")
                # Post a "no winner" message
                embed = EmbedViews.no_winner_embed(period)
                await best_image_channel.send(embed=embed)
                return
            
            # Create and post the winning image embed
            embed = await EmbedViews.best_image_embed(best_message, period, best_score)
            await best_image_channel.send(embed=embed)
            
            logger.info(f"Posted {period}ly best image by {best_message.author.display_name} with {best_score} net upvotes")
            
        except Exception as e:
            logger.error(f"Error posting {period}ly best image: {e}")
    
    async def _find_best_image_in_period(self, guild: discord.Guild, start_date: datetime, end_date: datetime) -> Tuple[Optional[discord.Message], int]:
        """Find the image with the highest net upvotes in the given period"""
        best_message = None
        best_score = -1
        
        # Search through both image reaction channels
        for channel_id in Config.IMAGE_REACTION_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                logger.warning(f"Could not find channel {channel_id}")
                continue
            
            logger.info(f"Searching for best images in #{channel.name}")
            
            try:
                # Search through messages in the time period
                async for message in channel.history(
                    after=start_date,
                    before=end_date,
                    limit=None
                ):
                    # Check if message has images
                    if not await self._message_has_image(message):
                        continue
                    
                    # Calculate net upvotes (thumbs up - thumbs down)
                    net_score = await self._calculate_net_score(message)
                    
                    if net_score > best_score:
                        best_score = net_score
                        best_message = message
                        logger.info(f"New best image found: {net_score} net upvotes by {message.author.display_name}")
            
            except Exception as e:
                logger.error(f"Error searching in channel {channel.name}: {e}")
        
        return best_message, best_score
    
    async def _message_has_image(self, message: discord.Message) -> bool:
        """Check if a message contains an image"""
        # Check for attachments (uploaded images)
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                return True
        
        # Check for embedded images (links)
        for embed in message.embeds:
            if embed.image or embed.thumbnail:
                return True
        
        return False
    
    async def _calculate_net_score(self, message: discord.Message) -> int:
        """Calculate net score (thumbs up - thumbs down) for a message"""
        thumbs_up = 0
        thumbs_down = 0
        
        for reaction in message.reactions:
            if str(reaction.emoji) == '👍':
                thumbs_up = reaction.count
            elif str(reaction.emoji) == '👎':
                thumbs_down = reaction.count
        
        return thumbs_up - thumbs_down
    
    @weekly_best_image.before_loop
    async def before_weekly_task(self):
        """Wait until the bot is ready before starting weekly task"""
        await self.bot.wait_until_ready()
    
    @monthly_best_image.before_loop
    async def before_monthly_task(self):
        """Wait until the bot is ready before starting monthly task"""
        await self.bot.wait_until_ready() 