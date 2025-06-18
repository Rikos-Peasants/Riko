# Quest System, Achievements, Events, and Streaks - Feature Documentation

## Overview

The Riko bot now includes a comprehensive quest system with daily quests, achievements, timed events, and streak tracking. This system gamifies the image sharing experience by rewarding users for posting images, earning likes, rating content, and maintaining consistency.

## Features

### 1. Daily Quests

Users can receive 3-5 randomly generated daily quests each day. Quest types include:

- **Post Images**: Post a certain number of images (1 or 3)
- **Earn Likes**: Receive likes (👍) on your images (5 or 10)  
- **Rate Images**: Rate other users' images with reactions (5 or 10)

#### Quest Commands

- **`/quests` or `R!quests`**: View your current daily quests
  - Shows progress for each quest
  - Displays reward points and completion status
  - Automatically generates new quests if none exist for the day

#### Quest Rewards

Each quest provides points based on difficulty:
- Post 1 image: 10 points
- Post 3 images: 25 points
- Earn 5 likes: 15 points
- Earn 10 likes: 30 points
- Rate 5 images: 10 points
- Rate 10 images: 20 points

### 2. Achievements

Persistent achievements that can be earned over time:

#### Competition Achievements
- **🥇 Weekly Champion**: Win image of the week (100 points)
- **👑 Monthly Master**: Win image of the month (250 points)
- **🏆 Yearly Legend**: Win image of the year (500 points)

#### Posting Achievements
- **📸 Dedicated Poster**: Post 50 images (75 points)
- **🎨 Image Enthusiast**: Post 150 images (200 points)
- **🌟 Content Creator**: Post 500 images (500 points)

#### Rating Achievements
- **🎭 Art Critic**: Rate 150 images (100 points)
- **🏛️ Master Curator**: Rate 500 images (250 points)

#### Score Achievements
- **⭐ Rising Star**: Reach 100 total score (50 points)
- **💫 Community Favorite**: Reach 500 total score (150 points)
- **🌠 Hall of Fame**: Reach 1000 total score (300 points)

#### Streak Achievements
- **🔥 Week Warrior**: Complete quests for 7 days in a row (100 points)
- **🌟 Monthly Dedication**: Complete quests for 30 days in a row (300 points)
- **👑 Streak Master**: Complete quests for 100 days in a row (1000 points)
- **📷 Daily Poster**: Post at least 1 image for 7 days in a row (75 points)
- **🎬 Content Machine**: Post at least 1 image for 30 days in a row (250 points)

#### Achievement Commands

- **`/achievements` or `R!achievements`**: View your earned achievements
  - Shows up to 10 most recent achievements
  - Displays total achievement count and points
  - Can view other users' achievements by mentioning them

### 3. Streak System 🔥

Track your consistency with two types of streaks:

#### Streak Types
- **📷 Posting Streak**: Days in a row with at least 1 image posted
- **🎯 Quest Streak**: Days in a row with at least 1 quest completed

#### Streak Features
- ✅ **Automatic Tracking**: Streaks update automatically when you post images or complete quests
- ✅ **Personal Bests**: Track your longest streaks ever achieved
- ✅ **Daily Reset**: Streaks reset at midnight if you miss a day
- ✅ **Achievement Integration**: Long streaks unlock special achievements
- ✅ **Visual Feedback**: Streak embeds show your progress and milestones

#### Streak Commands

- **`/streaks` or `R!streaks`**: View your streak statistics
  - Shows current posting and quest streaks
  - Displays your personal best records
  - Provides tips for maintaining streaks
  - Can view other users' streaks by mentioning them

### 4. Events System

Bot owners can create timed image contest events where users compete for the highest-scoring image.

#### Event Commands (Bot Owner Only)

- **`/createevent` or `R!createevent`**: Create a new image contest
  - Parameters: `name`, `description`, `duration_hours` (1-168 hours)
  - Example: `/createevent "Winter Art Contest" "Best winter-themed images!" 48`

- **`/endevent` or `R!endevent`**: Manually end an active event
  - Parameter: `event_name`
  - Determines winner based on highest scoring image
  - Example: `/endevent "Winter Art Contest"`

#### Event Commands (All Users)

- **`/events` or `R!events`**: View active image contests
  - Shows all currently running events
  - Displays contestant count and time remaining

#### How Events Work

1. Bot owners create events with a name, description, and duration
2. Users automatically become contestants when they post images during the event period
3. The event tracks all images posted in image channels during the timeframe
4. When the event ends (automatically or manually), the winner is determined by the highest net score (👍 - 👎)
5. Winner announcement is posted in image channels
6. Events automatically end when they expire (checked hourly)

### 5. Automatic Progress Tracking

The system automatically tracks user progress:

#### When Posting Images
- ✅ Updates "post images" quest progress
- ✅ Updates posting streak (consecutive days with posts)
- ✅ Adds user to active events as contestant
- ✅ Checks for new achievements (including streak achievements)
- ✅ Sends DM notifications for completed quests/achievements

#### When Reacting to Images
- ✅ Updates "rate images" quest progress for the person reacting
- ✅ Updates "earn likes" quest progress for the image author (when receiving 👍)
- ✅ Tracks rating statistics for achievements

#### When Completing Quests
- ✅ Updates quest completion streak (consecutive days with completed quests)
- ✅ Checks for streak achievements
- ✅ Sends streak milestone notifications

#### When Winning Competitions
- ✅ Awards competition achievements (Weekly Champion, Monthly Master, etc.)
- ✅ Sends achievement notifications via DM

### 6. Notifications

Users receive private messages when:
- 🎉 A daily quest is completed
- 🏆 A new achievement is earned
- 🔥 A streak milestone is reached (7, 30, 100+ days)
- 🎯 They win a competition (week/month/year)

All notifications are sent via DM and fail gracefully if the user has DMs disabled.

## Database Schema

The quest system uses MongoDB with the following collections:

### Collections
- `quests`: Template quest definitions
- `achievements`: Template achievement definitions  
- `events`: Active and completed events
- `user_quests`: Individual user daily quests
- `user_achievements`: User-earned achievements
- `user_quest_stats`: User statistics for achievement tracking
- `user_streaks`: User streak tracking (post streaks, quest streaks, records)

### Indexing
Proper MongoDB indexing ensures fast queries:
- User ID indexes for user-specific data
- Date indexes for time-based queries
- Compound indexes for complex queries

## Configuration

The quest system integrates with existing bot configuration:

### Image Channels
Uses `Config.IMAGE_REACTION_CHANNELS` to determine where to track image posts and reactions.

### Guild Restriction
All quest/achievement/event/streak functionality is restricted to the configured guild (`Config.GUILD_ID`).

### Permissions
- Quest/achievement/streak viewing: All users
- Event viewing: All users
- Event creation/management: Bot owners only (`@commands.is_owner()`)

## Error Handling

The system includes comprehensive error handling:
- Database connection failures are logged and handled gracefully
- DM failures (blocked users) are handled silently
- Invalid event operations return user-friendly error messages
- Streak calculations handle edge cases (timezone changes, etc.)
- All errors are logged for debugging

## Performance Considerations

- Quest progress is batched and updated efficiently
- Achievement checking is done only when relevant (after posting images)
- Event contestant tracking avoids duplicates
- Streak updates are optimized for daily operations
- Database queries use proper indexing
- Automatic cleanup of expired events and broken streaks

## Usage Examples

### Daily Workflow
1. User runs `/quests` to see their daily objectives
2. User runs `/streaks` to check their current streaks
3. User posts images → automatically progresses "post images" quests and posting streak
4. User reacts to others' images → progresses "rate images" quests
5. User receives likes → progresses "earn likes" quests
6. Completed quests send congratulatory DMs and update quest streak
7. System checks for new achievements and notifies user

### Streak Building
1. User posts first image → starts 1-day posting streak
2. User completes first quest → starts 1-day quest streak
3. Next day: User posts again → extends posting streak to 2 days
4. User completes quest → extends quest streak to 2 days
5. After 7 days → unlocks "Week Warrior" and "Daily Poster" achievements
6. Miss a day → streak resets to 0, start over

### Event Workflow
1. Bot owner creates event: `/createevent "Photo Contest" "Best photos win!" 24`
2. Event announcement is posted
3. Users post images → automatically entered as contestants
4. Event ends after 24 hours (or manually ended)
5. Winner determined by highest scoring image
6. Winner announcement posted with image showcase

### Achievement Unlocking
1. User posts their 50th image
2. System automatically detects milestone
3. "Dedicated Poster" achievement is awarded
4. User receives DM notification with achievement details
5. Achievement appears in their `/achievements` list

## Streak Strategies

### Maintaining Streaks
- **Set Daily Reminders**: Post at least one image and complete one quest daily
- **Use Multiple Quests**: Complete easier quests early to secure your quest streak
- **Plan Ahead**: Prepare content for busy days
- **Check Progress**: Use `/streaks` to monitor your current status

### Streak Recovery
- **Don't Give Up**: If you break a streak, start immediately the next day
- **Learn Patterns**: Identify when you're most likely to forget
- **Build Habits**: Make posting and questing part of your daily routine

## Future Enhancements

Potential future additions:
- Weekly/monthly leaderboards for quest completion
- Seasonal events with special themes
- Achievement badges in user profiles
- Quest point shop/rewards system
- Streak freeze items (skip a day without breaking)
- Team/guild streaks and competitions
- Streak leaderboards and hall of fame
- Notification preferences for different milestone types 