# Riko Discord Bot

A professional Discord bot built with discord.py using MVC architecture that prevents users with a specific banned role from accessing restricted roles. Features image voting leaderboards with MongoDB storage.

## Features

- **Role Management**: Automatically prevents users with banned role from getting restricted role
- **NSFWBAN System**: Ban users from NSFW content with persistent role reapplication on rejoin
- **Image Voting System**: Automatic 👍👎 reactions on images with real-time leaderboard tracking
- **MongoDB Integration**: Cloud-based data storage with real-time updates and backups
- **Best Image Posts**: Weekly, monthly, and yearly best image announcements
- **Leaderboard Commands**: View top users by image upvotes and personal statistics
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

2. **Configure Environment**
   - Update the `.env` file with your configuration:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   GUILD_ID=your_guild_id
   BANNED_ROLE_ID=your_banned_role_id
   RESTRICTED_ROLE_ID=your_restricted_role_id
   MONGO_URI=your_mongodb_connection_string
   ```

3. **Start the Bot**
   ```bash
   ./docker-start.sh
   ```

4. **Manage the Bot**
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
   - Update the `.env` file with your bot token, role IDs, and MongoDB URI
   - Make sure your bot has the following permissions:
     - Read Messages
     - Send Messages
     - Add Reactions
     - Manage Roles
     - Use Slash Commands
     - Read Message History

3. **Run the Bot**
   ```bash
   python bot.py
   ```

## MongoDB Setup

The bot uses MongoDB for storing leaderboard data. Configure your MongoDB connection in the `.env` file:

```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/database
```

### Migrating from JSON (if upgrading)

If you have existing JSON data, use the migration script:

```bash
python migrate_to_mongo.py
```

## Commands

All commands support both text and slash formats:

| Command | Text Format | Slash Format | Description | Access |
|---------|------------|--------------|-------------|--------|
| Uptime | `R!uptime` | `/uptime` | Shows bot uptime | Everyone |
| Leaderboard | `R!leaderboard` | `/leaderboard` | Shows image voting leaderboard | Everyone |
| Stats | `R!stats [@user]` | `/stats [user]` | Shows user's image statistics | Everyone |
| NSFWBAN | `R!nsfwban @user [reason]` | `/nsfwban user [reason]` | Ban user from NSFW content | Admins/Moderator Role/Owners |
| NSFWUNBAN | `R!nsfwunban @user` | `/nsfwunban user` | Remove NSFW ban from user | Admins/Moderator Role/Owners |
| Process Old | `R!processold` | `/processold` | Process historical images (past year) | Owners Only |
| Best Week | `R!bestweek` | `/bestweek` | Manually post best image of week | Owners Only |
| Best Month | `R!bestmonth` | `/bestmonth` | Manually post best image of month | Owners Only |
| Best Year | `R!bestyear` | `/bestyear` | Manually post best image of year | Owners Only |
| DB Status | `R!dbstatus` | `/dbstatus` | Check MongoDB connection status | Owners Only |
| Test Owner | `R!testowner` | `/testowner` | Test bot owner permissions | Owners Only |

## NSFWBAN System

- **Persistent Bans**: Users banned from NSFW content with role-based restrictions
- **Automatic Reapplication**: NSFWBAN role is automatically reapplied when users rejoin the server
- **Permission-Based Access**: Only users with the moderator role (ID: 1372477845997359244), administrators, or bot owners can use ban commands
- **Database Tracking**: All bans are stored in MongoDB with reason, timestamp, and moderator information
- **DM Notifications**: Users receive DM notifications when banned/unbanned with detailed information
- **Audit Trail**: Complete logging of all NSFWBAN actions for moderation transparency

## Image Voting System

- **Automatic Reactions**: Bot adds 👍👎 to all images in configured channels
- **Real-time Tracking**: Votes are tracked instantly in MongoDB
- **Net Scoring**: Score = 👍 votes - 👎 votes
- **Leaderboard**: Users ranked by total net score across all images
- **Best Image Posts**: Automatic weekly (Sunday), monthly (1st), yearly (Jan 1st) posts

## Project Structure

```
├── bot.py                          # Main bot file
├── config.py                       # Configuration management  
├── requirements.txt                # Dependencies
├── .env                           # Environment variables (includes MongoDB URI)
├── migrate_to_mongo.py            # JSON to MongoDB migration script
├── models/                        # Data models
│   ├── __init__.py
│   ├── mongo_leaderboard_manager.py  # MongoDB operations
│   └── role_manager.py            # Role management logic
├── views/                         # UI components
│   ├── __init__.py
│   └── embeds.py                  # Discord embeds
└── controllers/                   # Business logic
    ├── __init__.py
    ├── commands.py                # Hybrid commands
    ├── events.py                  # Discord events (includes image tracking)
    └── scheduler.py               # Scheduled tasks for best image posts
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
