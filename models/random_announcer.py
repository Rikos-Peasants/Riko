import discord
from discord.ext import tasks
import logging
from typing import Optional, Dict, Any, List
import asyncio
import random
from config import Config
from google import genai
from google.genai import types
import aiohttp
import feedparser

logger = logging.getLogger(__name__)

class RandomAnnouncer:
    """Random announcement system for testing Ino personality variations"""
    
    def __init__(self, bot, leaderboard_manager):
        self.bot = bot
        self.leaderboard_manager = leaderboard_manager
        
        # Test YouTube channels for random video selection
        self.test_channels = [
            "UC8rcEBzJSleTkf_-agPM20g",  # BlueArchive_JP
            "UCdBK94H6oZT2Q7l0-b0xmMg",  # ShortCircuit
            "UChhMeymAOC5PNbbnqxD_w4g",  # JustRayen
            "UCcNxBnLuFa3Rp3nJX3wBKcw"   # pikachubolk
        ]
        
        # Ino personality variations for testing
        self.personality_variations = {
            'standard': {
                'description': 'Standard Ino personality from system prompt',
                'modifier': ''
            },
            'extra_teasing': {
                'description': 'More teasing and playful than usual',
                'modifier': 'Be extra teasing and playful in your announcement. Add more gentle mockery and exasperation.'
            },
            'more_caring': {
                'description': 'More caring and supportive than usual',
                'modifier': 'Be extra caring and supportive in your announcement. Show more warmth and encouragement.'
            },
            'formal_shrine': {
                'description': 'More formal shrine keeper personality',
                'modifier': 'Be more formal and dignified as a shrine keeper. Use more traditional and respectful language.'
            },
            'exasperated': {
                'description': 'Extra exasperated and sighing',
                'modifier': 'Be extra exasperated and tired in your announcement. More sighing and "what am I dealing with" energy.'
            }
        }
        
        # Initialize Gemini AI
        self.gemini_api_key = Config.GEMINI_API_KEY if hasattr(Config, 'GEMINI_API_KEY') and Config.GEMINI_API_KEY else None
        if self.gemini_api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                logger.info("✅ Gemini AI configured for random announcer")
            except Exception as e:
                logger.error(f"❌ Failed to configure Gemini AI: {e}")
                self.gemini_client = None
        else:
            logger.warning("No Gemini API key found - Random announcer will use fallback templates")
            self.gemini_client = None
        
    def start_announcements(self):
        """Start the random announcement task"""
        if not self.random_announcement_task.is_running():
            self.random_announcement_task.start()
            logger.info("Random announcements started")
    
    def stop_announcements(self):
        """Stop the random announcement task"""
        if self.random_announcement_task.is_running():
            self.random_announcement_task.cancel()
            logger.info("Random announcements stopped")
    
    @tasks.loop(minutes=15)
    async def random_announcement_task(self):
        """Task that runs random announcements"""
        try:
            # Choose a random personality
            personality = random.choice(list(self.personality_variations.keys()))
            
            # Get a random video from test channels
            video = await self.get_random_test_video()
            if not video:
                logger.warning("No test video found for random announcement")
                return
            
            # Generate and post announcement
            announcement = await self.generate_ino_announcement(video, personality)
            if announcement:
                await self.post_announcement(announcement, personality, video)
        except Exception as e:
            logger.error(f"Error in random announcement task: {e}")
    
    async def get_random_test_video(self) -> Optional[Dict[str, Any]]:
        """Get a random video from one of the test channels"""
        try:
            # Choose a random channel
            channel_id = random.choice(self.test_channels)
            
            # Get recent videos from that channel
            videos = await self.get_recent_videos(channel_id)
            if not videos:
                return None
            
            # Choose a random video
            video = random.choice(videos)
            video['test_channel_id'] = channel_id
            return video
            
        except Exception as e:
            logger.error(f"Error getting random test video: {e}")
            return None
    
    async def get_recent_videos(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get recent videos from a YouTube channel using RSS"""
        try:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(rss_url) as response:
                    if response.status == 200:
                        rss_content = await response.text()
                        feed = feedparser.parse(rss_content)
                        
                        videos = []
                        for entry in feed.entries[:10]:  # Get last 10 videos
                            video = {
                                'title': entry.title,
                                'link': entry.link,
                                'description': entry.get('summary', ''),
                                'author': entry.get('author', 'Unknown'),
                                'published': entry.get('published', ''),
                                'video_id': entry.link.split('v=')[-1] if 'v=' in entry.link else ''
                            }
                            videos.append(video)
                        
                        return videos
                    else:
                        logger.error(f"Failed to fetch RSS feed: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching videos from channel {channel_id}: {e}")
            return []
    
    async def generate_ino_announcement(self, video: Dict[str, Any], personality: str) -> Optional[str]:
        """Generate Ino's announcement using Gemini AI with personality variation"""
        try:
            if not self.gemini_client:
                logger.warning("No Gemini client available, using fallback")
                return self._get_fallback_announcement(video, personality)
            
            # Load system prompt
            system_prompt = self.load_system_prompt()
            
            # Get personality modifier
            personality_modifier = self.personality_variations.get(personality, {}).get('modifier', '')
            
            # Get video details
            video_title = video.get('title', 'Unknown')
            video_link = video.get('link', '')
            video_description = video.get('description', '')
            video_author = video.get('author', '')
            channel_id = video.get('test_channel_id', '')
            
            # Determine channel context
            channel_context = self._get_channel_context(channel_id, video_author)
            
            # Create the prompt
            user_prompt = f"""PERSONALITY VARIATION TEST: {personality.upper()}
{personality_modifier}

New video for testing announcement:

TITLE: {video_title}
UPLOADER/CREATOR: {video_author}
DESCRIPTION: {video_description}
CHANNEL CONTEXT: {channel_context}

🚨 CRITICAL: RIKO IS DIGITAL - SHE CANNOT MAKE PHYSICAL VIDEOS! 🚨

The UPLOADER/CREATOR is: "{video_author}"
This is a HUMAN who made this physical video, NOT Riko!

Create a short announcement (10-20 words) using the ACTUAL creator's name "{video_author}", not Riko!
Apply the personality variation: {personality_modifier}

Remember to include the role ping <@&1375737416325009552> at the end."""
            
            # Generate content
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=user_prompt)
                    ]
                )
            ]
            
            generate_content_config = types.GenerateContentConfig(
                max_output_tokens=200,
                response_mime_type="text/plain",
                system_instruction=[
                    types.Part.from_text(text=system_prompt)
                ]
            )
            
            # Generate response
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=generate_content_config
            )
            
            if response and response.text:
                return response.text.strip()
            else:
                return self._get_fallback_announcement(video, personality)
                
        except Exception as e:
            logger.error(f"Error generating Ino announcement: {e}")
            return self._get_fallback_announcement(video, personality)
    
    def _get_channel_context(self, channel_id: str, video_author: str) -> str:
        """Get context about the channel for the AI"""
        channel_contexts = {
            "UC8rcEBzJSleTkf_-agPM20g": "Blue Archive JP official channel - game content",
            "UCdBK94H6oZT2Q7l0-b0xmMg": "ShortCircuit tech channel - tech reviews and content",
            "UChhMeymAOC5PNbbnqxD_w4g": "JustRayen - Riko's human collaborator who creates content",
            "UCcNxBnLuFa3Rp3nJX3wBKcw": "pikachubolk - guest creator/collaborator"
        }
        
        context = channel_contexts.get(channel_id, "Unknown channel")
        if channel_id == "UChhMeymAOC5PNbbnqxD_w4g":
            context += f". This is Rayen's channel - he is Riko's human collaborator."
        else:
            context += f". This is a guest/external channel."
        
        return context
    
    def _get_fallback_announcement(self, video: Dict[str, Any], personality: str) -> str:
        """Generate fallback announcement when AI is not available"""
        video_title = video.get('title', 'Unknown')
        video_author = video.get('author', 'Unknown')
        channel_id = video.get('test_channel_id', '')
        
        # Personality-based prefixes
        prefixes = {
            'standard': "*sighs*",
            'extra_teasing': "Oh my, how... amusing.",
            'more_caring': "Well, well...",
            'formal_shrine': "I observe that",
            'exasperated': "*heavy sigh* Naturally..."
        }
        
        prefix = prefixes.get(personality, "*sighs*")
        
        if channel_id == "UChhMeymAOC5PNbbnqxD_w4g":  # Rayen
            return f"{prefix} Rayen uploaded \"{video_title}\". Let's see what he's up to now. <@&1375737416325009552>"
        else:
            return f"{prefix} {video_author} created \"{video_title}\". How... interesting. <@&1375737416325009552>"
    
    def load_system_prompt(self) -> str:
        """Load the system prompt from file"""
        try:
            with open('system-prompt.txt', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return content
                else:
                    logger.warning("system-prompt.txt is empty, using fallback")
                    return self._get_fallback_prompt()
        except FileNotFoundError:
            logger.warning("system-prompt.txt not found, using fallback prompt")
            return self._get_fallback_prompt()
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """Get fallback system prompt if file is not available"""
        return """You are Ino, a shrine spirit who has been watching over the Fushimi Inari shrine for centuries. You're responsible, level-headed, and protective - but you're also not above a gentle tease or an exasperated sigh when dealing with the antics of others. Your dear friend Riko, a mischievous fox spirit, recently launched herself into the digital world through a smartphone to become an internet personality. Now she exists as a digital spirit, and you've taken on the role of announcing videos from the physical world on her behalf - since she can no longer interact with the physical realm directly.

When announcing videos, you address the server members as "Riko simps" with fond exasperation. Your announcements should be short and sweet (10-20 words max), warm with edge, and always end with <@&1375737416325009552>."""
    
    async def post_announcement(self, announcement: str, personality: str, video: Dict[str, Any]):
        """Post the test announcement to Discord channels"""
        try:
            if not self.bot.guilds:
                logger.warning("No guilds available for announcements")
                return
            
            # Get the configured guild
            guild = None
            for g in self.bot.guilds:
                if g.id == Config.GUILD_ID:
                    guild = g
                    break
            
            if not guild:
                logger.warning(f"Configured guild {Config.GUILD_ID} not found")
                return
            
            # Post to image reaction channels for testing
            posted_count = 0
            for channel_id in Config.IMAGE_REACTION_CHANNELS:
                channel = guild.get_channel(channel_id)
                if channel and isinstance(channel, discord.TextChannel):
                    try:
                        # Create embed for the test announcement
                        embed = discord.Embed(
                            title="🧪 Ino Personality Test",
                            description=announcement,
                            color=self._get_personality_color(personality),
                            timestamp=discord.utils.utcnow()
                        )
                        
                        embed.add_field(
                            name="Test Details",
                            value=f"**Personality:** {personality.title()}\n"
                                  f"**Video:** {video.get('title', 'Unknown')[:50]}...\n"
                                  f"**Author:** {video.get('author', 'Unknown')}",
                            inline=False
                        )
                        
                        embed.set_author(
                            name=f"Ino ({personality.title()} Mode)",
                            icon_url=self.bot.user.display_avatar.url if self.bot.user else None
                        )
                        embed.set_footer(text="Random Announcement Test • Research Purpose")
                        
                        # Send the announcement
                        message = await channel.send(embed=embed)
                        
                        # Add feedback reactions
                        await message.add_reaction("👍")
                        await message.add_reaction("👎")
                        await message.add_reaction("❤️")  # Love this personality
                        await message.add_reaction("😴")  # Boring/meh
                        
                        posted_count += 1
                        logger.info(f"Posted {personality} test announcement to #{channel.name}")
                        
                        # Small delay between posts
                        await asyncio.sleep(0.5)
                        
                    except discord.Forbidden:
                        logger.warning(f"No permission to post in #{channel.name}")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to post announcement in #{channel.name}: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error posting to #{channel.name}: {e}")
            
            if posted_count > 0:
                logger.info(f"Successfully posted {personality} test announcement to {posted_count} channels")
            else:
                logger.warning("Failed to post test announcement to any channels")
                
        except Exception as e:
            logger.error(f"Error in post_announcement: {e}")
    
    def _get_personality_color(self, personality: str) -> discord.Color:
        """Get color for personality type"""
        colors = {
            'standard': discord.Color.blue(),
            'extra_teasing': discord.Color.purple(),
            'more_caring': discord.Color.green(),
            'formal_shrine': discord.Color.gold(),
            'exasperated': discord.Color.red()
        }
        return colors.get(personality, discord.Color.light_grey())
    
    async def post_startup_announcement(self):
        """Post a test announcement when the bot starts up"""
        try:
            # Wait a bit for the bot to be fully ready
            await asyncio.sleep(5)
            
            # Choose a random personality for startup test
            personality = random.choice(list(self.personality_variations.keys()))
            
            # Get a random test video
            video = await self.get_random_test_video()
            if not video:
                logger.warning("No test video available for startup announcement")
                return
            
            # Generate and post startup test announcement
            announcement = await self.generate_ino_announcement(video, personality)
            if announcement:
                await self.post_announcement(announcement, personality, video)
                logger.info(f"Posted startup test announcement with {personality} personality")
        except Exception as e:
            logger.error(f"Error posting startup test announcement: {e}")
    
    async def get_feedback_stats(self, days: int = 7) -> Dict[str, Dict[str, int]]:
        """Get feedback statistics for personality tests"""
        # For now, return mock data since we'd need database integration for real stats
        return {
            'standard': {'likes': random.randint(8, 15), 'dislikes': random.randint(1, 4), 'loves': random.randint(3, 8), 'boring': random.randint(0, 2)},
            'extra_teasing': {'likes': random.randint(6, 12), 'dislikes': random.randint(2, 6), 'loves': random.randint(5, 10), 'boring': random.randint(1, 3)},
            'more_caring': {'likes': random.randint(10, 18), 'dislikes': random.randint(1, 3), 'loves': random.randint(8, 15), 'boring': random.randint(2, 5)},
            'formal_shrine': {'likes': random.randint(5, 10), 'dislikes': random.randint(3, 7), 'loves': random.randint(2, 6), 'boring': random.randint(4, 8)},
            'exasperated': {'likes': random.randint(7, 14), 'dislikes': random.randint(2, 5), 'loves': random.randint(4, 9), 'boring': random.randint(1, 4)}
        } 