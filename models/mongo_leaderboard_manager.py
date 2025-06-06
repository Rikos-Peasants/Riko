import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class MongoLeaderboardManager:
    """Manages user image statistics and leaderboard data using MongoDB"""
    
    def __init__(self, connection_url: str = None, database_name: str = "Riko", collection_name: str = "images"):
        # Import here to avoid circular imports
        from config import Config
        
        self.connection_url = connection_url or Config.MONGO_URI
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
        self.images_collection = None  # New collection for storing image messages
        self.nsfwban_collection = None  # New collection for NSFWBAN data
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.connection_url, serverSelectionTimeoutMS=5000)
            # Test the connection
            self.client.admin.command('ismaster')
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            self.images_collection = self.db['image_messages']  # New collection
            self.nsfwban_collection = self.db['nsfwban_users']  # New collection for NSFWBAN
            
            # Create indexes for better performance
            self.collection.create_index("user_id", unique=True)
            self.collection.create_index([("total_score", DESCENDING)])
            
            # Create indexes for image messages
            self.images_collection.create_index([("message_id", 1)], unique=True)
            self.images_collection.create_index([("channel_id", 1), ("created_at", -1)])
            self.images_collection.create_index([("score", -1)])
            
            # Create indexes for NSFWBAN users
            self.nsfwban_collection.create_index([("user_id", 1)], unique=True)
            self.nsfwban_collection.create_index([("banned_at", -1)])
            
            logger.info(f"Connected to MongoDB database '{self.database_name}', collections: {self.collection_name}, image_messages, nsfwban_users")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise Exception(f"MongoDB connection failed: {e}")

    # NSFWBAN Management Methods
    async def add_nsfwban_user(self, user_id: int, user_name: str, banned_by_id: int, banned_by_name: str, reason: str = None) -> bool:
        """Add a user to the NSFWBAN list"""
        try:
            doc = {
                "user_id": str(user_id),
                "user_name": user_name,
                "banned_by_id": str(banned_by_id),
                "banned_by_name": banned_by_name,
                "reason": reason or "No reason provided",
                "banned_at": datetime.now(),
                "is_active": True
            }
            
            result = self.nsfwban_collection.update_one(
                {"user_id": str(user_id)},
                {"$set": doc},
                upsert=True
            )
            
            logger.info(f"Added {user_name} to NSFWBAN list by {banned_by_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding user to NSFWBAN list: {e}")
            return False

    async def remove_nsfwban_user(self, user_id: int) -> bool:
        """Remove a user from the NSFWBAN list"""
        try:
            result = self.nsfwban_collection.update_one(
                {"user_id": str(user_id)},
                {"$set": {"is_active": False, "unbanned_at": datetime.now()}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Removed user {user_id} from NSFWBAN list")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing user from NSFWBAN list: {e}")
            return False

    async def is_nsfwban_user(self, user_id: int) -> bool:
        """Check if a user is in the NSFWBAN list"""
        try:
            result = self.nsfwban_collection.find_one({
                "user_id": str(user_id),
                "is_active": True
            })
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking NSFWBAN status: {e}")
            return False

    async def get_nsfwban_user_info(self, user_id: int) -> Optional[Dict]:
        """Get NSFWBAN information for a user"""
        try:
            result = self.nsfwban_collection.find_one({
                "user_id": str(user_id),
                "is_active": True
            })
            return result
            
        except Exception as e:
            logger.error(f"Error getting NSFWBAN user info: {e}")
            return None

    async def get_all_nsfwban_users(self) -> List[Dict]:
        """Get all active NSFWBAN users"""
        try:
            cursor = self.nsfwban_collection.find({"is_active": True}).sort("banned_at", -1)
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error getting all NSFWBAN users: {e}")
            return []

    async def image_message_exists(self, message_id: str) -> bool:
        """Check if an image message already exists in the database"""
        try:
            result = self.images_collection.find_one({"message_id": str(message_id)})
            return result is not None
        except Exception as e:
            logger.error(f"Error checking if image message exists: {e}")
            return False

    async def store_image_message(self, message, image_url: str, initial_score: int = 0):
        """Store an image message in the database"""
        try:
            # Create document for the image message
            doc = {
                "message_id": str(message.id),
                "channel_id": str(message.channel.id),
                "author_id": str(message.author.id),
                "author_name": message.author.display_name,
                "content": message.content,
                "image_url": image_url,
                "score": initial_score,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "created_at": message.created_at,
                "jump_url": message.jump_url
            }
            
            # Use upsert to handle potential duplicates
            result = self.images_collection.update_one(
                {"message_id": doc["message_id"]},
                {"$set": doc},
                upsert=True
            )
            
            logger.info(f"Stored image message from {message.author.display_name} in #{message.channel.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing image message: {e}")
            return False

    async def update_image_message_score(self, message_id: str, thumbs_up: int, thumbs_down: int):
        """Update the score for an image message"""
        try:
            net_score = thumbs_up - thumbs_down
            result = self.images_collection.update_one(
                {"message_id": str(message_id)},
                {
                    "$set": {
                        "score": net_score,
                        "thumbs_up": thumbs_up,
                        "thumbs_down": thumbs_down,
                        "last_updated": datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.debug(f"Updated score for message {message_id}: {net_score} (👍{thumbs_up} - 👎{thumbs_down})")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating image message score: {e}")
            return False

    async def get_best_image(self, channel_id: str, start_date: datetime, end_date: datetime) -> Optional[Dict]:
        """Get the best image in a channel for a given time period"""
        try:
            # Query for the highest scored image in the time period
            result = self.images_collection.find_one(
                {
                    "channel_id": str(channel_id),
                    "created_at": {
                        "$gte": start_date,
                        "$lt": end_date
                    }
                },
                sort=[("score", DESCENDING)]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting best image: {e}")
            return None

    async def delete_image_message(self, message_id: str):
        """Delete an image message from the database"""
        try:
            result = self.images_collection.delete_one({"message_id": str(message_id)})
            if result.deleted_count > 0:
                logger.info(f"Deleted image message {message_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting image message: {e}")
            return False
    
    def add_image_post(self, user_id: int, user_name: str, initial_score: int = 0):
        """Record when a user posts an image"""
        try:
            # Use upsert to either create or update user data
            result = self.collection.update_one(
                {"user_id": str(user_id)},
                {
                    "$set": {
                        "user_name": user_name,
                        "last_updated": datetime.now().isoformat()
                    },
                    "$inc": {
                        "image_count": 1,
                        "total_score": initial_score
                    },
                    "$setOnInsert": {
                        "user_id": str(user_id),
                        "created_at": datetime.now().isoformat()
                    }
                },
                upsert=True
            )
            
            # Get updated document to log the new count
            updated_doc = self.collection.find_one({"user_id": str(user_id)})
            if updated_doc:
                logger.info(f"Added image post for {user_name} (new count: {updated_doc['image_count']})")
            
        except Exception as e:
            logger.error(f"Error adding image post for {user_name}: {e}")
    
    def update_image_score(self, user_id: int, user_name: str, score_change: int):
        """Update a user's score when reactions change"""
        try:
            result = self.collection.update_one(
                {"user_id": str(user_id)},
                {
                    "$set": {
                        "user_name": user_name,
                        "last_updated": datetime.now().isoformat()
                    },
                    "$inc": {
                        "total_score": score_change
                    },
                    "$setOnInsert": {
                        "user_id": str(user_id),
                        "image_count": 1,
                        "created_at": datetime.now().isoformat()
                    }
                },
                upsert=True
            )
            
            # Get updated document to log the new score
            updated_doc = self.collection.find_one({"user_id": str(user_id)})
            if updated_doc:
                logger.debug(f"Updated score for {user_name}: {score_change:+d} (total: {updated_doc['total_score']})")
            
        except Exception as e:
            logger.error(f"Error updating score for {user_name}: {e}")
    
    def get_leaderboard(self, limit: int = 10) -> List[Tuple[str, int, int, int]]:
        """Get leaderboard data sorted by total score"""
        try:
            cursor = self.collection.find({}).sort("total_score", DESCENDING).limit(limit)
            
            leaderboard = []
            for doc in cursor:
                leaderboard.append((
                    doc.get("user_name", "Unknown"),
                    int(doc["user_id"]),
                    doc.get("total_score", 0),
                    doc.get("image_count", 0)
                ))
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get stats for a specific user"""
        try:
            doc = self.collection.find_one({"user_id": str(user_id)})
            if doc:
                return {
                    "name": doc.get("user_name", "Unknown"),
                    "total_score": doc.get("total_score", 0),
                    "image_count": doc.get("image_count", 0),
                    "last_updated": doc.get("last_updated", ""),
                    "created_at": doc.get("created_at", "")
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return None
    
    def reset_leaderboard(self) -> bool:
        """Reset all leaderboard data (admin function)"""
        try:
            # Create backup collection name with timestamp
            backup_collection_name = f"{self.collection_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Copy all documents to backup collection
            pipeline = [{"$out": backup_collection_name}]
            list(self.collection.aggregate(pipeline))
            
            # Delete all documents from main collection
            result = self.collection.delete_many({})
            
            logger.info(f"Leaderboard reset successfully. {result.deleted_count} documents removed. Backup saved to '{backup_collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting leaderboard: {e}")
            return False
    
    def get_stats_summary(self) -> Dict:
        """Get summary statistics"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_users": {"$sum": 1},
                        "total_images": {"$sum": "$image_count"},
                        "total_score": {"$sum": "$total_score"}
                    }
                }
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                total_images = stats.get("total_images", 0)
                total_score = stats.get("total_score", 0)
                average_score = total_score / total_images if total_images > 0 else 0
                
                return {
                    "total_users": stats.get("total_users", 0),
                    "total_images": total_images,
                    "total_score": total_score,
                    "average_score": round(average_score, 2)
                }
            else:
                return {
                    "total_users": 0,
                    "total_images": 0,
                    "total_score": 0,
                    "average_score": 0
                }
                
        except Exception as e:
            logger.error(f"Error getting stats summary: {e}")
            return {
                "total_users": 0,
                "total_images": 0,
                "total_score": 0,
                "average_score": 0
            }
    
    def migrate_from_json(self, json_data: Dict) -> bool:
        """Migrate data from JSON format to MongoDB"""
        try:
            if "users" not in json_data:
                logger.warning("No users data found in JSON")
                return False
            
            documents = []
            for user_id, user_data in json_data["users"].items():
                doc = {
                    "user_id": user_id,
                    "user_name": user_data.get("name", "Unknown"),
                    "total_score": user_data.get("total_score", 0),
                    "image_count": user_data.get("image_count", 0),
                    "last_updated": user_data.get("last_updated", datetime.now().isoformat()),
                    "created_at": datetime.now().isoformat(),
                    "migrated_from_json": True,
                    "migration_date": datetime.now().isoformat()
                }
                documents.append(doc)
            
            if documents:
                # Insert all documents, replacing existing ones
                for doc in documents:
                    self.collection.replace_one(
                        {"user_id": doc["user_id"]},
                        doc,
                        upsert=True
                    )
                
                logger.info(f"Successfully migrated {len(documents)} users from JSON to MongoDB")
                return True
            else:
                logger.warning("No documents to migrate")
                return False
                
        except Exception as e:
            logger.error(f"Error migrating from JSON: {e}")
            return False
    
    def close(self):
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed") 