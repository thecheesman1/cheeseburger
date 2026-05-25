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


# ── Mines ────────────────────────────────────────────────────────

@app.route('/mines', methods=['GET', 'POST'])
@login_required
def mines():
    user = get_user()
    result = {'win': False, 'mines': [], 'revealed': [], 'multiplier': 0, 'bet_amount': 0, 'payout': 0}
    if request.method == 'POST':
        action = request.form.get('action', 'start')
        bet_amount = int(request.form.get('bet_amount', 0))
        db = get_db()
        if action == 'start':
            if bet_amount < MIN_BET or bet_amount > user['balance']:
                return render_template('mines.html', user=user, result=result)
            db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
            db.commit()
            mine_positions = random.sample(range(25), 5)  # 5 mines in 5x5 grid
            result = {'win': False, 'mines': mine_positions, 'revealed': [], 'multiplier': 0, 'bet_amount': bet_amount, 'payout': 0, 'playing': True}
        elif action == 'reveal':
            pos = int(request.form.get('pos', -1))
            mines = [int(x) for x in request.form.get('mines', '').split(',') if x]
            revealed = [int(x) for x in request.form.get('revealed', '').split(',') if x]
            if pos not in revealed and pos not in mines:
                revealed.append(pos)
            if pos in mines:  # Hit a mine
                result = {'win': False, 'mines': mines, 'revealed': revealed + [pos], 'multiplier': 0, 'bet_amount': bet_amount, 'payout': 0, 'playing': False, 'bomb': pos}
            else:
                cleared = len(revealed)
                mult = round(1.0 + cleared * 0.3, 2)
                result = {'win': True, 'mines': mines, 'revealed': revealed, 'multiplier': mult, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult), 'playing': True}
        elif action == 'cashout':
            mines_list = [int(x) for x in request.form.get('mines', '').split(',') if x]
            revealed = [int(x) for x in request.form.get('revealed', '').split(',') if x]
            mult = round(1.0 + len(revealed) * 0.3, 2)
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
            db.commit()
            result = {'win': True, 'mines': mines_list, 'revealed': revealed, 'multiplier': mult, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult), 'playing': False, 'cashed_out': True}
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
        symbols = random.choices(['🍔', '🍟', '🥤', '⭐', '💎'], weights=[40,30,20,8,2], k=9)
        # Win if 3+ matching anywhere
        counts = {s: symbols.count(s) for s in set(symbols)}
        max_match = max(counts.values())
        mult_table = {3: 2, 4: 5, 5: 10, 6: 25, 7: 50, 8: 100, 9: 500}
        mult = mult_table.get(max_match, 0)
        if mult > 0:
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
        db.commit()
        result = {'win': mult > 0, 'cards': symbols, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult), 'matches': max_match}
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
        bet_amount = int(request.form.get('bet_amount', 0))
        db = get_db()
        if action == 'start':
            if bet_amount < MIN_BET or bet_amount > user['balance']:
                return render_template('tower.html', user=user, result=result)
            db.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bet_amount, user['id']))
            db.commit()
            result = {'win': True, 'levels': 0, 'bet_amount': bet_amount, 'payout': 0, 'playing': True, 'mines': []}
        elif action == 'climb':
            levels_done = int(request.form.get('levels', 0))
            diff = request.form.get('difficulty', 'medium')
            mine_prob = {'easy': 0.1, 'medium': 0.25, 'hard': 0.4}[diff]
            if random.random() < mine_prob:
                result = {'win': False, 'levels': levels_done, 'bet_amount': bet_amount, 'payout': 0, 'playing': False, 'bust': True}
            else:
                mult_now = round(1.5 ** (levels_done + 1), 2)
                result = {'win': True, 'levels': levels_done + 1, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult_now), 'playing': True}
        elif action == 'cashout':
            levels_done = int(request.form.get('levels', 0))
            mult = round(1.5 ** levels_done, 2)
            db.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (int(bet_amount * mult), user['id']))
            db.commit()
            result = {'win': True, 'levels': levels_done, 'bet_amount': bet_amount, 'payout': int(bet_amount * mult), 'playing': False, 'cashed_out': True}
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
            log_audit('esadsa', 'save_settings', f'min={MIN_BET} start={STARTING_BALANCE}')
        elif action == 'give_money':
            target = request.form.get('username', '').strip()
            amount = int(request.form.get('amount', 0))
            if target and amount > 0:
                db.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (amount, target))
                db.commit()
                log_audit('esadsa', 'give_money', f'{target} +{amount}')
        elif action == 'set_balance':
            target = request.form.get('username', '').strip()
            amount = int(request.form.get('amount', 0))
            if target and amount >= 0:
                db.execute('UPDATE users SET balance = ? WHERE username = ?', (amount, target))
                db.commit()
                log_audit('esadsa', 'set_balance', f'{target} = {amount}')
        elif action == 'ban_user':
            target = request.form.get('username', '').strip()
            if target and target != 'esadsa':
                db.execute('DELETE FROM user_inventory WHERE user_id = (SELECT id FROM users WHERE username=?)', (target,))
                db.execute('DELETE FROM market_listings WHERE seller_id = (SELECT id FROM users WHERE username=?)', (target,))
                db.execute('DELETE FROM chat_messages WHERE user_id = (SELECT id FROM users WHERE username=?)', (target,))
                db.execute('DELETE FROM users WHERE username = ?', (target,))
                db.commit()
                log_audit('esadsa', 'ban_user', target)
        elif action == 'reset_bot':
            target = request.form.get('username', '').strip()
            if target:
                db.execute('UPDATE users SET balance = ? WHERE username = ? AND is_bot = 1', (20000 + random.randint(5000, 100000), target))
                db.commit()
                log_audit('esadsa', 'reset_bot', target)
        elif action == 'toggle_bots':
            admin_settings['bots_enabled'] = not admin_settings.get('bots_enabled', True)
            log_audit('esadsa', 'toggle_bots', str(admin_settings['bots_enabled']))
        elif action == 'force_crash':
            global _crash_room
            if _crash_room:
                _crash_room['crash_point'] = float(request.form.get('crash_at', '1.01'))
                _crash_room['state'] = 'ending'
            log_audit('esadsa', 'force_crash', str(_crash_room.get('crash_point', 0)))
        elif action == 'wipe_economy':
            db.execute("UPDATE users SET balance = ? WHERE is_bot = 0 AND username != 'esadsa'", (STARTING_BALANCE,))
            db.execute('DELETE FROM user_inventory')
            db.execute('DELETE FROM market_listings')
            db.commit()
            seed_bots()
            log_audit('esadsa', 'wipe_economy', 'full reset')
        elif action == 'wipe_chat':
            db.execute('DELETE FROM chat_messages')
            db.commit()
            log_audit('esadsa', 'wipe_chat', '')
        elif action == 'nuke':
            db.execute('DELETE FROM user_inventory')
            db.execute('DELETE FROM market_listings')
            db.execute('DELETE FROM game_bets')
            db.execute('DELETE FROM chat_messages')
            db.execute("DELETE FROM users WHERE username != 'esadsa'")
            db.commit()
            seed_bots()
            log_audit('esadsa', 'nuke', 'full db reset')

    user = get_user()
    db.row_factory = sqlite3.Row
    bots = db.execute('SELECT username, balance FROM users WHERE is_bot = 1 ORDER BY balance DESC').fetchall()
    total_users = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    total_market = db.execute('SELECT COUNT(*) as c FROM market_listings').fetchone()['c']
    total_inventory = db.execute('SELECT COUNT(*) as c FROM user_inventory').fetchone()['c']
    total_chat = db.execute('SELECT COUNT(*) as c FROM chat_messages').fetchone()['c']
    top_human = db.execute("SELECT username, balance FROM users WHERE is_bot = 0 ORDER BY balance DESC LIMIT 5").fetchall()

    # House profit: total wagered - total paid out (all bets)
    wagered = db.execute("SELECT COALESCE(SUM(bet_amount), 0) as c FROM game_bets").fetchone()['c']
    paid = db.execute("SELECT COALESCE(SUM(result_amount), 0) as c FROM game_bets WHERE result='win'").fetchone()['c']
    house_profit = wagered - paid

    # Game stats
    game_stats = db.execute(
        "SELECT game, COUNT(*) as plays, SUM(bet_amount) as wagered, "
        "SUM(CASE WHEN result='win' THEN result_amount ELSE 0 END) as won, "
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
