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
    
    @discord.ui.button(label='🔄 Regenerate', style=discord.ButtonStyle.primary, custom_id='regenerate')
    async def regenerate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get the RandomAnnouncer instance from the bot
            random_announcer = getattr(interaction.client, 'random_announcer', None)
            if not random_announcer:
                await interaction.followup.send("❌ Random announcer not available!", ephemeral=True)
                return
            
            # Generate new announcement with same personality and video
            new_announcement = await random_announcer.generate_ino_announcement(self.video_data, self.personality)
            if new_announcement:
                # Update the embed with new announcement
                if interaction.message and interaction.message.embeds:
                    embed = interaction.message.embeds[0]
                    embed.description = f"## {new_announcement}\n\n*Testing AI personality variations for optimal video announcements*"
                    embed.timestamp = discord.utils.utcnow()
                    
                    await interaction.edit_original_response(embed=embed, view=self)
                else:
                    await interaction.followup.send("❌ Could not update message!", ephemeral=True)
                    return
                await interaction.followup.send(f"🔄 **Regenerated {self.personality.title()} announcement!**", ephemeral=True)
            else:
                await interaction.followup.send("❌ Failed to regenerate announcement!", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error regenerating announcement: {e}")
            await interaction.followup.send("❌ Error occurred while regenerating!", ephemeral=True)
    
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
        """Generate Ino's announcement using Gemini AI with personality variation"""
        logger.info(f"🤖 Generating AI announcement for {personality} personality...")
        
        try:
            if not self.gemini_client:
                logger.warning("❌ No Gemini client available, using fallback")
                return self._get_fallback_announcement(video, personality)
            
            # Use condensed system prompt for better AI performance
            system_prompt = self._get_condensed_system_prompt()
            logger.info(f"📜 Using condensed system prompt: {len(system_prompt)} characters")
            
            # Get personality modifier
            personality_modifier = self.personality_variations.get(personality, {}).get('modifier', '')
            logger.info(f"🎭 Personality modifier: {personality_modifier[:50]}...")
            
            # Get video details
            video_title = video.get('title', 'Unknown')
            video_link = video.get('link', '')
            video_description = video.get('description', '')
            video_author = video.get('author', '')
            channel_id = video.get('test_channel_id', '')
            
            logger.info(f"📺 Video: {video_title[:50]}... by {video_author}")
            
            # Determine channel context
            channel_context = self._get_channel_context(channel_id, video_author)
            
            # Create enhanced prompt with better instructions
            user_prompt = f"""🎭 PERSONALITY TEST: {personality.upper()}
{personality_modifier if personality_modifier else 'Use standard Ino personality from system prompt.'}

📺 NEW VIDEO TO ANNOUNCE:
Title: {video_title}
Creator: {video_author}
Description: {video_description[:200]}...
Channel: {channel_context}

🚨 CRITICAL INSTRUCTIONS:
- Riko is DIGITAL and CANNOT make physical videos!
- The creator "{video_author}" is a HUMAN, NOT Riko!
- Use the ACTUAL creator's name "{video_author}"
- Keep announcement 10-20 words maximum
- Apply the personality variation above
- End with role ping <@&1375737416325009552>

EXAMPLE FORMAT:
"*sighs* {video_author} uploaded something new: "{video_title[:30]}...". Here we go again, Riko simps. <@&1375737416325009552>"

Generate announcement now:"""
            
            logger.info(f"📝 Sending prompt to Gemini AI (personality: {personality})")
            logger.debug(f"Full prompt being sent:\n{user_prompt}")
            
            # Generate content with better configuration
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_prompt)]
                )
            ]
            
            generate_content_config = types.GenerateContentConfig(
                max_output_tokens=1000,  # Much higher to handle large system prompt
                response_mime_type="text/plain",
                temperature=0.7,  # Balanced creativity
                system_instruction=[types.Part.from_text(text=system_prompt)]
            )
            
            # Generate response
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=generate_content_config
            )
            
            if response and response.text:
                ai_response = response.text.strip()
                logger.info(f"✅ AI generated response: {ai_response[:100]}...")
                return ai_response
            else:
                # Check for specific failure reasons
                if response and hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                        finish_reason = candidate.finish_reason.name if hasattr(candidate.finish_reason, 'name') else str(candidate.finish_reason)
                        if finish_reason == 'MAX_TOKENS':
                            logger.warning("⚠️ AI hit max tokens limit - response truncated")
                        elif finish_reason == 'SAFETY':
                            logger.warning("⚠️ AI response blocked by safety filters")
                        else:
                            logger.warning(f"⚠️ AI stopped with reason: {finish_reason}")
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
        """Load the system prompt from file with enhanced validation"""
        try:
            logger.info("📜 Loading system prompt from system-prompt.txt...")
            with open('system-prompt.txt', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content and len(content) > 100:  # Ensure it's not just empty or too short
                    logger.info(f"✅ System prompt loaded successfully ({len(content)} chars)")
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
                        name="🗳️ Your Feedback Matters",
                        value="👍 Good announcement\n👎 Needs improvement\n❤️ Love this personality\n😴 Too boring/generic",
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