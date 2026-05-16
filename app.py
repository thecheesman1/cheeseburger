import sqlite3
import random
import bcrypt
from flask import Flask, render_template, request, redirect, url_for, session, g

app = Flask(__name__)
app.secret_key = 'cheeseburger-secret-key-change-in-production'
DATABASE = 'cheeseburger.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
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
        balance INTEGER NOT NULL DEFAULT 500
    )''')
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
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/slots', methods=['GET', 'POST'])
@login_required
def slots():
    user = get_user()
    result = None
    if request.method == 'POST':
        bet = int(request.form.get('bet', 0))
        if bet < 10:
            return render_template('slots.html', user=user, error='Minimum bet is 10', result=None)
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
        if bet < 10:
            return render_template('coinflip.html', user=user, error='Minimum bet is 10', result=None)
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
        if bet < 10:
            return render_template('dice.html', user=user, error='Minimum bet is 10', result=None)
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
            if bet < 10:
                return render_template('blackjack.html', user=user, error='Minimum bet is 10', result=None)
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

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=34797)
