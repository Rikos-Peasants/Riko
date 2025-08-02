import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import aiohttp
import discord
from pymongo import MongoClient, DESCENDING

logger = logging.getLogger(__name__)

class ModerationManager:
    """Manages AI-powered content moderation using OpenAI's Moderation API"""
    
    def __init__(self, mongo_client: MongoClient, database_name: str = "Riko"):
        # Import here to avoid circular imports
        from config import Config
        
        self.openai_api_key = Config.OPENAI_KEY
        self.db = mongo_client[database_name]
        
        # Collections for moderation system
        self.moderation_logs_collection = self.db['moderation_logs']
        self.moderation_decisions_collection = self.db['moderation_decisions']
        self.moderation_settings_collection = self.db['moderation_settings']
        
        # Create indexes for better performance
        self._create_indexes()
        
        # OpenAI Moderation API endpoint
        self.moderation_endpoint = "https://api.openai.com/v1/moderations"
        
        logger.info("Moderation Manager initialized")
    
    def _create_indexes(self):
        """Create database indexes for moderation collections"""
        try:
            # Moderation logs indexes
            self.moderation_logs_collection.create_index([("message_id", 1)], unique=True)
            self.moderation_logs_collection.create_index([("guild_id", 1), ("created_at", -1)])
            self.moderation_logs_collection.create_index([("status", 1)])
            self.moderation_logs_collection.create_index([("flagged", 1)])
            
            # Moderation decisions indexes
            self.moderation_decisions_collection.create_index([("content_hash", 1)], unique=True)
            self.moderation_decisions_collection.create_index([("decision", 1)])
            self.moderation_decisions_collection.create_index([("created_at", -1)])
            
            # Moderation settings indexes
            self.moderation_settings_collection.create_index([("guild_id", 1), ("setting_name", 1)], unique=True)
            
            logger.info("Moderation indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating moderation indexes: {e}")
    
    async def scan_message(self, message: discord.Message) -> Optional[Dict]:
        """
        Scan a message using OpenAI's Moderation API
        
        Returns:
            Dict containing moderation results or None if not flagged
        """
        if not self.openai_api_key:
            logger.warning("OpenAI API key not configured, skipping moderation")
            return None
        
        try:
            # Skip if message is empty or only contains mentions/emojis
            clean_content = message.clean_content.strip()
            if not clean_content or len(clean_content) < 3:
                return None
            
            # Call OpenAI Moderation API
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "input": clean_content
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.moderation_endpoint, headers=headers, json=data) as response:
                    if response.status != 200:
                        logger.error(f"OpenAI Moderation API error: {response.status}")
                        return None
                    
                    result = await response.json()
                    
                    if not result.get('results'):
                        return None
                    
                    moderation_result = result['results'][0]
                    
                    # Check if content was flagged
                    if moderation_result.get('flagged', False):
                        # Get content hash for caching decisions
                        content_hash = hash(clean_content.lower())
                        
                        # Check if we already have a decision for this content
                        existing_decision = await self.get_moderation_decision(content_hash)
                        
                        moderation_data = {
                            "message_id": str(message.id),
                            "guild_id": str(message.guild.id) if message.guild else None,
                            "channel_id": str(message.channel.id),
                            "author_id": str(message.author.id),
                            "author_name": message.author.display_name,
                            "content": clean_content,
                            "content_hash": content_hash,
                            "flagged": True,
                            "categories": moderation_result.get('categories', {}),
                            "category_scores": moderation_result.get('category_scores', {}),
                            "status": "auto_approved" if existing_decision and existing_decision['decision'] == "whitelist" else "pending_review",
                            "existing_decision": existing_decision['decision'] if existing_decision else None,
                            "created_at": datetime.utcnow(),
                            "jump_url": message.jump_url
                        }
                        
                        # Store in database
                        await self.store_moderation_log(moderation_data)
                        
                        # If we have an existing whitelist decision, auto-approve
                        if existing_decision and existing_decision['decision'] == "whitelist":
                            logger.info(f"Auto-approved flagged message from {message.author.display_name} (whitelisted content)")
                            return None
                        
                        # If we have an existing blacklist decision, take action
                        if existing_decision and existing_decision['decision'] == "blacklist":
                            moderation_data['status'] = "blacklisted"
                            await self.update_moderation_log(str(message.id), {"status": "blacklisted"})
                            logger.info(f"Blacklisted content detected from {message.author.display_name}")
                            return moderation_data
                        
                        logger.info(f"Message flagged for review from {message.author.display_name} in #{message.channel.name}")
                        return moderation_data
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Error scanning message for moderation: {e}")
            return None
    
    async def store_moderation_log(self, moderation_data: Dict) -> bool:
        """Store moderation log in database"""
        try:
            self.moderation_logs_collection.replace_one(
                {"message_id": moderation_data["message_id"]},
                moderation_data,
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error storing moderation log: {e}")
            return False
    
    async def update_moderation_log(self, message_id: str, update_data: Dict) -> bool:
        """Update moderation log"""
        try:
            result = self.moderation_logs_collection.update_one(
                {"message_id": message_id},
                {"$set": {**update_data, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating moderation log: {e}")
            return False
    
    async def get_moderation_log(self, message_id: str) -> Optional[Dict]:
        """Get moderation log by message ID"""
        try:
            return self.moderation_logs_collection.find_one({"message_id": message_id})
        except Exception as e:
            logger.error(f"Error getting moderation log: {e}")
            return None
    
    async def get_pending_moderation_logs(self, guild_id: str, limit: int = 10) -> List[Dict]:
        """Get pending moderation logs for review"""
        try:
            cursor = self.moderation_logs_collection.find({
                "guild_id": guild_id,
                "status": "pending_review"
            }).sort("created_at", DESCENDING).limit(limit)
            
            return list(cursor)
        except Exception as e:
            logger.error(f"Error getting pending moderation logs: {e}")
            return []
    
    async def store_moderation_decision(self, content_hash: int, decision: str, moderator_id: str, moderator_name: str, reason: str = None) -> bool:
        """Store moderation decision (whitelist/blacklist)"""
        try:
            decision_data = {
                "content_hash": content_hash,
                "decision": decision,  # "whitelist" or "blacklist"
                "moderator_id": moderator_id,
                "moderator_name": moderator_name,
                "reason": reason or "No reason provided",
                "created_at": datetime.utcnow()
            }
            
            self.moderation_decisions_collection.replace_one(
                {"content_hash": content_hash},
                decision_data,
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error storing moderation decision: {e}")
            return False
    
    async def get_moderation_decision(self, content_hash: int) -> Optional[Dict]:
        """Get existing moderation decision for content"""
        try:
            return self.moderation_decisions_collection.find_one({"content_hash": content_hash})
        except Exception as e:
            logger.error(f"Error getting moderation decision: {e}")
            return None
    
    async def approve_message(self, message_id: str, moderator_id: str, moderator_name: str, whitelist: bool = False) -> bool:
        """Approve a flagged message"""
        try:
            log_data = await self.get_moderation_log(message_id)
            if not log_data:
                return False
            
            update_data = {
                "status": "approved",
                "moderator_id": moderator_id,
                "moderator_name": moderator_name,
                "reviewed_at": datetime.utcnow()
            }
            
            # If whitelisting, store decision for future
            if whitelist:
                await self.store_moderation_decision(
                    log_data['content_hash'],
                    "whitelist",
                    moderator_id,
                    moderator_name,
                    "Whitelisted by community/staff vote"
                )
                update_data["whitelisted"] = True
            
            return await self.update_moderation_log(message_id, update_data)
            
        except Exception as e:
            logger.error(f"Error approving message: {e}")
            return False
    
    async def reject_message(self, message_id: str, moderator_id: str, moderator_name: str, blacklist: bool = False, reason: str = None) -> bool:
        """Reject a flagged message"""
        try:
            log_data = await self.get_moderation_log(message_id)
            if not log_data:
                return False
            
            update_data = {
                "status": "rejected",
                "moderator_id": moderator_id,
                "moderator_name": moderator_name,
                "reviewed_at": datetime.utcnow(),
                "rejection_reason": reason or "Inappropriate content"
            }
            
            # If blacklisting, store decision for future
            if blacklist:
                await self.store_moderation_decision(
                    log_data['content_hash'],
                    "blacklist",
                    moderator_id,
                    moderator_name,
                    reason or "Blacklisted by community/staff vote"
                )
                update_data["blacklisted"] = True
            
            return await self.update_moderation_log(message_id, update_data)
            
        except Exception as e:
            logger.error(f"Error rejecting message: {e}")
            return False
    
    async def overrule_decision(self, message_id: str, is_allowed: bool, admin_id: str, admin_name: str, reason: str = None) -> bool:
        """Admin overrule of moderation decision"""
        try:
            log_data = await self.get_moderation_log(message_id)
            if not log_data:
                return False
            
            update_data = {
                "status": "overruled_approved" if is_allowed else "overruled_rejected",
                "overrule_admin_id": admin_id,
                "overrule_admin_name": admin_name,
                "overrule_reason": reason or "Admin overrule",
                "overruled_at": datetime.utcnow()
            }
            
            # Update the decision in the decisions collection
            await self.store_moderation_decision(
                log_data['content_hash'],
                "whitelist" if is_allowed else "blacklist",
                admin_id,
                admin_name,
                f"Admin overrule: {reason or 'No reason provided'}"
            )
            
            return await self.update_moderation_log(message_id, update_data)
            
        except Exception as e:
            logger.error(f"Error overruling decision: {e}")
            return False
    
    # Settings Management
    async def set_moderation_setting(self, guild_id: str, setting_name: str, setting_value) -> bool:
        """Set a moderation setting for a guild"""
        try:
            self.moderation_settings_collection.replace_one(
                {"guild_id": guild_id, "setting_name": setting_name},
                {
                    "guild_id": guild_id,
                    "setting_name": setting_name,
                    "setting_value": setting_value,
                    "updated_at": datetime.utcnow()
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error setting moderation setting: {e}")
            return False
    
    async def get_moderation_setting(self, guild_id: str, setting_name: str, default_value=None):
        """Get a moderation setting for a guild"""
        try:
            result = self.moderation_settings_collection.find_one({
                "guild_id": guild_id,
                "setting_name": setting_name
            })
            return result["setting_value"] if result else default_value
        except Exception as e:
            logger.error(f"Error getting moderation setting: {e}")
            return default_value
    
    async def is_moderation_enabled(self, guild_id: str) -> bool:
        """Check if moderation is enabled for a guild"""
        return await self.get_moderation_setting(guild_id, "moderation_enabled", False)
    
    async def get_review_role_id(self, guild_id: str) -> Optional[int]:
        """Get the role ID that can review moderation"""
        role_id = await self.get_moderation_setting(guild_id, "review_role_id")
        return int(role_id) if role_id else None
    
    async def get_admin_role_id(self, guild_id: str) -> Optional[int]:
        """Get the role ID that can overrule decisions"""
        role_id = await self.get_moderation_setting(guild_id, "admin_role_id")
        return int(role_id) if role_id else None
    
    async def get_moderation_log_channel_id(self, guild_id: str) -> Optional[int]:
        """Get the channel ID for moderation logs"""
        channel_id = await self.get_moderation_setting(guild_id, "moderation_log_channel_id")
        return int(channel_id) if channel_id else None
    
    async def get_moderation_stats(self, guild_id: str, days: int = 30) -> Dict:
        """Get moderation statistics for a guild"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {"$match": {
                    "guild_id": guild_id,
                    "created_at": {"$gte": start_date}
                }},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
            
            results = list(self.moderation_logs_collection.aggregate(pipeline))
            stats = {item["_id"]: item["count"] for item in results}
            
            # Get total flagged messages
            total_flagged = self.moderation_logs_collection.count_documents({
                "guild_id": guild_id,
                "flagged": True,
                "created_at": {"$gte": start_date}
            })
            
            # Get blacklisted content hits
            blacklisted_hits = self.moderation_logs_collection.count_documents({
                "guild_id": guild_id,
                "status": "blacklisted",
                "created_at": {"$gte": start_date}
            })
            
            return {
                "total_flagged": total_flagged,
                "pending_review": stats.get("pending_review", 0),
                "approved": stats.get("approved", 0),
                "rejected": stats.get("rejected", 0),
                "blacklisted_hits": blacklisted_hits,
                "auto_approved": stats.get("auto_approved", 0),
                "overruled": stats.get("overruled_approved", 0) + stats.get("overruled_rejected", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting moderation stats: {e}")
            return {}

    def close(self):
        """Close MongoDB connection"""
        # Connection is managed by the parent mongo client
        pass