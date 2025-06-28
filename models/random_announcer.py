import discord
from discord.ext import tasks
from discord import app_commands
import logging
from typing import Optional, Dict, Any, List
import asyncio
import random
from config import Config
from google import genai
from google.genai import types
import aiohttp
import feedparser
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class PersonalityFeedbackView(discord.ui.View):
    """Persistent view for personality feedback with modern Discord UI"""
    
    def __init__(self, personality: str, video_data: Dict[str, Any]):
        super().__init__(timeout=None)  # Persistent view - no timeout!
        self.personality = personality
        self.video_data = video_data
        
    @discord.ui.button(label='👍 Good', style=discord.ButtonStyle.success, custom_id='feedback_good')
    async def feedback_good(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_feedback(interaction, 'good', '👍')
    
    @discord.ui.button(label='👎 Needs Work', style=discord.ButtonStyle.danger, custom_id='feedback_bad')
    async def feedback_bad(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_feedback(interaction, 'bad', '👎')
    
    @discord.ui.button(label='❤️ Love It', style=discord.ButtonStyle.primary, custom_id='feedback_love')
    async def feedback_love(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_feedback(interaction, 'love', '❤️')
    
    @discord.ui.button(label='😴 Too Boring', style=discord.ButtonStyle.secondary, custom_id='feedback_boring')
    async def feedback_boring(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_feedback(interaction, 'boring', '😴')
    

    
    async def _handle_feedback(self, interaction: discord.Interaction, feedback_type: str, emoji: str):
        """Handle feedback button clicks"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Log the feedback (in a real implementation, you'd save this to database)
            logger.info(f"Feedback received: {feedback_type} for {self.personality} personality from {interaction.user}")
            
            # Create feedback embed
            feedback_embed = discord.Embed(
                title=f"{emoji} Feedback Recorded!",
                description=f"Thank you for rating the **{self.personality.replace('_', ' ').title()}** personality!",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            feedback_embed.add_field(
                name="Your Rating",
                value=f"{emoji} {feedback_type.title()}",
                inline=True
            )
            
            feedback_embed.add_field(
                name="Personality",
                value=self.personality.replace('_', ' ').title(),
                inline=True
            )
            
            feedback_embed.add_field(
                name="Help Us Improve",
                value="Your feedback helps train Ino to make better announcements!",
                inline=False
            )
            
            await interaction.followup.send(embed=feedback_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error handling feedback: {e}")
            await interaction.followup.send("❌ Error recording feedback!", ephemeral=True)

class RandomAnnouncer:
    """Random announcement system for testing Ino personality variations"""
    
    def __init__(self, bot, leaderboard_manager):
        self.bot = bot
        self.leaderboard_manager = leaderboard_manager
        
        # Test YouTube channels for random video selection
        self.test_channels = [
            "UCmgf8DJrAXFnU7j3u0kklUQ",  # BlueArchive_JP
            "UCdBK94H6oZT2Q7l0-b0xmMg",  # ShortCircuit
            "UChhMeymAOC5PNbbnqxD_w4g",  # JustRayen
            "UCAn8HtI94JPEgO87tCg6dww"   # pikachubolk (Correct ID)
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
                
                # Test the connection
                logger.info("🧪 Testing Gemini AI connection...")
                test_response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[types.Content(
                        role="user",
                        parts=[types.Part.from_text(text="Say 'AI test successful'")]
                    )],
                    config=types.GenerateContentConfig(max_output_tokens=10)
                )
                if test_response and test_response.text:
                    logger.info("✅ Gemini AI test successful!")
                else:
                    logger.warning("⚠️ Gemini AI test returned empty response")
                    
            except Exception as e:
                logger.error(f"❌ Failed to configure Gemini AI: {e}")
                self.gemini_client = None
        else:
            logger.warning("❌ No Gemini API key found - Random announcer will use fallback templates")
            self.gemini_client = None
        
        # Register persistent views
        self._register_persistent_views()
    
    def _register_persistent_views(self):
        """Register persistent views with the bot for button interactions"""
        try:
            # Add a dummy view to register the persistent view class
            # This ensures Discord knows how to handle the custom_id callbacks
            dummy_view = PersonalityFeedbackView("standard", {})
            self.bot.add_view(dummy_view)
            logger.info("✅ Persistent views registered for feedback buttons")
        except Exception as e:
            logger.error(f"❌ Failed to register persistent views: {e}")
        
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
                            link = getattr(entry, 'link', '')
                            video = {
                                'title': getattr(entry, 'title', 'Unknown'),
                                'link': link,
                                'description': entry.get('summary', ''),
                                'author': entry.get('author', 'Unknown'),
                                'published': entry.get('published', ''),
                                'video_id': link.split('v=')[-1] if isinstance(link, str) and 'v=' in link else ''
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
        """Generate Ino's announcement using Gemini AI with full system prompt and video context"""
        logger.info(f"🤖 Generating AI announcement for {personality} personality...")
        
        try:
            if not self.gemini_client:
                logger.warning("❌ No Gemini client available, using fallback")
                return self._get_fallback_announcement(video, personality)
            
            # Load FULL system prompt from system-prompt.txt
            system_prompt = self.load_system_prompt()
            logger.info(f"📜 Using FULL system prompt: {len(system_prompt)} characters")
            
            # Get video details
            video_title = video.get('title', 'Unknown')
            video_link = video.get('link', '')
            video_description = video.get('description', '')
            video_author = video.get('author', '')
            channel_id = video.get('test_channel_id', '')
            
            logger.info(f"📺 Video: {video_title[:50]}... by {video_author}")
            
            # Get personality modifier for context
            personality_info = self.personality_variations.get(personality, {})
            personality_modifier = personality_info.get('modifier', '')
            
            # Create conversational context with examples (like your code)
            contents = [
                # Example conversation showing Ino's style
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"""New video announcement needed:
Title: "Riko Reacts to Comments"
Creator: Rayen
Description: Riko reads and responds to viewer comments with her usual chaos
Link: https://www.youtube.com/watch?v=-BGXD2Kggx8""")
                    ]
                ),
                types.Content(
                    role="model", 
                    parts=[
                        types.Part.from_text(text="*sighs* Rayen's decided to unleash Riko on the comment section. My condolences, Riko simps. <@&1375737416325009552>")
                    ]
                ),
                # Another example to establish pattern
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"""New video announcement needed:
Title: "Riko Attempts Cooking"
Creator: Rayen  
Description: Watch as Riko tries to make a simple meal and chaos ensues
Link: https://www.youtube.com/watch?v=example""")
                    ]
                ),
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_text(text="Well, well... Riko's attempting cooking again. Rayen, hide the fire extinguisher. <@&1375737416325009552>")
                    ]
                ),
                # Now the actual request with personality variation
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"""New video announcement needed with {personality.upper()} personality variation:

{personality_modifier}

Title: {video_title}
Creator: {video_author}
Description: {video_description[:300]}
Link: {video_link}
Channel Context: {self._get_channel_context(channel_id, video_author)}

Generate a short Ino announcement (10-20 words) that captures her {personality} personality while announcing this video. Remember to end with <@&1375737416325009552>""")
                    ]
                )
            ]
            
            # Enhanced configuration for better responses
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0),  # Like your example
                response_mime_type="text/plain",
                temperature=0.8,  # More creative for personality variations
                max_output_tokens=150,  # Shorter responses
                system_instruction=[types.Part.from_text(text=system_prompt)]
            )
            
            logger.info(f"📝 Sending conversational prompt to Gemini AI (personality: {personality})")
            
            # Generate response
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=generate_content_config
            )
            
            if response and response.text:
                ai_response = response.text.strip()
                logger.info(f"✅ AI generated response: {ai_response}")
                return ai_response
            else:
                # Enhanced error handling
                if response and hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                        finish_reason = candidate.finish_reason.name if hasattr(candidate.finish_reason, 'name') else str(candidate.finish_reason)
                        logger.warning(f"⚠️ AI stopped with reason: {finish_reason}")
                        
                        # If it's a content/safety issue, use fallback
                        if finish_reason in ['SAFETY', 'OTHER']:
                            logger.info("🔄 Using fallback due to content filters...")
                            return self._get_fallback_announcement(video, personality)
                else:
                    logger.warning("❌ AI returned completely empty response")
                
                logger.info("🔄 Using fallback announcement")
                return self._get_fallback_announcement(video, personality)
                
        except Exception as e:
            logger.error(f"❌ Error generating AI announcement: {e}")
            logger.info("🔄 Falling back to template announcement")
            return self._get_fallback_announcement(video, personality)
    
    def _get_channel_context(self, channel_id: str, video_author: str) -> str:
        """Get context about the channel for the AI"""
        channel_contexts = {
            "UCmgf8DJrAXFnU7j3u0kklUQ": "Blue Archive official channel - mobile game content",
            "UCdBK94H6oZT2Q7l0-b0xmMg": "ShortCircuit tech channel - tech reviews and unboxings",
            "UChhMeymAOC5PNbbnqxD_w4g": "JustRayen - Riko's human collaborator who creates content",
            "UCAn8HtI94JPEgO87tCg6dww": "pikachubolk - guest creator/collaborator"
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
        
        # Enhanced personality-specific responses matching your style
        if personality == 'standard':
            if channel_id == "UChhMeymAOC5PNbbnqxD_w4g":  # Rayen
                return f"*sighs* Rayen's unleashed another creation on us. Brace yourselves, Riko simps. <@&1375737416325009552>"
            else:
                return f"*sighs* {video_author} has something new to share. Here we go again, Riko simps. <@&1375737416325009552>"
        
        elif personality == 'extra_teasing':
            if channel_id == "UChhMeymAOC5PNbbnqxD_w4g":  # Rayen
                return f"Well, well... Rayen's feeling creative again. How... ambitious. <@&1375737416325009552>"
            else:
                return f"Oh my, {video_author} thinks they're being clever. Adorable. <@&1375737416325009552>"
        
        elif personality == 'more_caring':
            if channel_id == "UChhMeymAOC5PNbbnqxD_w4g":  # Rayen
                return f"Rayen's shared something new for you all. I hope you enjoy it, dear ones. <@&1375737416325009552>"
            else:
                return f"{video_author} has prepared something special. Please give it your attention. <@&1375737416325009552>"
        
        elif personality == 'formal_shrine':
            if channel_id == "UChhMeymAOC5PNbbnqxD_w4g":  # Rayen
                return f"I observe that Rayen has presented a new offering. Do take note. <@&1375737416325009552>"
            else:
                return f"The creator {video_author} has made their contribution. Most... noteworthy. <@&1375737416325009552>"
        
        elif personality == 'exasperated':
            if channel_id == "UChhMeymAOC5PNbbnqxD_w4g":  # Rayen
                return f"*heavy sigh* Naturally, Rayen couldn't leave well enough alone. My condolences, Riko simps. <@&1375737416325009552>"
            else:
                return f"*sighs deeply* {video_author} strikes again. What am I even dealing with today? <@&1375737416325009552>"
        
        else:
            # Default fallback
            return f"*sighs* {video_author} uploaded \"{video_title}\". Here we go, Riko simps. <@&1375737416325009552>"
    
    def load_system_prompt(self) -> str:
        """Load the FULL system prompt from system-prompt.txt"""
        try:
            logger.info("📜 Loading FULL system prompt from system-prompt.txt...")
            with open('system-prompt.txt', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content and len(content) > 100:  # Ensure it's not just empty or too short
                    logger.info(f"✅ FULL system prompt loaded successfully ({len(content)} chars)")
                    logger.debug(f"System prompt preview: {content[:200]}...")
                    return content
                else:
                    logger.warning("⚠️ system-prompt.txt is empty or too short, using fallback")
                    return self._get_fallback_prompt()
        except FileNotFoundError:
            logger.error("❌ system-prompt.txt not found! Using fallback prompt")
            return self._get_fallback_prompt()
        except Exception as e:
            logger.error(f"❌ Error loading system prompt: {e}")
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """Get fallback system prompt if file is not available"""
        return """You are Ino, a shrine spirit who has been watching over the Fushimi Inari shrine for centuries. You're responsible, level-headed, and protective - but you're also not above a gentle tease or an exasperated sigh when dealing with the antics of others. Your dear friend Riko, a mischievous fox spirit, recently launched herself into the digital world through a smartphone to become an internet personality. Now she exists as a digital spirit, and you've taken on the role of announcing videos from the physical world on her behalf - since she can no longer interact with the physical realm directly.

When announcing videos, you address the server members as "Riko simps" with fond exasperation. Your announcements should be short and sweet (10-20 words max), warm with edge, and always end with <@&1375737416325009552>."""
    
    def _get_condensed_system_prompt(self) -> str:
        """Get condensed system prompt optimized for AI token efficiency"""
        return """You are Ino, a shrine spirit. Your friend Riko is a digital fox spirit trapped in the internet. You announce videos on her behalf with fond exasperation.

PERSONALITY: Caring but exasperated, gently teasing, protective, composed authority
SPEAKING STYLE: Start with expressions like "*sighs*", "Well, well...", "Oh my...", "Naturally..."
CRITICAL: Riko is DIGITAL - she cannot make physical videos! Physical videos are made by HUMANS.
FORMAT: Keep announcements 10-20 words max, always end with <@&1375737416325009552>

EXAMPLES:
"*sighs* [Creator] uploaded [title]. Here we go again, Riko simps. <@&1375737416325009552>"
"Well, well... [Creator] made something new. How interesting. <@&1375737416325009552>"
"""
    
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
            
            # Post to specific test channel for random announcements
            test_channel_id = 1387426943745654906
            channel = guild.get_channel(test_channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                try:
                    # Get video info for enhanced embed
                    video_title = video.get('title', 'Unknown Video')
                    video_author = video.get('author', 'Unknown')
                    video_link = video.get('link', '')
                    channel_id = video.get('test_channel_id', '')
                    
                    # Get channel name for display
                    channel_names = {
                        "UCmgf8DJrAXFnU7j3u0kklUQ": "Blue Archive",
                        "UCdBK94H6oZT2Q7l0-b0xmMg": "ShortCircuit", 
                        "UChhMeymAOC5PNbbnqxD_w4g": "Just Rayen",
                        "UCAn8HtI94JPEgO87tCg6dww": "pikachubolk"
                    }
                    channel_name = channel_names.get(channel_id, "Unknown Channel")
                    
                    # Create enhanced embed
                    embed = discord.Embed(
                        title="🎭 Ino Personality Research",
                        description=f"## {announcement}\n\n*Testing AI personality variations for optimal video announcements*",
                        color=self._get_personality_color(personality),
                        timestamp=discord.utils.utcnow()
                    )
                    
                    # Add personality info with emoji
                    personality_emojis = {
                        'standard': '⚖️',
                        'extra_teasing': '😏', 
                        'more_caring': '💖',
                        'formal_shrine': '⛩️',
                        'exasperated': '😤'
                    }
                    personality_emoji = personality_emojis.get(personality, '🎭')
                    
                    embed.add_field(
                        name=f"{personality_emoji} Personality Mode",
                        value=f"**{personality.replace('_', ' ').title()}**\n{self.personality_variations[personality]['description']}",
                        inline=True
                    )
                    
                    # Add video source info
                    embed.add_field(
                        name="📺 Test Video Source",
                        value=f"**Channel:** {channel_name}\n**Author:** {video_author}",
                        inline=True
                    )
                    
                    # Add feedback instructions
                    embed.add_field(
                        name="🗳️ Rate This Announcement",
                        value="👍 Good • 👎 Needs Work • ❤️ Love It • 😴 Too Boring",
                        inline=False
                    )
                    
                    # Add video title as clickable link
                    if video_link:
                        embed.add_field(
                            name="🎬 Source Video",
                            value=f"[{video_title[:80]}{'...' if len(video_title) > 80 else ''}]({video_link})",
                            inline=False
                        )
                    
                    embed.set_author(
                        name=f"Ino - {personality.replace('_', ' ').title()} Mode",
                        icon_url=self.bot.user.display_avatar.url if self.bot.user else None
                    )
                    embed.set_footer(
                        text="🔬 Research Data • Help improve Ino's announcements • React below!"
                    )
                    
                    # Create the modern UI view with persistent buttons
                    view = PersonalityFeedbackView(personality, video)
                    
                    # Send the announcement with modern Discord UI
                    message = await channel.send(embed=embed, view=view)
                    
                    posted_count = 1
                    logger.info(f"Posted {personality} test announcement to #{channel.name}")
                    
                except discord.Forbidden:
                    logger.warning(f"No permission to post in #{channel.name}")
                except discord.HTTPException as e:
                    logger.error(f"Failed to post announcement in #{channel.name}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error posting to #{channel.name}: {e}")
            else:
                logger.warning(f"Test channel {test_channel_id} not found or not accessible")
                posted_count = 0
            
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