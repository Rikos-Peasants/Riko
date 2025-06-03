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
        
        # Start weekly, monthly, and yearly tasks
        if not self.weekly_best_image.is_running():
            self.weekly_best_image.start()
        
        if not self.monthly_best_image.is_running():
            self.monthly_best_image.start()
        
        if not self.yearly_best_image.is_running():
            self.yearly_best_image.start()
    
    def stop_tasks(self):
        """Stop all scheduled tasks"""
        logger.info("Stopping scheduled tasks...")
        
        if self.weekly_best_image.is_running():
            self.weekly_best_image.cancel()
        
        if self.monthly_best_image.is_running():
            self.monthly_best_image.cancel()
        
        if self.yearly_best_image.is_running():
            self.yearly_best_image.cancel()
    
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
    
    @tasks.loop(hours=24)  # Check daily
    async def yearly_best_image(self):
        """Post the best image of the year on the first day of January"""
        try:
            now = datetime.now()
            # Check if it's the first day of January
            if now.month == 1 and now.day == 1:
                logger.info("Starting yearly best image selection...")
                
                # Get the date range for the past year
                end_date = now
                start_date = now.replace(year=now.year-1, month=1, day=1)
                
                await self._post_best_image("year", start_date, end_date)
                
        except Exception as e:
            logger.error(f"Error in yearly best image task: {e}")
    
    async def _post_best_image(self, period: str, start_date: datetime, end_date: datetime):
        """Find and post the best image for the given period"""
        try:
            guild = self.bot.get_guild(Config.GUILD_ID)
            if not guild:
                logger.error(f"Could not find guild {Config.GUILD_ID}")
                return
            
            # Find the best image from each channel separately
            for channel_id in Config.IMAGE_REACTION_CHANNELS:
                channel = guild.get_channel(channel_id)
                if not channel:
                    logger.warning(f"Could not find channel {channel_id}")
                    continue
                
                logger.info(f"Finding best image in #{channel.name} for {period}")
                
                # Find the best image in this specific channel
                best_message, best_score = await self._find_best_image_in_channel(channel, start_date, end_date)
                
                if not best_message:
                    logger.info(f"No images found for {period}ly best image in #{channel.name}")
                    # Post a "no winner" message in this channel
                    embed = EmbedViews.no_winner_embed(period)
                    embed.add_field(
                        name="📍 Channel",
                        value=f"#{channel.name}",
                        inline=False
                    )
                    await channel.send(embed=embed)
                    continue
                
                # Create and post the winning image embed in the original channel
                embed = await EmbedViews.best_image_embed(best_message, period, best_score)
                embed.add_field(
                    name="🏆 Winner in this Channel",
                    value=f"Most upvoted image in #{channel.name}",
                    inline=False
                )
                await channel.send(embed=embed)
                
                logger.info(f"Posted {period}ly best image in #{channel.name} by {best_message.author.display_name} with {best_score} net upvotes")
                
        except Exception as e:
            logger.error(f"Error posting {period}ly best image: {e}")
    
    async def _find_best_image_in_channel(self, channel: discord.TextChannel, start_date: datetime, end_date: datetime) -> Tuple[Optional[discord.Message], int]:
        """Find the image with the highest net upvotes in a specific channel"""
        best_message = None
        best_score = -1
        
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
                    logger.info(f"New best image found in #{channel.name}: {net_score} net upvotes by {message.author.display_name}")
        
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
    
    async def generate_leaderboard(self, guild: discord.Guild, start_date: datetime = None, end_date: datetime = None) -> List[Tuple[str, int, int, int]]:
        """Generate leaderboard data for the specified period"""
        user_stats = {}  # user_id: {'name': str, 'total_score': int, 'image_count': int}
        
        # Search through both image reaction channels
        for channel_id in Config.IMAGE_REACTION_CHANNELS:
            channel = guild.get_channel(channel_id)
            if not channel:
                logger.warning(f"Could not find channel {channel_id}")
                continue
            
            logger.info(f"Analyzing images in #{channel.name} for leaderboard")
            
            try:
                # Build message history query
                history_kwargs = {}
                if start_date:
                    history_kwargs['after'] = start_date
                if end_date:
                    history_kwargs['before'] = end_date
                history_kwargs['limit'] = None
                
                # Search through messages in the time period
                async for message in channel.history(**history_kwargs):
                    # Check if message has images
                    if not await self._message_has_image(message):
                        continue
                    
                    # Calculate net upvotes (thumbs up - thumbs down)
                    net_score = await self._calculate_net_score(message)
                    
                    # Add to user stats
                    user_id = message.author.id
                    user_name = message.author.display_name
                    
                    if user_id not in user_stats:
                        user_stats[user_id] = {
                            'name': user_name,
                            'total_score': 0,
                            'image_count': 0
                        }
                    
                    user_stats[user_id]['total_score'] += net_score
                    user_stats[user_id]['image_count'] += 1
            
            except Exception as e:
                logger.error(f"Error analyzing channel {channel.name}: {e}")
        
        # Convert to sorted list format: (user_name, user_id, total_score, image_count)
        leaderboard = []
        for user_id, stats in user_stats.items():
            leaderboard.append((
                stats['name'],
                user_id,
                stats['total_score'],
                stats['image_count']
            ))
        
        # Sort by total score (descending)
        leaderboard.sort(key=lambda x: x[2], reverse=True)
        
        return leaderboard
    
    @weekly_best_image.before_loop
    async def before_weekly_task(self):
        """Wait until the bot is ready before starting weekly task"""
        await self.bot.wait_until_ready()
    
    @monthly_best_image.before_loop
    async def before_monthly_task(self):
        """Wait until the bot is ready before starting monthly task"""
        await self.bot.wait_until_ready()
    
    @yearly_best_image.before_loop
    async def before_yearly_task(self):
        """Wait until the bot is ready before starting yearly task"""
        await self.bot.wait_until_ready() 