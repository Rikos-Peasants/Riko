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