# Riko Discord Bot

A professional Discord bot built with discord.py using MVC architecture that prevents users with a specific banned role from accessing restricted roles.

## Features

- **Role Management**: Automatically prevents users with banned role from getting restricted role
- **Access Control**: Sends embed notification when access is denied
- **Hybrid Commands**: Support both text commands (`R!command`) and slash commands (`/command`)
- **Uptime Command**: Check bot uptime with `R!uptime` or `/uptime`
- **Cycling Status**: Funny status messages that cycle every 2 minutes
- **Professional Architecture**: Clean MVC structure for easy maintenance and expansion
- **Docker Support**: Easy deployment with Docker and Docker Compose

## Quick Start with Docker (Recommended)

1. **Prerequisites**
   ```bash
   # Install Docker and Docker Compose
   sudo pacman -S docker docker-compose  # Arch Linux
   # or
   sudo apt install docker.io docker-compose  # Ubuntu/Debian
   ```

2. **Start the Bot**
   ```bash
   ./docker-start.sh
   ```

3. **Manage the Bot**
   ```bash
   # View logs
   docker-compose logs -f
   
   # Stop the bot
   docker-compose down
   
   # Restart the bot
   docker-compose restart
   
   # Check status
   docker-compose ps
   ```

## Manual Setup (Alternative)

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   - The `.env` file is already configured with your bot token and role IDs
   - Make sure your bot has the following permissions:
     - Read Messages
     - Send Messages
     - Manage Roles
     - Use Slash Commands

3. **Run the Bot**
   ```bash
   python bot.py
   ```

## Project Structure

```
├── bot.py                 # Main bot file
├── config.py             # Configuration management
├── requirements.txt      # Dependencies
├── .env                 # Environment variables
├── Dockerfile            # Docker container configuration
├── docker-compose.yml    # Docker Compose setup
├── docker-start.sh       # Convenient startup script
├── models/              # Data models
│   ├── __init__.py
│   └── role_manager.py  # Role management logic
├── views/               # UI components
│   ├── __init__.py
│   └── embeds.py        # Discord embeds
└── controllers/         # Business logic
    ├── __init__.py
    ├── commands.py      # Hybrid commands
    └── events.py        # Discord events
```

## Troubleshooting

### "Unknown Integration" Error for Slash Commands

If slash commands show "Unknown integration":

1. **Check Bot Permissions**: Ensure the bot has "Use Slash Commands" permission
2. **Reinvite Bot**: Use this URL format to reinvite with proper permissions:
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot%20applications.commands
   ```
3. **Wait for Sync**: Commands may take up to 1 hour to appear globally
4. **Check Logs**: Look for "Successfully synced X commands" in the logs

### Command Registration Issues

- Commands are registered as hybrid commands (both text and slash)
- Text commands work immediately with `R!` prefix
- Slash commands require Discord sync (may take time)
- Check bot logs for sync status

## Funny Status Messages

The bot cycles through humorous status messages every 2 minutes, including:
- "Watching over {users} Riko Simps"
- "Listening to Rayen's New Proposals"
- "Watching Angel be mad at Taishi"
- "Listening to random people yap in DMs"
- "Watching new messages & ideas pile up"
- And many more hilarious statuses!

## Commands

All commands support both text and slash formats:

| Command | Text Format | Slash Format | Description |
|---------|------------|--------------|-------------|
| Uptime | `R!uptime` | `/uptime` | Shows bot uptime |

## Adding New Hybrid Commands

To add new hybrid commands, follow this pattern in `controllers/commands.py`:

1. Add your command method to the `CommandsController` class
2. Register it in the `register_commands` method using `@bot.hybrid_command()`

Example:
```python
@self.bot.hybrid_command(name="example", description="Example command")
async def example_command(ctx):
    """Example hybrid command"""
    await ctx.send("Hello! Use R!example or /example")
```

## Adding New Status Messages

To add more funny status messages, edit the `status_messages` list in `bot.py`:

```python
self.status_messages = [
    ("watching", "your custom message here"),
    ("listening", "to something funny"),
    ("playing", "with new features"),
    # Add more here...
]
```

## Configuration

The bot is configured for:
- **Guild ID**: 1278117138909102170
- **Banned Role ID**: 1378693499540471838 (users with this role cannot get restricted role)
- **Restricted Role ID**: 1378691142819909853 (role that banned users cannot access)
- **Text Command Prefix**: `R!` (e.g., `R!uptime`)
- **Slash Commands**: Available as `/command` (e.g., `/uptime`)

## Docker Benefits

- **Consistent Environment**: Same runtime across all systems
- **Easy Deployment**: One command to start the bot
- **Resource Management**: Built-in memory and CPU limits
- **Health Monitoring**: Automatic restart if bot crashes
- **Log Management**: Structured logging with rotation
