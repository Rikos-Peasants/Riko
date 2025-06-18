import discord
from datetime import datetime
from typing import Optional

class EmbedViews:
    """Handles creation of Discord embeds"""
    
    @staticmethod
    def access_denied_embed() -> discord.Embed:
        """Create an embed for access denied message"""
        embed = discord.Embed(
            title="🚫 Access Denied",
            description="You are banned from accessing this role/channel.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Contact an administrator if you believe this is an error")
        return embed
    
    @staticmethod
    def nsfwban_success_embed(user: discord.Member, reason: str, banned_by: discord.Member) -> discord.Embed:
        """Create an embed for successful NSFWBAN"""
        embed = discord.Embed(
            title="🔨 NSFWBAN Applied",
            description=f"**{user.display_name}** has been NSFWBAN'd",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="👤 User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="👮 Banned by", value=f"{banned_by.mention}", inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        return embed
    
    @staticmethod
    def nsfwunban_success_embed(user: discord.Member, unbanned_by: discord.Member) -> discord.Embed:
        """Create an embed for successful NSFWUNBAN"""
        embed = discord.Embed(
            title="✅ NSFWBAN Removed",
            description=f"**{user.display_name}** has been unbanned from NSFW content",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="👤 User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="👮 Unbanned by", value=f"{unbanned_by.mention}", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        return embed
    
    @staticmethod
    def nsfwban_dm_embed(reason: str, guild_name: str) -> discord.Embed:
        """Create an embed for NSFWBAN DM notification"""
        embed = discord.Embed(
            title="🔨 You have been NSFWBAN'd",
            description=f"You have been banned from accessing NSFW content in **{guild_name}**",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.add_field(
            name="ℹ️ What this means",
            value="• You cannot access NSFW channels\n• This restriction will persist if you leave and rejoin\n• Contact an administrator to appeal",
            inline=False
        )
        embed.set_footer(text="Contact server administrators if you believe this is an error")
        return embed
    
    @staticmethod
    def nsfwunban_dm_embed(guild_name: str) -> discord.Embed:
        """Create an embed for NSFWUNBAN DM notification"""
        embed = discord.Embed(
            title="✅ NSFWBAN Removed",
            description=f"Your NSFW ban has been removed in **{guild_name}**",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="🎉 You can now",
            value="• Access NSFW channels again\n• Participate in age-restricted content",
            inline=False
        )
        return embed
    
    @staticmethod
    def uptime_embed(uptime_str: str) -> discord.Embed:
        """Create an embed for uptime command"""
        embed = discord.Embed(
            title="🟢 Bot Uptime",
            description=f"Bot has been running for: **{uptime_str}**",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        return embed
    
    @staticmethod
    def error_embed(message: str) -> discord.Embed:
        """Create a generic error embed"""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        return embed
    
    @staticmethod
    async def best_image_embed(message: discord.Message, period: str, score: int) -> discord.Embed:
        """Create an embed for the best image of the week/month"""
        # Determine color and emojis based on period
        if period == "week":
            color = discord.Color.gold()
            trophy_emoji = "🥇"
            title = "Best Image of the Week!"
        elif period == "month":
            color = discord.Color.purple()
            trophy_emoji = "👑"
            title = "Best Image of the Month!"
        else:  # year
            color = discord.Color.red()
            trophy_emoji = "🏆"
            title = "Best Image of the Year!"
        
        embed = discord.Embed(
            title=f"{trophy_emoji} {title}",
            description=f"Congratulations to **{message.author.display_name}** for the most upvoted image!\n\n"
                       f"**Net Score:** {score} upvotes (👍 - 👎)\n"
                       f"**Channel:** #{message.channel.name}\n"
                       f"**Posted:** {message.created_at.strftime('%B %d, %Y at %I:%M %p')}",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        # Add the winning image
        image_url = None
        
        # Check for attachments first
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                image_url = attachment.url
                break
        
        # Check for embedded images if no attachment
        if not image_url:
            for embed_obj in message.embeds:
                if embed_obj.image:
                    image_url = embed_obj.image.url
                    break
                elif embed_obj.thumbnail:
                    image_url = embed_obj.thumbnail.url
                    break
        
        if image_url:
            # Display all images the same way (no NSFW spoilers)
            embed.set_image(url=image_url)
        
        # Add original message link
        embed.add_field(
            name="🔗 Original Post",
            value=f"[Click here to see the original]({message.jump_url})",
            inline=False
        )
        
        # Add author info
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url if message.author.display_avatar else None
        )
        
        embed.set_footer(text=f"🎉 Winner of the {period}!")
        
        return embed
    
    @staticmethod
    def no_winner_embed(period: str) -> discord.Embed:
        """Create an embed when no images are found for the period"""
        embed = discord.Embed(
            title=f"📭 No Best Image of the {period.title()}",
            description=f"No images were posted in this channel during the past {period}.\n\n"
                       f"Keep sharing your amazing images here for a chance to win next {period}!",
            color=discord.Color.light_grey(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_footer(text=f"Better luck next {period} in this channel!")
        
        return embed
    
    @staticmethod
    def warning_embed(user: discord.Member, moderator: discord.Member, reason: str, warning_count: int, action: str) -> discord.Embed:
        """Create an embed for a user warning"""
        # Determine color based on warning count
        if warning_count == 1:
            color = discord.Color.orange()
            title = "⚠️ Warning Issued"
        elif warning_count == 2:
            color = discord.Color.red()
            title = "🔴 Second Warning - Timeout Applied"
        elif warning_count == 3:
            color = discord.Color.dark_red()
            title = "🚨 Third Warning - Extended Timeout"
        elif warning_count == 4:
            color = discord.Color.dark_red()
            title = "⛔ Fourth Warning - Long Timeout"
        else:
            color = discord.Color.dark_red()
            title = "🔨 Final Warning - User Kicked"
        
        embed = discord.Embed(
            title=title,
            description=f"**{user.display_name}** has received warning #{warning_count}",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="👤 User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="👮 Moderator", value=f"{moderator.mention}", inline=True)
        embed.add_field(name="📊 Warning Count", value=f"**{warning_count}**/5", inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        
        # Add action taken
        action_text = {
            "warning": "⚠️ Warning logged - no immediate action",
            "timeout_1h": "🔇 User timed out for 1 hour",
            "timeout_4h": "🔇 User timed out for 4 hours", 
            "timeout_1w": "🔇 User timed out for 1 week",
            "kick": "👢 User has been kicked from the server"
        }
        
        embed.add_field(
            name="⚡ Action Taken",
            value=action_text.get(action, "No action taken"),
            inline=False
        )
        
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        embed.set_footer(text="Server Moderation System")
        
        return embed
    
    @staticmethod
    def user_warnings_embed(user: discord.Member, warnings: list, total_count: int) -> discord.Embed:
        """Create an embed showing a user's warnings"""
        embed = discord.Embed(
            title=f"📋 Warnings for {user.display_name}",
            description=f"Showing recent warnings ({len(warnings)} of {total_count} total)",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="👤 User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="⚠️ Active Warnings", value=f"**{total_count}**/5", inline=True)
        embed.add_field(name="📊 Status", value="❌ At Risk" if total_count >= 3 else "✅ Good Standing", inline=True)
        
        if warnings:
            for i, warning in enumerate(warnings[:5], 1):  # Show max 5 recent warnings
                created_at = warning.get('created_at', datetime.now())
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except:
                        created_at = datetime.now()
                
                embed.add_field(
                    name=f"Warning #{i}",
                    value=f"**Reason:** {warning.get('reason', 'No reason')}\n"
                          f"**By:** {warning.get('moderator_name', 'Unknown')}\n"
                          f"**Date:** {created_at.strftime('%m/%d/%Y at %I:%M %p')}",
                    inline=False
                )
        else:
            embed.add_field(name="✅ No Warnings", value="This user has no active warnings.", inline=False)
        
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        embed.set_footer(text="Use /clearwarnings to remove warnings")
        
        return embed
    
    @staticmethod
    def warning_cleared_embed(user: discord.Member, cleared_count: int, moderator: discord.Member) -> discord.Embed:
        """Create an embed for cleared warnings"""
        embed = discord.Embed(
            title="🧹 Warnings Cleared",
            description=f"All warnings have been cleared for **{user.display_name}**",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="👤 User", value=f"{user.mention} ({user.id})", inline=True)
        embed.add_field(name="👮 Cleared by", value=f"{moderator.mention}", inline=True)
        embed.add_field(name="📊 Warnings Cleared", value=f"**{cleared_count}** warnings", inline=True)
        
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        embed.set_footer(text="User is now in good standing")
        
        return embed
    
    @staticmethod
    def warning_log_embed(user: discord.Member, moderator: discord.Member, reason: str, warning_count: int, action: str) -> discord.Embed:
        """Create an embed for warning log messages"""
        # Determine color and emoji based on warning count
        if warning_count == 1:
            color = discord.Color.orange()
            emoji = "⚠️"
        elif warning_count == 2:
            color = discord.Color.red()
            emoji = "🔴"
        elif warning_count == 3:
            color = discord.Color.dark_red()
            emoji = "🚨"
        elif warning_count == 4:
            color = discord.Color.dark_red()
            emoji = "⛔"
        else:
            color = discord.Color.dark_red()
            emoji = "🔨"
        
        embed = discord.Embed(
            title=f"{emoji} Warning Issued - #{warning_count}",
            description=f"A warning has been issued to {user.mention}",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="👤 User", value=f"{user.mention}\n`{user.name}` ({user.id})", inline=True)
        embed.add_field(name="👮 Moderator", value=f"{moderator.mention}\n`{moderator.name}`", inline=True)
        embed.add_field(name="📊 Warning #", value=f"**{warning_count}**/5", inline=True)
        
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        
        # Add action taken
        action_text = {
            "warning": "⚠️ Warning logged",
            "timeout_1h": "🔇 Timed out for 1 hour",
            "timeout_4h": "🔇 Timed out for 4 hours", 
            "timeout_1w": "🔇 Timed out for 1 week",
            "kick": "👢 User kicked from server"
        }
        
        embed.add_field(
            name="⚡ Action Taken",
            value=action_text.get(action, "No action taken"),
            inline=False
        )
        
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        embed.set_footer(text="Warning System Log", icon_url=moderator.display_avatar.url if moderator.display_avatar else None)
        
        return embed
    
    @staticmethod
    def daily_quests_embed(quests: list, user_name: str) -> discord.Embed:
        """Create an embed for daily quests"""
        embed = discord.Embed(
            title="📋 Daily Quests",
            description=f"**{user_name}'s** daily quests",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if not quests:
            embed.add_field(
                name="No Quests Available",
                value="Use `/quests` to generate your daily quests!",
                inline=False
            )
        else:
            total_points = 0
            completed_count = 0
            
            for quest in quests:
                status = "✅" if quest.get("completed", False) else "📝"
                progress = f"{quest.get('current_count', 0)}/{quest['target_count']}"
                points = quest['reward_points']
                total_points += points
                
                if quest.get("completed", False):
                    completed_count += 1
                
                embed.add_field(
                    name=f"{status} {quest['name']} ({points} pts)",
                    value=f"{quest['description']}\nProgress: **{progress}**",
                    inline=True
                )
            
            embed.set_footer(text=f"Completed: {completed_count}/{len(quests)} • Total Points: {total_points}")
        
        return embed
    
    @staticmethod
    def achievements_embed(achievements: list, user_name: str) -> discord.Embed:
        """Create an embed for user achievements"""
        embed = discord.Embed(
            title="🏆 Achievements",
            description=f"**{user_name}'s** earned achievements",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        if not achievements:
            embed.add_field(
                name="No Achievements Yet",
                value="Keep posting and rating images to earn achievements!",
                inline=False
            )
        else:
            total_points = sum(a['reward_points'] for a in achievements)
            
            for achievement in achievements[:10]:  # Show latest 10
                icon = achievement.get('icon', '🏆')
                points = achievement['reward_points']
                earned_date = achievement['earned_at'].strftime('%m/%d/%Y')
                
                embed.add_field(
                    name=f"{icon} {achievement['name']} ({points} pts)",
                    value=f"{achievement['description']}\nEarned: {earned_date}",
                    inline=True
                )
            
            if len(achievements) > 10:
                embed.add_field(
                    name="...",
                    value=f"And {len(achievements) - 10} more achievements!",
                    inline=False
                )
            
            embed.set_footer(text=f"Total Achievements: {len(achievements)} • Total Points: {total_points}")
        
        return embed
    
    @staticmethod
    def quest_completed_embed(quest: dict) -> discord.Embed:
        """Create an embed for quest completion"""
        embed = discord.Embed(
            title="🎉 Quest Completed!",
            description=f"You completed: **{quest['name']}**",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Quest", 
            value=quest['description'], 
            inline=False
        )
        embed.add_field(
            name="Reward", 
            value=f"**{quest['reward_points']} points**", 
            inline=True
        )
        
        return embed
    
    @staticmethod
    def achievement_earned_embed(achievement: dict) -> discord.Embed:
        """Create an embed for achievement earned"""
        embed = discord.Embed(
            title="🏆 Achievement Unlocked!",
            description=f"**{achievement['name']}**",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        icon = achievement.get('icon', '🏆')
        embed.add_field(
            name=f"{icon} Achievement",
            value=achievement['description'],
            inline=False
        )
        embed.add_field(
            name="Reward",
            value=f"**{achievement['reward_points']} points**",
            inline=True
        )
        
        return embed
    
    @staticmethod
    def event_created_embed(event: dict) -> discord.Embed:
        """Create an embed for event creation"""
        embed = discord.Embed(
            title="🎯 New Image Contest Event!",
            description=f"**{event['name']}**",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📝 Description",
            value=event['description'],
            inline=False
        )
        embed.add_field(
            name="📅 Start Date",
            value=event['start_date'].strftime('%B %d, %Y at %I:%M %p'),
            inline=True
        )
        embed.add_field(
            name="🏁 End Date",
            value=event['end_date'].strftime('%B %d, %Y at %I:%M %p'),
            inline=True
        )
        embed.add_field(
            name="👤 Created by",
            value=event['created_by_name'],
            inline=True
        )
        embed.add_field(
            name="🎮 How to Participate",
            value="Post images in any image channel during the event period to automatically enter!",
            inline=False
        )
        
        embed.set_footer(text="All images posted during the event will compete for the highest score!")
        
        return embed
    
    @staticmethod
    def active_events_embed(events: list) -> discord.Embed:
        """Create an embed for active events"""
        embed = discord.Embed(
            title="🎯 Active Image Contest Events",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )
        
        if not events:
            embed.description = "No active events at the moment.\nBot owners can create events with `/createevent`"
        else:
            for event in events:
                contestants_count = len(event.get('contestants', []))
                time_left = event['end_date'] - datetime.now()
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                
                time_text = f"{days_left}d {hours_left}h remaining" if days_left > 0 else f"{hours_left}h remaining"
                
                embed.add_field(
                    name=f"🎯 {event['name']}",
                    value=f"{event['description']}\n"
                          f"**Contestants:** {contestants_count}\n"
                          f"**Time left:** {time_text}",
                    inline=False
                )
        
        return embed
    
    @staticmethod
    def event_winner_embed(event: dict, winner: dict) -> discord.Embed:
        """Create an embed for event winner announcement"""
        embed = discord.Embed(
            title="🏆 Event Winner!",
            description=f"**{event['name']}** has ended!",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        if winner:
            embed.add_field(
                name="🥇 Winner",
                value=f"**{winner['user_name']}**",
                inline=True
            )
            embed.add_field(
                name="📊 Final Score",
                value=f"**{winner['score']} points**",
                inline=True
            )
            embed.add_field(
                name="🔗 Winning Image",
                value=f"[View Original](https://discord.com/channels/@me/{winner['message_id']})",
                inline=True
            )
        else:
            embed.add_field(
                name="No Winner",
                value="No valid contestants found for this event.",
                inline=False
            )
        
        embed.set_footer(text="Congratulations to the winner!")
        
        return embed

    @staticmethod
    def leaderboard_embed(leaderboard_data: list, period: str = "all time") -> discord.Embed:
        """Create an embed for the leaderboard"""
        embed = discord.Embed(
            title=f"🏆 Image Leaderboard ({period.title()})",
            description="Top users by total net upvotes on their images",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        if not leaderboard_data:
            embed.add_field(
                name="📭 No Data",
                value="No images found for the specified period.",
                inline=False
            )
            return embed
        
        # Add leaderboard entries
        medal_emojis = ["🥇", "🥈", "🥉"]
        
        for i, (user_name, user_id, total_score, image_count) in enumerate(leaderboard_data[:10]):
            position = i + 1
            
            # Use medal emojis for top 3, numbers for others
            if position <= 3:
                position_emoji = medal_emojis[position - 1]
            else:
                position_emoji = f"{position}."
            
            # Calculate average score
            avg_score = total_score / image_count if image_count > 0 else 0
            
            embed.add_field(
                name=f"{position_emoji} {user_name}",
                value=f"**Total Score:** {total_score}\n**Images:** {image_count}\n**Avg:** {avg_score:.1f}",
                inline=True
            )
        
        embed.set_footer(text=f"📊 Based on net upvotes (👍 - 👎) • Showing top 10")
        
        return embed 