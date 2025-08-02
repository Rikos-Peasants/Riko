# 🤖 Enhanced AI Moderation System with UI Components

## Overview

Ino now features a sophisticated AI-powered moderation system with interactive UI components, collaborative voting, and smart decision-making algorithms. The system has been completely upgraded from reaction-based to modern Discord UI buttons with advanced voting mechanics.

## 🆕 Key Enhancements

### **Interactive UI Components**
- **Modern Button Interface**: Replaced reaction-based voting with Discord's UI component buttons
- **Persistent Views**: Buttons remain functional across bot restarts
- **Real-time Vote Tracking**: Live updates showing current vote counts
- **Rich Information Display**: Detailed voting status and threshold information

### **Advanced Voting System**

#### **Consensus-Based Decisions**
- **Auto-Whitelist**: 2+ whitelist votes automatically approve (unless majority blacklist)
- **Auto-Blacklist**: Majority blacklist votes automatically reject content
- **Tie Breaking**: 4+ total votes with tie requires admin intervention
- **Smart Thresholds**: Dynamic decision making based on vote patterns

#### **Role-Based Permissions**
- **Reviewers** (Seraphs): Can vote on flagged content
- **Admins**: Can overrule any decision using `/overrule` command
- **Bot Owners**: Full access to all moderation features

### **Enhanced Decision Logic**

```
Voting Rules:
├── 2+ Whitelist votes → Auto-approve (unless majority blacklist)
├── Majority Blacklist → Auto-reject  
├── Tie with 4+ votes → Admin intervention required
└── Admin overrule → Overrides all votes
```

## 🎛️ New UI Components

### **Moderation Review Panel**
When content is flagged, staff see an interactive panel with:

```
🚨 Content Flagged for Review
┌─────────────────────────────────────┐
│ ⚠️ Content Flagged for Review       │
│                                     │
│ 👤 Author: @Username                │
│ 📍 Channel: #channel-name           │
│ 🆔 Message ID: 123456789           │
│                                     │
│ 🚨 Flagged Categories               │
│ • Harassment (85.2%)               │
│ • Hate Speech (72.1%)              │
│                                     │
│ 📝 Content                          │
│ ```                                 │
│ Flagged message content here...     │
│ ```                                 │
│                                     │
│ 🗳️ Voting System                   │
│ • 2+ Whitelist votes = Auto-approve │
│ • Majority Blacklist = Auto-reject │
│ • Tie with 4+ votes = Admin needed │
│                                     │
│ [✅ Whitelist] [❌ Blacklist] [📊 Info] │
└─────────────────────────────────────┘
```

### **Vote Status Display**
```
📊 Moderation Vote Status
┌─────────────────────────────────────┐
│ ✅ Whitelist Votes: 2 votes        │
│ @Staff1, @Staff2                   │
│                                     │
│ ❌ Blacklist Votes: 1 vote         │
│ @Staff3                            │
│                                     │
│ 📈 Threshold Info                   │
│ • Auto-approve: 2+ whitelist       │
│ • Auto-reject: Majority blacklist  │
│ • Admin override: Use /overrule     │
└─────────────────────────────────────┘
```

## 🔧 Commands

### **Enhanced Configuration**
```bash
# Configure moderation system
/modconfig                           # View current settings
/modconfig enable true              # Enable moderation
/modconfig review_role @Seraphs     # Set reviewer role
/modconfig admin_role @Admin        # Set admin role  
/modconfig log_channel #mod-logs    # Set log channel

# Enhanced log channel setup
/setlogchannel                      # View all log channels
/setlogchannel moderation #channel  # Set moderation logs
/setlogchannel warnings #channel    # Set warning logs

# Admin overrule (enhanced with embed editing)
/overrule id:123456 isAllowed:true reason:"False positive - whitelisting"

# Statistics
/modstats                          # Show moderation statistics
/modstats 7                        # Show last 7 days stats

# Bulk Moderation Actions (Purge Group Commands)
/purge user @username 50           # Delete 50 messages from user
/purge user @username 100 reason:"Spam cleanup"  # With custom reason
/purge contains "spam text"        # Delete messages containing text
/purge contains "bad word" amount:200 reason:"Content cleanup"  # Advanced usage
```

### **Bulk Moderation Tools**

#### **Purge User Messages**
```bash
/purge user @spammer                 # Delete last 100 messages from user (default)
/purge user @spammer 50              # Delete last 50 messages from user
/purge user @spammer 200 reason:"Account compromised"  # With custom reason
```

#### **Purge by Content**
```bash
/purge contains "spam link"          # Delete messages containing "spam link"
/purge contains "discord.gg" amount:500 reason:"Link spam cleanup"  # Advanced usage
```

**Features:**
- ✅ **Command Group Structure**: Part of `/purge` group with subcommands
- ✅ **Permission Checks**: Admin commands require administrator permissions
- ✅ **Comprehensive Logging**: All purge actions logged to moderation channel
- ✅ **Flexible Limits**: 1-1000 message limit per operation
- ✅ **Case-Insensitive Search**: Content matching ignores case
- ✅ **Detailed Audit Trail**: Shows moderator, reason, and affected count

**Available Purge Commands:**
- `/purge humans` - Delete messages from human users only
- `/purge bots` - Delete messages from bots only  
- `/purge media` - Delete messages with attachments/images
- `/purge embeds` - Delete messages with embeds
- `/purge all` - Delete all messages
- `/purge user` - Delete messages from specific user (Admin only)
- `/purge contains` - Delete messages containing text (Admin only)

### **Statistics Dashboard**
```
📊 Moderation Statistics (Last 30 days)
┌─────────────────────────────────────┐
│ 🚨 Total Flagged: 45               │
│ ⏳ Pending Review: 2               │
│ ✅ Approved: 23                    │
│ ❌ Rejected: 18                    │
│ 🚫 Blacklisted Hits: 12           │
│ 📝 Auto-approved: 31              │
│ ⚖️ Overruled: 3                   │
│ 🎯 Review Rate: 91.1%              │
└─────────────────────────────────────┘
```

## 🎯 Workflow

### **1. Content Scanning**
```
User posts message → OpenAI scans → Decision tree:
├── Clean content → ✅ Allow silently
├── Whitelisted pattern → ✅ Auto-approve  
├── Blacklisted pattern → ❌ Auto-delete + log
└── New flagged content → 🗑️ Delete original + 🔔 Send to staff review
```

### **2. Staff Review Process**
```
Staff receives notification → Interactive review panel → Vote:
├── Click "Whitelist" → Add whitelist vote
├── Click "Blacklist" → Add blacklist vote  
├── Click "Info" → View detailed vote status
└── Automatic processing when threshold met
```

### **3. Decision Processing**
```
Vote threshold reached → Automatic decision:
├── 2+ Whitelist (no majority blacklist) → ✅ Auto-whitelist
├── Majority blacklist → ❌ Auto-blacklist
├── Tie with 4+ votes → ⏳ Admin intervention needed
└── Admin /overrule → 👑 Override all votes + Edit original message
```

### **3.1. Enhanced Overrule System**
When an admin uses `/overrule`, the system now:
- ✅ **Updates Database** - Changes the decision in the moderation log
- ✅ **Edits Original Embed** - Modifies the flagged review message to show overrule status
- ✅ **Disables Buttons** - Prevents further voting on overruled content
- ✅ **Visual Feedback** - Changes embed color (green for approved, red for rejected)
- ✅ **Admin Attribution** - Shows who made the overrule and when

### **4. Enhanced Content Similarity Detection**
```
Similar content posted later → Advanced similarity checking:
├── Exact hash match → ✅/❌ Instant decision
├── Normalized variant match → ✅/❌ Fast recognition  
├── Fuzzy similarity match (85%+) → ✅/❌ Smart detection
└── No similar content found → 🔄 Full review workflow
```

**Advanced Detection Features:**
- ✅ **Text Normalization** - Removes punctuation, spaces, case differences
- ✅ **Bypass Prevention** - Detects common evasion techniques (l33t speak, extra characters)
- ✅ **Multiple Hash Variants** - Stores normalized versions for fast lookup
- ✅ **Fuzzy Matching** - Uses similarity algorithms to catch minor variations
- ✅ **Recent Content Scanning** - Checks against last 1000 decisions for performance

**Example Detections:**
- `"That's too gay.."` ↔ `"That's too gay..m"` → **85%+ similarity detected**
- `"th4ts g4y"` ↔ `"thats gay"` → **Normalized variant match**
- `"t h a t s   g a y"` ↔ `"thats gay"` → **Spacing normalization match**

### **4.1. Technical Implementation**

#### **Content Normalization Process**
1. **Convert to lowercase** - Remove case sensitivity
2. **Remove URLs, mentions** - Strip Discord-specific elements
3. **Remove excessive punctuation** - Keep only alphanumeric and spaces
4. **Normalize whitespace** - Single spaces, trim edges
5. **Remove repeated characters** - "aaa" becomes "a"

#### **Variant Generation**
- **Base normalized** - Standard cleaned version
- **No spaces** - Remove all spacing
- **No vowels** - Common obfuscation technique
- **Leet speak fixes** - Replace numbers/symbols with letters
- **Alpha-only** - Letters and numbers only

#### **Smart Lookup Process**
```
New flagged content → Generate variants → Check exact matches
                                       ↓ (if no matches)
                    Recent decisions ← Fuzzy similarity (85% threshold)
                                       ↓ (if match found)
                        Apply previous decision automatically
```

**Performance Optimizations:**
- ✅ **Multiple hash storage** for O(1) exact lookups
- ✅ **Limited fuzzy scanning** (1000 recent decisions max)  
- ✅ **Variant caching** to avoid regeneration
- ✅ **Similarity threshold** tuning for accuracy vs performance

### **4.2. Real-World Example**

#### **Scenario: User Tries to Bypass Detection**
1. **First message**: `"That's too gay.."` → Flagged by OpenAI → Community votes to blacklist
2. **System stores**:
   - Primary hash: `hash("thats too gay")`
   - Variants: `hash("thatstoogay")`, `hash("thts t gy")`, etc.
   - Original content: `"That's too gay.."` for fuzzy matching

3. **Second message**: `"That's too gay..m"` → Flagged by OpenAI → System checks:
   - ❌ Exact hash match? No
   - ❌ Variant hash match? No  
   - ✅ Fuzzy similarity? **87% match** with previous blacklisted content
   - 🚫 **Auto-blacklist applied** - No staff review needed!

4. **Result**: User's bypass attempt is automatically caught and blocked

#### **Before Enhancement:**
- `"That's too gay.."` → `hash("that's too gay..")` = `123456`
- `"That's too gay..m"` → `hash("that's too gay..m")` = `789012`  
- ❌ **Different hashes** → No detection → Bypass successful

#### **After Enhancement:**
- Both messages normalize to similar patterns
- Multiple variants stored and checked
- Fuzzy matching catches 87% similarity  
- ✅ **Bypass prevented** → Consistent enforcement

### **Visual Examples**

#### **Overruled Embed Appearance**
When an admin overrules a decision, the original flagged embed transforms:

**Before Overrule:**
```
🚨 Content Flagged for Review
┌─────────────────────────────────────┐
│ ⚠️ Content Flagged for Review       │
│ 👤 Author: @Username                │
│ 📍 Channel: #channel-name           │
│ 🗳️ Current Votes: 1 Whitelist, 1 Blacklist │
│ [✅ Whitelist] [❌ Blacklist] [📊 Info] │
└─────────────────────────────────────┘
```

**After Admin Approval:**
```
✅ Content Overruled - APPROVED
┌─────────────────────────────────────┐
│ ✅ Content Overruled - APPROVED     │
│ 👤 Author: @Username                │
│ 📍 Channel: #channel-name           │
│ ⚖️ Admin Override:                  │
│   Admin: @AdminName                 │
│   Decision: APPROVED                │
│   Reason: False positive            │
│ [✅ Whitelist] [❌ Blacklist] [📊 Info] │ (All disabled)
└─────────────────────────────────────┘
Overruled by AdminName at 2024-01-01 12:00:00 UTC
```

## 🗂️ Database Schema

### **Enhanced Collections**
```javascript
// Moderation Logs (Enhanced)
{
  message_id: "123456789",
  guild_id: "987654321", 
  content: "flagged content",
  content_hash: 123456,
  categories: { harassment: true, hate: false },
  category_scores: { harassment: 0.85, hate: 0.23 },
  status: "pending_review|approved|rejected|blacklisted|overruled_approved|overruled_rejected",
  
  // New fields for review message tracking
  review_message_id: "987654321",     // ID of the flagged embed message
  review_channel_id: "111222333",     // Channel containing the review message
  
  // Voting data
  votes: {
    whitelist: ["user1", "user2"],
    blacklist: ["user3"] 
  },
  
  // Processing information
  processed_by: "community_vote|admin_overrule",
  
  // Overrule data (when admin overrules)
  overrule_admin_id: "456789",
  overrule_admin_name: "AdminName",
  overrule_reason: "False positive",
  overruled_at: Date,
  
  // Timestamps
  created_at: Date,
  reviewed_at: Date,
  updated_at: Date
}

// Moderation Decisions (Enhanced with Similarity Detection)
{
  content_hash: 123456,                    // Primary hash
  hash_variants: [123456, 789012, 345678], // All normalized variants
  original_content: "That's too gay..",    // Original text for fuzzy matching
  decision: "whitelist|blacklist",
  moderator_id: "123",
  moderator_name: "Staff Member", 
  reason: "Community voted to whitelist",
  is_variant: false,                       // true for variant entries
  primary_hash: 123456,                    // Reference to primary (for variants)
  created_at: Date
}

// Moderation Settings
{
  guild_id: "123",
  setting_name: "moderation_enabled",
  setting_value: true,
  updated_at: Date
}
```

## 🚀 Setup Instructions

### **1. Enable System**
```bash
/modconfig enable true
/setlogchannel moderation #mod-logs
```

### **2. Configure Roles** (Optional)
```bash
/modconfig review_role @CustomReviewers
/modconfig admin_role @CustomAdmins
```

### **3. Test System**
- Post potentially problematic content
- Check mod-logs channel for review requests
- Test voting with different staff members
- Test admin overrule functionality

## 🎨 UI Component Features

Based on [Discord's Components V2 system](https://disky.me/docs/interactions/componentsv2/), the moderation system includes:

### **Button Styles**
- **✅ Whitelist**: Green button with checkmark
- **❌ Blacklist**: Red button with X 
- **📊 Vote Info**: Gray info button

### **Persistent Views**
- Buttons work across bot restarts
- Custom IDs for reliable interaction handling
- View cleanup after decisions

### **Real-time Updates**
- Vote counts update immediately  
- Visual feedback for user actions
- Threshold notifications

## 🔒 Security Features

### **Permission Validation**
- Role-based access control
- Guild-specific permissions
- Bot owner override capabilities

### **Anti-Spam Protection**
- One vote per user per content
- Vote switching allowed (removes previous vote)
- Processing locks prevent double-decisions

### **Audit Trail**
- Complete decision logging
- Vote history tracking  
- Admin override documentation

## 📈 Performance Optimizations

### **Database Indexes**
- Message ID indexing for fast lookups
- Content hash indexing for duplicate detection
- Guild/date compound indexes for statistics

### **Caching System**
- Content hash-based decision caching
- Persistent view management
- Memory-efficient vote tracking

### **Smart Processing**
- Automatic threshold detection
- Background vote processing
- Efficient embed updates

## 🎯 Benefits

1. **Enhanced User Experience**: Modern UI components vs old reactions
2. **Collaborative Moderation**: Multiple staff can vote on decisions  
3. **Smart Automation**: Reduces staff workload with intelligent thresholds
4. **Admin Control**: Overrule system for final authority
5. **Comprehensive Logging**: Full audit trail of all decisions
6. **Scalable Architecture**: Handles high-volume servers efficiently

The enhanced moderation system transforms Ino into a sophisticated AI-powered moderator with modern UI, collaborative decision-making, and intelligent automation while maintaining complete admin control and comprehensive logging.