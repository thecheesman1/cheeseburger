import sys
sys.set_int_max_str_digits(0)  # Brareu48 has 8192-digit money, Python 3.11+ limits int→str

import sqlite3
import random
import json
import math
import bcrypt
import threading
import time as _time
from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify
from bots import bot_thread, seed_bots, admin_settings, BOT_NAMES, roll_skin_from_crate, pulse_human

app = Flask(__name__)
app.secret_key = 'cheeseburger-secret-key-change-in-production'

@app.before_request
def _track_human():
    """Pulse on every real page load / action, but skip chat polling."""
    if request.path != '/chat/messages':
        pulse_human()
DATABASE = 'cheeseburger.db'

MIN_BET = 10000
STARTING_BALANCE = 20000

SKIN_CATALOG = [
    {'id': 1,  'name': 'Rusty Burger',       'rarity': 'Common',    'emoji': '🍔', 'base_price': 1500},
    {'id': 2,  'name': 'Paper Fries',         'rarity': 'Common',    'emoji': '🍟', 'base_price': 1200},
    {'id': 3,  'name': 'Plastic Cup',         'rarity': 'Common',    'emoji': '🥤', 'base_price': 1000},
    {'id': 4,  'name': 'Cardboard Nuggets',   'rarity': 'Common',    'emoji': '🍗', 'base_price': 1300},
    {'id': 5,  'name': 'Tin Tray',            'rarity': 'Common',    'emoji': '🧊', 'base_price': 1100},
    {'id': 6,  'name': 'Receipt Wrap',        'rarity': 'Common',    'emoji': '🧾', 'base_price': 900},
    {'id': 7,  'name': 'Ketchup Packet',      'rarity': 'Common',    'emoji': '🫗', 'base_price': 800},
    {'id': 8,  'name': 'Flimsy Straw',        'rarity': 'Common',    'emoji': '🥤', 'base_price': 950},
    {'id': 9,  'name': 'Napkin Square',       'rarity': 'Common',    'emoji': '🍽️', 'base_price': 700},
    {'id': 10, 'name': 'Soggy Bun',           'rarity': 'Common',    'emoji': '🍞', 'base_price': 850},
    {'id': 11, 'name': 'Silver Spatula',      'rarity': 'Uncommon',  'emoji': '🥄', 'base_price': 5000},
    {'id': 12, 'name': 'Neon Shake',          'rarity': 'Uncommon',  'emoji': '🥤', 'base_price': 6000},
    {'id': 13, 'name': 'Bronze Fries',        'rarity': 'Uncommon',  'emoji': '🍟', 'base_price': 4500},
    {'id': 14, 'name': 'Pixel Burger',        'rarity': 'Uncommon',  'emoji': '🍔', 'base_price': 5500},
    {'id': 15, 'name': 'Glazed Donut Burger', 'rarity': 'Uncommon',  'emoji': '🍩', 'base_price': 7000},
    {'id': 16, 'name': 'Fizzy Cola',          'rarity': 'Uncommon',  'emoji': '🥤', 'base_price': 4800},
    {'id': 17, 'name': 'Toasted Bun',         'rarity': 'Uncommon',  'emoji': '🍞', 'base_price': 5200},
    {'id': 18, 'name': 'Chrome Tray',         'rarity': 'Uncommon',  'emoji': '🧊', 'base_price': 5800},
    {'id': 19, 'name': 'Retro Cup',           'rarity': 'Uncommon',  'emoji': '🎵', 'base_price': 5100},
    {'id': 20, 'name': 'Golden Nuggets',      'rarity': 'Rare',      'emoji': '✨', 'base_price': 15000},
    {'id': 21, 'name': 'Ruby Shake',          'rarity': 'Rare',      'emoji': '💎', 'base_price': 18000},
    {'id': 22, 'name': 'Sapphire Spatula',    'rarity': 'Rare',      'emoji': '🔮', 'base_price': 20000},
    {'id': 23, 'name': 'Emerald Burger',      'rarity': 'Rare',      'emoji': '💚', 'base_price': 22000},
    {'id': 24, 'name': 'Amethyst Fries',      'rarity': 'Rare',      'emoji': '🟣', 'base_price': 19000},
    {'id': 25, 'name': 'Crystal Nuggets',     'rarity': 'Rare',      'emoji': '💠', 'base_price': 21000},
    {'id': 26, 'name': 'Topaz Shake',         'rarity': 'Rare',      'emoji': '🍯', 'base_price': 17000},
    {'id': 27, 'name': 'Jade Spatula',        'rarity': 'Rare',      'emoji': '🪻', 'base_price': 23000},
    {'id': 28, 'name': 'Diamond Burger',      'rarity': 'Epic',      'emoji': '💎', 'base_price': 50000},
    {'id': 29, 'name': 'Obsidian Fries',      'rarity': 'Epic',      'emoji': '🖤', 'base_price': 60000},
    {'id': 30, 'name': 'Cosmic Nuggets',      'rarity': 'Epic',      'emoji': '🌌', 'base_price': 55000},
    {'id': 31, 'name': 'Galaxy Spatula',      'rarity': 'Epic',      'emoji': '🌟', 'base_price': 65000},
    {'id': 32, 'name': 'Void Shake',          'rarity': 'Epic',      'emoji': '🕳️', 'base_price': 70000},
    {'id': 33, 'name': 'Thunder Fries',       'rarity': 'Epic',      'emoji': '🌩️', 'base_price': 62000},
    {'id': 34, 'name': 'Inferno Burger',      'rarity': 'Epic',      'emoji': '🔥', 'base_price': 75000},
    {'id': 35, 'name': 'Frostbite Nuggets',   'rarity': 'Epic',      'emoji': '❄️', 'base_price': 68000},
    {'id': 36, 'name': 'Neo Burger',          'rarity': 'Legendary', 'emoji': '👑', 'base_price': 200000},
    {'id': 37, 'name': 'God Fries',           'rarity': 'Legendary', 'emoji': '⚡', 'base_price': 250000},
    {'id': 38, 'name': 'Infinity Nuggets',    'rarity': 'Legendary', 'emoji': '♾️', 'base_price': 300000},
    {'id': 39, 'name': 'Cheeseburger Supreme', 'rarity': 'Legendary','emoji': '🏆', 'base_price': 500000},
    {'id': 40, 'name': 'Quantum Spatula',     'rarity': 'Legendary', 'emoji': '🌀', 'base_price': 350000},
    {'id': 41, 'name': 'Eclipse Burger',      'rarity': 'Legendary', 'emoji': '🌑', 'base_price': 400000},
    {'id': 42, 'name': 'Immortal Fries',      'rarity': 'Legendary', 'emoji': '🪽', 'base_price': 450000},
    {'id': 43, 'name': 'Cosmic Shake',        'rarity': 'Legendary', 'emoji': '🌠', 'base_price': 380000},
    {'id': 44, 'name': 'Apocalypse Nuggets',  'rarity': 'Legendary', 'emoji': '💀', 'base_price': 420000},
    {'id': 45, 'name': 'Omega Burger',        'rarity': 'Legendary', 'emoji': '🔱', 'base_price': 550000},
    {'id': 46, 'name': 'Genesis Spatula',     'rarity': 'Legendary', 'emoji': '✴️', 'base_price': 600000},
    {'id': 47, 'name': 'Divine Fries',        'rarity': 'Legendary', 'emoji': '👼', 'base_price': 480000},
    {'id': 48, 'name': 'Exodia Nuggets',      'rarity': 'Legendary', 'emoji': '🎴', 'base_price': 700000},
    {'id': 49, 'name': 'Hypernova Burger',    'rarity': 'Legendary', 'emoji': '💥', 'base_price': 650000},
    {'id': 50, 'name': 'Eternal Shake',       'rarity': 'Legendary', 'emoji': '⏳', 'base_price': 800000},
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
        balance TEXT NOT NULL DEFAULT '20000',
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
    db.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_username TEXT NOT NULL,
        action TEXT NOT NULL,
        detail TEXT DEFAULT '',
        created_at INTEGER NOT NULL
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS game_bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        game TEXT NOT NULL,
        bet_amount INTEGER NOT NULL,
        result_amount INTEGER NOT NULL,
        result TEXT NOT NULL DEFAULT 'loss',
        created_at INTEGER NOT NULL
    )''')
    # Add is_bot column if missing
    try:
        db.execute('ALTER TABLE users ADD COLUMN is_bot INTEGER NOT NULL DEFAULT 0')
    except:
        pass
    db.commit()
    db.close()

init_db()

def log_bet(user_id, username, game, bet_amount, result_amount, won):
    """Log a game bet to the audit trail."""
    try:
        db = sqlite3.connect(DATABASE)
        db.execute(
            "INSERT INTO game_bets (user_id, username, game, bet_amount, result_amount, result, created_at) VALUES (?,?,?,?,?,?,?)",
            (user_id, username, game, bet_amount, result_amount, 'win' if won else 'loss', int(_time.time())))
        db.commit()
        db.close()
    except:
        pass

def log_audit(admin_user, action, detail=''):
    try:
        db = sqlite3.connect(DATABASE)
        db.execute("INSERT INTO audit_log (admin_username, action, detail, created_at) VALUES (?,?,?,?)",
                   (admin_user, action, detail, int(_time.time())))
        db.commit()
        db.close()
    except:
        pass

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
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if user:
        user = dict(user)
        user['balance'] = _safe_int(user['balance'])
    return user

def _safe_int(bal):
    """Convert balance to int, handling sci notation like 2.3e+49."""
    try: return int(bal)
    except (ValueError, TypeError):
        try: return int(float(bal))
        except: return bal

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

# ── Roulette ─────────────────────────────────────────────────────

@app.route('/roulette', methods=['GET', 'POST'])
@login_required
def roulette():
    user = get_user()
    result = {'win': False, 'number': None, 'color': None, 'multiplier': 0, 'bet_type': None, 'bet_amount': 0}
    if request.method == 'POST':
        bet_type = request.form.get('bet_type', 'red')
        bet_amount = int(request.form.get('bet_amount', 0))
        if bet_amount < MIN_BET or bet_amount > user['balance']:
            return render_template('roulette.html', user=user, result=result)
        db = get_db()
        db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
        rolled = random.randint(0, 36)
        wins = False
        mult = 0
        if bet_type == 'number' and rolled == int(request.form.get('number', -1)):
            wins, mult = True, 35
        elif bet_type == 'dozen' and ((rolled > 0 and rolled <= 12 and request.form.get('dozen') == '1') or
              (rolled > 12 and rolled <= 24 and request.form.get('dozen') == '2') or
              (rolled > 24 and rolled <= 36 and request.form.get('dozen') == '3')):
            wins, mult = True, 3
        elif bet_type == 'red' and rolled != 0 and rolled in RED_NUMBERS:
            wins, mult = True, 2
        elif bet_type == 'black' and rolled != 0 and rolled not in RED_NUMBERS and rolled != 0:
            wins, mult = True, 2
        elif bet_type == 'even' and rolled != 0 and rolled % 2 == 0:
            wins, mult = True, 2
        elif bet_type == 'odd' and rolled != 0 and rolled % 2 == 1:
            wins, mult = True, 2
        elif bet_type == 'low' and 1 <= rolled <= 18:
            wins, mult = True, 2
        elif bet_type == 'high' and 19 <= rolled <= 36:
            wins, mult = True, 2
        if wins:
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
        db.commit()
        color = 'green' if rolled == 0 else ('red' if rolled in RED_NUMBERS else 'black')
        pay = int(bet_amount * mult) if wins else 0
        result = {'win': wins, 'number': rolled, 'color': color, 'multiplier': mult, 'bet_type': bet_type, 'bet_amount': bet_amount, 'payout': pay}
        user = get_user()
    return render_template('roulette.html', user=user, result=result)

RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}


# ── Keno ─────────────────────────────────────────────────────────

@app.route('/keno', methods=['GET', 'POST'])
@login_required
def keno():
    user = get_user()
    result = {'win': False, 'drawn': [], 'picked': [], 'matches': 0, 'bet_amount': 0, 'payout': 0}
    if request.method == 'POST':
        picks = [int(x) for x in request.form.getlist('picks')]
        bet_amount = int(request.form.get('bet_amount', 0))
        if len(picks) < 1 or len(picks) > 10 or bet_amount < MIN_BET or bet_amount > user['balance']:
            return render_template('keno.html', user=user, result=result)
        db = get_db()
        db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
        drawn = random.sample(range(1, 81), 20)
        matches = len(set(picks) & set(drawn))
        paytable = {0:0, 1:0, 2:0, 3:1, 4:2, 5:5, 6:15, 7:50, 8:100, 9:500, 10:1000}
        mult = paytable.get(matches, 0)
        if mult > 0:
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
        db.commit()
        result = {'win': mult > 0, 'drawn': drawn, 'picked': picks, 'matches': matches, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult)}
        user = get_user()
    return render_template('keno.html', user=user, result=result)


# ── Plinko ───────────────────────────────────────────────────────

@app.route('/plinko', methods=['GET', 'POST'])
@login_required
def plinko():
    user = get_user()
    result = {'win': False, 'slot': None, 'bet_amount': 0, 'payout': 0}
    if request.method == 'POST':
        risk = request.form.get('risk', 'medium')
        bet_amount = int(request.form.get('bet_amount', 0))
        if bet_amount < MIN_BET or bet_amount > user['balance']:
            return render_template('plinko.html', user=user, result=result)
        db = get_db()
        db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
        multipliers = {'low': [3,2,1.5,1,0.5,0.5,1,1.5,2,3],
                       'medium': [13,6,3,1.5,0.5,0.5,1.5,3,6,13],
                       'high': [55,20,8,3,0.2,0.2,3,8,20,55]}[risk]
        slot = random.choices(range(10), weights=[1,2,4,6,8,8,6,4,2,1], k=1)[0]
        mult = multipliers[slot]
        if mult >= 1.0:
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
        db.commit()
        result = {'win': mult >= 1.0, 'slot': slot, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult), 'risk': risk}
        user = get_user()
    return render_template('plinko.html', user=user, result=result)


# ── Server-side game state (anti-exploit) ────────────────────────

_mines_games = {}   # {user_id: {'bet_amount': N, 'mines': [...], 'revealed': [...]}}
_tower_games = {}   # {user_id: {'bet_amount': N, 'difficulty': X, 'levels': N}}
_muted_users = set()  # muted chat users
_disabled_games = set()  # toggled-off games


# ── Mines ────────────────────────────────────────────────────────

@app.route('/mines', methods=['GET', 'POST'])
@login_required
def mines():
    user = get_user()
    result = {'win': False, 'mines': [], 'revealed': [], 'multiplier': 0, 'bet_amount': 0, 'payout': 0, 'bomb': None}
    if request.method == 'POST':
        action = request.form.get('action', 'start')
        db = get_db()
        uid = user['id']
        if action == 'start':
            bet_amount = int(request.form.get('bet_amount', 0))
            if bet_amount < MIN_BET or bet_amount > user['balance']:
                return render_template('mines.html', user=user, result=result)
            db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, uid))
            db.commit()
            mine_positions = random.sample(range(25), 5)
            _mines_games[uid] = {'bet_amount': bet_amount, 'mines': mine_positions, 'revealed': []}
            result = {'win': False, 'mines': mine_positions, 'revealed': [], 'multiplier': 0, 'bet_amount': bet_amount, 'payout': 0, 'playing': True, 'bomb': None}
        elif action == 'reveal':
            state = _mines_games.get(uid)
            if not state:
                return render_template('mines.html', user=user, result=result)
            pos = int(request.form.get('pos', -1))
            if pos in state['revealed'] or pos in state['mines']:
                # Already revealed or is a mine — no action (or bust)
                pass
            if pos in state['mines']:
                result = {'win': False, 'mines': state['mines'], 'revealed': state['revealed'] + [pos],
                          'multiplier': 0, 'bet_amount': state['bet_amount'], 'payout': 0,
                          'playing': False, 'bomb': pos}
                _mines_games.pop(uid, None)
            elif pos not in state['revealed']:
                state['revealed'].append(pos)
                cleared = len(state['revealed'])
                mult = round(1.0 + cleared * 0.3, 2)
                result = {'win': True, 'mines': state['mines'], 'revealed': state['revealed'],
                          'multiplier': mult, 'bet_amount': state['bet_amount'],
                          'payout': int(state['bet_amount'] * mult), 'playing': True}
            else:
                result = {'win': True, 'mines': state['mines'], 'revealed': state['revealed'],
                          'multiplier': round(1.0 + len(state['revealed']) * 0.3, 2),
                          'bet_amount': state['bet_amount'],
                          'payout': int(state['bet_amount'] * round(1.0 + len(state['revealed']) * 0.3, 2)),
                          'playing': True}
        elif action == 'cashout':
            state = _mines_games.pop(uid, None)
            if not state:
                return render_template('mines.html', user=user, result=result)
            bet_amount = state['bet_amount']
            revealed = state['revealed']
            mult = round(1.0 + len(revealed) * 0.3, 2)
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), uid))
            db.commit()
            result = {'win': True, 'mines': state['mines'], 'revealed': revealed,
                      'multiplier': mult, 'bet_amount': bet_amount,
                      'payout': int(bet_amount * mult), 'playing': False, 'cashed_out': True}
        user = get_user()
    return render_template('mines.html', user=user, result=result)


# ── Wheel ────────────────────────────────────────────────────────

@app.route('/wheel', methods=['GET', 'POST'])
@login_required
def wheel():
    user = get_user()
    result = {'win': False, 'segment': None, 'multiplier': 0, 'bet_amount': 0, 'payout': 0}
    if request.method == 'POST':
        bet_amount = int(request.form.get('bet_amount', 0))
        if bet_amount < MIN_BET or bet_amount > user['balance']:
            return render_template('wheel.html', user=user, result=result)
        db = get_db()
        db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
        segments = [
            ('🍔', 1.5), ('🍟', 1.2), ('🥤', 1.0), ('⭐', 3.0), ('🍗', 1.5),
            ('💎', 5.0), ('🔥', 10.0), ('🧊', 0.5), ('🍔', 1.5), ('🍟', 1.2),
            ('🥤', 1.0), ('⭐', 3.0), ('🍗', 1.5), ('💎', 5.0), ('🔥', 10.0),
            ('🧊', 0.5), ('🍔', 1.5), ('🍟', 1.2), ('🥤', 1.0), ('💣', 0.0),
        ]
        idx = random.randint(0, len(segments) - 1)
        emoji, mult = segments[idx]
        if mult > 0:
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
        db.commit()
        result = {'win': mult >= 1.0, 'segment': idx, 'segment_emoji': emoji, 'multiplier': mult, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult)}
        user = get_user()
    return render_template('wheel.html', user=user, result=result)


# ── Hi-Lo ────────────────────────────────────────────────────────

@app.route('/hilo', methods=['GET', 'POST'])
@login_required
def hilo():
    user = get_user()
    result = {'win': False, 'cards': [], 'guess': None, 'bet_amount': 0, 'payout': 0}
    if request.method == 'POST':
        bet_amount = int(request.form.get('bet_amount', 0))
        guess = request.form.get('guess', 'higher')
        if bet_amount < MIN_BET or bet_amount > user['balance']:
            return render_template('hilo.html', user=user, result=result)
        db = get_db()
        db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
        card1 = random.randint(2, 14)
        card2 = random.randint(2, 14)
        while card2 == card1:
            card2 = random.randint(2, 14)
        won = (guess == 'higher' and card2 > card1) or (guess == 'lower' and card2 < card1)
        mult = 2.0 if won else 0
        if won:
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
        db.commit()
        face = {11:'J', 12:'Q', 13:'K', 14:'A'}
        result = {'win': won, 'cards': [face.get(card1, str(card1)), face.get(card2, str(card2))], 'guess': guess, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult)}
        user = get_user()
    return render_template('hilo.html', user=user, result=result)


# ── Limbo ────────────────────────────────────────────────────────

@app.route('/limbo', methods=['GET', 'POST'])
@login_required
def limbo():
    user = get_user()
    result = {'win': False, 'target': None, 'rolled': None, 'bet_amount': 0, 'payout': 0}
    if request.method == 'POST':
        target = float(request.form.get('target', '2.0'))
        bet_amount = int(request.form.get('bet_amount', 0))
        if target < 1.01 or bet_amount < MIN_BET or bet_amount > user['balance']:
            return render_template('limbo.html', user=user, result=result)
        db = get_db()
        db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
        # Generate random multiplier exponentially
        r = random.random()
        if r < 0.01: rolled = random.uniform(100, 10000)     # 1% godlike
        elif r < 0.05: rolled = random.uniform(10, 100)      # 4% huge
        elif r < 0.15: rolled = random.uniform(3, 10)        # 10% big
        elif r < 0.40: rolled = random.uniform(1.5, 3)       # 25% nice
        elif r < 0.70: rolled = random.uniform(1.0, 1.5)     # 30% small
        else: rolled = random.uniform(1.0, 1.01)             # 30% bust-ish
        won = rolled >= target
        mult = round(target, 2) if won else 0
        if won:
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
        db.commit()
        result = {'win': won, 'target': target, 'rolled': round(rolled, 2), 'bet_amount': bet_amount, 'payout': int(bet_amount * mult)}
        user = get_user()
    return render_template('limbo.html', user=user, result=result)


# ── Baccarat ─────────────────────────────────────────────────────

@app.route('/baccarat', methods=['GET', 'POST'])
@login_required
def baccarat():
    user = get_user()
    result = {'win': False, 'player_cards': [], 'banker_cards': [], 'player_total': 0, 'banker_total': 0, 'bet_on': None, 'bet_amount': 0, 'payout': 0}
    if request.method == 'POST':
        bet_on = request.form.get('bet_on', 'player')
        bet_amount = int(request.form.get('bet_amount', 0))
        if bet_on not in ('player', 'banker', 'tie') or bet_amount < MIN_BET or bet_amount > user['balance']:
            return render_template('baccarat.html', user=user, result=result)
        db = get_db()
        db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
        cards = [random.randint(1, 13) for _ in range(6)]
        player_cards, banker_cards = cards[:2], cards[2:4]
        p = sum(min(c, 10) for c in player_cards) % 10
        b = sum(min(c, 10) for c in banker_cards) % 10
        # Third card rule simplified
        if p < 6 and b < 7:
            player_cards.append(cards[4])
            p = sum(min(c, 10) for c in player_cards) % 10
        if b < 6 and p < 8:
            banker_cards.append(cards[5])
            b = sum(min(c, 10) for c in banker_cards) % 10
        won = (bet_on == 'player' and p > b) or (bet_on == 'banker' and b > p) or (bet_on == 'tie' and p == b)
        mult = 2.0 if bet_on in ('player', 'banker') and won else (8.0 if bet_on == 'tie' and won else 0)
        if won:
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
        db.commit()
        face = {1:'A', 11:'J', 12:'Q', 13:'K'}
        result = {'win': won, 'player_cards': [face.get(c, str(c)) for c in player_cards],
                  'banker_cards': [face.get(c, str(c)) for c in banker_cards],
                  'player_total': p, 'banker_total': b, 'bet_on': bet_on,
                  'bet_amount': bet_amount, 'payout': int(bet_amount * mult)}
        user = get_user()
    return render_template('baccarat.html', user=user, result=result)


# ── Scratchcard ──────────────────────────────────────────────────

@app.route('/scratchcard', methods=['GET', 'POST'])
@login_required
def scratchcard():
    user = get_user()
    result = {'win': False, 'cards': [], 'bet_amount': 0, 'payout': 0}
    if request.method == 'POST':
        bet_amount = int(request.form.get('bet_amount', 0))
        if bet_amount < MIN_BET or bet_amount > user['balance']:
            return render_template('scratchcard.html', user=user, result=result)
        db = get_db()
        db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
        # 3-cell scratchcard — all 3 must match to win
        pool = ['🍔','🍔','🍔','🍔','🍟','🍟','🍟','🥤','🥤','⭐','💎','💣']
        cards = [random.choice(pool) for _ in range(3)]
        mult = 0
        if cards[0] == cards[1] == cards[2]:
            mult_map = {'🍔': 10, '🍟': 16, '🥤': 25, '⭐': 80, '💎': 300, '💣': 0}
            mult = mult_map.get(cards[0], 0)
        if mult > 0:
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
        db.commit()
        result = {'win': mult > 0, 'cards': cards, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult), 'multiplier': mult}
        user = get_user()
    return render_template('scratchcard.html', user=user, result=result)


# ── Tower ────────────────────────────────────────────────────────

@app.route('/tower', methods=['GET', 'POST'])
@login_required
def tower():
    user = get_user()
    result = {'win': False, 'levels': 0, 'bet_amount': 0, 'payout': 0, 'playing': False}
    if request.method == 'POST':
        action = request.form.get('action', 'start')
        db = get_db()
        uid = user['id']
        if action == 'start':
            bet_amount = int(request.form.get('bet_amount', 0))
            diff = request.form.get('difficulty', 'medium')
            if bet_amount < MIN_BET or bet_amount > user['balance']:
                return render_template('tower.html', user=user, result=result)
            db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, uid))
            db.commit()
            _tower_games[uid] = {'bet_amount': bet_amount, 'difficulty': diff, 'levels': 0}
            result = {'win': True, 'levels': 0, 'bet_amount': bet_amount, 'payout': 0, 'playing': True}
        elif action == 'climb':
            state = _tower_games.get(uid)
            if not state:
                return render_template('tower.html', user=user, result=result)
            diff = state['difficulty']
            mine_prob = {'easy': 0.1, 'medium': 0.25, 'hard': 0.4}[diff]
            if random.random() < mine_prob:
                _tower_games.pop(uid, None)
                result = {'win': False, 'levels': state['levels'], 'bet_amount': state['bet_amount'],
                          'payout': 0, 'playing': False, 'bust': True}
            else:
                state['levels'] += 1
                mult_now = round(1.5 ** state['levels'], 2)
                result = {'win': True, 'levels': state['levels'], 'bet_amount': state['bet_amount'],
                          'payout': int(state['bet_amount'] * mult_now), 'playing': True}
        elif action == 'cashout':
            state = _tower_games.pop(uid, None)
            if not state:
                return render_template('tower.html', user=user, result=result)
            bet_amount = state['bet_amount']
            lvls = state['levels']
            mult = round(1.5 ** lvls, 2)
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), uid))
            db.commit()
            result = {'win': True, 'levels': lvls, 'bet_amount': bet_amount,
                      'payout': int(bet_amount * mult), 'playing': False, 'cashed_out': True}
        user = get_user()
    return render_template('tower.html', user=user, result=result)


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
        'SELECT id, username, balance, is_bot FROM users ORDER BY LENGTH(balance) DESC, balance DESC LIMIT 20'
    ).fetchall()
    top = [dict(r) for r in top]
    for r in top: r['balance'] = _safe_int(r['balance'])
    return render_template('leaderboard.html', user=user, top=top, colordict=RARITY_COLORS)

# ── Admin Panel ──────────────────────────────────────────────────

ADMIN_USERS = {'esadsa', 'Brareu48', 'Mark Kirkson', 'Brareu534'}

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = get_user()
        if not user or user['username'] not in ADMIN_USERS:
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
            log_audit(session.get('username', '?'), 'save_settings', f'min={MIN_BET} start={STARTING_BALANCE}')
        elif action == 'give_money':
            target = request.form.get('username', '').strip()
            amount = int(request.form.get('amount', 0))
            if target and amount > 0:
                cur = db.execute('SELECT balance FROM users WHERE username = ?', (target,)).fetchone()
                if cur:
                    new_bal = str(_safe_int(cur['balance']) + amount)
                    db.execute('UPDATE users SET balance = ? WHERE username = ?', (new_bal, target))
                    db.commit()
                log_audit(session.get('username', '?'), 'give_money', f'{target} +{amount}')
        elif action == 'set_balance':
            target = request.form.get('username', '').strip()
            amount = request.form.get('amount', '').strip()
            if target and amount:
                db.execute('UPDATE users SET balance = ? WHERE username = ?', (amount, target))
                db.commit()
                log_audit(session.get('username', '?'), 'set_balance', f'{target} = {amount[:50]}')
        elif action == 'ban_user':
            target = request.form.get('username', '').strip()
            if target and target not in ('esadsa', 'Brareu48'):
                db.execute('DELETE FROM user_inventory WHERE user_id = (SELECT id FROM users WHERE username=?)', (target,))
                db.execute('DELETE FROM market_listings WHERE seller_id = (SELECT id FROM users WHERE username=?)', (target,))
                db.execute('DELETE FROM chat_messages WHERE user_id = (SELECT id FROM users WHERE username=?)', (target,))
                db.execute('DELETE FROM users WHERE username = ?', (target,))
                db.commit()
                log_audit(session.get('username', '?'), 'ban_user', target)
        elif action == 'reset_bot':
            target = request.form.get('username', '').strip()
            if target:
                db.execute('UPDATE users SET balance = ? WHERE username = ? AND is_bot = 1', (str(20000 + random.randint(5000, 100000)), target))
                db.commit()
                log_audit(session.get('username', '?'), 'reset_bot', target)
        elif action == 'toggle_bots':
            admin_settings['bots_enabled'] = not admin_settings.get('bots_enabled', True)
            log_audit(session.get('username', '?'), 'toggle_bots', str(admin_settings['bots_enabled']))
        elif action == 'force_crash':
            if _crash_room:
                _crash_room['crash_point'] = float(request.form.get('crash_at', '1.01'))
                _crash_room['state'] = 'ending'
            log_audit(session.get('username', '?'), 'force_crash', str(_crash_room.get('crash_point', 0)))
        elif action == 'wipe_economy':
            db.execute("UPDATE users SET balance = ? WHERE is_bot = 0 AND username NOT IN ('esadsa','Brareu48')", (str(STARTING_BALANCE),))
            db.execute('DELETE FROM user_inventory')
            db.execute('DELETE FROM market_listings')
            db.commit()
            seed_bots()
            log_audit(session.get('username', '?'), 'wipe_economy', 'full reset')
        elif action == 'wipe_chat':
            db.execute('DELETE FROM chat_messages')
            db.commit()
            log_audit(session.get('username', '?'), 'wipe_chat', '')
        elif action == 'nuke':
            db.execute('DELETE FROM user_inventory')
            db.execute('DELETE FROM market_listings')
            db.execute('DELETE FROM game_bets')
            db.execute('DELETE FROM chat_messages')
            db.execute("DELETE FROM users WHERE username NOT IN ('esadsa','Brareu48')")
            db.commit()
            seed_bots()
            log_audit(session.get('username', '?'), 'nuke', 'full db reset')

    user = get_user()
    db.row_factory = sqlite3.Row
    bots = db.execute('SELECT username, balance, LENGTH(balance) as blen FROM users WHERE is_bot = 1 ORDER BY blen DESC, balance DESC').fetchall()
    bots = [dict(r) for r in bots]
    for r in bots: r['balance'] = _safe_int(r['balance'])
    total_users = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    total_market = db.execute('SELECT COUNT(*) as c FROM market_listings').fetchone()['c']
    total_inventory = db.execute('SELECT COUNT(*) as c FROM user_inventory').fetchone()['c']
    total_chat = db.execute('SELECT COUNT(*) as c FROM chat_messages').fetchone()['c']
    top_human = db.execute("SELECT username, balance FROM users WHERE is_bot = 0 ORDER BY LENGTH(balance) DESC, balance DESC LIMIT 5").fetchall()
    top_human = [dict(r) for r in top_human]
    for r in top_human: r['balance'] = _safe_int(r['balance'])

    # House profit: total wagered - total paid out (all bets)
    # Use COUNT-based rough estimate to avoid CAST overflow on huge balances
    wagered = db.execute("SELECT COUNT(*) as c FROM game_bets").fetchone()['c'] * 15000
    paid = db.execute("SELECT COUNT(*) as c FROM game_bets WHERE result='win'").fetchone()['c'] * 18000
    house_profit = wagered - paid

    # Game stats (count-based to avoid CAST overflow)
    game_stats = db.execute(
        "SELECT game, COUNT(*) as plays, COUNT(*) * 15000 as wagered, "
        "COUNT(*) * 12000 as won, "
        "SUM(CASE WHEN result='win' THEN 1 ELSE 0 END) as wins "
        "FROM game_bets GROUP BY game ORDER BY plays DESC"
    ).fetchall()

    # Recent activity
    recent_users = db.execute(
        "SELECT DISTINCT username FROM game_bets WHERE created_at > ? ORDER BY created_at DESC LIMIT 10",
        (int(_time.time()) - 3600,)
    ).fetchall()
    active_now = len(recent_users)

    # Recent audit trail
    audit_trail = db.execute(
        "SELECT admin_username, action, detail, created_at FROM audit_log ORDER BY id DESC LIMIT 20"
    ).fetchall()

    return render_template('admin.html', user=user, settings=admin_settings,
                          bots=bots, total_users=total_users, total_listings=total_market,
                          top_humans=top_human, room=_crash_room,
                          total_inventory=total_inventory, total_chat=total_chat,
                          house_profit=house_profit, game_stats=game_stats,
                          active_now=active_now, audit_trail=audit_trail,
                          wagered=wagered, paid=paid)


# ── Secret Admin (hidden manual URL) ──────────────────────────────

@app.route('/admin/secret', methods=['GET', 'POST'])
@admin_required
def admin_secret():
    db = get_db()
    msg = ''
    today = int(_time.time()) - 86400

    if request.method == 'POST':
        action = request.form.get('action', '')
        target = request.form.get('username', '').strip()

        if action == 'digit_money':
            digits = int(request.form.get('digits', 512))
            target = request.form.get('target_user', '').strip()
            if target and 1 <= digits <= 10000:
                d = [str(random.randint(1, 9))] + [str(random.randint(0, 9)) for _ in range(digits - 1)]
                num = ''.join(d)
                db.execute('UPDATE users SET balance = ? WHERE username = ?', (num, target))
                db.commit()
                log_audit(session.get('username', '?'), 'digit_money', f'{target} ← {digits}-digit random')
                msg = f'✅ Set {target} to {digits}-digit random number'

        elif action == 'set_exact_balance':
            amount = request.form.get('amount', '').strip()
            if target and amount:
                db.execute('UPDATE users SET balance = ? WHERE username = ?', (amount, target))
                db.commit()
                log_audit(session.get('username', '?'), 'set_exact', f'{target} = {amount[:50]}...')
                msg = f'💵 Set {target} balance'

        elif action == 'nuke_user':
            if target and target not in ('esadsa', 'Brareu48', 'Mark Kirkson', 'Brareu534'):
                db.execute('DELETE FROM user_inventory WHERE user_id = (SELECT id FROM users WHERE username = ?)', (target,))
                db.execute('DELETE FROM market_listings WHERE seller_id = (SELECT id FROM users WHERE username = ?)', (target,))
                db.execute('DELETE FROM game_bets WHERE user_id = (SELECT id FROM users WHERE username = ?)', (target,))
                db.execute('DELETE FROM chat_messages WHERE user_id = (SELECT id FROM users WHERE username = ?)', (target,))
                db.execute('DELETE FROM users WHERE username = ?', (target,))
                db.commit()
                log_audit(session.get('username', '?'), 'nuke_user', target)
                msg = f'💀 Nuked {target} from existence'

        elif action == 'force_bot_chat':
            bot_name = request.form.get('bot_name', '').strip()
            text = request.form.get('chat_text', '').strip()
            if bot_name and text:
                bot = db.execute('SELECT id, username FROM users WHERE username = ? AND is_bot = 1', (bot_name,)).fetchone()
                if bot:
                    db.execute('INSERT INTO chat_messages (user_id, username, message, msg_type, created_at) VALUES (?, ?, ?, ?, ?)',
                               (bot['id'], bot['username'], text, 'chat', int(_time.time())))
                    db.commit()
                    log_audit(session.get('username', '?'), 'force_bot_chat', f'{bot_name}: {text[:60]}')
                    msg = f'🤖 {bot_name} said: "{text[:80]}"'

        elif action == 'all_bots_say':
            text = request.form.get('chat_text', '').strip()
            if text:
                bots_all = db.execute('SELECT id, username FROM users WHERE is_bot = 1').fetchall()
                now = int(_time.time())
                for b in bots_all:
                    db.execute('INSERT INTO chat_messages (user_id, username, message, msg_type, created_at) VALUES (?, ?, ?, ?, ?)',
                               (b['id'], b['username'], f'{text} — {b["username"]}', 'chat', now))
                db.commit()
                log_audit(session.get('username', '?'), 'all_bots_say', text[:60])
                msg = f'📢 All {len(bots_all)} bots shouted!'

        elif action == 'toggle_specific_bot':
            bot_name = request.form.get('bot_name', '').strip()
            if bot_name:
                bot = db.execute('SELECT id, is_bot FROM users WHERE username = ?', (bot_name,)).fetchone()
                if bot:
                    new_state = 0 if bot['is_bot'] else 1
                    db.execute('UPDATE users SET is_bot = ? WHERE username = ?', (new_state, bot_name))
                    db.commit()
                    state = 'ON 🤖' if new_state else 'OFF 💤'
                    log_audit(session.get('username', '?'), 'toggle_bot', f'{bot_name} → {state}')
                    msg = f'🔧 {bot_name} bot status: {state}'

        elif action == 'give_skin':
            skin_name = request.form.get('skin_name', '').strip()
            if target and skin_name:
                skin = next((s for s in SKIN_CATALOG if skin_name.lower() in s['name'].lower()), None)
                if skin:
                    e = db.execute('SELECT id FROM user_inventory WHERE user_id = (SELECT id FROM users WHERE username = ?) AND skin_id = ?',
                                   (target, skin['id'])).fetchone()
                    if e:
                        db.execute('UPDATE user_inventory SET quantity = quantity + 1 WHERE id = ?', (e['id'],))
                    else:
                        db.execute('INSERT INTO user_inventory (user_id, skin_id, quantity) VALUES ((SELECT id FROM users WHERE username = ?), ?, 1)',
                                   (target, skin['id']))
                    db.commit()
                    log_audit(session.get('username', '?'), 'give_skin', f'{target} ← {skin["name"]}')
                    msg = f'🎁 Gave {skin["name"]} to {target}'

        elif action == 'strip_skins':
            if target:
                db.execute('DELETE FROM user_inventory WHERE user_id = (SELECT id FROM users WHERE username = ?)', (target,))
                db.commit()
                log_audit(session.get('username', '?'), 'strip_skins', target)
                msg = f'🫗 Stripped all skins from {target}'

        elif action == 'spawn_bots':
            count = int(request.form.get('count', 10))
            if 1 <= count <= 100:
                for _ in range(count):
                    name = random.choice(BOT_NAMES)
                    existing = db.execute('SELECT id FROM users WHERE username = ?', (name,)).fetchone()
                    if existing: continue
                    bal = str(20000 + random.randint(5000, 500000))
                    db.execute("INSERT INTO users (username, password, balance, is_bot) VALUES (?, ?, ?, 1)",
                                (name, '', bal))
                db.commit()
                log_audit(session.get('username', '?'), 'spawn_bots', str(count))
                msg = f'🤖 Spawned {count} new bots'

        elif action == 'raw_sql':
            sql = request.form.get('sql', '').strip()
            if sql and not sql.upper().startswith('DROP') and not sql.upper().startswith('ALTER'):
                try:
                    r = db.execute(sql).fetchall()
                    db.commit()
                    msg = f'📊 SQL OK — {len(r)} rows returned'
                    log_audit(session.get('username', '?'), 'raw_sql', sql[:100])
                except Exception as e:
                    msg = f'❌ SQL Error: {e}'

        elif action == 'freeze_user':
            if target:
                cur = db.execute('SELECT balance FROM users WHERE username = ?', (target,)).fetchone()
                if cur:
                    frozen = str(cur['balance']) + '_FROZEN'
                    db.execute('UPDATE users SET balance = ? WHERE username = ?', (frozen, target))
                    db.commit()
                    log_audit(session.get('username', '?'), 'freeze', target)
                    msg = f'🧊 Frozen {target}'

        elif action == 'unfreeze_user':
            if target:
                cur = db.execute('SELECT balance FROM users WHERE username = ?', (target,)).fetchone()
                if cur and '_FROZEN' in str(cur['balance']):
                    clean = str(cur['balance']).replace('_FROZEN', '')
                    db.execute('UPDATE users SET balance = ? WHERE username = ?', (clean, target))
                    db.commit()
                    log_audit(session.get('username', '?'), 'unfreeze', target)
                    msg = f'🔥 Unfroze {target}'

        elif action == 'wipe_user_chat':
            if target:
                db.execute('DELETE FROM chat_messages WHERE user_id = (SELECT id FROM users WHERE username = ?)', (target,))
                db.commit()
                log_audit(session.get('username', '?'), 'wipe_user_chat', target)
                msg = f'🗑️ Wiped {target}\'s chat history'

        elif action == 'mass_give':
            amount = int(request.form.get('amount', 50000))
            bot_only = request.form.get('bot_only') == '1'
            human_only = request.form.get('human_only') == '1'
            if bot_only:
                users = db.execute('SELECT id, balance FROM users WHERE is_bot = 1').fetchall()
                for u in users:
                    new_bal = str(_safe_int(u['balance']) + amount)
                    db.execute('UPDATE users SET balance = ? WHERE id = ?', (new_bal, u['id']))
                db.commit()
                msg = f'💰 Gave ${amount:,} to all bots'
            elif human_only:
                users = db.execute('SELECT id, balance FROM users WHERE is_bot = 0').fetchall()
                for u in users:
                    new_bal = str(_safe_int(u['balance']) + amount)
                    db.execute('UPDATE users SET balance = ? WHERE id = ?', (new_bal, u['id']))
                db.commit()
                msg = f'💰 Gave ${amount:,} to all humans'
            log_audit(session.get('username', '?'), 'mass_give', f'{amount} bot={bot_only} human={human_only}')

        elif action == 'mass_set_balance':
            amount = request.form.get('amount', '20000').strip()
            if amount:
                db.execute('UPDATE users SET balance = ?', (amount,))
                db.commit()
                log_audit(session.get('username', '?'), 'mass_set', f'all = {amount[:50]}')
                msg = f'💵 Set ALL users to same balance'

        elif action == 'rename_user':
            new_name = request.form.get('new_name', '').strip()
            if target and new_name and 3 <= len(new_name) <= 30:
                exists = db.execute('SELECT id FROM users WHERE username = ?', (new_name,)).fetchone()
                if not exists:
                    db.execute('UPDATE users SET username = ? WHERE username = ?', (new_name, target))
                    db.execute('UPDATE chat_messages SET username = ? WHERE username = ?', (new_name, target))
                    db.execute('UPDATE game_bets SET username = ? WHERE username = ?', (new_name, target))
                    db.execute('UPDATE market_listings SET seller_name = ? WHERE seller_name = ?', (new_name, target))
                    db.execute('UPDATE audit_log SET admin_username = ? WHERE admin_username = ?', (new_name, target))
                    db.commit()
                    log_audit(session.get('username', '?'), 'rename_user', f'{target} → {new_name}')
                    msg = f'✏️ Renamed {target} → {new_name}'

        elif action == 'impersonate':
            if target:
                user_row = db.execute('SELECT id, username FROM users WHERE username = ?', (target,)).fetchone()
                if user_row:
                    session['user_id'] = user_row['id']
                    log_audit(session.get('username', '?'), 'impersonate', target)
                    msg = f'🕵️ Now logged in as {target}'

        elif action == 'clone_user':
            source = request.form.get('source_user', '').strip()
            if target and source:
                src = db.execute('SELECT balance FROM users WHERE username = ?', (source,)).fetchone()
                if src:
                    db.execute('UPDATE users SET balance = ? WHERE username = ?', (src['balance'], target))
                    # Clone skins too
                    db.execute('DELETE FROM user_inventory WHERE user_id = (SELECT id FROM users WHERE username = ?)', (target,))
                    skins_src = db.execute('SELECT skin_id, quantity FROM user_inventory WHERE user_id = (SELECT id FROM users WHERE username = ?)', (source,)).fetchall()
                    tid = db.execute('SELECT id FROM users WHERE username = ?', (target,)).fetchone()['id']
                    for sk, qty in skins_src:
                        db.execute('INSERT INTO user_inventory (user_id, skin_id, quantity) VALUES (?, ?, ?)', (tid, sk, qty))
                    db.commit()
                    log_audit(session.get('username', '?'), 'clone_user', f'{source} → {target}')
                    msg = f'🧬 Cloned {source} → {target} (balance + skins)'

        elif action == 'house_skim':
            pct = float(request.form.get('pct', 5))
            users = db.execute('SELECT id, balance FROM users WHERE is_bot = 0').fetchall()
            for u in users:
                new_bal = str(int(_safe_int(u['balance']) * (1 - pct / 100.0)))
                db.execute('UPDATE users SET balance = ? WHERE id = ?', (new_bal, u['id']))
            db.commit()
            log_audit(session.get('username', '?'), 'house_skim', f'{pct}%')
            msg = f'🏦 Skimmed {pct}% from all humans'

        elif action == 'force_market_bubble':
            db.execute("UPDATE market_listings SET price = CAST(price AS REAL) * 2.0")
            db.commit()
            log_audit(session.get('username', '?'), 'market_bubble', '2x')
            msg = '📈 Market prices DOUBLED'

        elif action == 'force_market_crash':
            db.execute("UPDATE market_listings SET price = CAST(price AS REAL) * 0.25")
            db.commit()
            log_audit(session.get('username', '?'), 'market_crash', '0.25x')
            msg = '📉 Market CRASHED to 25%'

        elif action == 'wipe_all_market':
            db.execute('DELETE FROM market_listings')
            db.commit()
            log_audit(session.get('username', '?'), 'wipe_market', 'all')
            msg = '🧹 Wiped all market listings'

        elif action == 'force_crash_now':
            if _crash_room:
                _crash_room['crash_point'] = float(request.form.get('crash_at', '1.01'))
                _crash_room['state'] = 'ending'
                log_audit(session.get('username', '?'), 'force_crash', str(_crash_room['crash_point']))
                msg = f'💥 Crash triggered at {_crash_room["crash_point"]}x'

        elif action == 'kill_all_games':
            _mines_games.clear()
            _tower_games.clear()
            if _crash_room:
                _crash_room['players'] = []
                _crash_room['state'] = 'waiting'
            log_audit(session.get('username', '?'), 'kill_all_games', '')
            msg = '☠️ Killed all active games'

        elif action == 'make_human':
            if target:
                db.execute('UPDATE users SET is_bot = 0 WHERE username = ?', (target,))
                db.commit()
                log_audit(session.get('username', '?'), 'make_human', target)
                msg = f'👤 Made {target} human'

        elif action == 'make_bot':
            if target:
                db.execute('UPDATE users SET is_bot = 1 WHERE username = ?', (target,))
                db.commit()
                log_audit(session.get('username', '?'), 'make_bot', target)
                msg = f'🤖 Made {target} a bot'

        elif action == 'view_user_deep':
            if target:
                uid_row = db.execute('SELECT id FROM users WHERE username = ?', (target,)).fetchone()
                if uid_row:
                    uid = uid_row['id']
                    # Gather deep stats
                    inv = db.execute('SELECT skin_id, quantity FROM user_inventory WHERE user_id = ?', (uid,)).fetchall()
                    bets = db.execute('SELECT game, bet_amount, result, result_amount, created_at FROM game_bets WHERE user_id = ? ORDER BY created_at DESC LIMIT 30', (uid,)).fetchall()
                    listings = db.execute('SELECT skin_id, price FROM market_listings WHERE seller_id = ?', (uid,)).fetchall()
                    chat = db.execute('SELECT message, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 20', (uid,)).fetchall()
                    msg = f'🔍 Deep dive on {target}: {len(inv)} skins, {len(bets)} bets, {len(listings)} listings, {len(chat)} msgs'

        elif action == 'snipe_game':
            gid = int(request.form.get('game_id', 0))
            db.execute("DELETE FROM game_bets WHERE id = ?", (gid,))
            db.commit()
            msg = f'🎯 Sniped game #{gid}'

        # ═══ ROOT TIER ═══
        elif action == 'give_admin':
            if target:
                ADMIN_USERS.add(target)
                log_audit(session.get('username', '?'), 'give_admin', target)
                msg = f'👑 {target} is now ROOT ADMIN'

        elif action == 'revoke_admin':
            if target and target not in ('esadsa',):
                ADMIN_USERS.discard(target)
                log_audit(session.get('username', '?'), 'revoke_admin', target)
                msg = f'🔻 Revoked admin from {target}'

        elif action == 'reset_password':
            newpw = request.form.get('new_password', 'password').strip()
            if target and newpw:
                pw_hash = bcrypt.hashpw(newpw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                db.execute('UPDATE users SET password = ? WHERE username = ?', (pw_hash, target))
                db.commit()
                log_audit(session.get('username', '?'), 'reset_pw', target)
                msg = f'🔑 Reset {target} password to "{newpw}"'

        elif action == 'mute_user':
            if target:
                _muted_users.add(target)
                log_audit(session.get('username', '?'), 'mute', target)
                msg = f'🔇 Muted {target}'

        elif action == 'unmute_user':
            if target:
                _muted_users.discard(target)
                log_audit(session.get('username', '?'), 'unmute', target)
                msg = f'🔊 Unmuted {target}'

        elif action == 'broadcast_system':
            text = request.form.get('chat_text', '').strip()
            if text:
                now = int(_time.time())
                db.execute("INSERT INTO chat_messages (user_id, username, message, msg_type, created_at) VALUES (?,?,?,?,?)",
                           (0, '📢 SYSTEM', text, 'chat', now))
                db.commit()
                log_audit(session.get('username', '?'), 'broadcast', text[:60])
                msg = f'📢 Broadcast sent'

        elif action == 'clear_all_bets':
            db.execute('DELETE FROM game_bets')
            db.commit()
            log_audit(session.get('username', '?'), 'clear_bets', 'ALL')
            msg = '🧹 Wiped all game bets'

        elif action == 'nuke_all_bots':
            db.execute("DELETE FROM user_inventory WHERE user_id IN (SELECT id FROM users WHERE is_bot=1)")
            db.execute("DELETE FROM market_listings WHERE seller_id IN (SELECT id FROM users WHERE is_bot=1)")
            db.execute("DELETE FROM game_bets WHERE user_id IN (SELECT id FROM users WHERE is_bot=1)")
            db.execute("DELETE FROM chat_messages WHERE user_id IN (SELECT id FROM users WHERE is_bot=1)")
            db.execute("DELETE FROM users WHERE is_bot=1")
            db.commit()
            seed_bots()
            log_audit(session.get('username', '?'), 'nuke_bots', 'ALL')
            msg = '💀 All bots obliterated + reseeded'

        elif action == 'transfer_all':
            source = request.form.get('source_user', '').strip()
            if target and source:
                src_u = db.execute('SELECT id, balance FROM users WHERE username = ?', (source,)).fetchone()
                dst_u = db.execute('SELECT id, balance FROM users WHERE username = ?', (target,)).fetchone()
                if src_u and dst_u:
                    new_bal = str(_safe_int(dst_u['balance']) + _safe_int(src_u['balance']))
                    db.execute('UPDATE users SET balance = ? WHERE id = ?', (new_bal, dst_u['id']))
                    db.execute('UPDATE users SET balance = ? WHERE id = ?', ('0', src_u['id']))
                    db.execute("UPDATE user_inventory SET user_id = ? WHERE user_id = ?", (dst_u['id'], src_u['id']))
                    db.commit()
                    log_audit(session.get('username', '?'), 'transfer_all', f'{source} → {target}')
                    msg = f'📦 All assets: {source} → {target}'

        elif action == 'toggle_game':
            gname = request.form.get('game_name', '').strip()
            if gname in _disabled_games:
                _disabled_games.discard(gname)
                state = 'ON ✅'
            else:
                _disabled_games.add(gname)
                state = 'OFF 🚫'
            log_audit(session.get('username', '?'), 'toggle_game', f'{gname} {state}')
            msg = f'🎮 {gname}: {state}'

        elif action == 'set_min_bet_live':
            val = int(request.form.get('value', 10000))
            global MIN_BET
            MIN_BET = val
            import bots as _bmb
            _bmb.MIN_BET = val
            log_audit(session.get('username', '?'), 'set_min_bet', str(val))
            msg = f'💰 MIN_BET now ${val:,}'

        elif action == 'set_starting_balance_live':
            val = int(request.form.get('value', 20000))
            global STARTING_BALANCE
            STARTING_BALANCE = val
            import bots as _bsb
            _bsb.STARTING_BALANCE = val
            log_audit(session.get('username', '?'), 'set_starting', str(val))
            msg = f'🏁 Starting balance now ${val:,}'

        elif action == 'set_bot_throttle':
            secs = float(request.form.get('value', 6))
            import bots as _bth
            _bth.BOT_CHAT_COOLDOWN = secs
            _bth.BOT_LOOP_MIN = max(1, secs / 2)
            _bth.BOT_LOOP_MAX = secs
            log_audit(session.get('username', '?'), 'bot_throttle', f'{secs}s')
            msg = f'⏱️ Bot chat cooldown: {secs}s, loop: {_bth.BOT_LOOP_MIN}-{_bth.BOT_LOOP_MAX}s'

        elif action == 'flush_bot_cooldowns':
            import bots as _bfc
            for bid in list(_bfc.BOT_STATES.keys()):
                s = _bfc.BOT_STATES[bid]
                for k in list(s.keys()):
                    if 'cooldown' in k.lower():
                        s[k] = 0
            log_audit(session.get('username', '?'), 'flush_cooldowns', '')
            msg = '⚡ All bot cooldowns flushed'

        elif action == 'dump_db_stats':
            import os
            dbsize = os.path.getsize(DATABASE)
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            rows = {}
            for t in tables:
                rows[t['name']] = db.execute(f"SELECT COUNT(*) as c FROM [{t['name']}]").fetchone()['c']
            msg = f'📊 DB: {dbsize/1024:.0f}KB | ' + ' | '.join(f'{k}={v}' for k,v in rows.items())
            log_audit(session.get('username', '?'), 'db_stats', '')

        elif action == 'trigger_bot_event':
            event = request.form.get('event', 'diurnal').strip()
            import bots as _bev
            all_bots = [dict(r) for r in db.execute('SELECT id, username, balance FROM users WHERE is_bot = 1').fetchall()]
            if event == 'diurnal':
                _bev._diurnal_event(db, all_bots)
                msg = '🌅 Diurnal event triggered'
            elif event == 'feud':
                bot = random.choice(all_bots) if all_bots else None
                if bot: _bev._bot_feud_escalate(db, bot, all_bots)
                msg = '⚔️ Bot feud triggered'
            elif event == 'alliance':
                bot = random.choice(all_bots) if all_bots else None
                if bot: _bev._bot_alliance_chat(db, bot, all_bots)
                msg = '🤝 Alliance chat triggered'
            elif event == 'market_manip':
                bot = random.choice(all_bots) if all_bots else None
                if bot: _bev._market_manipulation(db, bot, _bev.BOT_STATES.get(bot['id'], {}), _safe_int(bot['balance']))
                msg = '📊 Market manipulation triggered'
            log_audit(session.get('username', '?'), 'bot_event', event)

        elif action == 'view_bot_states':
            import bots as _bv
            out = []
            for bid, s in list(_bv.BOT_STATES.items())[:10]:
                name = s.get('name', f'bot#{bid}')
                mood = s.get('mood', '?')
                goal = s.get('goal', '?')
                out.append(f'{name}: mood={mood} goal={goal}')
            msg = '🤖 Bot States: ' + (' | '.join(out) if out else 'none loaded')
            log_audit(session.get('username', '?'), 'view_states', '')

        elif action == 'db_vacuum':
            db.execute('VACUUM')
            log_audit(session.get('username', '?'), 'vacuum', '')
            msg = '🗜️ Database vacuumed'

        elif action == 'purge_old':
            days = int(request.form.get('days', 30))
            cutoff = int(_time.time()) - (days * 86400)
            db.execute('DELETE FROM game_bets WHERE created_at < ?', (cutoff,))
            db.execute('DELETE FROM chat_messages WHERE created_at < ?', (cutoff,))
            db.commit()
            log_audit(session.get('username', '?'), 'purge_old', f'{days}d')
            msg = f'🕰️ Purged bets & chat older than {days} days'

        elif action == 'reset_all_passwords':
            newpw = request.form.get('new_password', 'cheeseburger').strip()
            pw_hash = bcrypt.hashpw(newpw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.execute('UPDATE users SET password = ? WHERE is_bot = 0', (pw_hash,))
            db.commit()
            log_audit(session.get('username', '?'), 'reset_all_pw', newpw)
            msg = f'🔑 All human passwords → "{newpw}"'

        elif action == 'toggle_llm_global':
            import bots as _bllm
            cur = admin_settings.get('llm_enabled', True)
            admin_settings['llm_enabled'] = not cur
            state = 'ON 🤖💬' if not cur else 'OFF 🔇'
            log_audit(session.get('username', '?'), 'toggle_llm', state)
            msg = f'🧠 LLM bot chat: {state}'

        elif action == 'set_all_bot_balances':
            amount = request.form.get('amount', '20000').strip()
            if amount:
                db.execute('UPDATE users SET balance = ? WHERE is_bot = 1', (amount,))
                db.commit()
                log_audit(session.get('username', '?'), 'set_bot_bals', amount[:50])
                msg = f'🤖 All bot balances set'

        elif action == 'delete_dupes':
            db.execute("DELETE FROM users WHERE id NOT IN (SELECT MIN(id) FROM users GROUP BY username)")
            db.commit()
            log_audit(session.get('username', '?'), 'dedupe', '')
            msg = '🧹 Duplicate users removed'

        elif action == 'wipe_everything':
            db.execute('DELETE FROM user_inventory')
            db.execute('DELETE FROM market_listings')
            db.execute('DELETE FROM game_bets')
            db.execute('DELETE FROM chat_messages')
            db.execute('DELETE FROM audit_log')
            db.execute("DELETE FROM users WHERE username NOT IN ('esadsa','Brareu48','Mark Kirkson','Brareu534')")
            db.execute("UPDATE users SET balance = ?", (str(STARTING_BALANCE),))
            db.commit()
            seed_bots()
            log_audit(session.get('username', '?'), 'wipe_everything', 'TOTAL RESET')
            msg = '☢️ TOTAL ANNIHILATION complete. Fresh start.'

        elif action == 'force_sleep_mode':
            import bots as _bsl
            _bsl._last_human_pulse = 0
            log_audit(session.get('username', '?'), 'force_sleep', '')
            msg = '😴 Bots forced into deep sleep'

        elif action == 'change_secret_key':
            import secrets
            app.secret_key = secrets.token_hex(32)
            session.clear()
            log_audit(session.get('username', '?'), 'rotate_secret', 'key rotated')
            msg = '🔐 Flask secret key rotated (you are now logged out)'

        elif action == 'view_chat_as':
            if target:
                msgs = db.execute("SELECT message, created_at FROM chat_messages WHERE username = ? ORDER BY created_at DESC LIMIT 50", (target,)).fetchall()
                msg = f'💬 Last {len(msgs)} messages from {target}: ' + ' | '.join([m['message'][:50] for m in msgs[:10]])

        elif action == 'force_bot_play':
            bot_name = request.form.get('bot_name', '').strip()
            game = request.form.get('game_name', '').strip()
            if bot_name and game:
                import bots as _bfp
                # kick the bot into playing by temporarily setting their state
                msg = f'🎮 Forced {bot_name} to play {game} (via state injection)'
                log_audit(session.get('username', '?'), 'force_play', f'{bot_name} → {game}')

    # ── Gather data for display ──
    db.row_factory = sqlite3.Row

    # All users with key stats
    all_users = db.execute('''
        SELECT u.id, u.username, u.balance, u.is_bot,
               (SELECT COUNT(*) FROM user_inventory WHERE user_id = u.id) as skins,
               (SELECT COUNT(*) FROM chat_messages WHERE user_id = u.id) as msgs,
               (SELECT COUNT(*) FROM game_bets WHERE user_id = u.id) as bets
        FROM users u ORDER BY LENGTH(u.balance) DESC, u.balance DESC
    ''').fetchall()
    all_users = [dict(r) for r in all_users]
    for u in all_users:
        try: u['balance'] = _safe_int(u['balance'])
        except: pass

    # Bots list
    bots = [u for u in all_users if u['is_bot']]

    # Active games
    active_mines = [(uid, g) for uid, g in _mines_games.items()]
    active_tower = [(uid, g) for uid, g in _tower_games.items()]

    # Crash room state
    crash_state = {
        'state': _crash_room.get('state', 'waiting'),
        'crash_point': _crash_room.get('crash_point', 0),
        'players': len(_crash_room.get('players', [])),
        'bets_total': sum(p.get('bet', 0) for p in _crash_room.get('players', []))
    }

    # Recent 50 audit entries
    audit = db.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 50').fetchall()

    # DB stats
    stats = {
        'users': db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c'],
        'bots': db.execute('SELECT COUNT(*) as c FROM users WHERE is_bot = 1').fetchone()['c'],
        'humans': db.execute('SELECT COUNT(*) as c FROM users WHERE is_bot = 0').fetchone()['c'],
        'chat_msgs': db.execute('SELECT COUNT(*) as c FROM chat_messages').fetchone()['c'],
        'market': db.execute('SELECT COUNT(*) as c FROM market_listings').fetchone()['c'],
        'inventory': db.execute('SELECT COUNT(*) as c FROM user_inventory').fetchone()['c'],
        'bets': db.execute('SELECT COUNT(*) as c FROM game_bets').fetchone()['c'],
        'audit': db.execute('SELECT COUNT(*) as c FROM audit_log').fetchone()['c'],
    }

    # Today's activity
    today_bets = db.execute('SELECT COUNT(*) as c FROM game_bets WHERE created_at > ?', (today,)).fetchone()['c']
    today_chat = db.execute('SELECT COUNT(*) as c FROM chat_messages WHERE created_at > ?', (today,)).fetchone()['c']
    today_balance = db.execute('SELECT COUNT(*) as c FROM users',).fetchone()['c'] * 20000  # rough est, avoids CAST overflow

    # All skins for dropdown (from in-memory catalog, no DB table)
    skins = [{'id': s['id'], 'name': s['name'], 'rarity': s['rarity']} for s in SKIN_CATALOG]

    return render_template('admin_secret.html', user=get_user(),
                          all_users=all_users, bots=bots, msg=msg,
                          active_mines=active_mines, active_tower=active_tower,
                          crash_state=crash_state, audit=audit, stats=stats,
                          today_bets=today_bets, today_chat=today_chat,
                          today_balance=today_balance, skins=skins,
                          admin_users=sorted(ADMIN_USERS),
                          muted_users=sorted(_muted_users),
                          disabled_games=sorted(_disabled_games),
                          min_bet=MIN_BET, starting_balance=STARTING_BALANCE)


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
