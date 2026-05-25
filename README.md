# 🍔 Cheeseburger Casino

High-stakes multiplayer casino — Crash, Slots, Coin Flip, Dice, Blackjack, Crates, Skin Market & Leaderboard.

Built with **Flask**, **SQLite**, and **HTML/CSS/JS** — using **OpenHands**.

## Games

| Game | Description | Payout |
|---|---|---|
| 🚀 **Crash** | Multiplayer — bet with others, cash out before it crashes. Bots join live | Variable |
| 🎰 **Slots** | Match 2 or 3 symbols across 3 reels with spin animation | Up to 10x |
| 🪙 **Coin Flip** | Pick heads or tails, watch the coin flip | 2x |
| 🎲 **Dice** | Guess the sum of two dice (2–12) | 6x |
| 🃏 **Blackjack** | Classic blackjack with hit/stand, dealer hits on <17 | 1.5x on BJ |

## Economy

- **💰 Min bet:** $10,000 | **Starting balance:** $20,000
- **📦 Crates** — Standard ($8K), Premium ($25K), Legendary ($100K) — **50 unique skins** across 5 rarities
- **🏪 Player-to-Player Market** — Buy/sell skins, dynamic pricing engine
- **🔄 Dynamic Pricing** — Prices fluctuate on 5 forces: rarity floor, supply scarcity, rotating trend cycles (every 5 min), sales velocity, and noise jitter

## Skins (50 total)

| Rarity | Count | Price Range | Examples |
|---|---|---|---|
| ⚪ Common | 10 | $700 – $1,500 | Rusty Burger, Ketchup Packet, Soggy Bun |
| 🟢 Uncommon | 9 | $4,500 – $7,000 | Silver Spatula, Glazed Donut Burger, Chrome Tray |
| 🔵 Rare | 8 | $15,000 – $23,000 | Ruby Shake, Emerald Burger, Jade Spatula |
| 🟣 Epic | 8 | $50,000 – $75,000 | Diamond Burger, Inferno Burger, Void Shake |
| 🟡 Legendary | 15 | $200,000 – $800,000 | Cheeseburger Supreme, Exodia Nuggets, Eternal Shake |

## Features

- **🤖 10 AI Bots** — Play crash, slots, blackjack, open crates, trade on market. Personality archetypes (Whale, Grinder, Degenerate, Merchant, SystemPlayer) with distinct strategies. Martingale, bailout loans, diurnal cycle, dynamic mood system
- **💬 Sidebar Chat** — Persistent 300px panel on every page. Bots trashtalk wins/losses, market trades appear live. Color-coded usernames, collapsible
- **🏆 Leaderboard** — Top 20 richest players
- **🎒 Inventory** — Collect skins, equip them, sell on market
- **⚙️ Admin Panel** — `/admin` (esadsa only) — change settings, give money, manage bots, wipe economy, view analytics

## Architecture

```
app.py          — Flask routes, DB schema, game logic
bots.py         — 10 AI bot personalities, trading, gambling, chat (extracted module)
templates/      — Jinja2 templates (base.html with sidebar chat)
static/         — CSS
cheeseburger.db — SQLite database (auto-created)
```

See `bots.py` header docs for how to extend bot behavior.

## Run Locally

```bash
pip install -r requirements.txt
python app.py
```

Opens on `http://localhost:34797`.

## Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:34797
```

