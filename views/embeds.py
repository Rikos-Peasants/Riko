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
        else:  # month
            color = discord.Color.purple()
            trophy_emoji = "👑"
            title = "Best Image of the Month!"
        
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
            description=f"No images were posted in the image channels during the past {period}.\n\n"
                       f"Keep sharing your amazing images for a chance to win next {period}!",
            color=discord.Color.light_grey(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_footer(text=f"Better luck next {period}!")
        
        return embed 