import discord
from discord.ext import commands, tasks
import asyncio
import logging
import random
from config import Config
from controllers.commands import CommandsController
from controllers.events import EventsController

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
        
        # Initialize controllers
        self.commands_controller = CommandsController(self)
        self.events_controller = EventsController(self)
        
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
        
        # Register commands and events
        self.commands_controller.register_commands()
        self.events_controller.register_events()
        
        # Sync commands to enable slash command functionality
        logger.info("Syncing hybrid commands...")
        try:
            # Sync to specific guild first
            guild = discord.Object(id=Config.GUILD_ID)
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Successfully synced {len(synced)} commands to guild {Config.GUILD_ID}")
            
        except Exception as e:
            logger.error(f"Failed to sync commands to guild: {e}")
            # Try global sync as fallback
            try:
                logger.info("Trying global command sync as fallback...")
                synced = await self.tree.sync()
                logger.info(f"Fallback: Synced {len(synced)} commands globally")
            except Exception as global_e:
                logger.error(f"Global sync also failed: {global_e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has logged in!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        logger.info(f'Text command prefix: R!')
        logger.info(f'Commands available as both text (R!command) and slash (/command)')
        
        # Start the status cycling task
        if not self.cycle_status.is_running():
            self.cycle_status.start()
    
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