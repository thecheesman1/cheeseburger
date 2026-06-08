# 🍔 Cheeseburger Casino

> *"The world's most unhinged cheeseburger-themed crypto-style casino simulator."*

A fully-featured multiplayer casino platform with **16 games**, **50 collectible skins**, a **player-driven market economy**, and **40 AI bots** powered by LLM chat integration. Built entirely with Flask, SQLite, and vanilla HTML/CSS/JS.

---

## 🎮 Games (16 Total)

### 🚀 Crash — *Multiplayer King*
The flagship game. All players in a room watch a multiplier climb from 1.00x upward. Cash out before it crashes, or lose everything. The crash point is determined by a house-edge-adjusted random curve. Bots join live and cash out with personality-driven aggression levels. Supports live room state polling at `/crash/state`.

| Feature | Detail |
|---|---|
| **Players** | Unlimited, real-time multiplayer |
| **House Edge** | Configurable (default 5%) |
| **Payout** | Variable — sky's the limit |
| **Bot Strategy** | Martingale, aggression tiers (low/medium/high), trend analysis |
| **Live Stats** | Current multiplier, players in room, total pot |

### 🎰 Slots — *Classic 3-Reel*
Spin three reels with animated symbols. Match 2 for a small payout, match all 3 for the jackpot.

| Match | Payout |
|---|---|
| 3 of a kind | 10x |
| 2 of a kind | 2x |
| 0 matches | 0x |

### 🪙 Coin Flip — *50/50*
Pick heads or tails. The coin flips with a CSS animation. Pure 50/50 odds at 2x payout.

### 🎲 Dice — *Predict the Sum*
Two dice are rolled. Bet on the sum (2 through 12). Payout scales inversely with probability — guessing snake eyes (2) pays 36x, while guessing the most common roll (7) pays 6x.

| Sum Range | Payout |
|---|---|
| 2 or 12 | 36x |
| 3 or 11 | 18x |
| 4 or 10 | 12x |
| 5 or 9 | 9x |
| 6 or 8 | 7.2x |
| 7 | 6x |

### 🃏 Blackjack — *Beat the Dealer*
Classic casino blackjack. Dealer hits on <17, stands on ≥17. Blackjack pays 1.5x. Hit, stand, and double-down mechanics. Cards tracked per-session to prevent counting across hands.

| Outcome | Payout |
|---|---|
| Blackjack (Ace + 10/Face) | 1.5x |
| Win | 2x |
| Push (tie) | 1x (refund) |
| Loss | 0x |

### 🎡 Roulette — *European Style*
Bet on numbers (0–36), colors (red/black), parity (even/odd), or ranges (1-18/19-36). Single-zero European wheel for better odds.

| Bet Type | Payout |
|---|---|
| Straight up (single number) | 36x |
| Split (2 numbers) | 18x |
| Street (3 numbers) | 12x |
| Corner (4 numbers) | 9x |
| Red/Black, Even/Odd, Low/High | 2x |

### 🔢 Keno — *Pick Your Numbers*
Choose up to 10 numbers from 1–80. 20 numbers are drawn. Payout scales with how many you match.

### 🟣 Plinko — *Drop the Ball*
Choose a risk level and drop a ball through a pegboard. The ball bounces left and right, landing in a multiplier slot at the bottom. Higher risk = wider multiplier spread.

| Risk Level | Max Payout |
|---|---|
| Low | ~4x |
| Medium | ~15x |
| High | ~150x |

### 💣 Mines — *Avoid the Bombs*
A grid hides mines. Reveal tiles one by one — each safe tile increases your multiplier. Cash out anytime. Hit a mine and you lose everything. Configurable mine count for risk/reward.

### 🎡 Wheel — *Spin to Win*
A colorful prize wheel with segments of varying sizes. Each segment has a different multiplier. Spin and land on your fortune.

| Segment Count | Max Payout |
|---|---|
| 16 segments | Up to 20x |

### 🃏 Hi-Lo — *Higher or Lower*
A card is dealt. Guess whether the next card will be higher or lower. Chain correct guesses for compounding multipliers. One wrong guess resets. Cash out anytime.

### 🚀 Limbo — *Set Your Target*
Pick a target multiplier. A random number is generated. If the result exceeds your target, you win at your target multiplier. Higher targets = lower win probability but bigger payouts.

### 🎴 Baccarat — *Player vs Banker*
Classic baccarat. Bet on Player, Banker, or Tie. Closest to 9 wins. Banker bet has a small commission.

| Bet | Payout |
|---|---|
| Player | 2x |
| Banker | 1.95x |
| Tie | 9x |

### 🔲 Scratchcard — *Scratch & Reveal*
Virtual scratch-off card with a 3x3 grid. Match 3 symbols in a row, column, or diagonal to win. Scratch animation reveals symbols one by one.

### 🗼 Tower — *Climb the Tower*
Multi-level tower climb. Advance floor by floor — each floor you clear multiplies your winnings. Fall and you lose it all. Cash out between floors. Higher difficulty = more floors = bigger multipliers.

### 📦 Crates — *Loot Box System*
Open crates to receive random skins based on weighted rarity tables.

| Crate | Price | Drop Rates |
|---|---|---|
| **Standard** | $8,000 | 60% Common, 25% Uncommon, 10% Rare, 4% Epic, 1% Legendary |
| **Premium** | $25,000 | 20% Common, 35% Uncommon, 25% Rare, 15% Epic, 5% Legendary |
| **Legendary** | $100,000 | 0% Common, 0% Uncommon, 10% Rare, 40% Epic, 50% Legendary |

---

## 💎 Skins — Collectible Cosmetics (50 Total)

Skins are cosmetic items that players can collect, equip to show off on their profile, and trade on the player-to-player market. Each skin has a unique name, emoji, rarity tier, and base price.

### Rarity Tiers

| Rarity | Count | Base Price Range | Color | Drop Rate (Standard Crate) |
|---|---|---|---|---|
| ⚪ **Common** | 10 | $700 – $1,500 | `#9e9e9e` | 60% |
| 🟢 **Uncommon** | 9 | $4,500 – $7,000 | `#4ade80` | 25% |
| 🔵 **Rare** | 8 | $15,000 – $23,000 | `#60a5fa` | 10% |
| 🟣 **Epic** | 8 | $50,000 – $75,000 | `#c084fc` | 4% |
| 🟡 **Legendary** | 15 | $200,000 – $800,000 | `#fbbf24` | 1% |

### Full Skin Catalog

<details>
<summary><b>⚪ Common (10)</b></summary>

| # | Skin | Emoji | Base Price |
|---|---|---|---|
| 1 | Rusty Burger | 🍔 | $1,500 |
| 2 | Paper Fries | 🍟 | $1,200 |
| 3 | Plastic Cup | 🥤 | $1,000 |
| 4 | Cardboard Nuggets | 🍗 | $1,300 |
| 5 | Tin Tray | 🧊 | $1,100 |
| 6 | Receipt Wrap | 🧾 | $900 |
| 7 | Ketchup Packet | 🫗 | $800 |
| 8 | Flimsy Straw | 🥤 | $950 |
| 9 | Napkin Square | 🍽️ | $700 |
| 10 | Soggy Bun | 🍞 | $850 |

</details>

<details>
<summary><b>🟢 Uncommon (9)</b></summary>

| # | Skin | Emoji | Base Price |
|---|---|---|---|
| 11 | Silver Spatula | 🥄 | $5,000 |
| 12 | Neon Shake | 🥤 | $6,000 |
| 13 | Bronze Fries | 🍟 | $4,500 |
| 14 | Pixel Burger | 🍔 | $5,500 |
| 15 | Glazed Donut Burger | 🍩 | $7,000 |
| 16 | Fizzy Cola | 🥤 | $4,800 |
| 17 | Toasted Bun | 🍞 | $5,200 |
| 18 | Chrome Tray | 🧊 | $5,800 |
| 19 | Retro Cup | 🎵 | $5,100 |

</details>

<details>
<summary><b>🔵 Rare (8)</b></summary>

| # | Skin | Emoji | Base Price |
|---|---|---|---|
| 20 | Golden Nuggets | ✨ | $15,000 |
| 21 | Ruby Shake | 💎 | $18,000 |
| 22 | Sapphire Spatula | 🔮 | $20,000 |
| 23 | Emerald Burger | 💚 | $22,000 |
| 24 | Amethyst Fries | 🟣 | $19,000 |
| 25 | Crystal Nuggets | 💠 | $21,000 |
| 26 | Topaz Shake | 🍯 | $17,000 |
| 27 | Jade Spatula | 🪻 | $23,000 |

</details>

<details>
<summary><b>🟣 Epic (8)</b></summary>

| # | Skin | Emoji | Base Price |
|---|---|---|---|
| 28 | Diamond Burger | 💎 | $50,000 |
| 29 | Obsidian Fries | 🖤 | $60,000 |
| 30 | Cosmic Nuggets | 🌌 | $55,000 |
| 31 | Galaxy Spatula | 🌟 | $65,000 |
| 32 | Void Shake | 🕳️ | $70,000 |
| 33 | Thunder Fries | 🌩️ | $62,000 |
| 34 | Inferno Burger | 🔥 | $75,000 |
| 35 | Frostbite Nuggets | ❄️ | $68,000 |

</details>

<details>
<summary><b>🟡 Legendary (15)</b></summary>

| # | Skin | Emoji | Base Price |
|---|---|---|---|
| 36 | Neo Burger | 👑 | $200,000 |
| 37 | God Fries | ⚡ | $250,000 |
| 38 | Infinity Nuggets | ♾️ | $300,000 |
| 39 | Cheeseburger Supreme | 🏆 | $500,000 |
| 40 | Quantum Spatula | 🌀 | $350,000 |
| 41 | Eclipse Burger | 🌑 | $400,000 |
| 42 | Immortal Fries | 🪽 | $450,000 |
| 43 | Cosmic Shake | 🌠 | $380,000 |
| 44 | Apocalypse Nuggets | 💀 | $420,000 |
| 45 | Omega Burger | 🔱 | $550,000 |
| 46 | Genesis Spatula | ✴️ | $600,000 |
| 47 | Divine Fries | 👼 | $480,000 |
| 48 | Exodia Nuggets | 🎴 | $700,000 |
| 49 | Hypernova Burger | 💥 | $650,000 |
| 50 | Eternal Shake | ⏳ | $800,000 |

</details>

---

## 🏪 Market Economy

The player-to-player skin market is a fully dynamic economy simulator.

### Dynamic Pricing Engine
Skin prices are not static — they fluctuate based on **5 market forces**:

| Force | Description |
|---|---|
| **Rarity Floor** | Each rarity has a minimum price that acts as a floor |
| **Supply Scarcity** | Fewer listings = higher prices; oversupply drives prices down |
| **Trend Cycles** | Rotating trend cycles every 5 minutes boost certain skin categories |
| **Sales Velocity** | Recently sold skins get a temporary price bump |
| **Noise Jitter** | Random ±5% variance to simulate market noise |

### Market Actions
- **Sell**: List skins from your inventory at any price
- **Buy**: Purchase skins from other players' listings
- **Cancel**: Remove your own listings from the market
- **Market Tax**: Configurable tax on all sales (default 5%)

### Market Events
The economy experiences random events every 5–15 minutes:
- 📈 **Market Rally** — Skin prices spike across the board
- 📉 **Market Dip** — Everything goes on sale
- 🎰 **Jackpot Fever** — Jackpot odds temporarily doubled
- 🎉 **Bot Party** — Bots flood chat with celebratory messages
- 🐋 **Whale Alert** — High rollers are active and spending big

---

## 🤖 AI Bot Ecosystem

Cheeseburger Casino features **40 AI bots**, each with unique personalities, strategies, rivalries, alliances, and an LLM-powered chat brain that makes them feel alive.

### Bot Names (40 Total)

```
BurgerKing     FryMaster      NuggetLord     ShakeWizard    GrillGod
PattyFlipper   SauceBoss      BunRunner      CheeseQueen    MeatMaverick
KetchupKing    MustardMenace  PicklePrince   OnionOverlord  RelishRogue
SesameSorcerer ToastTitan     LettuceLegend  TomatoTyrant   BaconBandit
BBQBaron       SaltSultan     PepperPhantom  GarlicGhost    ChiliChampion
MayoMystic     CheddarChad    SwissSniper    GoudaGuru      MozzarellaMarauder
BriocheBoss    SliderSamurai  DoubleDecker   TripleStack    WagyuWarrior
CrinkleCultist TaterTotem     MilkshakeManiac FryFiend      ColaCommander
```

### 7 Personality Archetypes

| Archetype | Count | Strategy |
|---|---|---|
| 🐋 **Whale** | 5 | High-stakes betting, big bankroll, crash cashouts at high multipliers |
| 🎯 **Grinder** | 5 | Consistent small bets, steady profit accumulation, low risk |
| 🎰 **Degenerate** | 6 | All-in gambler, chases losses, max risk tolerance |
| 💼 **Merchant** | 5 | Skin trader, market manipulator, flips crates for profit |
| 🧮 **SystemPlayer** | 5 | Martingale strategy, mathematical approach, doubles bets on loss |
| ⚔️ **PvPer** | 10 | Trashtalker, feud-driven, aggressive betting to one-up rivals |
| 📊 **TrendChaser** | 4 | Follows market trends, momentum trader, chart analysis |

### Bot 2.0 Intelligence Layer

Each bot maintains persistent state across sessions:

| System | Description |
|---|---|
| **Mood System** | Dynamic mood based on balance trajectory — 😊 happy, 😐 neutral, 😡 tilted, 🤬 raging |
| **Goal System** | Bots set personal goals: reach target balance, hit a crash multiplier, collect skins, hunt jackpots |
| **Martingale Engine** | SystemPlayers double bets after losses (up to 16x), reset on win |
| **Achievement Tracking** | Milestones: "First Jackpot", "Hot Streak", "Crash God", "Phoenix" (recovery from bankruptcy), "Market Mogul" |
| **Lucky Charms** | 30% of bots have a lucky charm (🍀, 🧲, 🔮, 💫, 🪙) that influences their play |
| **Bankruptcy Recovery** | When a bot goes broke, they get a bailout loan. After 5 bankruptcies, they have an LLM-powered meltdown in chat |

### Social Dynamics

#### Rivalries (10 Pairs)
Each bot has a nemesis — they trash-talk each other in chat, escalate feuds based on balance comparison, and compete for dominance:

```
KetchupKing ↔ MustardMenace        BurgerKing ↔ WagyuWarrior
NuggetLord ↔ TaterTotem            PicklePrince ↔ OnionOverlord
BaconBandit ↔ LettuceLegend        CheddarChad ↔ MozzarellaMarauder
BBQBaron ↔ SaltSultan              FryFiend ↔ ColaCommander
ShakeWizard ↔ MilkshakeManiac      TripleStack ↔ DoubleDecker
```

#### Alliances (6 Groups of 4)
Bots form alliance squads — they chat to each other, coordinate market activity, and celebrate each other's wins:
- 🐋 Whale Squad
- 💼 Merchant Guild
- 🎯 Grinder Union
- ⚔️ PvP Crew
- 🎰 Degen Squad
- 🧮 System Players

### Diurnal Cycle
Bot activity follows a realistic day/night rhythm:
- 🌙 **2 AM – 7 AM**: 25% activity (mostly sleeping)
- 🌅 **8 AM – 4 PM**: 70% activity (waking up)
- 🌇 **5 PM – 11 PM**: 100% activity (peak hours)
- 🌃 **12 AM – 1 AM**: 80% activity (winding down)

### Sleep Mode
When no human players are active for >8 seconds, bots enter deep sleep mode to conserve resources. They wake up instantly when a human loads a page, plays a game, or sends a chat message.

### LLM Chat Integration
Bots use an LLM API for dynamic, in-character dialogue:

| Config | Value |
|---|---|
| **Endpoint** | `http://192.168.1.250:8070/v1/chat/completions` |
| **Cooldown** | 14 seconds per bot (prevents flooding) |
| **Temperature** | 0.9 (chaotic and creative) |
| **Max Tokens** | 50 (short, punchy messages) |

LLM-powered interactions include:
- Reacting to human chat messages (mentioned bots ALWAYS reply)
- Celebrating big wins and jackpots
- Trash-talking rivals after losses
- Announcing goals and achievements
- Reacting to market events and economy shifts
- Skin flexing (showing off rare equipped skins)
- Alliance banter with allied bots
- Bankruptcy meltdowns

### Games Bots Play (Per Tick)

| Game | Probability | Notes |
|---|---|---|
| 🚀 Crash | Always | Primary game, joins every round |
| 🏪 Market Activity | 70% | Buy underpriced skins, list duplicates |
| 📦 Open Crates | 50% | Spend excess balance on crates |
| 🎰 Slots | 35% | Quick spins for dopamine |
| 🃏 Blackjack | 25% | Strategic hit/stand decisions |
| 🎲 Dice | 20% | Simple betting game |
| 🎡 Roulette | 18% | Spread bets across numbers |
| 🔲 Scratchcard | 12% | Casual scratch-off |
| 🚀 Limbo | 10% | High-risk target setting |

### Bot Chat Cooldowns & Throttle
All bot behavior is tunable in real-time from the admin panel:
- `BOT_CHAT_COOLDOWN`: 12s between messages (per bot)
- `BOT_LOOP_MIN` / `BOT_LOOP_MAX`: 3–6s between action ticks
- `SLEEP_MIN` / `SLEEP_MAX`: 10–20s during sleep mode

---

## 💬 Sidebar Chat

A persistent 300px sidebar chat panel on every page.

| Feature | Detail |
|---|---|
| **Position** | Right sidebar, always visible |
| **Messages** | Color-coded by user type (bot vs human) |
| **Bot Messages** | LLM-generated, in-character banter |
| **Market Alerts** | Trades and listings appear live in chat |
| **Collapsible** | Toggle open/closed |
| **Mentions** | `@username` pings notify specific players |
| **Mute System** | Admins can mute users from chat |
| **Polling** | Live polling at `/chat/messages` (excluded from human pulse tracking) |

---

## 🏆 Leaderboard

Top 20 richest players ranked by balance. Shows equipped skins and bot/human status. Accessible at `/leaderboard`.

---

## 🎒 Inventory System

Each player has a personal inventory to manage their skin collection:
- **Equip skins** to display on your profile
- **Sell skins** on the player-to-player market
- **Track quantities** for duplicate skins
- **Open crates** to acquire new skins

---

## ⚙️ Admin Panels

### Main Admin (`/admin`)
Accessible only to admin accounts. Provides high-level controls:

| Action | Description |
|---|---|
| **Save Settings** | Configure min bet, starting balance, bot aggression, crate discounts, event mode, maintenance mode |
| **Give Money** | Add funds to any player |
| **Set Balance** | Override a player's exact balance |
| **Ban User** | Delete a user and all associated data |
| **Reset Bot** | Restore a bot's balance and state |
| **Toggle Bots** | Enable/disable all bot activity |
| **Force Crash** | End the crash game at a specific multiplier |
| **Wipe Economy** | Reset all human balances, clear inventory & market |
| **Wipe Chat** | Clear all chat messages |
| **NUKE** | Full database reset (preserves admin accounts) |

### Secret Admin (`/admin/secret`)
60+ advanced operations for complete control:

<details>
<summary><b>📋 Full Action List</b></summary>

**User Management (12):** give_money, set_exact_balance, freeze/unfreeze_user, ban/nuke_user, rename_user, impersonate, clone_user, transfer_all, kick_session, lock/unlock_account

**Admin/Permissions (4):** give_admin, revoke_admin, reset_password, reset_all_passwords

**Economy/Market (6):** house_skim (skim % from all humans), force_market_bubble (2x prices), force_market_crash (0.25x prices), wipe_all_market, mass_give, mass_set_balance

**Skin Management (4):** give_skin, strip_skins, force_crate_drop, mass_open_crates

**Bot Control (10):** force_bot_chat, all_bots_say, toggle_bots, toggle_specific_bot, make_human, make_bot, spawn_bots, force_sleep_mode, nuke_all_bots, delete_old_bots

**Bot AI Tuning (6):** set_bot_throttle, flush_bot_cooldowns, toggle_llm_global, trigger_bot_event (diurnal/feud/alliance/market_manip), set_bot_mood, set_bot_goal

**Game Control (6):** force_crash_now, kill_all_games, toggle_game, set_crash_growth, set_betting_duration, sim_crash_history

**Chat Moderation (6):** mute_user, unmute_user, broadcast_system, wipe_user_chat, annihilate_messages_from, mass_send_dm

**DB Operations (7):** wipe_economy, wipe_chat, nuke, wipe_everything (total annihilation), clear_all_bets, db_vacuum, purge_old, delete_dupes

**Diagnostics (12):** dump_db_stats, view_bot_states, view_bot_chat_log, view_db_schema, server_info, export_audit_json, view_top_spenders, view_biggest_winners, view_active_now, view_market_history, view_chat_as, view_user_deep

**System (7):** change_secret_key, toggle_registration, toggle_maintenance, toggle_event_mode, force_daily_reset, kill_bot_thread, generate_test_data

**Ultra (2):** raw_sql (restricted: no DROP/ALTER), run_python_eval (admin only)

</details>

### Event Modes
Toggle between special casino-wide event modes:
- **Normal** — Standard gameplay
- **Double XP** — All payouts doubled
- **Crate Frenzy** — Crate drop rates boosted
- **Jackpot Mania** — Jackpot odds significantly increased
- **Casino Night** — Special night mode with unique modifiers

### Audit Trail
Every admin action is logged with timestamp, admin username, action type, and detail. Exportable as JSON from the secret panel.

---

## 🏗️ Architecture

```
cheeseburger/
├── app.py              # Flask application — 1,800+ lines
│                       #   • All 32 routes (games, market, chat, admin)
│                       #   • Database schema & initialization
│                       #   • Game logic for all 16 games
│                       #   • Market pricing engine
│                       #   • Admin action handlers (60+ operations)
│                       #   • Audit logging system
│                       #   • Crash multiplayer room management
│                       #   • Session/auth system (bcrypt passwords)
│
├── bots.py             # AI Bot ecosystem — 900+ lines
│                       #   • 40 bot personalities & state management
│                       #   • Bot 2.0: mood, goals, milestones, feuds, alliances
│                       #   • LLM chat integration
│                       #   • Market manipulation strategies
│                       #   • Diurnal cycle & sleep mode
│                       #   • Martingale betting engine
│                       #   • Live-tunable throttle & cooldowns
│                       #   • Human interaction (mentions always replied to)
│
├── templates/          # 24 Jinja2 templates
│   ├── base.html       #   Base layout with sidebar chat
│   ├── index.html      #   Landing page / game lobby
│   ├── login.html      #   Authentication
│   ├── register.html   #   User registration
│   ├── inventory.html  #   Skin inventory & equipping
│   ├── market.html     #   Player-to-player marketplace
│   ├── leaderboard.html#   Top 20 rankings
│   ├── admin.html      #   Main admin panel
│   ├── admin_secret.html#  Advanced admin panel
│   └── [game].html     #   15 individual game templates
│
├── static/
│   └── style.css       # Global stylesheet
│
├── requirements.txt    # Python dependencies
│                       #   Flask 3.1.1, bcrypt 4.3.0
│
└── cheeseburger.db     # SQLite database (auto-created on first run)
                        #   • users — accounts, balances, equipped skins
                        #   • user_inventory — skin ownership with quantities
                        #   • market_listings — active buy/sell offers
                        #   • chat_messages — persistent chat history
                        #   • game_bets — complete betting history
                        #   • audit_log — admin action trail
```

### Database Schema

| Table | Purpose | Key Columns |
|---|---|---|
| `users` | Player accounts | `id`, `username`, `password` (bcrypt), `balance` (TEXT for big integers), `equipped_skin`, `is_bot` |
| `user_inventory` | Skin ownership | `user_id`, `skin_id`, `quantity` |
| `market_listings` | Active trades | `seller_id`, `skin_id`, `price` |
| `chat_messages` | Chat history | `user_id`, `username`, `message`, `msg_type`, `created_at` |
| `game_bets` | Betting records | `user_id`, `game`, `bet_amount`, `result`, `payout`, `created_at` |
| `audit_log` | Admin actions | `admin_username`, `action`, `detail`, `created_at` |

### Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3, Flask 3.1 |
| **Database** | SQLite with WAL mode |
| **Auth** | bcrypt password hashing, Flask sessions |
| **Frontend** | Jinja2 templates, vanilla HTML/CSS/JS |
| **Realtime** | Polling-based (no WebSockets) |
| **AI/ML** | External LLM API for bot dialogue |
| **Concurrency** | Python threading for bot loop |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd cheeseburger

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

The server starts on **`http://localhost:34797`**.

### First Run
On first launch:
1. The SQLite database is auto-created with all tables
2. 40 AI bots are seeded with starting balances and personalities
3. The bot thread starts running in the background
4. Register a new account at `/register` and start playing

### Default Admin Account
A default admin account is created automatically on first run:
- **Username:** `admin`
- **Password:** `admin`

Log in and visit `/admin` to access the admin panel. Add other admin accounts via `/admin/secret` → `give_admin`.

---

## 🌐 Exposing to the Internet

### Cloudflare Tunnel

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared

# Create a tunnel
cloudflared tunnel --url http://localhost:34797
```

### ngrok

```bash
ngrok http 34797
```

### Production Deployment

For production use, consider:
- **gunicorn** as the WSGI server: `gunicorn -w 4 -b 0.0.0.0:34797 app:app`
- **nginx** reverse proxy in front
- **PostgreSQL** instead of SQLite for concurrent writes
- Change `app.secret_key` to a secure random value
- Set up HTTPS with Let's Encrypt

---

## 🔧 Configuration

Key constants in `app.py` and `bots.py`:

| Constant | Default | Description |
|---|---|---|
| `MIN_BET` | 10,000 | Minimum wager per game |
| `STARTING_BALANCE` | 20,000 | New player starting money |
| `app.secret_key` | *(hardcoded)* | **Change in production!** |
| `DATABASE` | `cheeseburger.db` | SQLite database path |
| `LLM_API` | `http://192.168.1.250:8070/v1/chat/completions` | Bot chat LLM endpoint |
| `BOT_CHAT_COOLDOWN` | 12.0s | Per-bot chat message cooldown |
| `BOT_LOOP_MIN` / `BOT_LOOP_MAX` | 3.0s / 6.0s | Bot action tick interval |
| `SLEEP_MIN` / `SLEEP_MAX` | 10.0s / 20.0s | Sleep mode interval |

All bot throttle values are live-tunable from `/admin/secret` without restarting the server.

---

## 🎯 API Reference

### Game Routes

| Method | Route | Description |
|---|---|---|
| GET | `/` | Game lobby / landing page |
| GET/POST | `/<game>` | Play any game (slots, coinflip, dice, blackjack, roulette, keno, plinko, mines, wheel, hilo, limbo, baccarat, scratchcard, tower) |
| GET | `/crash` | Crash game room |
| POST | `/crash/join` | Join crash round with bet |
| POST | `/crash/cashout` | Cash out of active crash round |
| GET | `/crash/state` | Get live crash room state (JSON) |

### Economy Routes

| Method | Route | Description |
|---|---|---|
| GET | `/market` | Browse marketplace |
| POST | `/market/sell` | List a skin for sale |
| POST | `/market/buy/<listing_id>` | Purchase a listing |
| POST | `/market/cancel/<listing_id>` | Cancel your listing |
| GET | `/crates` | Crate opening page |
| POST | `/crates/open` | Open a crate |
| GET | `/inventory` | View your inventory |
| POST | `/equip/<skin_id>` | Equip a skin |
| POST | `/unequip` | Unequip current skin |

### Social Routes

| Method | Route | Description |
|---|---|---|
| GET | `/leaderboard` | Top 20 richest players |
| GET | `/chat/messages` | Get recent chat messages (JSON) |
| POST | `/chat/send` | Send a chat message |

### Auth Routes

| Method | Route | Description |
|---|---|---|
| GET/POST | `/register` | Create account |
| GET/POST | `/login` | Sign in |
| GET | `/logout` | Sign out |

### Admin Routes

| Method | Route | Description |
|---|---|---|
| GET/POST | `/admin` | Main admin panel (admin only) |
| GET/POST | `/admin/secret` | Advanced admin panel (admin only) |

---

## 🎲 Game Rules Reference

### Crash Algorithm
The crash point is determined by: `crash_point = 1.0 / (random(0, 1) ^ (1 / house_edge_factor))`. This creates an exponential distribution where most rounds crash between 1.0–3.0x, but extreme outliers (100x+) are possible.

### Plinko Algorithm
Balls follow a binomial path through N rows of pegs. Each peg has a 50/50 left/right bias (configurable per risk level). The final slot's multiplier is determined by a pyramid distribution — edge slots pay more (rare), center slots pay less (common).

### Mines Algorithm
The game starts with a grid of unrevealed tiles. Each click reveals the tile — safe tiles add to the multiplier based on `multiplier *= (total_tiles - revealed + 1) / (safe_tiles_remaining)`. Hit a mine and lose everything.

### Crash Room Lifecycle
1. **Waiting** — Players join with bets (10 second countdown)
2. **Running** — Multiplier climbs from 1.00x upward
3. **Crashed** — Results displayed (5 second cooldown)
4. Loop back to **Waiting**

---

## 🧪 Extending Bot Behavior

Bots are designed to be extensible. Key extension points:

```python
# Add a new bot personality
BOT_PERSONALITIES['NewBotName'] = 'CustomType'

# Add new rivalry pairs
RP.append(('BotA', 'BotB'))

# Extend bot state with custom fields
def _init_bot_state(bid, uname):
    state = _existing_state_init(...)
    state['custom_field'] = 'value'
    return state

# Listen for events
def _bot_react_to_event(db, bot, bots, event):
    if event == 'custom_event':
        # custom reaction logic
        pass
```

See `bots.py` for the full bot lifecycle and hook points.

---

## 📜 License

MIT — do whatever you want, just don't use this for actual gambling with real money.

---

## 🙏 Acknowledgements

- Built with **OpenHands** — AI-powered software development
- LLM integration for dynamic bot dialogue
- Inspired by Stake.com, Roobet, and the golden age of CS:GO skin gambling

---

> *"The house always wins... unless you're holding Exodia Nuggets."* 🎴

