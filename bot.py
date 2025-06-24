import discord
from discord.ext import commands, tasks
import asyncio
import logging
import random
from config import Config
from controllers.commands import CommandsController
from controllers.events import EventsController
from controllers.scheduler import SchedulerController
from models.mongo_leaderboard_manager import MongoLeaderboardManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RikoBot(commands.Bot):
    """Main Discord bot class"""
    
    def __init__(self):
        # Define intents
        intents = discord.Intents.default()
        intents.members = True  # Required for member update events
        intents.message_content = True  # Required for text commands to work properly
        
        super().__init__(
            command_prefix='R!',  # Text command prefix
            intents=intents,
            case_insensitive=True
        )
        
        # Initialize leaderboard manager based on available database
        logger.info("🔗 Connecting to database...")
        try:
            # Try to initialize MongoDB leaderboard manager
            self.leaderboard_manager = MongoLeaderboardManager()
            logger.info("✅ MongoDB leaderboard manager initialized successfully")
        except Exception as mongo_error:
            logger.error(f"❌ Failed to initialize MongoDB manager: {mongo_error}")
            logger.info("📄 Falling back to JSON leaderboard manager")
            from models.leaderboard_manager import LeaderboardManager
            self.leaderboard_manager = LeaderboardManager()
            logger.info("✅ JSON leaderboard manager initialized successfully")
        
        # Initialize controllers
        self.commands_controller = CommandsController(self)
        self.events_controller = EventsController(self)
        self.scheduler_controller = SchedulerController(self)
        
        # Initialize YouTube monitor
        try:
            from models.youtube_monitor import YouTubeMonitor
            self.youtube_monitor = YouTubeMonitor(self.leaderboard_manager)
            self.youtube_monitor.bot = self  # Pass bot reference
            logger.info("✅ YouTube monitor initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize YouTube monitor: {e}")
            self.youtube_monitor = None
        
        # Funny status messages
        self.status_messages = [
            ("watching", "over {users} Riko Simps"),
            ("listening", "to Rayen's New Proposals"),
            ("watching", "Angel be mad at Taishi"),
            ("listening", "to random people yap in DMs"),
            ("watching", "new messages & ideas pile up"),
            ("playing", "with role permissions"),
            ("watching", "for troublemakers"),
            ("listening", "to the sound of silence"),
            ("watching", "paint dry (more fun than modding)"),
            ("playing", "hide and seek with bugs"),
            ("listening", "to the screams of banned users"),
            ("watching", "chaos unfold in general chat"),
            ("playing", "therapist for drama queens"),
            ("watching", "people argue about pineapple on pizza"),
            ("listening", "to excuses from rule breakers"),
            ("watching", "memes get overused"),
            ("playing", "whack-a-mole with spammers"),
            ("watching", "people simp for anime characters"),
            ("listening", "to theories about everything"),
            ("watching", "the admin's sanity deteriorate")
        ]
    
    async def setup_hook(self):
        """Setup hook called when bot is starting"""
        logger.info("Setting up bot...")
        
        # Register commands and events FIRST
        logger.info("Registering commands...")
        self.commands_controller.register_commands()
        logger.info("Registering events...")
        self.events_controller.register_events()
        
        # Debug: List all registered text commands
        logger.info(f"Text commands registered: {len(self.commands)}")
        for cmd in self.commands:
            logger.info(f"  - Text command: R!{cmd.name}")
        
        # Wait for registration to complete
        await asyncio.sleep(0.5)
        
        # Show registered commands for debugging
        logger.info(f"Registered {len(self.tree.get_commands())} app commands globally")
        logger.info(f"Registered {len(self.tree.get_commands(guild=discord.Object(id=Config.GUILD_ID)))} app commands for guild")
        
        # Debug: List all app commands
        for cmd in self.tree.get_commands():
            logger.info(f"  - App command: /{cmd.name} - {cmd.description}")
        
        # Sync commands to enable slash command functionality
        logger.info("Syncing hybrid commands...")
        try:
            # First try guild-specific sync for faster updates
            guild = discord.Object(id=Config.GUILD_ID)
            try:
                synced_guild = await self.tree.sync(guild=guild)
                logger.info(f"Successfully synced {len(synced_guild)} commands to guild {Config.GUILD_ID}")
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    logger.warning(f"Rate limited syncing to guild, skipping: {e}")
                else:
                    logger.error(f"Failed to sync commands to guild: {e}")
            
            # Also sync globally for other servers (with rate limit handling)
            try:
                synced_global = await self.tree.sync()
                logger.info(f"Successfully synced {len(synced_global)} commands globally")
                
                # List the synced commands
                for cmd in synced_global:
                    logger.info(f"  - Global command: /{cmd.name} - {cmd.description}")
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    logger.warning(f"Rate limited syncing globally, commands may not update immediately: {e}")
                else:
                    logger.error(f"Failed to sync commands globally: {e}")
                    
        except Exception as e:
            logger.error(f"Unexpected error during command sync: {e}")
            logger.error("This might be due to missing 'applications.commands' scope")
            logger.error("Please reinvite the bot with proper permissions")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has logged in!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        logger.info(f'Text command prefix: R!')
        logger.info(f'Commands available as both text (R!command) and slash (/command)')
        
        # Generate proper invite URL
        bot_id = self.user.id if self.user else "YOUR_BOT_ID"
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot_id}&permissions=268437568&scope=bot%20applications.commands"
        logger.info(f"Bot invite URL (with applications.commands): {invite_url}")
        
        # Start the status cycling task
        if not self.cycle_status.is_running():
            self.cycle_status.start()
        
        # Initialize quest manager in events controller
        self.events_controller.initialize_quest_manager()
        logger.info("Quest manager initialized")
        
        # Start scheduler tasks for best image posting
        self.scheduler_controller.start_tasks()
        logger.info("Started scheduled tasks for best image posting")
        logger.info("Best images will be posted back to their original channels")
    
    @tasks.loop(minutes=2)  # Change status every 2 minutes
    async def cycle_status(self):
        """Cycle through different funny status messages"""
        try:
            # Get the guild to count members
            guild = self.get_guild(Config.GUILD_ID)
            member_count = guild.member_count if guild else "unknown"
            
            # Pick a random status
            activity_type, message = random.choice(self.status_messages)
            
            # Format the message with member count if needed
            formatted_message = message.format(users=member_count)
            
            # Set the appropriate activity type
            if activity_type == "watching":
                activity = discord.Activity(type=discord.ActivityType.watching, name=formatted_message)
            elif activity_type == "listening":
                activity = discord.Activity(type=discord.ActivityType.listening, name=formatted_message)
            elif activity_type == "playing":
                activity = discord.Activity(type=discord.ActivityType.playing, name=formatted_message)
            else:
                activity = discord.Activity(type=discord.ActivityType.watching, name=formatted_message)
            
            await self.change_presence(activity=activity, status=discord.Status.online)
            logger.info(f"Status changed to: {activity_type.title()} {formatted_message}")
            
        except Exception as e:
            logger.error(f"Error changing status: {e}")
    
    @cycle_status.before_loop
    async def before_cycle_status(self):
        """Wait until the bot is ready before starting status cycling"""
        await self.wait_until_ready()

    async def close(self):
        """Called when bot is shutting down"""
        logger.info("Shutting down bot...")
        
        # Stop scheduler tasks
        self.scheduler_controller.stop_tasks()
        
        # Close MongoDB connection
        if hasattr(self, 'leaderboard_manager'):
            self.leaderboard_manager.close()
            logger.info("MongoDB connection closed")
        
        # Call parent close
        await super().close()

async def main():
    """Main function to run the bot"""
    try:
        # Validate configuration
        Config.validate()
        
        # Create and run bot
        bot = RikoBot()
        await bot.start(Config.TOKEN)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except discord.LoginFailure:
        logger.error("Invalid bot token")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 