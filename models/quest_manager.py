import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.collection import Collection
from pymongo.database import Database
import random

logger = logging.getLogger(__name__)

class QuestManager:
    """Manages daily quests, achievements, events, and streaks system"""
    
    def __init__(self, connection_url: Optional[str] = None, database_name: str = "Riko"):
        # Import here to avoid circular imports
        from config import Config
        
        self.connection_url = connection_url or Config.MONGO_URI
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.quests_collection: Optional[Collection] = None
        self.achievements_collection: Optional[Collection] = None
        self.events_collection: Optional[Collection] = None
        self.user_quests_collection: Optional[Collection] = None
        self.user_achievements_collection: Optional[Collection] = None
        self.user_stats_collection: Optional[Collection] = None
        self.user_streaks_collection: Optional[Collection] = None
        self._connect()
        self._initialize_quests_and_achievements()
    
    def _connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.connection_url, serverSelectionTimeoutMS=5000)
            # Test the connection
            self.client.admin.command('ismaster')
            self.db = self.client[self.database_name]
            
            # Initialize collections
            self.quests_collection = self.db['quests']
            self.achievements_collection = self.db['achievements']
            self.events_collection = self.db['events']
            self.user_quests_collection = self.db['user_quests']
            self.user_achievements_collection = self.db['user_achievements']
            self.user_stats_collection = self.db['user_quest_stats']
            self.user_streaks_collection = self.db['user_streaks']
            
            # Create indexes
            self.quests_collection.create_index([("quest_type", 1), ("is_daily", 1)])
            self.achievements_collection.create_index([("achievement_type", 1)])
            self.events_collection.create_index([("start_date", -1), ("end_date", -1)])
            self.user_quests_collection.create_index([("user_id", 1), ("date", -1)])
            self.user_achievements_collection.create_index([("user_id", 1), ("achievement_id", 1)], unique=True)
            self.user_stats_collection.create_index([("user_id", 1)], unique=True)
            self.user_streaks_collection.create_index([("user_id", 1)], unique=True)
            
            logger.info(f"Connected to MongoDB for Quest Manager")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise Exception(f"MongoDB connection failed: {e}")
    
    def _ensure_connected(self) -> bool:
        """Ensure database connection is available"""
        return (self.db is not None and 
                self.quests_collection is not None and 
                self.achievements_collection is not None and 
                self.events_collection is not None and 
                self.user_quests_collection is not None and 
                self.user_achievements_collection is not None and 
                self.user_stats_collection is not None and 
                self.user_streaks_collection is not None)
    
    def _initialize_quests_and_achievements(self):
        """Initialize default quests and achievements if they don't exist"""
        if not self._ensure_connected():
            logger.error("Cannot initialize quests and achievements: Database not connected")
            return
        # Daily Quests
        daily_quests = [
            {
                "quest_id": "daily_post_1",
                "name": "Image Poster",
                "description": "Post 1 image",
                "quest_type": "post_images",
                "target_count": 1,
                "reward_points": 10,
                "is_daily": True
            },
            {
                "quest_id": "daily_post_3",
                "name": "Active Poster",
                "description": "Post 3 images",
                "quest_type": "post_images",
                "target_count": 3,
                "reward_points": 25,
                "is_daily": True
            },
            {
                "quest_id": "daily_like_5",
                "name": "Like Collector",
                "description": "Earn 5 likes on your images",
                "quest_type": "earn_likes",
                "target_count": 5,
                "reward_points": 15,
                "is_daily": True
            },
            {
                "quest_id": "daily_like_10",
                "name": "Popular Creator",
                "description": "Earn 10 likes on your images",
                "quest_type": "earn_likes",
                "target_count": 10,
                "reward_points": 30,
                "is_daily": True
            },
            {
                "quest_id": "daily_rate_5",
                "name": "Image Critic",
                "description": "Rate 5 images (👍 or 👎)",
                "quest_type": "rate_images",
                "target_count": 5,
                "reward_points": 10,
                "is_daily": True
            },
            {
                "quest_id": "daily_rate_10",
                "name": "Active Rater",
                "description": "Rate 10 images (👍 or 👎)",
                "quest_type": "rate_images",
                "target_count": 10,
                "reward_points": 20,
                "is_daily": True
            }
        ]
        
        # Achievements
        achievements = [
            {
                "achievement_id": "winner_week",
                "name": "Weekly Champion",
                "description": "Win image of the week",
                "achievement_type": "competition_win",
                "target_count": 1,
                "reward_points": 100,
                "icon": "🥇"
            },
            {
                "achievement_id": "winner_month",
                "name": "Monthly Master",
                "description": "Win image of the month",
                "achievement_type": "competition_win",
                "target_count": 1,
                "reward_points": 250,
                "icon": "👑"
            },
            {
                "achievement_id": "winner_year",
                "name": "Yearly Legend",
                "description": "Win image of the year",
                "achievement_type": "competition_win",
                "target_count": 1,
                "reward_points": 500,
                "icon": "🏆"
            },
            {
                "achievement_id": "post_50",
                "name": "Dedicated Poster",
                "description": "Post 50 images",
                "achievement_type": "post_images",
                "target_count": 50,
                "reward_points": 75,
                "icon": "📸"
            },
            {
                "achievement_id": "post_150",
                "name": "Image Enthusiast",
                "description": "Post 150 images",
                "achievement_type": "post_images",
                "target_count": 150,
                "reward_points": 200,
                "icon": "🎨"
            },
            {
                "achievement_id": "post_500",
                "name": "Content Creator",
                "description": "Post 500 images",
                "achievement_type": "post_images",
                "target_count": 500,
                "reward_points": 500,
                "icon": "🌟"
            },
            {
                "achievement_id": "rate_150",
                "name": "Art Critic",
                "description": "Rate 150 images",
                "achievement_type": "rate_images",
                "target_count": 150,
                "reward_points": 100,
                "icon": "🎭"
            },
            {
                "achievement_id": "rate_500",
                "name": "Master Curator",
                "description": "Rate 500 images",
                "achievement_type": "rate_images",
                "target_count": 500,
                "reward_points": 250,
                "icon": "🏛️"
            },
            {
                "achievement_id": "score_100",
                "name": "Rising Star",
                "description": "Reach 100 total score",
                "achievement_type": "total_score",
                "target_count": 100,
                "reward_points": 50,
                "icon": "⭐"
            },
            {
                "achievement_id": "score_500",
                "name": "Community Favorite",
                "description": "Reach 500 total score",
                "achievement_type": "total_score",
                "target_count": 500,
                "reward_points": 150,
                "icon": "💫"
            },
            {
                "achievement_id": "score_1000",
                "name": "Hall of Fame",
                "description": "Reach 1000 total score",
                "achievement_type": "total_score",
                "target_count": 1000,
                "reward_points": 300,
                "icon": "🌠"
            },
            # Streak Achievements
            {
                "achievement_id": "streak_7",
                "name": "Week Warrior",
                "description": "Complete quests for 7 days in a row",
                "achievement_type": "quest_streak",
                "target_count": 7,
                "reward_points": 100,
                "icon": "🔥"
            },
            {
                "achievement_id": "streak_30",
                "name": "Monthly Dedication",
                "description": "Complete quests for 30 days in a row",
                "achievement_type": "quest_streak",
                "target_count": 30,
                "reward_points": 300,
                "icon": "🌟"
            },
            {
                "achievement_id": "streak_100",
                "name": "Streak Master",
                "description": "Complete quests for 100 days in a row",
                "achievement_type": "quest_streak",
                "target_count": 100,
                "reward_points": 1000,
                "icon": "👑"
            },
            {
                "achievement_id": "post_streak_7",
                "name": "Daily Poster",
                "description": "Post at least 1 image for 7 days in a row",
                "achievement_type": "post_streak",
                "target_count": 7,
                "reward_points": 75,
                "icon": "📷"
            },
            {
                "achievement_id": "post_streak_30",
                "name": "Content Machine",
                "description": "Post at least 1 image for 30 days in a row",
                "achievement_type": "post_streak",
                "target_count": 30,
                "reward_points": 250,
                "icon": "🎬"
            }
        ]
        
        # Insert quests if they don't exist
        for quest in daily_quests:
            self.quests_collection.update_one(
                {"quest_id": quest["quest_id"]},
                {"$set": quest},
                upsert=True
            )
        
        # Insert achievements if they don't exist
        for achievement in achievements:
            self.achievements_collection.update_one(
                {"achievement_id": achievement["achievement_id"]},
                {"$set": achievement},
                upsert=True
            )
        
        logger.info("Initialized default quests and achievements")
    
    async def generate_daily_quests(self, user_id: int) -> List[Dict]:
        """Generate 3-5 random daily quests for a user"""
        try:
            today = datetime.now().date()
            
            # Check if user already has quests for today
            existing_quests = list(self.user_quests_collection.find({
                "user_id": str(user_id),
                "date": today.isoformat()
            }))
            
            if existing_quests:
                return existing_quests
            
            # Get all available daily quests
            available_quests = list(self.quests_collection.find({"is_daily": True}))
            
            # Randomly select 3-5 quests
            selected_count = random.randint(3, 5)
            selected_quests = random.sample(available_quests, min(selected_count, len(available_quests)))
            
            # Create user quest records
            user_quests = []
            for quest in selected_quests:
                user_quest = {
                    "user_id": str(user_id),
                    "quest_id": quest["quest_id"],
                    "name": quest["name"],
                    "description": quest["description"],
                    "quest_type": quest["quest_type"],
                    "target_count": quest["target_count"],
                    "current_count": 0,
                    "reward_points": quest["reward_points"],
                    "completed": False,
                    "date": today.isoformat(),
                    "created_at": datetime.now()
                }
                
                self.user_quests_collection.insert_one(user_quest)
                user_quests.append(user_quest)
            
            logger.info(f"Generated {len(user_quests)} daily quests for user {user_id}")
            return user_quests
            
        except Exception as e:
            logger.error(f"Error generating daily quests: {e}")
            return []
    
    async def update_quest_progress(self, user_id: int, quest_type: str, count: int = 1):
        """Update quest progress for a user"""
        try:
            today = datetime.now().date()
            
            # Update daily quests
            result = self.user_quests_collection.update_many(
                {
                    "user_id": str(user_id),
                    "quest_type": quest_type,
                    "date": today.isoformat(),
                    "completed": False
                },
                {"$inc": {"current_count": count}}
            )
            
            # Check for completed quests
            completed_quests = []
            quests_to_check = self.user_quests_collection.find({
                "user_id": str(user_id),
                "quest_type": quest_type,
                "date": today.isoformat(),
                "completed": False
            })
            
            for quest in quests_to_check:
                if quest["current_count"] >= quest["target_count"]:
                    # Mark quest as completed
                    self.user_quests_collection.update_one(
                        {"_id": quest["_id"]},
                        {
                            "$set": {
                                "completed": True,
                                "completed_at": datetime.now()
                            }
                        }
                    )
                    completed_quests.append(quest)
            
            # Update streak if any quest was completed
            if completed_quests:
                await self._update_quest_streak(user_id)
            
            return completed_quests
            
        except Exception as e:
            logger.error(f"Error updating quest progress: {e}")
            return []
    
    async def check_achievements(self, user_id: int, leaderboard_manager) -> List[Dict]:
        """Check and award achievements for a user"""
        try:
            # Get user stats
            user_stats = leaderboard_manager.get_user_stats(user_id)
            if not user_stats:
                return []
            
            # Get all achievements
            all_achievements = list(self.achievements_collection.find())
            
            # Get user's current achievements
            user_achievements = set(
                doc["achievement_id"] for doc in 
                self.user_achievements_collection.find({"user_id": str(user_id)})
            )
            
            new_achievements = []
            
            for achievement in all_achievements:
                # Skip if user already has this achievement
                if achievement["achievement_id"] in user_achievements:
                    continue
                
                earned = False
                
                if achievement["achievement_type"] == "post_images":
                    earned = user_stats["image_count"] >= achievement["target_count"]
                elif achievement["achievement_type"] == "total_score":
                    earned = user_stats["total_score"] >= achievement["target_count"]
                elif achievement["achievement_type"] == "rate_images":
                    rating_count = await self.get_user_stat(user_id, "ratings_given")
                    earned = rating_count >= achievement["target_count"]
                elif achievement["achievement_type"] == "quest_streak":
                    current_streak = await self.get_user_streak(user_id, "quest_streak")
                    earned = current_streak >= achievement["target_count"]
                elif achievement["achievement_type"] == "post_streak":
                    current_streak = await self.get_user_streak(user_id, "post_streak")
                    earned = current_streak >= achievement["target_count"]
                
                if earned:
                    # Award achievement
                    achievement_record = {
                        "user_id": str(user_id),
                        "achievement_id": achievement["achievement_id"],
                        "name": achievement["name"],
                        "description": achievement["description"],
                        "reward_points": achievement["reward_points"],
                        "earned_at": datetime.now(),
                        "icon": achievement.get("icon", "🏆")
                    }
                    
                    self.user_achievements_collection.insert_one(achievement_record)
                    new_achievements.append(achievement_record)
            
            logger.info(f"Awarded {len(new_achievements)} new achievements to user {user_id}")
            return new_achievements
            
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
            return []
    
    async def get_user_daily_quests(self, user_id: int) -> List[Dict]:
        """Get today's quests for a user"""
        try:
            today = datetime.now().date()
            quests = list(self.user_quests_collection.find({
                "user_id": str(user_id),
                "date": today.isoformat()
            }))
            return quests
        except Exception as e:
            logger.error(f"Error getting user daily quests: {e}")
            return []
    
    async def get_user_achievements(self, user_id: int) -> List[Dict]:
        """Get all achievements for a user"""
        try:
            achievements = list(self.user_achievements_collection.find({
                "user_id": str(user_id)
            }).sort("earned_at", -1))
            return achievements
        except Exception as e:
            logger.error(f"Error getting user achievements: {e}")
            return []
    
    async def create_event(self, name: str, description: str, start_date: datetime, end_date: datetime, created_by_id: int, created_by_name: str) -> Optional[str]:
        """Create a new image contest event"""
        try:
            if not self._ensure_connected():
                logger.error("Cannot create event: Database not connected")
                return None
            event = {
                "name": name,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
                "created_by_id": str(created_by_id),
                "created_by_name": created_by_name,
                "created_at": datetime.now(),
                "is_active": True,
                "contestants": [],
                "winner": None
            }
            
            result = self.events_collection.insert_one(event)
            event_id = str(result.inserted_id)
            
            logger.info(f"Created event '{name}' by {created_by_name}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return None
    
    async def get_active_events(self) -> List[Dict]:
        """Get all currently active events"""
        try:
            now = datetime.now()
            events = list(self.events_collection.find({
                "is_active": True,
                "start_date": {"$lte": now},
                "end_date": {"$gte": now}
            }))
            return events
        except Exception as e:
            logger.error(f"Error getting active events: {e}")
            return []
    
    async def add_event_contestant(self, message_id: str, user_id: int, user_name: str):
        """Add a contestant to active events when they post an image"""
        try:
            active_events = await self.get_active_events()
            
            for event in active_events:
                # Check if user is already a contestant
                if any(c["user_id"] == str(user_id) for c in event.get("contestants", [])):
                    continue
                
                # Add user as contestant
                self.events_collection.update_one(
                    {"_id": event["_id"]},
                    {
                        "$push": {
                            "contestants": {
                                "user_id": str(user_id),
                                "user_name": user_name,
                                "message_id": message_id,
                                "joined_at": datetime.now()
                            }
                        }
                    }
                )
                
                logger.info(f"Added {user_name} as contestant to event '{event['name']}'")
            
        except Exception as e:
            logger.error(f"Error adding event contestant: {e}")
    
    async def end_event(self, event_id: str, leaderboard_manager) -> Optional[Dict]:
        """End an event and determine the winner"""
        try:
            if not self._ensure_connected():
                logger.error("Cannot end event: Database not connected")
                return None
                
            from bson import ObjectId
            
            assert self.events_collection is not None  # Type assertion after connection check
            event = self.events_collection.find_one({"_id": ObjectId(event_id)})
            if not event:
                return None
            
            # Find the highest scoring image from contestants during the event period
            best_image = None
            best_score = float('-inf')
            
            for contestant in event.get("contestants", []):
                # Get the image message from leaderboard manager
                image_data = leaderboard_manager.images_collection.find_one({
                    "message_id": contestant["message_id"]
                })
                
                if image_data and image_data["score"] > best_score:
                    best_score = image_data["score"]
                    best_image = {
                        "user_id": contestant["user_id"],
                        "user_name": contestant["user_name"],
                        "message_id": contestant["message_id"],
                        "score": image_data["score"]
                    }
            
            # Update event with winner
            assert self.events_collection is not None  # Type assertion
            self.events_collection.update_one(
                {"_id": ObjectId(event_id)},
                {
                    "$set": {
                        "is_active": False,
                        "ended_at": datetime.now(),
                        "winner": best_image
                    }
                }
            )
            
            logger.info(f"Ended event '{event['name']}' with winner: {best_image['user_name'] if best_image else 'None'}")
            return {"event": event, "winner": best_image}
            
        except Exception as e:
            logger.error(f"Error ending event: {e}")
            return None
    
    async def update_user_stat(self, user_id: int, stat_type: str, count: int = 1):
        """Update user statistics for quest tracking"""
        try:
            self.user_stats_collection.update_one(
                {"user_id": str(user_id)},
                {
                    "$inc": {stat_type: count},
                    "$set": {"last_updated": datetime.now()}
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating user stat: {e}")
    
    async def get_user_stat(self, user_id: int, stat_type: str) -> int:
        """Get a specific user statistic"""
        try:
            doc = self.user_stats_collection.find_one({"user_id": str(user_id)})
            if doc:
                return doc.get(stat_type, 0)
            return 0
        except Exception as e:
            logger.error(f"Error getting user stat: {e}")
            return 0
    
    async def award_competition_achievement(self, user_id: int, user_name: str, competition_type: str):
        """Award a competition achievement to a user"""
        try:
            achievement_id = f"winner_{competition_type}"
            
            # Check if user already has this achievement
            existing = self.user_achievements_collection.find_one({
                "user_id": str(user_id),
                "achievement_id": achievement_id
            })
            
            if existing:
                return None  # Already has the achievement
            
            # Get the achievement details
            achievement = self.achievements_collection.find_one({"achievement_id": achievement_id})
            if not achievement:
                return None
            
            # Award the achievement
            achievement_record = {
                "user_id": str(user_id),
                "achievement_id": achievement_id,
                "name": achievement["name"],
                "description": achievement["description"],
                "reward_points": achievement["reward_points"],
                "earned_at": datetime.now(),
                "icon": achievement.get("icon", "🏆")
            }
            
            self.user_achievements_collection.insert_one(achievement_record)
            logger.info(f"Awarded {competition_type} achievement to user {user_id}")
            return achievement_record
            
        except Exception as e:
            logger.error(f"Error awarding competition achievement: {e}")
            return None
    
    # ==================== STREAK SYSTEM ====================
    
    async def update_post_streak(self, user_id: int):
        """Update posting streak for a user"""
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # Get or create streak record
            streak_doc = self.user_streaks_collection.find_one({"user_id": str(user_id)})
            
            if not streak_doc:
                # First time posting
                streak_doc = {
                    "user_id": str(user_id),
                    "post_streak": 1,
                    "quest_streak": 0,
                    "last_post_date": today.isoformat(),
                    "last_quest_date": None,
                    "max_post_streak": 1,
                    "max_quest_streak": 0,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                self.user_streaks_collection.insert_one(streak_doc)
                logger.info(f"Started post streak for user {user_id}")
                return 1
            
            last_post_date = datetime.fromisoformat(streak_doc["last_post_date"]).date()
            
            if last_post_date == today:
                # Already posted today, no change
                return streak_doc["post_streak"]
            elif last_post_date == yesterday:
                # Continuing streak
                new_streak = streak_doc["post_streak"] + 1
                max_streak = max(new_streak, streak_doc.get("max_post_streak", 0))
                
                self.user_streaks_collection.update_one(
                    {"user_id": str(user_id)},
                    {
                        "$set": {
                            "post_streak": new_streak,
                            "last_post_date": today.isoformat(),
                            "max_post_streak": max_streak,
                            "updated_at": datetime.now()
                        }
                    }
                )
                logger.info(f"Extended post streak for user {user_id} to {new_streak} days")
                return new_streak
            else:
                # Streak broken, restart
                self.user_streaks_collection.update_one(
                    {"user_id": str(user_id)},
                    {
                        "$set": {
                            "post_streak": 1,
                            "last_post_date": today.isoformat(),
                            "updated_at": datetime.now()
                        }
                    }
                )
                logger.info(f"Post streak broken for user {user_id}, restarted at 1")
                return 1
                
        except Exception as e:
            logger.error(f"Error updating post streak: {e}")
            return 0
    
    async def _update_quest_streak(self, user_id: int):
        """Update quest completion streak for a user (internal method)"""
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # Check if user completed any quest today
            today_quests = list(self.user_quests_collection.find({
                "user_id": str(user_id),
                "date": today.isoformat(),
                "completed": True
            }))
            
            if not today_quests:
                return  # No completed quests today
            
            # Get or create streak record
            streak_doc = self.user_streaks_collection.find_one({"user_id": str(user_id)})
            
            if not streak_doc:
                # First time completing quest
                streak_doc = {
                    "user_id": str(user_id),
                    "post_streak": 0,
                    "quest_streak": 1,
                    "last_post_date": None,
                    "last_quest_date": today.isoformat(),
                    "max_post_streak": 0,
                    "max_quest_streak": 1,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                self.user_streaks_collection.insert_one(streak_doc)
                logger.info(f"Started quest streak for user {user_id}")
                return 1
            
            # Check if already updated today
            last_quest_date_str = streak_doc.get("last_quest_date")
            if last_quest_date_str:
                last_quest_date = datetime.fromisoformat(last_quest_date_str).date()
                if last_quest_date == today:
                    return streak_doc["quest_streak"]  # Already counted today
                elif last_quest_date == yesterday:
                    # Continuing streak
                    new_streak = streak_doc["quest_streak"] + 1
                    max_streak = max(new_streak, streak_doc.get("max_quest_streak", 0))
                    
                    self.user_streaks_collection.update_one(
                        {"user_id": str(user_id)},
                        {
                            "$set": {
                                "quest_streak": new_streak,
                                "last_quest_date": today.isoformat(),
                                "max_quest_streak": max_streak,
                                "updated_at": datetime.now()
                            }
                        }
                    )
                    logger.info(f"Extended quest streak for user {user_id} to {new_streak} days")
                    return new_streak
                else:
                    # Streak broken, restart
                    self.user_streaks_collection.update_one(
                        {"user_id": str(user_id)},
                        {
                            "$set": {
                                "quest_streak": 1,
                                "last_quest_date": today.isoformat(),
                                "updated_at": datetime.now()
                            }
                        }
                    )
                    logger.info(f"Quest streak broken for user {user_id}, restarted at 1")
                    return 1
            else:
                # First quest completion
                self.user_streaks_collection.update_one(
                    {"user_id": str(user_id)},
                    {
                        "$set": {
                            "quest_streak": 1,
                            "last_quest_date": today.isoformat(),
                            "max_quest_streak": max(1, streak_doc.get("max_quest_streak", 0)),
                            "updated_at": datetime.now()
                        }
                    }
                )
                logger.info(f"Started quest streak for user {user_id}")
                return 1
                
        except Exception as e:
            logger.error(f"Error updating quest streak: {e}")
            return 0
    
    async def get_user_streak(self, user_id: int, streak_type: str) -> int:
        """Get current streak for a user"""
        try:
            streak_doc = self.user_streaks_collection.find_one({"user_id": str(user_id)})
            if not streak_doc:
                return 0
            return streak_doc.get(streak_type, 0)
        except Exception as e:
            logger.error(f"Error getting user streak: {e}")
            return 0
    
    async def get_user_streaks(self, user_id: int) -> Dict:
        """Get all streak information for a user"""
        try:
            streak_doc = self.user_streaks_collection.find_one({"user_id": str(user_id)})
            if not streak_doc:
                return {
                    "post_streak": 0,
                    "quest_streak": 0,
                    "max_post_streak": 0,
                    "max_quest_streak": 0,
                    "last_post_date": None,
                    "last_quest_date": None
                }
            
            return {
                "post_streak": streak_doc.get("post_streak", 0),
                "quest_streak": streak_doc.get("quest_streak", 0),
                "max_post_streak": streak_doc.get("max_post_streak", 0),
                "max_quest_streak": streak_doc.get("max_quest_streak", 0),
                "last_post_date": streak_doc.get("last_post_date"),
                "last_quest_date": streak_doc.get("last_quest_date")
            }
        except Exception as e:
            logger.error(f"Error getting user streaks: {e}")
            return {}
    
    async def check_and_break_streaks(self):
        """Check all users for broken streaks (called daily by scheduler)"""
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            # Find all users with active streaks
            active_streaks = list(self.user_streaks_collection.find({
                "$or": [
                    {"post_streak": {"$gt": 0}},
                    {"quest_streak": {"$gt": 0}}
                ]
            }))
            
            for streak_doc in active_streaks:
                user_id = streak_doc["user_id"]
                updates = {}
                
                # Check post streak
                if streak_doc.get("post_streak", 0) > 0:
                    last_post_date_str = streak_doc.get("last_post_date")
                    if last_post_date_str:
                        last_post_date = datetime.fromisoformat(last_post_date_str).date()
                        if last_post_date < yesterday:
                            updates["post_streak"] = 0
                            logger.info(f"Broke post streak for user {user_id}")
                
                # Check quest streak
                if streak_doc.get("quest_streak", 0) > 0:
                    last_quest_date_str = streak_doc.get("last_quest_date")
                    if last_quest_date_str:
                        last_quest_date = datetime.fromisoformat(last_quest_date_str).date()
                        if last_quest_date < yesterday:
                            updates["quest_streak"] = 0
                            logger.info(f"Broke quest streak for user {user_id}")
                
                # Apply updates if any
                if updates:
                    updates["updated_at"] = datetime.now()
                    self.user_streaks_collection.update_one(
                        {"user_id": user_id},
                        {"$set": updates}
                    )
                    
        except Exception as e:
            logger.error(f"Error checking and breaking streaks: {e}") 