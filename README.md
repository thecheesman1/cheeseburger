# 🍔 Cheeseburger Casino

High-stakes multiplayer casino — Crash, Slots, Coin Flip, Dice, Blackjack, Crates, Skin Market & Leaderboard.

Built with **Flask**, **SQLite**, and **HTML/CSS/JS** — using **OpenHands**.

## Games

| Game | Description | Payout |
|---|---|---|
| 🚀 **Crash** | Multiplayer — bet with others, cash out before it crashes | Variable |
| 🎰 **Slots** | Match 2 or 3 symbols across 3 reels with spin animation | Up to 10x |
| 🪙 **Coin Flip** | Pick heads or tails, watch the coin flip | 2x |
| 🎲 **Dice** | Guess the sum of two dice (2–12) | 6x |
| 🃏 **Blackjack** | Classic blackjack with hit/stand, dealer hits on <17 | 1.5x on BJ |

## Economy

- **💰 Min bet:** $10,000 | **Starting balance:** $20,000
- **📦 Crates** — Standard ($8K), Premium ($25K), Legendary ($100K) — 20 unique skins, 5 rarities
- **🏪 Player-to-Player Market** — Buy/sell skins, prices driven by supply/demand
- **🔄 Dynamic Pricing** — Skin prices fluctuate based on inventory supply

## Features

- **🤖 10 AI Bots** — Play crash, open crates, trade on market. Smart cashout strategies.
- **🏆 Leaderboard** — Top 20 richest players
- **🎒 Inventory** — Collect skins, equip them, sell on market
- **⚙️ Admin Panel** — `/admin` (esadsa only) — change settings, give money, manage bots, wipe economy

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

