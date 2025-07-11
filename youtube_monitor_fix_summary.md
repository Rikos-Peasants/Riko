# YouTube Monitor Initialization Fix

## Issue Summary

The YouTube monitoring functionality was not being initialized properly, causing repeated warnings in the logs:

```
YouTube monitor not available on bot instance
```

## Root Cause

The issue was in the `YouTubeMonitor` class initialization (`models/youtube_monitor.py`). The problematic code was:

```python
# Initialize monitored channels from database
asyncio.create_task(self.load_monitored_channels())
```

This line was trying to create an async task during the `__init__` method, but at initialization time there is no active event loop, causing the task creation to fail silently and the YouTube monitor to not initialize properly.

## Solution

### 1. Fixed YouTube Monitor Initialization

**File:** `models/youtube_monitor.py`

**Before:**
```python
# Initialize monitored channels from database
asyncio.create_task(self.load_monitored_channels())
```

**After:**
```python
# Note: monitored channels will be loaded later when an event loop is available
```

### 2. Ensured Channels Load During Runtime

**File:** `controllers/scheduler.py`

**Added:**
```python
# Load monitored channels (this is safe to call repeatedly)
await youtube_monitor.load_monitored_channels()
```

This ensures that monitored channels are loaded when the scheduler task runs (when there's an active event loop).

## How the Fix Works

1. **Removes the problematic async task creation** during initialization
2. **Loads monitored channels on-demand** when the scheduler checks for new videos
3. **Safe to call repeatedly** - the `load_monitored_channels()` method can be called multiple times without issues

## Expected Results

After applying this fix:

1. ✅ YouTube monitor will initialize successfully during bot startup
2. ✅ No more "YouTube monitor not available on bot instance" warnings
3. ✅ Monitored channels will be loaded when needed
4. ✅ YouTube video checking will function properly

## Environment Variables

The bot still requires these environment variables for full functionality:

- `DISCORD_TOKEN` - Required for bot operation
- `GUILD_ID` - Required for guild-specific operations  
- `MONGO_URI` - Required for database operations
- `GEMINI_API_KEY` - Optional, for AI-generated video responses
- `YOUTUBE_API_KEY` - Optional, for better YouTube API performance (will use RSS fallback if not provided)

## Testing

To verify the fix is working:

1. Start the bot
2. Check logs for YouTube monitor initialization success
3. Verify no more repeated "YouTube monitor not available" warnings
4. Monitor the scheduler logs for successful video checking

## Files Modified

1. `models/youtube_monitor.py` - Removed problematic async task creation during init
2. `controllers/scheduler.py` - Added on-demand channel loading during video checks