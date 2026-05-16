# 🍔 Cheeseburger Casino

A fake gambling web app built with **Flask**, **SQLite**, and **HTML/CSS/JS** — using **OpenHands** and **DeepSeek V4 Flash**.

## Games

| Game | Description | Payout |
|---|---|---|
| 🎰 **Slots** | Match 2 or 3 symbols across 3 reels with spin animation | Up to 10x |
| 🪙 **Coin Flip** | Pick heads or tails, watch the coin flip | 2x |
| 🎲 **Dice** | Guess the sum of two dice (2–12) | 6x |
| 🃏 **Blackjack** | Classic blackjack with hit/stand, dealer hits on <17 | 1.5x on blackjack |

## Features

- User accounts with **bcrypt** password hashing
- Starting balance of **$500**
- Balance tracked in **SQLite**
- Animated slot reels, coin flips, dice rolls, and card dealing
- Dark casino-themed UI with gold/neon accents

## Run Locally

```bash
pip install -r requirements.txt
python app.py
```

Opens on `http://localhost:34797`.

