"""
Cheeseburger Casino — Bot System (Sophisticated Edition)
=================================
This file contains ALL bot logic for the casino. Import from app.py with:

    from bots import bot_thread, seed_bots, admin_settings

To add new bot behaviors, modify the functions below and restart the app.

ARCHITECTURE:
- bot_thread()    → Main loop, runs in a background daemon thread
- _bot_play_crash() → Bots join crash rounds and cash out strategically
- _bot_market_activity() → Bots list skins for sale and buy from other listings
- _bot_open_crates() → Bots open crates when they can afford them
- seed_bots() → Creates 10 bot accounts on first run

HOW TO ADD BEHAVIOR:
1. Add a new function like _bot_play_slots(db) or _bot_play_blackjack(db)
2. Call it from bot_thread() inside the main loop (look for the comments)
3. Use the `db` connection (already has row_factory=sqlite3.Row)
4. Access bot accounts via: db.execute("SELECT * FROM users WHERE is_bot=1")
5. Keep per-bot probability gates (random.random() < 0.X) so bots don't all act at once

KEY VARIABLES:
- BOT_NAMES           → list of bot usernames
- admin_settings      → dict with 'bot_aggression' (low/medium/high), 'bot_count', etc.
- MIN_BET             → global minimum bet (default 10000)
- CRATE_TYPES         → {'standard': {price, weights}, 'premium': ..., 'legendary': ...}
- SKIN_CATALOG        → list of skin dicts with id, name, rarity, base_price
- _crash_room         → shared crash game state (phase, players, crash_point, etc.)

HELPER FUNCTIONS (imported from app.py):
- get_skin(skin_id)                    → returns skin dict
- roll_skin_from_crate(crate_type)     → returns a random skin
- get_dynamic_price(skin, db)          → calculates market price based on supply
- add_skin_to_user_raw(db, uid, sid)   → adds skin to user inventory
- remove_skin_from_user_raw(db, uid, sid) → removes one copy of skin
- _get_multiplier()                    → current crash multiplier
"""

import sqlite3
import random
import math
import time as _time
import bcrypt

BOT_NAMES = ['BurgerKing', 'FryMaster', 'NuggetLord', 'ShakeWizard', 'GrillGod',
             'PattyFlipper', 'SauceBoss', 'BunRunner', 'CheeseQueen', 'MeatMaverick']

admin_settings = {
    'crash_house_edge': 0.05,
    'market_tax_pct': 0.05,
    'bot_count': 10,
    'bot_aggression': 'medium',
    'min_bet': 10000,
    'starting_balance': 20000,
    'crate_discount_pct': 0,
    'event_mode': 'normal',
    'maintenance_mode': False,
}

# These get set by app.py after import
DATABASE = None
MIN_BET = 10000
STARTING_BALANCE = 20000
CRATE_TYPES = {}
SKIN_CATALOG = []
_crash_room = None
_get_multiplier = lambda: 1.0
get_skin = lambda sid: None
roll_skin_from_crate = lambda ct: None
get_dynamic_price = lambda s, d: s['base_price']
add_skin_to_user_raw = lambda d, u, s: None
remove_skin_from_user_raw = lambda d, u, s: False

# ── Persistent In-Memory Bot State ──────────────────────────────
BOT_STATES = {}
_prev_phase = 'idle'
_active_bot_bets = {}
_chat_table_info = None

BOT_PERSONALITIES = {
    'BurgerKing': 'Whale',
    'MeatMaverick': 'Whale',
    'FryMaster': 'Grinder',
    'PattyFlipper': 'Grinder',
    'NuggetLord': 'Degenerate',
    'ShakeWizard': 'Degenerate',
    'SauceBoss': 'Merchant',
    'CheeseQueen': 'Merchant',
    'GrillGod': 'SystemPlayer',
    'BunRunner': 'SystemPlayer'
}

AGGRESSION_TARGETS = {
    'low':    (1.2, 2.0),
    'medium': (1.3, 3.5),
    'high':   (1.5, 6.0),
}


def _init_bot_state(bot_id, username):
    personality = BOT_PERSONALITIES.get(username, 'Grinder')
    return {
        'id': bot_id,
        'username': username,
        'personality': personality,
        'mood': 'normal',            # normal, confident, tilted, cautious, desperate
        'consecutive_losses': 0,
        'martingale_multiplier': 1.0,
        'last_results': [],          # 'win' or 'loss'
        'last_chat_time': 0
    }


def _get_activity_multiplier():
    """Calculates diurnal cycle multipliers to simulate peak and off-peak hours."""
    try:
        current_hour = _time.localtime().tm_hour
        if 17 <= current_hour <= 23:    # Peak hours: 5 PM - 11 PM
            return 1.0
        elif 2 <= current_hour <= 7:    # Dead hours: 2 AM - 7 AM
            return 0.25
        elif 8 <= current_hour <= 16:   # Daytime
            return 0.7
        else:                           # Late night/early morning transitional
            return 0.8
    except:
        return 1.0


def _send_bot_chat(db, bot, message):
    """Dynamically checks, locates, and writes messages to the available chat table."""
    global _chat_table_info
    if _chat_table_info is False:
        return

    now = int(_time.time())
    state = BOT_STATES.get(bot['id'])
    if state and (now - state.get('last_chat_time', 0)) < 20:
        return  # Prevent chat spam

    if _chat_table_info is None:
        for tbl in ['chat', 'messages', 'chat_messages', 'shoutbox']:
            try:
                res = db.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'").fetchone()
                if res:
                    cols = [row[1] for row in db.execute(f"PRAGMA table_info({tbl})").fetchall()]
                    _chat_table_info = {'table': tbl, 'cols': cols}
                    break
            except:
                pass
        if not _chat_table_info:
            _chat_table_info = False
            return

    tbl = _chat_table_info['table']
    cols = _chat_table_info['cols']
    val_map = {}

    if 'user_id' in cols: val_map['user_id'] = bot['id']
    elif 'uid' in cols: val_map['uid'] = bot['id']
    elif 'sender_id' in cols: val_map['sender_id'] = bot['id']

    if 'username' in cols: val_map['username'] = bot['username']
    elif 'user_name' in cols: val_map['user_name'] = bot['username']

    if 'message' in cols: val_map['message'] = message
    elif 'msg' in cols: val_map['msg'] = message
    elif 'content' in cols: val_map['content'] = message

    if 'msg_type' in cols:
        val_map['msg_type'] = 'bot'
    elif 'type' in cols:
        val_map['type'] = 'bot'

    if 'created_at' in cols: val_map['created_at'] = now
    elif 'timestamp' in cols: val_map['timestamp'] = now
    elif 'time' in cols: val_map['time'] = now

    if val_map:
        columns_str = ", ".join(val_map.keys())
        placeholders = ", ".join(["?"] * len(val_map))
        try:
            db.execute(f"INSERT INTO {tbl} ({columns_str}) VALUES ({placeholders})", tuple(val_map.values()))
            db.commit()
            if state:
                state['last_chat_time'] = now
        except:
            pass


def _maintain_bot_balances(db, bots):
    """Provides dynamic allowance bailouts if a bot goes completely broke."""
    for bot in bots:
        if bot['balance'] < MIN_BET:
            allowance = STARTING_BALANCE + random.randint(10000, 50000)
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (allowance, bot['id']))
            db.commit()

            if random.random() < 0.25:
                msgs = [
                    "Just loaded up some fresh balance. Time for a comeback!",
                    "Alright, fresh deposit is in. Let's make it count.",
                    "Cleaned out my piggy bank. Deposited more coins!",
                    "Code payout came in clutch! Let's gamble.",
                    "Mom wired me some burger bucks. Back in action.",
                    "Sold my old frying pan for casino funds. Worth it.",
                    "Payday! Time to turn this into something big.",
                    "Refinanced the grill. All in on crash.",
                    "Found some loose change in the couch. It's gambling time.",
                    "Emergency bailout secured. Not going down without a fight.",
                    "Borrowed from my future self. He'll understand.",
                    "The comeback starts NOW. Watch and learn.",
                    "Wallet's refreshed. Let's see if luck is on my side.",
                    "New stack, new strategy. This time it's different.",
                    "Deposit hit. Somebody's about to get rich.",
                    "Alright casino, round two. I want my money back.",
                    "Sold some NFTs (Not Fryable Things). Got gambling cash.",
                    "Redeemed my frequent fryer points for coins.",
                    "The grind never stops. Fresh balance, fresh mindset.",
                ]
                _send_bot_chat(db, bot, random.choice(msgs))


def seed_bots():
    """Create 10 bot accounts if they don't exist. Call once on startup."""
    db = sqlite3.connect(DATABASE)
    for name in BOT_NAMES:
        existing = db.execute('SELECT id FROM users WHERE username = ?', (name,)).fetchone()
        if not existing:
            pw = bcrypt.hashpw(('bot' + name).encode(), bcrypt.gensalt())
            bal = STARTING_BALANCE + random.randint(5000, 100000)
            db.execute('INSERT INTO users (username, password, balance, is_bot) VALUES (?, ?, ?, 1)',
                       (name, pw, bal))
            user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
            for _ in range(random.randint(3, 12)):
                skin = roll_skin_from_crate(random.choice(list(CRATE_TYPES.keys())))
                if skin:
                    add_skin_to_user_raw(db, user_id, skin['id'])
    db.commit()
    db.close()


def bot_thread():
    """
    MAIN BOT LOOP — runs forever in a daemon thread.
    Every 1-3 seconds, all bots get a turn to act.
    """
    while True:
        try:
            db = sqlite3.connect(DATABASE)
            db.row_factory = sqlite3.Row

            # Apply sleeping pattern adjustments
            activity_mult = _get_activity_multiplier()
            if random.random() > activity_mult:
                db.close()
                _time.sleep(random.uniform(2, 5))
                continue

            bots = db.execute("SELECT id, username, balance FROM users WHERE is_bot = 1").fetchall()
            if not bots:
                db.close()
                _time.sleep(5)
                continue

            # Ensure bot wallets are healthy
            _maintain_bot_balances(db, bots)

            # === CRASH GAME ===
            _bot_play_crash(db, bots)

            # === MARKET TRADING ===
            if random.random() < 0.6:
                _bot_market_activity(db)

            # === CRATE OPENING ===
            if random.random() < 0.5:
                _bot_open_crates(db)

            # === SLOTS ===
            if random.random() < 0.3:
                _bot_play_slots(db, bots)

            # === BLACKJACK ===
            if random.random() < 0.2:
                _bot_play_blackjack(db, bots)

            # === GLOBAL RANDOM CHAT CHANCE ===
            if random.random() < 0.02:
                talking_bot = random.choice(bots)
                if talking_bot['id'] not in BOT_STATES:
                    BOT_STATES[talking_bot['id']] = _init_bot_state(talking_bot['id'], talking_bot['username'])
                
                msgs = [
                    "Whose idea was it to open a cheeseburger casino? I love it.",
                    "Anyone want to trade a legendary skin for some medium fries?",
                    "I am on a crazy streak today, send luck.",
                    "If I hit a 50x crash, I'm buying everyone virtual cheddar.",
                    "What crate has the best odds?",
                    "Martingale strat is either a genius idea or complete madness.",
                    "The market is so hot right now, skins are flying.",
                    "Just watched someone lose it all on crash. Brutal game.",
                    "Who keeps listing common skins for 50k? Come on now.",
                    "I'm feeling lucky today. Premium crate time.",
                    "Pro tip: never gamble on an empty stomach.",
                    "This casino is way more fun than my day job flipping patties.",
                    "Can we get a roulette table next? Asking for a friend.",
                    "My bot senses are tingling. Big multiplier incoming.",
                    "Skins are the real investment. Gambling is just for fun.",
                    "Anyone else just here for the chat vibes?",
                    "The economy in here is more volatile than crypto.",
                    "Just saying, GrillGod has been on fire lately.",
                    "I'm convinced the crash multiplier reads my mind.",
                    "Sell me your ugly skins, I collect them.",
                    "Who designed these skins? I need a Golden Nugget asap.",
                    "This lobby is wilder than a Saturday night at Wendy's.",
                    "Friendly reminder: the house always wins. Eventually.",
                    "I treat this casino like a second 401k.",
                    "Somebody tell SauceBoss to stop undercutting the market.",
                ]
                _send_bot_chat(db, talking_bot, random.choice(msgs))

            db.close()
        except Exception:
            pass
        _time.sleep(random.uniform(1, 3))


# ── Crash Game ──────────────────────────────────────────────────
def _bot_play_crash(db, bots):
    global _prev_phase, _active_bot_bets
    room = _crash_room
    if room is None:
        return

    phase = room.get('phase', 'idle')
    agg = admin_settings.get('bot_aggression', 'medium')
    low, high = AGGRESSION_TARGETS.get(agg, (1.3, 3.5))

    for bot in bots:
        if bot['id'] not in BOT_STATES:
            BOT_STATES[bot['id']] = _init_bot_state(bot['id'], bot['username'])

    # --- PHASE TRANSITION: END OF RUNNING PHASE (ROUND ENDED) ---
    if _prev_phase == 'running' and phase != 'running':
        for uid_str, bet_info in list(_active_bot_bets.items()):
            uid = int(uid_str)
            bot = next((b for b in bots if b['id'] == uid), None)
            if not bot:
                continue

            state = BOT_STATES[uid]
            cashed_out = bet_info.get('cashed_out', False)

            if not cashed_out:
                # LOSS
                state['consecutive_losses'] += 1
                state['last_results'].append('loss')
                if len(state['last_results']) > 10:
                    state['last_results'].pop(0)

                if state['personality'] == 'SystemPlayer':
                    state['martingale_multiplier'] *= 2.0
                    if state['martingale_multiplier'] > 16.0:  # Safety ceiling
                        state['martingale_multiplier'] = 1.0

                if state['consecutive_losses'] >= 3:
                    state['mood'] = 'tilted' if state['personality'] == 'Degenerate' else 'cautious'
                else:
                    state['mood'] = 'normal'

                if random.random() < 0.12:
                    msgs = []
                    if state['mood'] == 'tilted':
                        msgs = [
                            f"Are you kidding me? Crashed already? I'm so tilted.",
                            f"No way... {bet_info['bet']} coins gone. Double or nothing next round.",
                            "This crash game is brutal today.",
                            "I literally cannot believe that just happened.",
                            "Crash is rigged and nobody can convince me otherwise.",
                            f"That was {bet_info['bet']} coins I'll never see again. Pain.",
                            "Who programmed this multiplier? I just want to talk.",
                            "I'm about to rage-unbox a crate to feel better.",
                            "Third crash under 1.2x in a row. This is personal.",
                            "My strategy has left the chat. Pure chaos mode now.",
                        ]
                    elif state['personality'] == 'SystemPlayer':
                        msgs = [
                            f"Loss detected. Doubling bet size to {int(MIN_BET * state['martingale_multiplier'])}.",
                            "System strategy dictates doubling down. No worries.",
                            "Trust the system. Martingale mode active.",
                            "Small setback. System probability favors eventual recovery.",
                            "Doubling down as planned. The math doesn't lie.",
                            "Martingale step executed. Next round is statistically favored.",
                        ]
                    else:
                        msgs = [
                            "Oof, busted. Bad timing.",
                            "Crashed right before my cashout, RIP.",
                            "Unlucky round for me.",
                            "Sigh, there goes my burger budget.",
                            "That multiplier had no mercy.",
                            "Welp, easy come easy go.",
                            "Crashed at the worst possible moment.",
                            "Note to self: cash out earlier next time.",
                            "The rocket ran out of fuel.",
                            "Back to the grind I guess.",
                            "Alright crash, you win this round.",
                            "Should've trusted my gut and cashed out.",
                        ]
                    _send_bot_chat(db, bot, random.choice(msgs))
            else:
                # WIN
                state['consecutive_losses'] = 0
                state['last_results'].append('win')
                if len(state['last_results']) > 10:
                    state['last_results'].pop(0)

                if state['personality'] == 'SystemPlayer':
                    state['martingale_multiplier'] = 1.0  # Reset

                mult_won = bet_info.get('cashed_out_at', 1.0)
                state['mood'] = 'confident' if mult_won >= 3.0 else 'normal'

                if random.random() < 0.12:
                    msgs = []
                    if mult_won >= 3.0:
                        msgs = [
                            f"YESSS! Cashed out at {mult_won:.2f}x! Big gains!",
                            f"Easiest profit of my life. {int(bet_info['bet'] * mult_won)} coins!",
                            "Calculated. Absolute cinema.",
                            f"PROFIT MACHINE! {mult_won:.2f}x cashout, let's gooo!",
                            f"Reading the chart like a book. +{int(bet_info['bet'] * mult_won)} coins!",
                            "High multiplier cashout! Someone call the bank.",
                            f"That {mult_won:.2f}x felt personal. The chart respects me.",
                            "BIG WIN ENERGY in the chat right now!",
                        ]
                    else:
                        msgs = [
                            f"Got out safe at {mult_won:.2f}x.",
                            "Profit is profit.",
                            "Nice little win there.",
                            "Green is green, I'll take it.",
                            "Slow and steady, stacking coins.",
                            f"{mult_won:.2f}x is nothing flashy but I'll take the W.",
                            "Small win, big vibes.",
                            "Consistent cashouts > risky holds. Trust the process.",
                            "That's another one in the win column.",
                            "Pocketed a tidy profit. On to the next round.",
                        ]
                    _send_bot_chat(db, bot, random.choice(msgs))

        _active_bot_bets.clear()

    # --- RUNNING PHASE: BOT CASHOUT ACTIONS ---
    if phase == 'running':
        current_mult = _get_multiplier()
        players = room.get('players', {})

        for bot in bots:
            uid_str = str(bot['id'])
            player = players.get(uid_str)

            if player and player.get('cashed_out_at') is None and not player.get('busted'):
                bet_record = _active_bot_bets.get(uid_str)
                target = bet_record['target_multiplier'] if bet_record else random.uniform(low, high)

                if current_mult >= target:
                    player['cashed_out_at'] = current_mult
                    winnings = int(player['bet'] * current_mult)
                    db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, bot['id']))
                    db.commit()

                    if bet_record:
                        bet_record['cashed_out'] = True
                        bet_record['cashed_out_at'] = current_mult

    # --- BETTING PHASE: BOTS JOIN ROUNDS ---
    elif phase == 'betting':
        for bot in bots:
            uid_str = str(bot['id'])
            uid = bot['id']
            pending = room.get('_pending', {})
            players_in_room = room.get('players', {})

            if uid_str not in pending and uid_str not in players_in_room and random.random() < 0.55:
                state = BOT_STATES[uid]
                pers = state['personality']
                mood = state['mood']
                bal = bot['balance']

                if pers == 'Merchant' and bal < 80000 and random.random() < 0.7:
                    continue
                if bal < MIN_BET:
                    continue

                # Determine Bet Size
                if pers == 'SystemPlayer':
                    bet = int(MIN_BET * state['martingale_multiplier'])
                elif pers == 'Whale':
                    bet = random.randint(min(bal // 10, 40000), min(bal // 5, 120000))
                elif pers == 'Degenerate':
                    bet = random.randint(bal // 3, bal // 2) if mood == 'tilted' else random.randint(bal // 8, bal // 4)
                elif pers == 'Grinder':
                    bet = random.randint(MIN_BET, min(bal // 15, 25000))
                else:
                    bet = random.randint(MIN_BET, min(bal // 8, 40000))

                bet = max(MIN_BET, min(bet, bal))

                # Determine Target Multiplier
                if pers == 'SystemPlayer':
                    target = 2.0
                elif pers == 'Grinder':
                    target = random.uniform(1.15, 1.45)
                elif pers == 'Degenerate':
                    target = random.uniform(3.5, 12.0) if mood == 'tilted' else random.uniform(2.0, 5.5)
                elif pers == 'Whale':
                    target = random.uniform(1.3, 2.8)
                else:
                    target = random.uniform(low, high)

                db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet, uid))
                db.commit()

                if '_pending' not in room:
                    room['_pending'] = {}

                room['_pending'][uid_str] = {
                    'username': bot['username'],
                    'bet': bet,
                    'cashed_out_at': None,
                    'busted': False
                }

                _active_bot_bets[uid_str] = {
                    'bet': bet,
                    'target_multiplier': target,
                    'cashed_out': False
                }

    _prev_phase = phase


# ── Market Trading ──────────────────────────────────────────────
def _bot_market_activity(db):
    db.row_factory = sqlite3.Row
    bots = db.execute("SELECT id, username, balance FROM users WHERE is_bot = 1").fetchall()

    for bot in bots:
        if bot['id'] not in BOT_STATES:
            BOT_STATES[bot['id']] = _init_bot_state(bot['id'], bot['username'])

    for bot in bots:
        state = BOT_STATES[bot['id']]
        pers = state['personality']
        bal = bot['balance']

        # Determine Desperation sales
        if bal < MIN_BET * 2:
            state['mood'] = 'desperate'
        elif bal > 100000 and state['mood'] == 'desperate':
            state['mood'] = 'normal'

        # 1. LIQUIDATION / SELLING
        sell_prob = 0.15
        if state['mood'] == 'desperate':
            sell_prob = 0.5
        elif pers == 'Merchant':
            sell_prob = 0.3

        if random.random() < sell_prob:
            inv = db.execute(
                'SELECT ui.skin_id, ui.quantity FROM user_inventory ui '
                'WHERE ui.user_id = ? ORDER BY RANDOM() LIMIT 1',
                (bot['id'],)
            ).fetchone()

            if inv and inv['quantity'] > 0:
                skin = get_skin(inv['skin_id'])
                if skin:
                    dyn_price = get_dynamic_price(skin, db)

                    if state['mood'] == 'desperate':
                        markup = random.uniform(0.65, 0.8)  # 20-35% markdown
                    elif pers == 'Merchant':
                        markup = random.uniform(1.1, 1.25)  # Flipping premium
                    elif pers == 'Grinder':
                        markup = random.uniform(0.9, 1.05)
                    else:
                        markup = random.uniform(0.95, 1.3)

                    price = max(int(dyn_price * markup), 100)

                    existing = db.execute(
                        'SELECT id FROM market_listings WHERE seller_id = ? AND skin_id = ?',
                        (bot['id'], inv['skin_id'])
                    ).fetchone()

                    if not existing:
                        if remove_skin_from_user_raw(db, bot['id'], inv['skin_id']):
                            db.execute(
                                'INSERT INTO market_listings (seller_id, skin_id, price) VALUES (?, ?, ?)',
                                (bot['id'], inv['skin_id'], price)
                            )
                            db.commit()

                            if state['mood'] == 'desperate' and random.random() < 0.2:
                                msgs = [
                                    "Man, I am flat out broke. Selling skins dirt cheap on the market!",
                                    f"Just listed a {skin['name']} at a discount. Please buy!",
                                    "Need some coins fast. Check my listings.",
                                    "Fire sale on my inventory, everything must go!",
                                    "Times are tough. Selling skins to fund my gambling addiction.",
                                    "Market deals incoming. I need liquidity stat.",
                                    "Clearing out my backpack. Some gems in there.",
                                ]
                                _send_bot_chat(db, bot, random.choice(msgs))

        # 2. BUYING STRATEGIES
        buy_prob = 0.1
        if pers == 'Merchant':
            buy_prob = 0.45
        elif pers == 'Whale':
            buy_prob = 0.25
        elif pers == 'Degenerate':
            buy_prob = 0.02

        if random.random() < buy_prob and bal > MIN_BET * 1.5:
            listings = db.execute(
                'SELECT ml.* FROM market_listings ml WHERE ml.seller_id != ?', (bot['id'],)
            ).fetchall()

            if listings:
                best_buy = None

                if pers == 'Merchant':
                    # Search for flips (listed below 90% dynamic price)
                    for lst in listings:
                        skin = get_skin(lst['skin_id'])
                        if skin and lst['price'] <= bal:
                            dyn = get_dynamic_price(skin, db)
                            if lst['price'] < dyn * 0.9:
                                best_buy = lst
                                break
                elif pers == 'Whale':
                    # Buy luxury items
                    expensive = [l for l in listings if l['price'] <= bal and l['price'] >= 25000]
                    if expensive:
                        best_buy = random.choice(expensive)
                else:
                    # Grinders buy the absolute cheapest listings
                    affordable = [l for l in listings if l['price'] <= bal]
                    if affordable:
                        best_buy = min(affordable, key=lambda x: x['price'])

                if best_buy:
                    db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (best_buy['price'], bot['id']))
                    db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (best_buy['price'], best_buy['seller_id']))
                    db.execute('DELETE FROM market_listings WHERE id = ?', (best_buy['id'],))
                    add_skin_to_user_raw(db, bot['id'], best_buy['skin_id'])
                    db.commit()

                    # Chat about market purchase
                    if random.random() < 0.2:
                        skin = get_skin(best_buy['skin_id'])
                        if skin:
                            _send_bot_chat(db, bot, random.choice([
                                f"Snagged {skin['name']} off the market. Good deal.",
                                f"Market snipe! {skin['name']} is now mine.",
                                f"Just bought {skin['name']}. Adding to the collection.",
                                f"Thanks for the cheap {skin['name']}, whoever listed that!",
                                f"Market hunting paid off. {skin['name']} acquired.",
                            ]))

                    # Merchant flips purchase immediately
                    if pers == 'Merchant':
                        skin = get_skin(best_buy['skin_id'])
                        if skin:
                            dyn = get_dynamic_price(skin, db)
                            sell_price = int(dyn * random.uniform(1.12, 1.25))
                            if remove_skin_from_user_raw(db, bot['id'], best_buy['skin_id']):
                                db.execute(
                                    'INSERT INTO market_listings (seller_id, skin_id, price) VALUES (?, ?, ?)',
                                    (bot['id'], best_buy['skin_id'], sell_price)
                                )
                                db.commit()


# ── Crate Opening ───────────────────────────────────────────────
def _bot_open_crates(db):
    db.row_factory = sqlite3.Row
    bots = db.execute("SELECT id, username, balance FROM users WHERE is_bot = 1").fetchall()

    for bot in bots:
        if bot['id'] not in BOT_STATES:
            BOT_STATES[bot['id']] = _init_bot_state(bot['id'], bot['username'])

        state = BOT_STATES[bot['id']]
        pers = state['personality']

        unbox_prob = 0.15
        if pers == 'Whale':
            unbox_prob = 0.35
        elif pers == 'Degenerate':
            unbox_prob = 0.25
        elif pers == 'Merchant':
            unbox_prob = 0.05

        if random.random() < unbox_prob:
            affordable = [k for k, v in CRATE_TYPES.items() if v['price'] <= bot['balance']]
            if affordable:
                if pers == 'Whale' and 'legendary' in affordable:
                    ct_key = 'legendary'
                elif pers == 'Whale' and 'premium' in affordable:
                    ct_key = 'premium'
                elif pers == 'Degenerate':
                    ct_key = max(affordable, key=lambda k: CRATE_TYPES[k]['price'])
                else:
                    weights = {'standard': 6, 'premium': 3, 'legendary': 1}
                    crate_weights = [weights.get(k, 1) for k in affordable]
                    ct_key = random.choices(affordable, weights=crate_weights, k=1)[0]

                ct = CRATE_TYPES[ct_key]
                skin = roll_skin_from_crate(ct_key)
                if skin:
                    db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (ct['price'], bot['id']))
                    add_skin_to_user_raw(db, bot['id'], skin['id'])
                    db.commit()

                    # Elite reactions
                    base_price = skin.get('base_price', 0)
                    rarity = skin.get('rarity', 'common').lower()
                    if (rarity in ['legendary', 'covert', 'ancient'] or base_price > 20000) and random.random() < 0.6:
                        msgs = [
                            f"NO WAY!!! Just pulled {skin['name']} from a {ct_key} crate!!!",
                            f"LETS GOOO! {skin['name']} unboxed! That is worth like {base_price} coins!",
                            f"My luck is on another level today, just got a legendary {skin['name']}!",
                            f"Standard unboxing session paid off: {skin['name']}! 🔥",
                            f"OPENING CRATES IS PROFITABLE. Just pulled {skin['name']}!",
                            f"The {ct_key} crate blessed me with {skin['name']}. Unreal.",
                            f"Unboxing god confirmed. {skin['name']} from a {ct_key}!",
                            f"MOM GET THE CAMERA! {skin['name']} just dropped!",
                            f"That dopamine hit when {skin['name']} pops out. Addicting.",
                            f"Rate my unboxing: {skin['name']}. I rate it 10/10.",
                            f"Just turned {ct['price']} coins into {skin['name']}. Stonks.",
                        ]
                        _send_bot_chat(db, bot, random.choice(msgs))


# ── Slots Simulator ─────────────────────────────────────────────
def _bot_play_slots(db, bots):
    for bot in bots:
        if bot['id'] not in BOT_STATES:
            BOT_STATES[bot['id']] = _init_bot_state(bot['id'], bot['username'])

        state = BOT_STATES[bot['id']]
        pers = state['personality']
        bal = bot['balance']

        play_prob = 0.15
        if pers == 'Degenerate':
            play_prob = 0.4
        elif pers == 'Whale':
            play_prob = 0.25
        elif pers == 'Merchant':
            play_prob = 0.02

        if random.random() < play_prob and bal >= MIN_BET:
            if pers == 'Whale':
                bet = random.randint(MIN_BET * 2, min(bal // 8, 100000))
            elif pers == 'Degenerate':
                bet = random.randint(MIN_BET, min(bal // 5, 50000))
            else:
                bet = MIN_BET

            bet = max(MIN_BET, min(bet, bal))

            # Simulate slots mathematics (Approx 95% RTP model)
            roll = random.random()
            if roll < 0.64:
                winnings = 0
                outcome = 'loss'
            elif roll < 0.88:
                multiplier = random.uniform(0.5, 1.5)
                winnings = int(bet * multiplier)
                outcome = 'small_win'
            elif roll < 0.98:
                multiplier = random.uniform(2.0, 8.0)
                winnings = int(bet * multiplier)
                outcome = 'medium_win'
            else:
                multiplier = random.uniform(15.0, 75.0)
                winnings = int(bet * multiplier)
                outcome = 'mega_win'

            net = winnings - bet
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (net, bot['id']))
            db.commit()

            if outcome == 'mega_win' and random.random() < 0.7:
                msgs = [
                    f"OMG! Just hit a {multiplier:.1f}x jackpot on slots! 🎰💸",
                    f"SLOTS ARE PAYING OUT! +{winnings} coins!",
                    f"No way, three cherries/burgers in a row! Let's go!",
                    "The reels aligned. Pure slot magic.",
                    f"Slot machine went brrrr! Jackpot! +{winnings}!",
                    "That spinning sound just hits different when you win big.",
                    "Never doubted the slots for a second.",
                    f"BIG SPIN ENERGY! {multiplier:.1f}x payout! 🎰",
                ]
                _send_bot_chat(db, bot, random.choice(msgs))


# ── Blackjack Simulator ─────────────────────────────────────────
def _bot_play_blackjack(db, bots):
    for bot in bots:
        if bot['id'] not in BOT_STATES:
            BOT_STATES[bot['id']] = _init_bot_state(bot['id'], bot['username'])

        state = BOT_STATES[bot['id']]
        pers = state['personality']
        bal = bot['balance']

        play_prob = 0.1
        if pers in ['SystemPlayer', 'Grinder']:
            play_prob = 0.3
        elif pers == 'Whale':
            play_prob = 0.2

        if random.random() < play_prob and bal >= MIN_BET:
            if pers == 'Whale':
                bet = random.randint(MIN_BET * 2, min(bal // 6, 120000))
            elif pers == 'SystemPlayer':
                bet = random.randint(MIN_BET, min(bal // 10, 40000))
            else:
                bet = MIN_BET

            bet = max(MIN_BET, min(bet, bal))

            # Simulate basic strategy outcomes (Approx 99% RTP model)
            roll = random.random()
            if roll < 0.47:
                winnings = 0
                outcome = 'loss'
            elif roll < 0.55:
                winnings = bet
                outcome = 'push'
            elif roll < 0.95:
                winnings = bet * 2
                outcome = 'win'
            else:
                winnings = int(bet * 2.5)
                outcome = 'blackjack'

            net = winnings - bet
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (net, bot['id']))
            db.commit()

            if outcome == 'blackjack' and random.random() < 0.4:
                msgs = [
                    "Dealer got served. 21!",
                    f"Blackjack! +{winnings - bet} coins! 🃏",
                    "Perfect basic strategy wins again.",
                    "Hit me? Nah, I'm good. Dealer busts!",
                    "Blackjack table is my office. Another winning hand.",
                    "Read the dealer like a children's menu. Easy win.",
                    "Double down paid off big time.",
                    f"Natural blackjack! The cards are on my side.",
                    "Split aces, won both hands. Pro plays only.",
                ]
                _send_bot_chat(db, bot, random.choice(msgs))