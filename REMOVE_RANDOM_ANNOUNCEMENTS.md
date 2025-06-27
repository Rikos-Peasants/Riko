# How to Remove Random Announcements (TEMPORARY RESEARCH FEATURE)

This document explains how to completely remove the random announcement system that was added for research purposes.

## Quick Removal (5 minutes)

### Step 1: Stop the System
Run these Discord commands:
```
/stop_announcements
```

### Step 2: Remove Files
Delete these files:
- `models/random_announcer.py`
- `REMOVE_RANDOM_ANNOUNCEMENTS.md` (this file)

### Step 3: Clean Up Bot Code
Remove these sections from `bot.py`:

**Remove from `__init__` method (around line 55-62):**
```python
# Initialize Random Announcer (TEMPORARY FOR RESEARCH)
try:
    from models.random_announcer import RandomAnnouncer
    self.random_announcer = RandomAnnouncer(self, self.leaderboard_manager)
    logger.info("✅ Random announcer initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize random announcer: {e}")
    self.random_announcer = None
```

**Remove from `on_ready` method (around line 165-169):**
```python
# Start random announcements (TEMPORARY FOR RESEARCH)
if self.random_announcer:
    self.random_announcer.start_announcements()
    logger.info("Started random announcement system - TEMPORARY FOR RESEARCH")
    logger.info("Random announcements will be posted every 15 minutes with feedback buttons")
```

**Remove from `close` method (around line 219-222):**
```python
# Stop random announcements (TEMPORARY FOR RESEARCH)
if hasattr(self, 'random_announcer') and self.random_announcer:
    self.random_announcer.stop_announcements()
    logger.info("Stopped random announcement system")
```

### Step 4: Clean Up Commands
Remove these sections from `controllers/commands.py`:

**Remove all the research commands (around line 1985-2060):**
```python
# TEMPORARY RESEARCH COMMANDS FOR RANDOM ANNOUNCEMENTS
@self.bot.hybrid_command(name='start_announcements', description='Start random announcements (RESEARCH)')
# ... (all the announcement commands)
```

### Step 5: Clean Up Database (Optional)
If you want to remove the research data:
```javascript
// MongoDB cleanup
db.random_announcements.drop()
db.random_announcement_feedback.drop()
```

## What This System Did

- Posted random announcements every 15 minutes
- Used 5 different AI personalities (tame, vulgar, bad, sarcastic, wholesome)
- Included feedback buttons (👍/👎) for research
- Stored feedback data in MongoDB for analysis
- Used Gemini AI to generate varied responses
- Could create short URLs with short.io tracking

## Research Data Location

The research data was stored in these MongoDB collections:
- `random_announcements` - Announcement data and metadata
- `random_announcement_feedback` - User feedback (likes/dislikes)

## Commands That Will Be Removed

- `/start_announcements` - Start the system
- `/stop_announcements` - Stop the system  
- `/test_announcement [personality]` - Test specific personalities
- `/announcement_stats [days]` - View feedback statistics

---

**Note:** This was a temporary research feature to test user preferences for different AI personality variations. All components are designed for easy removal without affecting the main bot functionality. 