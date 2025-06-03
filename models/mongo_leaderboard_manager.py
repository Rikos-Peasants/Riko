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
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.connection_url, serverSelectionTimeoutMS=5000)
            # Test the connection
            self.client.admin.command('ismaster')
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Create indexes for better performance
            self.collection.create_index("user_id", unique=True)
            self.collection.create_index([("total_score", DESCENDING)])
            
            logger.info(f"Connected to MongoDB database '{self.database_name}', collection '{self.collection_name}'")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise Exception(f"MongoDB connection failed: {e}")
    
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