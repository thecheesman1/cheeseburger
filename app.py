import sqlite3
import random
import json
import math
import bcrypt
import threading
import time as _time
from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify
from bots import bot_thread, seed_bots, admin_settings, BOT_NAMES, roll_skin_from_crate

app = Flask(__name__)
app.secret_key = 'cheeseburger-secret-key-change-in-production'
DATABASE = 'cheeseburger.db'

MIN_BET = 10000
STARTING_BALANCE = 20000

SKIN_CATALOG = [
    {'id': 1,  'name': 'Rusty Burger',       'rarity': 'Common',    'emoji': '🍔', 'base_price': 1500},
    {'id': 2,  'name': 'Paper Fries',         'rarity': 'Common',    'emoji': '🍟', 'base_price': 1200},
    {'id': 3,  'name': 'Plastic Cup',         'rarity': 'Common',    'emoji': '🥤', 'base_price': 1000},
    {'id': 4,  'name': 'Cardboard Nuggets',   'rarity': 'Common',    'emoji': '🍗', 'base_price': 1300},
    {'id': 5,  'name': 'Tin Tray',            'rarity': 'Common',    'emoji': '🧊', 'base_price': 1100},
    {'id': 6,  'name': 'Silver Spatula',      'rarity': 'Uncommon',  'emoji': '🥄', 'base_price': 5000},
    {'id': 7,  'name': 'Neon Shake',          'rarity': 'Uncommon',  'emoji': '🥤', 'base_price': 6000},
    {'id': 8,  'name': 'Bronze Fries',        'rarity': 'Uncommon',  'emoji': '🍟', 'base_price': 4500},
    {'id': 9,  'name': 'Pixel Burger',        'rarity': 'Uncommon',  'emoji': '🍔', 'base_price': 5500},
    {'id': 10, 'name': 'Golden Nuggets',      'rarity': 'Rare',      'emoji': '✨', 'base_price': 15000},
    {'id': 11, 'name': 'Ruby Shake',          'rarity': 'Rare',      'emoji': '💎', 'base_price': 18000},
    {'id': 12, 'name': 'Sapphire Spatula',    'rarity': 'Rare',      'emoji': '🔮', 'base_price': 20000},
    {'id': 13, 'name': 'Diamond Burger',      'rarity': 'Epic',      'emoji': '💎', 'base_price': 50000},
    {'id': 14, 'name': 'Obsidian Fries',      'rarity': 'Epic',      'emoji': '🖤', 'base_price': 60000},
    {'id': 15, 'name': 'Cosmic Nuggets',      'rarity': 'Epic',      'emoji': '🌌', 'base_price': 55000},
    {'id': 16, 'name': 'Galaxy Spatula',      'rarity': 'Epic',      'emoji': '🌟', 'base_price': 65000},
    {'id': 17, 'name': 'Neo Burger',          'rarity': 'Legendary', 'emoji': '👑', 'base_price': 200000},
    {'id': 18, 'name': 'God Fries',           'rarity': 'Legendary', 'emoji': '⚡', 'base_price': 250000},
    {'id': 19, 'name': 'Infinity Nuggets',    'rarity': 'Legendary', 'emoji': '♾️', 'base_price': 300000},
    {'id': 20, 'name': 'Cheeseburger Supreme', 'rarity': 'Legendary','emoji': '🏆', 'base_price': 500000},
]

CRATE_TYPES = {
    'standard':  {'name': 'Standard Crate',  'price': 8000,  'weights': {'Common': 60, 'Uncommon': 25, 'Rare': 10, 'Epic': 4,  'Legendary': 1}},
    'premium':   {'name': 'Premium Crate',   'price': 25000, 'weights': {'Common': 20, 'Uncommon': 35, 'Rare': 25, 'Epic': 15, 'Legendary': 5}},
    'legendary': {'name': 'Legendary Crate', 'price': 100000,'weights': {'Common': 0,  'Uncommon': 0,  'Rare': 10, 'Epic': 40, 'Legendary': 50}},
}

RARITY_RANK = {'Common': 0, 'Uncommon': 1, 'Rare': 2, 'Epic': 3, 'Legendary': 4}
RARITY_COLORS = {'Common': '#9e9e9e', 'Uncommon': '#4ade80', 'Rare': '#60a5fa', 'Epic': '#c084fc', 'Legendary': '#fbbf24'}


# Wire bots.py to our globals
import bots as botmod
botmod.DATABASE = DATABASE
botmod.CRATE_TYPES = CRATE_TYPES
botmod.SKIN_CATALOG = SKIN_CATALOG
botmod.MIN_BET = MIN_BET
botmod.STARTING_BALANCE = STARTING_BALANCE

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        balance INTEGER NOT NULL DEFAULT 20000,
        equipped_skin TEXT DEFAULT '',
        is_bot INTEGER NOT NULL DEFAULT 0
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS user_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        skin_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS market_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER NOT NULL,
        skin_id INTEGER NOT NULL,
        price INTEGER NOT NULL,
        listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(seller_id) REFERENCES users(id)
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        message TEXT NOT NULL,
        msg_type TEXT DEFAULT 'chat',
        skin_id INTEGER,
        created_at INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    # Add is_bot column if missing
    try:
        db.execute('ALTER TABLE users ADD COLUMN is_bot INTEGER NOT NULL DEFAULT 0')
    except:
        pass
    db.commit()
    db.close()

init_db()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    return db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

def get_skin(skin_id):
    for s in SKIN_CATALOG:
        if s['id'] == skin_id:
            return s
    return None

def get_dynamic_price(skin, db_conn=None):
    """Dynamic pricing with trend cycles, velocity, and rarity desirability.

    Five forces shape every price:
      1. Base × rarity multiplier (classic floor)
      2. Supply scarcity — more of this skin in circulation = cheaper
      3. Trend cycle — each skin has a 5-15min trend window; if you're in it, +bonus
      4. Sales velocity — skins that sold recently get a hype bump
      5. Demand noise — small random jitter to prevent staleness
    """
    base = skin['base_price']
    own_db = db_conn is None
    if own_db:
        db_conn = sqlite3.connect(DATABASE)
        db_conn.row_factory = sqlite3.Row

    skin_id = skin['id']

    # ── 1. Supply: how many exist in circulation ──
    total_held = db_conn.execute(
        'SELECT COALESCE(SUM(quantity), 0) FROM user_inventory WHERE skin_id = ?',
        (skin_id,)
    ).fetchone()[0]
    listed = db_conn.execute(
        'SELECT COUNT(*) FROM market_listings WHERE skin_id = ?',
        (skin_id,)
    ).fetchone()[0]
    supply = total_held + listed

    # ── 2. Rarity floor ──
    rarity_mult = {
        'Common': 0.5, 'Uncommon': 1.0, 'Rare': 2.0, 'Epic': 4.0, 'Legendary': 8.0
    }[skin['rarity']]

    # ── 3. Trend cycle (deterministic per skin, rotates every 5-15 min) ──
    epoch = int(_time.time() / 300)  # 5-minute blocks
    trend_seed = (skin_id * 17 + epoch * 31) % 100
    trend_bonus = 1.0
    if trend_seed < 15:       # 15% of skins are "hot" right now
        trend_bonus = random.uniform(1.2, 2.0)
    elif trend_seed < 35:     # 20% are "warm"
        trend_bonus = random.uniform(1.05, 1.25)
    elif trend_seed > 85:     # 15% are "cold"
        trend_bonus = random.uniform(0.6, 0.85)

    # ── 4. Sales velocity — recent transactions pump the price ──
    try:
        recent_sales = db_conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE msg_type = 'market_buy' AND skin_id = ? "
            "AND created_at > ?",
            (skin_id, int(_time.time()) - 600)
        ).fetchone()[0]
    except:
        recent_sales = 0
    velocity_bonus = 1.0 + min(recent_sales * 0.08, 0.6)  # cap at +60%

    # ── 5. Scarcity curve — asymptotic floor at 0.3 ──
    scarcity = max(0.3, 1.0 / (1.0 + supply * 0.015))

    # ── 6. Noise ──
    demand_noise = random.uniform(0.88, 1.12)

    price = int(base * rarity_mult * scarcity * trend_bonus * velocity_bonus * demand_noise)

    if own_db:
        db_conn.close()
    return max(base // 2, price)

def roll_skin_from_crate(crate_type):
    ct = CRATE_TYPES.get(crate_type)
    if not ct:
        return None
    rarities = list(ct['weights'].keys())
    weights = list(ct['weights'].values())
    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    pool = [s for s in SKIN_CATALOG if s['rarity'] == chosen_rarity]
    return random.choice(pool) if pool else None

def get_user_inventory(user_id):
    db = get_db()
    rows = db.execute('SELECT skin_id, quantity FROM user_inventory WHERE user_id = ?', (user_id,)).fetchall()
    inv = []
    for r in rows:
        skin = get_skin(r['skin_id'])
        if skin:
            inv.append({**skin, 'quantity': r['quantity']})
    return inv

def add_skin_to_user(user_id, skin_id):
    db = get_db()
    existing = db.execute('SELECT id, quantity FROM user_inventory WHERE user_id = ? AND skin_id = ?', (user_id, skin_id)).fetchone()
    if existing:
        db.execute('UPDATE user_inventory SET quantity = quantity + 1 WHERE id = ?', (existing['id'],))
    else:
        db.execute('INSERT INTO user_inventory (user_id, skin_id, quantity) VALUES (?, ?, 1)', (user_id, skin_id))
    db.commit()

def remove_skin_from_user(user_id, skin_id):
    db = get_db()
    row = db.execute('SELECT id, quantity FROM user_inventory WHERE user_id = ? AND skin_id = ?', (user_id, skin_id)).fetchone()
    if not row:
        return False
    if row['quantity'] > 1:
        db.execute('UPDATE user_inventory SET quantity = quantity - 1 WHERE id = ?', (row['id'],))
    else:
        db.execute('DELETE FROM user_inventory WHERE id = ?', (row['id'],))
    db.commit()
    return True

# ── Routes ──────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html', user=get_user())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            return render_template('register.html', error='All fields required')
        db = get_db()
        if db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            return render_template('register.html', error='Username taken')
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed))
        db.commit()
        return redirect(url_for('login'))
    return render_template('register.html', user=get_user())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and bcrypt.checkpw(password.encode(), user['password']):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html', user=get_user())

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ── Games ────────────────────────────────────────────────────────

@app.route('/slots', methods=['GET', 'POST'])
@login_required
def slots():
    user = get_user()
    result = None
    if request.method == 'POST':
        bet = int(request.form.get('bet', 0))
        if bet < MIN_BET:
            return render_template('slots.html', user=user, error=f'Minimum bet is ${MIN_BET:,}', result=None)
        if bet > user['balance']:
            return render_template('slots.html', user=user, error='Insufficient balance', result=None)
        symbols = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣']
        reels = [random.choice(symbols) for _ in range(3)]
        win = 0
        if reels[0] == reels[1] == reels[2]:
            multiplier = 10 if reels[0] == '7️⃣' else 5 if reels[0] == '💎' else 3
            win = bet * multiplier
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            win = bet
        net = win - bet
        db = get_db()
        db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (net, user['id']))
        db.commit()
        user = get_user()
        result = {'reels': reels, 'win': win, 'net': net}
    return render_template('slots.html', user=user, result=result)

@app.route('/coinflip', methods=['GET', 'POST'])
@login_required
def coinflip():
    user = get_user()
    result = None
    if request.method == 'POST':
        bet = int(request.form.get('bet', 0))
        call = request.form.get('call')
        if bet < MIN_BET:
            return render_template('coinflip.html', user=user, error=f'Minimum bet is ${MIN_BET:,}', result=None)
        if bet > user['balance']:
            return render_template('coinflip.html', user=user, error='Insufficient balance', result=None)
        flip = random.choice(['heads', 'tails'])
        win = bet * 2 if call == flip else 0
        net = win - bet
        db = get_db()
        db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (net, user['id']))
        db.commit()
        user = get_user()
        result = {'flip': flip, 'call': call, 'win': win, 'net': net}
    return render_template('coinflip.html', user=user, result=result)

@app.route('/dice', methods=['GET', 'POST'])
@login_required
def dice():
    user = get_user()
    result = None
    if request.method == 'POST':
        bet = int(request.form.get('bet', 0))
        guess = int(request.form.get('guess'))
        if bet < MIN_BET:
            return render_template('dice.html', user=user, error=f'Minimum bet is ${MIN_BET:,}', result=None)
        if bet > user['balance']:
            return render_template('dice.html', user=user, error='Insufficient balance', result=None)
        if guess < 2 or guess > 12:
            return render_template('dice.html', user=user, error='Guess between 2 and 12', result=None)
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2
        win = bet * 6 if total == guess else 0
        net = win - bet
        db = get_db()
        db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (net, user['id']))
        db.commit()
        user = get_user()
        result = {'dice': [d1, d2], 'total': total, 'guess': guess, 'win': win, 'net': net}
    return render_template('dice.html', user=user, result=result)

@app.route('/blackjack', methods=['GET', 'POST'])
@login_required
def blackjack():
    user = get_user()
    result = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'deal':
            bet = int(request.form.get('bet', 0))
            if bet < MIN_BET:
                return render_template('blackjack.html', user=user, error=f'Minimum bet is ${MIN_BET:,}', result=None)
            if bet > user['balance']:
                return render_template('blackjack.html', user=user, error='Insufficient balance', result=None)
            deck = [2,3,4,5,6,7,8,9,10,10,10,10,11]*4
            random.shuffle(deck)
            p_hand = [deck.pop(), deck.pop()]
            d_hand = [deck.pop(), deck.pop()]
            session['deck'] = deck
            session['p_hand'] = p_hand
            session['d_hand'] = d_hand
            session['bet'] = bet
            if sum(p_hand) == 21:
                return resolve_blackjack('blackjack')
            return render_template('blackjack.html', user=user, game={
                'p_hand': p_hand, 'd_hand': [d_hand[0], '?'],
                'standing': False, 'bust': False, 'd_sum': None
            })
        elif action == 'hit':
            deck = session.get('deck', [])
            p_hand = session.get('p_hand', [])
            d_hand = session.get('d_hand', [])
            p_hand.append(deck.pop())
            session['deck'] = deck
            session['p_hand'] = p_hand
            if sum(p_hand) > 21:
                return resolve_blackjack('bust')
            return render_template('blackjack.html', user=user, game={
                'p_hand': p_hand, 'd_hand': [d_hand[0], '?'],
                'standing': False, 'bust': False, 'd_sum': None
            })
        elif action == 'stand':
            return resolve_blackjack('stand')
    return render_template('blackjack.html', user=user, game=None)

def resolve_blackjack(outcome):
    user = get_user()
    bet = session.get('bet', 0)
    d_hand = session.get('d_hand', [])
    p_hand = session.get('p_hand', [])
    deck = session.get('deck', [])
    db = get_db()

    p_cards = ' '.join(str(c) for c in p_hand)
    d_cards = ' '.join(str(c) for c in d_hand)

    if outcome == 'blackjack':
        win = int(bet * 1.5)
        db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (win, user['id']))
        db.commit()
        user = get_user()
        return render_template('blackjack.html', user=user, result={
            'outcome': 'Blackjack!', 'win': win + bet, 'net': win,
            'p_cards': p_cards, 'd_cards': d_cards
        }, game=None)

    while sum(d_hand) < 17:
        d_hand.append(deck.pop())

    d_sum = sum(d_hand)
    p_sum = sum(p_hand)

    if outcome == 'bust':
        win = 0
    elif d_sum > 21 or p_sum > d_sum:
        win = bet
    elif p_sum == d_sum:
        win = bet
    else:
        win = 0

    net = win - bet
    db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (net, user['id']))
    db.commit()
    user = get_user()

    if outcome == 'bust':
        result = {'outcome': 'Bust!', 'win': 0, 'net': -bet}
    elif d_sum > 21:
        result = {'outcome': 'Dealer bust! You win!', 'win': bet, 'net': bet}
    elif p_sum > d_sum:
        result = {'outcome': 'You win!', 'win': bet, 'net': bet}
    elif p_sum == d_sum:
        result = {'outcome': 'Push', 'win': bet, 'net': 0}
    else:
        result = {'outcome': 'Dealer wins', 'win': 0, 'net': -bet}

    result['d_sum'] = d_sum
    result['p_cards'] = p_cards
    result['d_cards'] = d_cards
    return render_template('blackjack.html', user=user, result=result, game=None)

# ── Multiplayer Crash Game ───────────────────────────────────────

import time as _time

_crash_room = {
    'phase': 'betting',
    'round': 0,
    'crash_point': None,
    'start_time': None,
    'players': {},
    'next_phase_at': 0,
    'history': [],  # last 10 crash points
}

BETTING_DURATION = 8
CRASHED_DURATION = 5
CRASH_GROWTH = 0.08  # multiplier growth rate (lower = slower)

def _advance_crash_phase():
    now = _time.time()
    room = _crash_room
    if room['next_phase_at'] == 0:
        room['next_phase_at'] = now + BETTING_DURATION
        return
    if room['phase'] == 'betting' and now >= room['next_phase_at']:
        room['phase'] = 'running'
        room['round'] += 1
        room['start_time'] = now
        # Crash point: most rounds crash between 1.2x-8x, occasional huge ones
        # 1% chance of instant crash (1.00x), otherwise weighted toward 1.3x-6x
        roll = random.random()
        if roll < 0.01:
            cp = 1.00
        elif roll < 0.40:
            cp = round(random.uniform(1.10, 2.0), 2)
        elif roll < 0.75:
            cp = round(random.uniform(2.0, 5.0), 2)
        elif roll < 0.93:
            cp = round(random.uniform(5.0, 15.0), 2)
        else:
            cp = round(random.uniform(15.0, 50.0), 2)
        room['crash_point'] = cp
        room['players'] = room.get('_pending', {})
        room['_pending'] = {}
        room['next_phase_at'] = 0
    elif room['phase'] == 'crashed' and now >= room['next_phase_at']:
        if room['crash_point']:
            room['history'].insert(0, room['crash_point'])
            if len(room['history']) > 10:
                room['history'] = room['history'][:10]
        room['phase'] = 'betting'
        room['crash_point'] = None
        room['start_time'] = None
        room['players'] = {}
        room['_pending'] = {}
        room['next_phase_at'] = now + BETTING_DURATION

def _get_multiplier():
    room = _crash_room
    if room['phase'] != 'running' or not room['start_time']:
        return 1.0
    elapsed = _time.time() - room['start_time']
    return math.pow(math.e, elapsed * CRASH_GROWTH)

def _maybe_crash():
    room = _crash_room
    if room['phase'] != 'running':
        return
    mult = _get_multiplier()
    if mult >= room['crash_point']:
        room['phase'] = 'crashed'
        room['next_phase_at'] = _time.time() + CRASHED_DURATION
        # mark all non-cashed-out players as busted (refund already deducted)
        db = get_db()
        for pid, p in room['players'].items():
            if p.get('cashed_out_at') is None:
                p['busted'] = True
        db.commit()

@app.route('/crash')
@login_required
def crash():
    _advance_crash_phase()
    _maybe_crash()
    user = get_user()
    room = _crash_room
    joined = str(user['id']) in room.get('players', {}) or str(user['id']) in room.get('_pending', {})
    return render_template('crash.html', user=user, room=room, joined=joined,
                           betting_duration=BETTING_DURATION, crashed_duration=CRASHED_DURATION)

@app.route('/crash/join', methods=['POST'])
@login_required
def crash_join():
    _advance_crash_phase()
    user = get_user()
    room = _crash_room
    uid = str(user['id'])
    if room['phase'] != 'betting':
        return jsonify({'error': 'Round already started'}), 400
    if uid in room.get('_pending', {}) or uid in room.get('players', {}):
        return jsonify({'error': 'Already joined'}), 400
    bet = int(request.form.get('bet', 0))
    if bet < MIN_BET:
        return jsonify({'error': f'Minimum bet is ${MIN_BET:,}'}), 400
    if bet > user['balance']:
        return jsonify({'error': 'Insufficient balance'}), 400
    db = get_db()
    db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet, user['id']))
    db.commit()
    if '_pending' not in room:
        room['_pending'] = {}
    room['_pending'][uid] = {'username': user['username'], 'bet': bet, 'cashed_out_at': None, 'busted': False}
    return jsonify({'success': True})

@app.route('/crash/cashout', methods=['POST'])
@login_required
def crash_cashout():
    _maybe_crash()
    user = get_user()
    room = _crash_room
    uid = str(user['id'])
    if room['phase'] != 'running':
        return jsonify({'error': 'Not running'}), 400
    player = room['players'].get(uid)
    if not player or player.get('cashed_out_at') is not None or player.get('busted'):
        return jsonify({'error': 'Not in game or already out'}), 400
    multiplier = float(request.form.get('multiplier', 1.0))
    if multiplier > room['crash_point']:
        player['busted'] = True
        return jsonify({'busted': True, 'crash_point': room['crash_point'], 'loss': player['bet']})
    player['cashed_out_at'] = multiplier
    winnings = int(player['bet'] * multiplier)
    db = get_db()
    db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (winnings, user['id']))
    db.commit()
    user = get_user()
    return jsonify({
        'cashed_out': True, 'multiplier': multiplier,
        'winnings': winnings, 'profit': winnings - player['bet'],
        'balance': user['balance']
    })

@app.route('/crash/state')
@login_required
def crash_state():
    _advance_crash_phase()
    _maybe_crash()
    room = _crash_room
    mult = _get_multiplier() if room['phase'] in ('running', 'crashed') else 1.0
    if room['phase'] == 'crashed':
        mult = room['crash_point']
    players_out = []
    all_players = {**room.get('_pending', {}), **room.get('players', {})}
    for pid, p in all_players.items():
        players_out.append({
            'username': p['username'],
            'bet': p['bet'],
            'cashed_out_at': p.get('cashed_out_at'),
            'busted': p.get('busted', False),
        })
    return jsonify({
        'phase': room['phase'],
        'round': room['round'],
        'multiplier': round(mult, 2),
        'crash_point': room['crash_point'],
        'start_time': room['start_time'],
        'players': players_out,
        'countdown': max(0, int(room.get('next_phase_at', 0) - _time.time())),
        'history': room.get('history', []),
    })

# ── Skins Market ─────────────────────────────────────────────────

@app.route('/inventory')
@login_required
def inventory():
    user = get_user()
    inv = get_user_inventory(user['id'])
    return render_template('inventory.html', user=user, inventory=inv, rarity_colors=RARITY_COLORS)

@app.route('/market')
@login_required
def market():
    user = get_user()
    db = get_db()
    listings = db.execute('''
        SELECT ml.id, ml.price, ml.skin_id, ml.seller_id, u.username as seller_name
        FROM market_listings ml JOIN users u ON ml.seller_id = u.id
        ORDER BY ml.listed_at DESC
    ''').fetchall()
    enriched = []
    for l in listings:
        skin = get_skin(l['skin_id'])
        if skin:
            enriched.append({**dict(l), 'skin': skin})
    return render_template('market.html', user=user, listings=enriched, rarity_colors=RARITY_COLORS)

@app.route('/market/sell', methods=['POST'])
@login_required
def market_sell():
    user = get_user()
    skin_id = int(request.form.get('skin_id'))
    price = int(request.form.get('price', 0))
    if price < 1:
        return redirect(url_for('inventory'))
    skin = get_skin(skin_id)
    if not skin:
        return redirect(url_for('inventory'))
    if not remove_skin_from_user(user['id'], skin_id):
        return redirect(url_for('inventory'))
    db = get_db()
    db.execute('INSERT INTO market_listings (seller_id, skin_id, price) VALUES (?, ?, ?)', (user['id'], skin_id, price))
    db.commit()
    return redirect(url_for('market'))

@app.route('/market/buy/<int:listing_id>', methods=['POST'])
@login_required
def market_buy(listing_id):
    user = get_user()
    db = get_db()
    listing = db.execute('SELECT * FROM market_listings WHERE id = ?', (listing_id,)).fetchone()
    if not listing:
        return redirect(url_for('market'))
    if listing['seller_id'] == user['id']:
        return render_template('market.html', user=user, error="Can't buy your own listing", listings=[])
    if user['balance'] < listing['price']:
        return render_template('market.html', user=user, error='Insufficient balance', listings=[])
    db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (listing['price'], user['id']))
    db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (listing['price'], listing['seller_id']))
    db.execute('DELETE FROM market_listings WHERE id = ?', (listing_id,))
    add_skin_to_user(user['id'], listing['skin_id'])
    # Log for velocity tracking
    skin = get_skin(listing['skin_id'])
    now = int(_time.time())
    db.execute(
        "INSERT INTO chat_messages (user_id, username, message, msg_type, skin_id, created_at) VALUES (?, ?, ?, 'market_buy', ?, ?)",
        (user['id'], user['username'], f"snagged {skin['name']}" if skin else 'bought a skin', listing['skin_id'], now))
    db.commit()
    return redirect(url_for('market'))

@app.route('/market/cancel/<int:listing_id>', methods=['POST'])
@login_required
def market_cancel(listing_id):
    user = get_user()
    db = get_db()
    listing = db.execute('SELECT * FROM market_listings WHERE id = ? AND seller_id = ?', (listing_id, user['id'])).fetchone()
    if listing:
        add_skin_to_user(user['id'], listing['skin_id'])
        db.execute('DELETE FROM market_listings WHERE id = ?', (listing_id,))
        db.commit()
    return redirect(url_for('market'))

# ── Crates ───────────────────────────────────────────────────────

@app.route('/crates', methods=['GET'])
@login_required
def crates():
    user = get_user()
    return render_template('crates.html', user=user, crate_types=CRATE_TYPES, rarity_colors=RARITY_COLORS)

@app.route('/crates/open', methods=['POST'])
@login_required
def crates_open():
    user = get_user()
    crate_type = request.form.get('crate_type')
    ct = CRATE_TYPES.get(crate_type)
    if not ct:
        return redirect(url_for('crates'))
    if user['balance'] < ct['price']:
        return render_template('crates.html', user=user, error='Insufficient balance', crate_types=CRATE_TYPES, rarity_colors=RARITY_COLORS)
    skin = roll_skin_from_crate(crate_type)
    if not skin:
        return redirect(url_for('crates'))
    db = get_db()
    db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (ct['price'], user['id']))
    add_skin_to_user(user['id'], skin['id'])
    db.commit()
    user = get_user()
    return render_template('crates.html', user=user, crate_types=CRATE_TYPES, rarity_colors=RARITY_COLORS,
                           opened_skin=skin, opened_rarity_color=RARITY_COLORS.get(skin['rarity'], '#fff'))

# ── Equip Skin ───────────────────────────────────────────────────

@app.route('/equip/<int:skin_id>', methods=['POST'])
@login_required
def equip_skin(skin_id):
    user = get_user()
    inv = get_user_inventory(user['id'])
    if any(s['id'] == skin_id for s in inv):
        db = get_db()
        db.execute('UPDATE users SET equipped_skin = ? WHERE id = ?', (str(skin_id), user['id']))
        db.commit()
    return redirect(url_for('inventory'))

@app.route('/unequip', methods=['POST'])
@login_required
def unequip_skin():
    db = get_db()
    db.execute("UPDATE users SET equipped_skin = '' WHERE id = ?", (session['user_id'],))
    db.commit()
    return redirect(url_for('inventory'))

# ── Leaderboard ─────────────────────────────────────────────────


# ── Chat ─────────────────────────────────────────────────────────

@app.route('/chat/messages')
def chat_messages():
    """Return latest 50 messages as JSON for the sidebar poll."""
    db = get_db()
    msgs = db.execute(
        'SELECT id, username, message, msg_type, created_at FROM chat_messages '
        'ORDER BY id DESC LIMIT 50'
    ).fetchall()
    return jsonify([dict(m) for m in reversed(msgs)])


@app.route('/chat/send', methods=['POST'])
@login_required
def chat_send():
    """Post a message to the global chat."""
    user = get_user()
    text = request.form.get('message', '').strip()
    if not text or len(text) > 200:
        return redirect(url_for('index'))
    db = get_db()
    db.execute(
        'INSERT INTO chat_messages (user_id, username, message, msg_type, created_at) VALUES (?, ?, ?, ?, ?)',
        (user['id'], user['username'], text, 'chat', int(_time.time())))
    db.commit()
    return redirect(url_for('index'))

@app.route('/leaderboard')
@login_required
def leaderboard():
    user = get_user()
    db = get_db()
    top = db.execute(
        'SELECT id, username, balance, is_bot FROM users ORDER BY balance DESC LIMIT 20'
    ).fetchall()
    return render_template('leaderboard.html', user=user, top=top, colordict=RARITY_COLORS)

# ── Admin Panel ──────────────────────────────────────────────────

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = get_user()
        if not user or user['username'] != 'esadsa':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'save_settings':
            admin_settings['min_bet'] = int(request.form.get('min_bet', 10000))
            admin_settings['starting_balance'] = int(request.form.get('starting_balance', 20000))
            admin_settings['bot_aggression'] = request.form.get('bot_aggression', 'medium')
            admin_settings['crate_discount_pct'] = int(request.form.get('crate_discount', 0))
            admin_settings['event_mode'] = request.form.get('event_mode', 'normal')
            admin_settings['maintenance_mode'] = request.form.get('maintenance_mode') == 'on'
            global MIN_BET, STARTING_BALANCE
            MIN_BET = admin_settings['min_bet']
            STARTING_BALANCE = admin_settings['starting_balance']
        elif action == 'give_money':
            target = request.form.get('username', '').strip()
            amount = int(request.form.get('amount', 0))
            if target and amount > 0:
                db.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (amount, target))
                db.execute("UPDATE users SET balance = balance + ? WHERE username = 'esadsa'", (amount,))
                db.commit()
        elif action == 'reset_bot':
            target = request.form.get('username', '').strip()
            if target:
                db.execute('UPDATE users SET balance = ? WHERE username = ? AND is_bot = 1', (20000 + random.randint(5000, 100000), target))
                db.commit()
        elif action == 'wipe_economy':
            db.execute("UPDATE users SET balance = ? WHERE is_bot = 0 AND username != 'esadsa'", (STARTING_BALANCE,))
            db.execute('DELETE FROM user_inventory')
            db.execute('DELETE FROM market_listings')
            db.commit()
            seed_bots()
        elif action == 'nuke':
            db.execute('DELETE FROM user_inventory')
            db.execute('DELETE FROM market_listings')
            db.execute("DELETE FROM users WHERE username != 'esadsa'")
            db.commit()
            seed_bots()

    user = get_user()
    bots = db.execute('SELECT username, balance FROM users WHERE is_bot = 1 ORDER BY balance DESC').fetchall()
    total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_market = db.execute('SELECT COUNT(*) FROM market_listings').fetchone()[0]
    top_human = db.execute("SELECT username, balance FROM users WHERE is_bot = 0 ORDER BY balance DESC LIMIT 5").fetchall()
    return render_template('admin.html', user=user, settings=admin_settings,
                          bots=bots, total_users=total_users, total_listings=total_market,
                          top_humans=top_human, room=_crash_room)


# ── Bot wiring + startup ─────────────────────────────────────────
# Called at module import to wire bots.py to app globals

import bots as _b
_b._crash_room = _crash_room
_b._get_multiplier = _get_multiplier
_b.get_skin = get_skin
_b.get_dynamic_price = get_dynamic_price
_b.roll_skin_from_crate = roll_skin_from_crate

# Provide raw inventory helpers
def _add_raw(db, uid, sid):
    db.row_factory = sqlite3.Row
    e = db.execute('SELECT id, quantity FROM user_inventory WHERE user_id=? AND skin_id=?', (uid, sid)).fetchone()
    if e: db.execute('UPDATE user_inventory SET quantity=quantity+1 WHERE id=?', (e['id'],))
    else: db.execute('INSERT INTO user_inventory (user_id,skin_id,quantity) VALUES (?,?,1)', (uid, sid))
def _rem_raw(db, uid, sid):
    db.row_factory = sqlite3.Row
    r = db.execute('SELECT id, quantity FROM user_inventory WHERE user_id=? AND skin_id=?', (uid, sid)).fetchone()
    if not r: return False
    if r['quantity'] > 1: db.execute('UPDATE user_inventory SET quantity=quantity-1 WHERE id=?', (r['id'],))
    else: db.execute('DELETE FROM user_inventory WHERE id=?', (r['id'],))
    db.commit(); return True
_b.add_skin_to_user_raw = _add_raw
_b.remove_skin_from_user_raw = _rem_raw

seed_bots()
threading.Thread(target=bot_thread, daemon=True).start()

if __name__ == '__main__':

    app.run(debug=False, host='0.0.0.0', port=34797)
