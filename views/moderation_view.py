import discord
import logging
from datetime import datetime
from typing import Dict, List, Optional
from views.embeds import EmbedViews

logger = logging.getLogger(__name__)

class ModerationReviewView(discord.ui.View):
    """Interactive UI view for moderation reviews with voting system"""
    
    def __init__(self, message_id: str, moderation_data: dict, bot):
        super().__init__(timeout=None)  # Persistent view
        self.message_id = message_id
        self.moderation_data = moderation_data
        self.bot = bot
        self.votes = {
            'whitelist': set(),  # Set of user IDs who voted to whitelist
            'blacklist': set()   # Set of user IDs who voted to blacklist
        }
        self.processed = False
        
        # Custom ID for persistent views
        self.whitelist_button.custom_id = f"mod_whitelist:{message_id}"
        self.blacklist_button.custom_id = f"mod_blacklist:{message_id}"
        self.info_button.custom_id = f"mod_info:{message_id}"
    
    @discord.ui.button(
        label="✅ Whitelist", 
        style=discord.ButtonStyle.green, 
        emoji="📝"
    )
    async def whitelist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle whitelist vote"""
        if not await self._can_moderate(interaction):
            await interaction.response.send_message("❌ You don't have permission to moderate content.", ephemeral=True)
            return
        
        if self.processed:
            await interaction.response.send_message("❌ This moderation request has already been processed.", ephemeral=True)
            return
        
        # Remove from blacklist votes if user previously voted blacklist
        self.votes['blacklist'].discard(interaction.user.id)
        
        # Add to whitelist votes
        if interaction.user.id in self.votes['whitelist']:
            await interaction.response.send_message("ℹ️ You have already voted to whitelist this content.", ephemeral=True)
            return
        
        self.votes['whitelist'].add(interaction.user.id)
        
        # Check if we should process the decision
        decision_result = await self._check_decision_threshold(interaction)
        
        if decision_result:
            await self._process_decision(interaction, decision_result)
        else:
            # Update the embed to show current votes
            await self._update_vote_display(interaction)
    
    @discord.ui.button(
        label="❌ Blacklist", 
        style=discord.ButtonStyle.red, 
        emoji="🚫"
    )
    async def blacklist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle blacklist vote"""
        if not await self._can_moderate(interaction):
            await interaction.response.send_message("❌ You don't have permission to moderate content.", ephemeral=True)
            return
        
        if self.processed:
            await interaction.response.send_message("❌ This moderation request has already been processed.", ephemeral=True)
            return
        
        # Remove from whitelist votes if user previously voted whitelist
        self.votes['whitelist'].discard(interaction.user.id)
        
        # Add to blacklist votes
        if interaction.user.id in self.votes['blacklist']:
            await interaction.response.send_message("ℹ️ You have already voted to blacklist this content.", ephemeral=True)
            return
        
        self.votes['blacklist'].add(interaction.user.id)
        
        # Check if we should process the decision
        decision_result = await self._check_decision_threshold(interaction)
        
        if decision_result:
            await self._process_decision(interaction, decision_result)
        else:
            # Update the embed to show current votes
            await self._update_vote_display(interaction)
    
    @discord.ui.button(
        label="📊 Vote Info", 
        style=discord.ButtonStyle.gray, 
        emoji="ℹ️"
    )
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show voting information"""
        whitelist_count = len(self.votes['whitelist'])
        blacklist_count = len(self.votes['blacklist'])
        total_votes = whitelist_count + blacklist_count
        
        # Get voter names
        whitelist_voters = []
        blacklist_voters = []
        
        for user_id in self.votes['whitelist']:
            user = self.bot.get_user(user_id)
            if user:
                whitelist_voters.append(user.mention)
        
        for user_id in self.votes['blacklist']:
            user = self.bot.get_user(user_id)
            if user:
                blacklist_voters.append(user.mention)
        
        embed = discord.Embed(
            title="📊 Moderation Vote Status",
            description=f"Current voting status for message `{self.message_id}`",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="✅ Whitelist Votes", 
            value=f"**{whitelist_count}** votes\n" + ("\n".join(whitelist_voters) if whitelist_voters else "No votes yet"), 
            inline=True
        )
        
        embed.add_field(
            name="❌ Blacklist Votes", 
            value=f"**{blacklist_count}** votes\n" + ("\n".join(blacklist_voters) if blacklist_voters else "No votes yet"), 
            inline=True
        )
        
        embed.add_field(
            name="📈 Threshold Info", 
            value="• **Auto-approve:** 2+ whitelist votes (unless majority blacklist)\n"
                  "• **Auto-reject:** Majority blacklist votes\n"
                  "• **Admin override:** Use `/overrule` command", 
            inline=False
        )
        
        embed.set_footer(text="Voting continues until threshold is met or admin overrules")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _can_moderate(self, interaction: discord.Interaction) -> bool:
        """Check if user can moderate content"""
        try:
            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                return False
            
            # Bot owners can always moderate
            if await self.bot.is_owner(interaction.user):
                return True
            
            # Check if user has administrator permissions
            if member.guild_permissions.administrator:
                return True
            
            # Check configured review role
            leaderboard_manager = getattr(self.bot, 'leaderboard_manager', None)
            if not leaderboard_manager or not leaderboard_manager.moderation_manager:
                return False
            
            moderation_manager = leaderboard_manager.moderation_manager
            review_role_id = await moderation_manager.get_review_role_id(str(interaction.guild.id))
            
            if not review_role_id:
                # Use default review role from config
                from config import Config
                review_role_id = Config.DEFAULT_MODERATION_REVIEW_ROLE_ID
            
            review_role = discord.utils.get(member.roles, id=review_role_id)
            return review_role is not None
            
        except Exception as e:
            logger.error(f"Error checking moderation permissions: {e}")
            return False
    
    async def _is_admin(self, interaction: discord.Interaction) -> bool:
        """Check if user is admin for overrule purposes"""
        try:
            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                return False
            
            # Bot owners are admins
            if await self.bot.is_owner(interaction.user):
                return True
            
            # Check if user has administrator permissions
            if member.guild_permissions.administrator:
                return True
            
            # Check configured admin role
            leaderboard_manager = getattr(self.bot, 'leaderboard_manager', None)
            if not leaderboard_manager or not leaderboard_manager.moderation_manager:
                return False
            
            moderation_manager = leaderboard_manager.moderation_manager
            admin_role_id = await moderation_manager.get_admin_role_id(str(interaction.guild.id))
            
            if not admin_role_id:
                # Use default admin role from config
                from config import Config
                admin_role_id = Config.DEFAULT_MODERATION_ADMIN_ROLE_ID
            
            admin_role = discord.utils.get(member.roles, id=admin_role_id)
            return admin_role is not None
            
        except Exception as e:
            logger.error(f"Error checking admin permissions: {e}")
            return False
    
    async def _check_decision_threshold(self, interaction: discord.Interaction) -> Optional[str]:
        """
        Check if voting threshold has been met
        Returns: 'whitelist', 'blacklist', or None
        """
        whitelist_count = len(self.votes['whitelist'])
        blacklist_count = len(self.votes['blacklist'])
        total_votes = whitelist_count + blacklist_count
        
        # If 2+ whitelist votes and not majority blacklist -> auto whitelist
        if whitelist_count >= 2 and blacklist_count < whitelist_count:
            return 'whitelist'
        
        # If majority are blacklist votes (and at least 2 total votes) -> auto blacklist
        if total_votes >= 2 and blacklist_count > whitelist_count:
            return 'blacklist'
        
        # If tie with 4+ votes, require admin intervention
        if total_votes >= 4 and whitelist_count == blacklist_count:
            # Send notification that admin intervention is needed
            await interaction.followup.send(
                "⚖️ **Tie Vote Detected!**\nAdmin intervention required. Use `/overrule` command to make final decision.",
                ephemeral=True
            )
        
        return None
    
    async def _process_decision(self, interaction: discord.Interaction, decision: str):
        """Process the final moderation decision"""
        try:
            self.processed = True
            
            # Get moderation manager
            leaderboard_manager = getattr(self.bot, 'leaderboard_manager', None)
            if not leaderboard_manager or not leaderboard_manager.moderation_manager:
                await interaction.response.send_message("❌ Moderation system unavailable.", ephemeral=True)
                return
            
            moderation_manager = leaderboard_manager.moderation_manager
            
            # Process the decision
            if decision == 'whitelist':
                success = await moderation_manager.approve_message(
                    self.message_id, 
                    str(interaction.user.id), 
                    f"Community Vote ({len(self.votes['whitelist'])} whitelist votes)", 
                    whitelist=True
                )
                
                # Create decision embed
                embed = EmbedViews.moderation_approved_embed(
                    self.moderation_data, 
                    f"Community Vote ({len(self.votes['whitelist'])} votes)", 
                    whitelisted=True
                )
                embed.add_field(
                    name="🗳️ Vote Results", 
                    value=f"✅ **{len(self.votes['whitelist'])}** Whitelist\n❌ **{len(self.votes['blacklist'])}** Blacklist", 
                    inline=True
                )
                
            else:  # blacklist
                success = await moderation_manager.reject_message(
                    self.message_id, 
                    str(interaction.user.id), 
                    f"Community Vote ({len(self.votes['blacklist'])} blacklist votes)", 
                    blacklist=True, 
                    reason="Community voted to blacklist"
                )
                
                # Create decision embed
                embed = EmbedViews.moderation_rejected_embed(
                    self.moderation_data, 
                    f"Community Vote ({len(self.votes['blacklist'])} votes)", 
                    "Community voted to blacklist", 
                    blacklisted=True
                )
                embed.add_field(
                    name="🗳️ Vote Results", 
                    value=f"✅ **{len(self.votes['whitelist'])}** Whitelist\n❌ **{len(self.votes['blacklist'])}** Blacklist", 
                    inline=True
                )
            
            if success:
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                # Remove the view from the manager
                if hasattr(self.bot, 'moderation_view_manager') and self.bot.moderation_view_manager:
                    self.bot.moderation_view_manager.remove_view(self.message_id)
                
                # Update the original message
                await interaction.response.edit_message(embed=embed, view=self)
                
                # Send notification
                action_text = "whitelisted" if decision == 'whitelist' else "blacklisted"
                await interaction.followup.send(
                    f"✅ **Decision Processed!**\nContent has been **{action_text}** by community vote.",
                    ephemeral=True
                )
                
                logger.info(f"Community moderation decision: {decision} for message {self.message_id}")
                
            else:
                await interaction.response.send_message("❌ Failed to process moderation decision.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error processing moderation decision: {e}")
            await interaction.response.send_message("❌ An error occurred processing the decision.", ephemeral=True)
    
    async def _update_vote_display(self, interaction: discord.Interaction):
        """Update the embed to show current vote counts"""
        try:
            # Get the original embed and update it
            embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
            
            # Update or add vote field
            whitelist_count = len(self.votes['whitelist'])
            blacklist_count = len(self.votes['blacklist'])
            
            vote_field_added = False
            for i, field in enumerate(embed.fields):
                if field.name == "🗳️ Current Votes":
                    embed.set_field_at(
                        i, 
                        name="🗳️ Current Votes", 
                        value=f"✅ **{whitelist_count}** Whitelist\n❌ **{blacklist_count}** Blacklist", 
                        inline=True
                    )
                    vote_field_added = True
                    break
            
            if not vote_field_added:
                embed.add_field(
                    name="🗳️ Current Votes", 
                    value=f"✅ **{whitelist_count}** Whitelist\n❌ **{blacklist_count}** Blacklist", 
                    inline=True
                )
            
            # Update footer to show voting progress
            threshold_text = "Need 2+ whitelist votes (unless majority blacklist) for auto-approval"
            embed.set_footer(text=f"{threshold_text} • Use 📊 for details")
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error updating vote display: {e}")
            await interaction.response.send_message("✅ Vote recorded!", ephemeral=True)

class ModerationViewManager:
    """Manages persistent moderation views"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_views: Dict[str, ModerationReviewView] = {}
    
    def create_view(self, message_id: str, moderation_data: dict) -> ModerationReviewView:
        """Create a new moderation view"""
        view = ModerationReviewView(message_id, moderation_data, self.bot)
        self.active_views[message_id] = view
        return view
    
    def get_view(self, message_id: str) -> Optional[ModerationReviewView]:
        """Get an existing moderation view"""
        return self.active_views.get(message_id)
    
    def remove_view(self, message_id: str):
        """Remove a moderation view"""
        self.active_views.pop(message_id, None)
    
    async def handle_interaction(self, interaction: discord.Interaction):
        """Handle button interactions for moderation views"""
        if not interaction.data or 'custom_id' not in interaction.data:
            return False
        
        custom_id = interaction.data['custom_id']
        if not custom_id.startswith('mod_'):
            return False
        
        # Parse custom_id: mod_{action}:{message_id}
        try:
            parts = custom_id.split(':', 1)
            if len(parts) != 2:
                return False
            
            action_part = parts[0]  # mod_{action}
            message_id = parts[1]
            
            view = self.get_view(message_id)
            if not view:
                await interaction.response.send_message(
                    "❌ This moderation request is no longer active.", 
                    ephemeral=True
                )
                return True
            
            # Route to appropriate button handler
            if action_part == 'mod_whitelist':
                await view.whitelist_button.callback(view, interaction, view.whitelist_button)
            elif action_part == 'mod_blacklist':
                await view.blacklist_button.callback(view, interaction, view.blacklist_button)
            elif action_part == 'mod_info':
                await view.info_button.callback(view, interaction, view.info_button)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling moderation interaction: {e}")
            await interaction.response.send_message(
                "❌ An error occurred processing your request.", 
                ephemeral=True
            )
            return True
    
    def setup_persistent_views(self):
        """Setup persistent views after bot restart"""
        # This would be called on bot startup to restore active moderation views
        # For now, we'll handle this through the interaction handler
        pass