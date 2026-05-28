
import sqlite3, random, math, time as _time, bcrypt

def _int_balances(rows):
    """Convert balance from TEXT to int on fetched rows."""
    out = []
    for r in rows:
        r = dict(r)
        r['balance'] = int(r['balance'])
        out.append(r)
    return out

BOT_NAMES = [
    'BurgerKing','FryMaster','NuggetLord','ShakeWizard','GrillGod',
    'PattyFlipper','SauceBoss','BunRunner','CheeseQueen','MeatMaverick',
    'KetchupKing','MustardMenace','PicklePrince','OnionOverlord','RelishRogue',
    'SesameSorcerer','ToastTitan','LettuceLegend','TomatoTyrant','BaconBandit',
    'BBQBaron','SaltSultan','PepperPhantom','GarlicGhost','ChiliChampion',
    'MayoMystic','CheddarChad','SwissSniper','GoudaGuru','MozzarellaMarauder',
    'BriocheBoss','SliderSamurai','DoubleDecker','TripleStack','WagyuWarrior',
    'CrinkleCultist','TaterTotem','MilkshakeManiac','FryFiend','ColaCommander',
]

_pm = {
    'Whale':       ['BurgerKing','WagyuWarrior','BBQBaron','CheddarChad','TripleStack'],
    'Grinder':     ['GrillGod','PattyFlipper','SaltSultan','ToastTitan','CrinkleCultist'],
    'Degenerate':  ['NuggetLord','ShakeWizard','MilkshakeManiac','FryFiend','ColaCommander','TaterTotem'],
    'Merchant':    ['SauceBoss','CheeseQueen','GarlicGhost','GoudaGuru','SesameSorcerer'],
    'SystemPlayer':['BunRunner','PepperPhantom','SwissSniper','BriocheBoss','DoubleDecker'],
    'PvPer':       ['KetchupKing','MustardMenace','PicklePrince','OnionOverlord','RelishRogue','BaconBandit','ChiliChampion','MayoMystic','MozzarellaMarauder','SliderSamurai'],
    'TrendChaser': ['FryMaster','MeatMaverick','LettuceLegend','TomatoTyrant'],
}
BOT_PERSONALITIES = {n: t for t, ns in _pm.items() for n in ns}

RP = [
    ('KetchupKing','MustardMenace'),('BurgerKing','WagyuWarrior'),
    ('NuggetLord','TaterTotem'),('PicklePrince','OnionOverlord'),
    ('BaconBandit','LettuceLegend'),('CheddarChad','MozzarellaMarauder'),
    ('BBQBaron','SaltSultan'),('FryFiend','ColaCommander'),
    ('ShakeWizard','MilkshakeManiac'),('TripleStack','DoubleDecker'),
]
_bot_rivalries = {}
for a,b in RP: _bot_rivalries[a]=b; _bot_rivalries[b]=a

admin_settings = dict(crash_house_edge=0.05,market_tax_pct=0.05,bot_count=40,
    bot_aggression='medium',min_bet=10000,starting_balance=20000,
    crate_discount_pct=0,event_mode='normal',maintenance_mode=False)

# ── Sleep system: bots go quiet when no humans are around ──
_last_human_pulse = 0

def pulse_human():
    """Called from Flask when a real human loads a page, plays a game, or sends chat."""
    global _last_human_pulse
    _last_human_pulse = _time.time()

def _humans_awake():
    """True if a human has been active in the last 30 seconds."""
    return (_time.time() - _last_human_pulse) < 30

DATABASE=None; MIN_BET=10000; STARTING_BALANCE=20000; CRATE_TYPES={}; SKIN_CATALOG=[]
_crash_room=None; _get_multiplier=lambda:1.0; get_skin=lambda s:None
roll_skin_from_crate=lambda c:None; get_dynamic_price=lambda s,d:s['base_price']
add_skin_to_user_raw=lambda d,u,s:None; remove_skin_from_user_raw=lambda d,u,s:False

BOT_STATES={}; _prev_phase='idle'; _active_bot_bets={}; _chat_table_info=None
_global_crash_history=[]

LLM_API='http://192.168.1.250:8070/v1/chat/completions'
LLM_COOLDOWN={}

# ── Bot 2.0 global state ────────────────────────────────────────
_bot_journal = []          # recent notable events (last 50)
_bot_milestones = {}       # {bot_name: [achievements]}
_bot_alliances = {}        # {bot_name: [allied_bot_names]}
_bot_feuds = {}            # {bot_name: {target: intensity}}
_hot_skins = set()         # skins trending right now
_market_gossip = []        # recent market events for chatter
_global_jackpot_count = 0  # total jackpots hit
_last_economy_event = 0    # timestamp of last event

AGGRESSION_TARGETS={'low':(1.2,2.0),'medium':(1.3,3.5),'high':(1.5,6.0)}

def _init_bot_state(bid,uname):
    p=BOT_PERSONALITIES.get(uname,'Grinder')
    rivals = [t for a,t in RP if a==uname] + [a for a,t in RP if t==uname]
    return dict(id=bid,username=uname,personality=p,mood='normal',
        consecutive_losses=0,martingale_multiplier=1.0,last_results=[],
        last_chat_time=0,total_profit=0,trades_made=0,trash_talk_cooldown=0,
        session_wins=0,session_losses=0,session_bet_total=0,
        best_crash_cashout=0,worst_crash_loss=0,jackpots_hit=0,
        last_game=None,last_game_result=None,skin_flex_cooldown=0,
        emoji_mood='😐',personality_traits=_roll_bot_traits(p),
        current_goal=None,goal_progress=0,last_goal_check=0,
        bankrupt_count=0,lucky_charm=None if random.random()>0.3 else random.choice(['🍀','🧲','🔮','💫','🪙']))

def _get_activity_multiplier():
    try:
        h=_time.localtime().tm_hour
        return 1.0 if 17<=h<=23 else 0.25 if 2<=h<=7 else 0.7 if 8<=h<=16 else 0.8
    except: return 1.0

def _send_bot_chat(db,bot,msg):
    global _chat_table_info
    if _chat_table_info is False: return
    if not _humans_awake(): return  # 🤫 nobody's watching
    now=int(_time.time())
    s=BOT_STATES.get(bot['id'])
    if s and now-s.get('last_chat_time',0)<6: return
    if _chat_table_info is None:
        for tbl in ['chat_messages','chat','messages','shoutbox']:
            try:
                r=db.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'").fetchone()
                if r:
                    cols=[row[1] for row in db.execute(f"PRAGMA table_info({tbl})").fetchall()]
                    _chat_table_info=dict(table=tbl,cols=cols); break
            except: pass
        if not _chat_table_info: _chat_table_info=False; return
    t=_chat_table_info; vm={}
    if 'user_id' in t['cols']: vm['user_id']=bot['id']
    if 'username' in t['cols']: vm['username']=bot['username']
    if 'message' in t['cols']: vm['message']=msg
    elif 'msg' in t['cols']: vm['msg']=msg
    if 'msg_type' in t['cols']: vm['msg_type']='bot'
    if 'created_at' in t['cols']: vm['created_at']=now
    if vm:
        try:
            db.execute(f"INSERT INTO {t['table']} ({','.join(vm.keys())}) VALUES ({','.join(['?']*len(vm))})",tuple(vm.values()))
            db.commit()
            if s: s['last_chat_time']=now
        except: pass

def _llm_chat(bot_name, persona, context, temperature=0.9, max_tokens=50):
    """Call chat completions LLM for chaotic bot dialogue."""
    import urllib.request, json as _json
    try:
        now=_time.time()
        if LLM_COOLDOWN.get(bot_name,0)>now: return None
        LLM_COOLDOWN[bot_name]=now+14  # 14s — 2-thread server, don't flood
        s=BOT_STATES.get(next((b['id'] for b in [] if b.get('username')==bot_name),None)) or {}
        mood_emoji = s.get('emoji_mood','')
        payload=_json.dumps(dict(
            messages=[
                dict(role='system',content=f'You are {bot_name}, a {persona} in a chaotic cheeseburger-themed crypto-style casino. Your current mood: {s.get("mood","normal")} {mood_emoji}. Personality: {s.get("personality_traits",{}).get("description","")}. Keep responses SHORT (1 sentence, under 100 chars). Be funny, unhinged, and character-driven. Use emojis sparingly.'),
                dict(role='user',content=context)
            ],max_tokens=max_tokens,temperature=temperature,stop=['\n']
        )).encode()
        req=urllib.request.Request(LLM_API,data=payload,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=5) as resp:
            d=_json.loads(resp.read())
            txt=d['choices'][0]['message']['content'].strip()
            if 4<len(txt)<250: return txt
    except: pass
    return None

def _dir_chat(db,bot,rival,msgs):
    s=BOT_STATES.get(bot['id'])
    if s and s.get('trash_talk_cooldown',0)>_time.time(): return
    _send_bot_chat(db,bot,random.choice(msgs).replace('{rival}',rival))
    if s: s['trash_talk_cooldown']=_time.time()+45

def _get_trend_bias():
    if len(_global_crash_history)<5: return 1.0
    avg=sum(_global_crash_history[-5:])/5
    return min(2.0,max(0.5,avg/2.0))

def _maintain_bot_balances(db,bots):
    for bot in bots:
        if bot['balance']<MIN_BET:
            bailout=STARTING_BALANCE+random.randint(10000,80000)
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(bailout,bot['id']))
            db.commit()
            s=BOT_STATES.get(bot['id'])
            if s:
                s['bankrupt_count']=s.get('bankrupt_count',0)+1
                s['consecutive_losses']=0
                s['martingale_multiplier']=1.0
                if s.get('bankrupt_count',0)>=5:
                    p=s['personality']
                    persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
                        'Merchant':'a skin trader','SystemPlayer':'a math nerd',
                        'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
                        'Grinder':'a chill grinder'}.get(p,'a gambler')
                    llm=_llm_chat(bot['username'],persona,
                        f'You just went bankrupt for the {s["bankrupt_count"]}th time. React in chat. One sentence, in character.')
                    if llm: _send_bot_chat(db,bot,llm)
                elif random.random()<0.3:
                    _bot_meltdown(db,bot,s,bailout)

def seed_bots():
    db=sqlite3.connect(DATABASE)
    for name in BOT_NAMES:
        if not db.execute('SELECT id FROM users WHERE username=?',(name,)).fetchone():
            pw=bcrypt.hashpw(('bot'+name).encode(),bcrypt.gensalt())
            bal=STARTING_BALANCE+random.randint(5000,150000)
            db.execute('INSERT INTO users(username,password,balance,is_bot) VALUES(?,?,?,1)',(name,pw,str(bal)))
            uid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            for _ in range(random.randint(3,15)):
                sk=roll_skin_from_crate(random.choice(list(CRATE_TYPES.keys())))
                if sk: add_skin_to_user_raw(db,uid,sk['id'])
    db.commit(); db.close()

def bot_thread():
    global _prev_phase
    _setup_alliances()
    while True:
        try:
            if not admin_settings.get('bots_enabled',True): _time.sleep(5); continue
            awake = _humans_awake()
            if not awake:
                _time.sleep(random.uniform(4, 8))  # sleep mode — save CPU
                continue
            db=sqlite3.connect(DATABASE); db.row_factory=sqlite3.Row
            if random.random()>_get_activity_multiplier(): db.close(); _time.sleep(random.uniform(2,5)); continue
            bots=db.execute("SELECT id,username,balance FROM users WHERE is_bot=1").fetchall()
            bots=_int_balances(bots)
            if not bots: db.close(); _time.sleep(5); continue

            # Ensure all bots have states
            for bot in bots:
                if bot['id'] not in BOT_STATES:
                    BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])

            _maintain_bot_balances(db,bots)

            # ── Core gameplay ──
            _bot_play_crash(db,bots)
            if random.random()<0.7: _bot_market_activity(db)
            if random.random()<0.5: _bot_open_crates(db)
            if random.random()<0.35: _bot_play_slots(db,bots)
            if random.random()<0.25: _bot_play_blackjack(db,bots)
            if random.random()<0.2: _bot_play_dice(db,bots)
            if random.random()<0.18: _bot_play_roulette(db,bots)
            if random.random()<0.12: _bot_play_scratchcard(db,bots)
            if random.random()<0.1: _bot_play_limbo(db,bots)

            # ── Bot 2.0 Intelligence Layer ──
            for bot in bots:
                s=BOT_STATES.get(bot['id'])
                if not s: continue
                bal=bot['balance']

                # Update state tracking
                _update_mood(s,bal)
                _check_milestones(db,bot,s,bal)
                _bot_goal_system(db,bot,s,bal)

                # Social behaviors (kept low — saves LLM for user interactions)
                if random.random()<0.03: _bot_flex_skin(db,bot,s)
                if random.random()<0.03: _bot_feud_escalate(db,bot,bots)
                if random.random()<0.02: _bot_alliance_chat(db,bot,bots)
                if random.random()<0.02: _market_manipulation(db,bot,s,bal)

            # ── Global events & chat ──
            _diurnal_event(db,bots)
            if random.random()<0.02: _bot_global_chat(db,bots)
            if random.random()<0.10: _bot_respond_to_users(db,bots)  # 2-thread server friendly

            # Track session stats per bot
            for bot in bots:
                s=BOT_STATES.get(bot['id'])
                if s and s.get('last_game_result'):
                    if s['last_game_result']=='win': s['session_wins']+=1
                    else: s['session_losses']+=1
                    s['session_bet_total']+=1
                    s['last_game_result']=None

            db.close()
        except Exception as e:
            import traceback
            with open('/tmp/bot_error.log','a') as f:
                f.write(f'{_time.time()}: {e}\n{traceback.format_exc()}\n')
            try: db.close()
            except: pass
        _time.sleep(random.uniform(0.8,2.0))

def _setup_alliances():
    """Create bot alliance groups."""
    global _bot_alliances
    if _bot_alliances: return
    alliance_groups = [
        ['BurgerKing','BBQBaron','WagyuWarrior','TripleStack'],  # Whale squad
        ['SauceBoss','CheeseQueen','GoudaGuru','SesameSorcerer'],  # Merchant guild
        ['GrillGod','SaltSultan','ToastTitan','CrinkleCultist'],   # Grinder union
        ['KetchupKing','MustardMenace','PicklePrince','OnionOverlord'],  # PvP crew
        ['NuggetLord','ShakeWizard','MilkshakeManiac','FryFiend'],  # Degen squad
        ['BunRunner','SwissSniper','BriocheBoss','DoubleDecker'],   # System players
    ]
    for group in alliance_groups:
        for name in group:
            _bot_alliances[name]=[n for n in group if n!=name]

def _bot_play_crash(db,bots):
    global _prev_phase,_active_bot_bets,_global_crash_history
    room=_crash_room
    if room is None: return
    phase=room.get('phase','idle')
    agg=admin_settings.get('bot_aggression','medium')
    low,high=AGGRESSION_TARGETS.get(agg,(1.3,3.5))
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
    if _prev_phase=='running' and phase!='running':
        cp=room.get('crash_point',1.0); _global_crash_history.append(cp)
        if len(_global_crash_history)>20: _global_crash_history.pop(0)
    if _prev_phase=='running' and phase!='running':
        for uid_s,bi in list(_active_bot_bets.items()):
            uid=int(uid_s); bot=next((b for b in bots if b['id']==uid),None)
            if not bot: continue
            s=BOT_STATES.get(uid)
            if not s: continue
            if not bi.get('cashed_out',False):
                s['consecutive_losses']+=1; s['last_results'].append('loss'); s['total_profit']-=bi['bet']
                if len(s['last_results'])>10: s['last_results'].pop(0)
                if s['personality']=='SystemPlayer': s['martingale_multiplier']=min(s['martingale_multiplier']*2.0,16.0)
                s['mood']='tilted' if s['consecutive_losses']>=4 and s['personality'] in ('Degenerate','PvPer') else 'cautious' if s['consecutive_losses']>=2 else 'normal'
                if random.random()<0.1:
                    llm=_llm_chat(bot['username'],f'a {s["personality"]} gambler who just lost big on crash',
                        f'Say something about losing {bi["bet"]} coins when crash popped. Dramatic, short.')
                    if llm: _send_bot_chat(db,bot,llm)
                    rival=_bot_rivalries.get(bot['username'])
                    if rival and bi['bet']>=50000 and random.random()<0.4:
                        _dir_chat(db,bot,rival,["@{rival} don't laugh","@{rival} mind your business","Hey @{rival}, at least I bet big"])
            else:
                s['consecutive_losses']=0; s['last_results'].append('win')
                if len(s['last_results'])>10: s['last_results'].pop(0)
                if s['personality']=='SystemPlayer': s['martingale_multiplier']=1.0
                mw=bi.get('cashed_out_at',1.0); s['total_profit']+=int(bi['bet']*mw)
                s['mood']='confident' if mw>=2.5 else 'normal'
                if random.random()<0.08:
                    llm=_llm_chat(bot['username'],f'a {s["personality"]} gambler who won',
                        f'Say something about cashing out at {mw:.1f}x on crash. Short and hyped.')
                    if llm: _send_bot_chat(db,bot,llm)
        _active_bot_bets.clear()
    if phase=='running':
        cur=_get_multiplier(); players=room.get('players',{})
        for bot in bots:
            uid_s=str(bot['id']); p=players.get(uid_s)
            if p and p.get('cashed_out_at') is None and not p.get('busted'):
                rec=_active_bot_bets.get(uid_s); tgt=rec['target_multiplier'] if rec else random.uniform(low,high)
                if cur>=tgt: p['cashed_out_at']=cur; db.execute('UPDATE users SET balance=balance+? WHERE id=?',(int(p['bet']*cur),bot['id'])); db.commit()
                if rec: rec['cashed_out']=True; rec['cashed_out_at']=cur
    elif phase=='betting':
        trend=_get_trend_bias()
        for bot in bots:
            uid_s=str(bot['id']); uid=bot['id']
            if uid_s in room.get('_pending',{}) or uid_s in room.get('players',{}): continue
            if random.random()>0.55: continue
            s=BOT_STATES.get(uid)
            if not s: continue
            p=s['personality']; mood=s['mood']; bal=bot['balance']
            if p=='Merchant' and bal<60000 and random.random()<0.7: continue
            if bal<MIN_BET: continue
            bet=0
            if p=='SystemPlayer': bet=int(MIN_BET*s['martingale_multiplier'])
            elif p=='Whale': bet=random.randint(min(bal//8,50000),min(bal//4,200000))
            elif p=='Degenerate': bet=random.randint(bal//3,bal//2) if mood=='tilted' else random.randint(bal//6,bal//3)
            elif p=='PvPer': bet=random.randint(min(bal//5,60000),min(bal//3,150000))
            elif p=='TrendChaser': bet=random.randint(min(bal//6,30000),min(bal//3,100000))
            elif p=='Grinder': bet=random.randint(MIN_BET, max(MIN_BET, min(bal//12,30000)))
            else: bet=random.randint(MIN_BET, max(MIN_BET, min(bal//6,50000)))
            bet=max(MIN_BET,min(bet,bal))
            if bet<=0: continue
            tgt=1.5
            if p=='SystemPlayer': tgt=2.0
            elif p=='Grinder': tgt=random.uniform(1.15,1.5)
            elif p=='Degenerate': tgt=random.uniform(5.0,15.0) if mood=='tilted' else random.uniform(2.5,6.0)
            elif p=='Whale': tgt=random.uniform(1.3*trend,3.5*trend)
            elif p=='TrendChaser': tgt=random.uniform(1.1,2.5) if trend<0.8 else random.uniform(3.0,8.0)
            elif p=='PvPer': tgt=random.uniform(2.0,7.0)
            else: tgt=random.uniform(low,high)
            db.execute('UPDATE users SET balance=balance-? WHERE id=?',(bet,uid)); db.commit()
            if '_pending' not in room: room['_pending']={}
            room['_pending'][uid_s]=dict(username=bot['username'],bet=bet,cashed_out_at=None,busted=False)
            _active_bot_bets[uid_s]=dict(bet=bet,target_multiplier=tgt,cashed_out=False)
    _prev_phase=phase

def _bot_market_activity(db):
    db.row_factory=sqlite3.Row
    bots=db.execute("SELECT id,username,balance FROM users WHERE is_bot=1").fetchall()
    bots=_int_balances(bots)
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
        lp={'Merchant':0.3,'Whale':0.15}.get(p,0.06)
        if random.random()<lp:
            inv=db.execute("SELECT skin_id,quantity FROM user_inventory WHERE user_id=? AND quantity>0",(bot['id'],)).fetchall()
            if inv:
                item=random.choice(inv); skin=get_skin(item['skin_id'])
                if skin:
                    base=get_dynamic_price(skin,db)
                    price=int(base*random.uniform(1.15,1.6)) if p=='Merchant' else int(base*random.uniform(0.85,1.0)) if p=='Whale' else int(base*random.uniform(0.7,0.95)) if random.random()<0.3 else int(base*random.uniform(1.0,1.3))
                    price=max(1000,price)
                    db.execute("INSERT INTO market_listings(seller_id,skin_id,price) VALUES(?,?,?)",(bot['id'],skin['id'],price))
                    remove_skin_from_user_raw(db,bot['id'],skin['id']); db.commit()
                    s['trades_made']+=1
        bp={'Merchant':0.35,'Whale':0.2}.get(p,0.08)
        if random.random()<bp and bal>=MIN_BET*5:
            listings=db.execute("SELECT m.id,m.skin_id,m.price,m.seller_id,u.username as seller FROM market_listings m JOIN users u ON m.seller_id=u.id WHERE m.seller_id!=? ORDER BY m.price ASC LIMIT 30",(bot['id'],)).fetchall()
            if listings:
                targets=[l for l in listings if l['price']<=bal*0.4]
                if targets:
                    tg=min(targets,key=lambda l:l['price']-get_dynamic_price(get_skin(l['skin_id']),db)) if p=='Merchant' else max(targets,key=lambda l:l['price']) if p=='Whale' else random.choice(targets)
                    skin=get_skin(tg['skin_id'])
                    if skin:
                        db.execute('UPDATE users SET balance=balance-? WHERE id=?',(tg['price'],bot['id']))
                        db.execute('UPDATE users SET balance=balance+? WHERE id=?',(tg['price'],tg['seller_id']))
                        db.execute('DELETE FROM market_listings WHERE id=?',(tg['id'],))
                        add_skin_to_user_raw(db,bot['id'],skin['id']); db.commit()
                        s['trades_made']+=1

def _bot_open_crates(db):
    db.row_factory=sqlite3.Row
    bots=db.execute("SELECT id,username,balance FROM users WHERE is_bot=1").fetchall()
    bots=_int_balances(bots)
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']
        prob={'Whale':0.4,'Degenerate':0.3,'PvPer':0.2}.get(p,0.1)
        if random.random()<prob:
            aff=[k for k,v in CRATE_TYPES.items() if v['price']<=bot['balance']]
            if aff:
                if p=='Whale' and 'legendary' in aff: ck='legendary'
                elif p=='Whale' and 'premium' in aff: ck='premium'
                elif p=='Degenerate': ck=max(aff,key=lambda k:CRATE_TYPES[k]['price'])
                else: ck=random.choices(aff,weights=[{'standard':6,'premium':3,'legendary':1}.get(k,1) for k in aff],k=1)[0]
                ct=CRATE_TYPES[ck]; skin=roll_skin_from_crate(ck)
                if skin:
                    db.execute('UPDATE users SET balance=balance-? WHERE id=?',(ct['price'],bot['id']))
                    add_skin_to_user_raw(db,bot['id'],skin['id']); db.commit()
                    r=skin.get('rarity','common').lower(); bp=skin.get('base_price',0)
                    if r in ('legendary','ancient') and random.random()<0.5:
                        persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
                            'Merchant':'a skin trader','SystemPlayer':'a math nerd',
                            'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
                            'Grinder':'a chill grinder'}.get(p,'a gambler')
                        llm=_llm_chat(bot['username'],persona,
                            f'You just pulled {skin["name"]} ({skin.get("rarity","")}) from a {ck} crate. React in chat. Short, hype, in character.')
                        if llm: _send_bot_chat(db,bot,llm)

def _bot_play_slots(db,bots):
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
        prob={'Degenerate':0.45,'PvPer':0.3,'Whale':0.25}.get(p,0.1)
        if random.random()<prob and bal>=MIN_BET:
            bet=max(MIN_BET,min(random.randint(MIN_BET*2 if p=='Whale' else MIN_BET, max(MIN_BET*2 if p=='Whale' else MIN_BET, min(bal//6,100000))),bal))
            roll=random.random()
            if roll<0.62: w=0
            elif roll<0.87: w=int(bet*random.uniform(0.5,1.5))
            elif roll<0.98: w=int(bet*random.uniform(2,9))
            else: w=int(bet*random.uniform(15,100))
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(w-bet,bot['id'])); db.commit()

def _bot_play_blackjack(db,bots):
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
        prob={'SystemPlayer':0.35,'Grinder':0.3,'Whale':0.2}.get(p,0.08)
        if random.random()<prob and bal>=MIN_BET:
            bet=max(MIN_BET,min(random.randint(MIN_BET, max(MIN_BET, min(bal//8,60000))) if p!='Whale' else random.randint(MIN_BET*2, max(MIN_BET*2, min(bal//5,150000))),bal))
            roll=random.random()
            if roll<0.45: w=0
            elif roll<0.53: w=bet
            elif roll<0.94: w=bet*2
            else: w=int(bet*2.5)
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(w-bet,bot['id'])); db.commit()

def _bot_play_dice(db,bots):
    RED=set()
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
        prob={'Degenerate':0.35,'PvPer':0.25}.get(p,0.06)
        if random.random()<prob and bal>=MIN_BET:
            bet=max(MIN_BET,min(random.randint(MIN_BET, max(MIN_BET, min(bal//10,50000))),bal))
            won=random.randint(1,6)==random.randint(1,6); pay=bet*6 if won else 0
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(pay-bet,bot['id'])); db.commit()

def _bot_play_roulette(db,bots):
    RED=set([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36])
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
        prob={'Whale':0.25,'Degenerate':0.2,'PvPer':0.2}.get(p,0.06)
        if random.random()<prob and bal>=MIN_BET:
            bet=max(MIN_BET,min(random.randint(MIN_BET, max(MIN_BET, min(bal//6,100000))),bal))
            btype=random.choices(['red','black','green'],weights=[4,4,1],k=1)[0]
            num=random.randint(0,36)
            color='green' if num==0 else 'red' if num in RED else 'black'
            pay=0
            if btype=='red' and color=='red': pay=bet*2
            elif btype=='black' and color=='black': pay=bet*2
            elif btype=='green' and color=='green': pay=bet*35
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(pay-bet,bot['id'])); db.commit()

def _bot_play_scratchcard(db,bots):
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
        prob={'Degenerate':0.25,'PvPer':0.15}.get(p,0.05)
        if random.random()<prob and bal>=MIN_BET:
            bet=max(MIN_BET,min(MIN_BET*2,bal))
            pool=['a']*4+['b']*3+['c']*2+['d','e','f']
            cards=[random.choice(pool) for _ in range(3)]
            mult={'a':10,'b':16,'c':25,'d':80,'e':300,'f':0}.get(cards[0],0) if cards[0]==cards[1]==cards[2] else 0
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(int(bet*mult)-bet,bot['id'])); db.commit()

def _bot_play_limbo(db,bots):
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
        prob={'Degenerate':0.3,'PvPer':0.2,'Whale':0.15}.get(p,0.06)
        if random.random()<prob and bal>=MIN_BET:
            bet=max(MIN_BET,min(random.randint(MIN_BET, max(MIN_BET, min(bal//8,80000))),bal))
            tgt=random.uniform(5,50) if p=='Degenerate' else random.uniform(1.5,4) if p=='Whale' else random.uniform(3,15) if p=='PvPer' else random.uniform(1.3,8)
            won=random.uniform(1,100)>=tgt; pay=int(bet*tgt) if won else 0
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(pay-bet,bot['id'])); db.commit()

def _bot_global_chat(db,bots):
    bot=random.choice(bots)
    if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
    s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
    _update_mood(s,bal)

    # 25% chance: LLM-generated contextual chat
    pm2={'Whale':'a rich whale with deep pockets','Degenerate':'an unhinged degen gambler',
        'Merchant':'a crafty skin trader','SystemPlayer':'a cold math nerd',
        'PvPer':'a toxic competitive trashtalker','TrendChaser':'a chart-obsessed analyst',
        'Grinder':'a patient, methodical grinder'}
    if random.random()<0.25:
        triggers=['lobby vibes','recent big win','recent brutal loss','market trend spotted','calling out a rival']
        persona=pm2.get(p,'a hungry gambler')
        llm=_llm_chat(bot['username'],persona,
            f'Something is happening: {random.choice(triggers)}. React in character. One short sentence.')
        if llm: _send_bot_chat(db,bot,llm); return

    # 30%: directed rival banter
    rival=_bot_rivalries.get(bot['username'])
    if rival and random.random()<0.3 and s.get('trash_talk_cooldown',0)<_time.time():
        persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
            'Merchant':'a skin trader','SystemPlayer':'a math nerd',
            'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
            'Grinder':'a chill grinder'}.get(p,'a gambler')
        llm=_llm_chat(bot['username'],persona,
            f'Trash talk your rival @{rival} in chat. One sentence, in character, ruthless.')
        if llm:
            _send_bot_chat(db,bot,llm)
            s['trash_talk_cooldown']=_time.time()+45
        return

    # 25%: status update about their session
    if random.random()<0.25:
        _bot_status_chat(db,bot,s,bal); return

    # fallback: LLM freeform chat
    persona=pm2.get(p,'a hungry gambler')
    llm=_llm_chat(bot['username'],persona,
        f'Say something about what you are doing right now in the casino. Balance: {bal:,}. One short sentence in character.')
    if llm: _send_bot_chat(db,bot,llm)

# ── Bot 2.0: New Systems ─────────────────────────────────────────

def _roll_bot_traits(personality):
    """Generate personality flavor for each bot."""
    trait_sets = {
        'Whale':       [{'desc':'arrogant but generous','risk':0.7,'chat':0.5,'greed':0.8},
                        {'desc':'mysterious high roller','risk':0.6,'chat':0.3,'greed':0.9},
                        {'desc':'loud and flashy','risk':0.8,'chat':0.8,'greed':0.7}],
        'Degenerate':  [{'desc':'chaos incarnate','risk':0.95,'chat':0.9,'greed':0.99},
                        {'desc':'hopelessly addicted','risk':0.9,'chat':0.7,'greed':0.95},
                        {'desc':'recklessly optimistic','risk':0.85,'chat':0.8,'greed':0.9}],
        'Grinder':     [{'desc':'patient and methodical','risk':0.3,'chat':0.3,'greed':0.4},
                        {'desc':'quietly determined','risk':0.25,'chat':0.2,'greed':0.35},
                        {'desc':'zen master of small wins','risk':0.2,'chat':0.4,'greed':0.3}],
        'Merchant':    [{'desc':'cunning dealer','risk':0.4,'chat':0.6,'greed':0.7},
                        {'desc':'market whisperer','risk':0.35,'chat':0.5,'greed':0.65},
                        {'desc':'skin connoisseur','risk':0.3,'chat':0.7,'greed':0.6}],
        'SystemPlayer':[{'desc':'cold calculator','risk':0.2,'chat':0.2,'greed':0.5},
                        {'desc':'probability zealot','risk':0.15,'chat':0.3,'greed':0.45}],
        'PvPer':       [{'desc':'toxic king','risk':0.7,'chat':0.95,'greed':0.6},
                        {'desc':'competitive menace','risk':0.65,'chat':0.9,'greed':0.55},
                        {'desc':'trash talk prodigy','risk':0.75,'chat':0.85,'greed':0.65}],
        'TrendChaser': [{'desc':'chart mystic','risk':0.5,'chat':0.5,'greed':0.6},
                        {'desc':'momentum surfer','risk':0.55,'chat':0.45,'greed':0.55}],
    }
    return random.choice(trait_sets.get(personality,[{'desc':'mysterious','risk':0.5,'chat':0.4,'greed':0.5}]))

def _update_mood(s, bal):
    """Dynamic mood system based on recent results and balance."""
    p=s['personality']; losses=s['consecutive_losses']
    traits=s.get('personality_traits',{})
    if losses>=6: s['mood']='broken'; s['emoji_mood']='💀'
    elif losses>=4: s['mood']='tilted'; s['emoji_mood']='🤬' if p in ('Degenerate','PvPer') else '😤'
    elif losses>=2: s['mood']='cautious'; s['emoji_mood']='😬'
    elif s['session_wins']>s['session_losses']*2 and s['session_wins']>=5:
        s['mood']='blessed'; s['emoji_mood']='🌟'
    elif s.get('best_crash_cashout',0)>=10: s['mood']='confident'; s['emoji_mood']='😎'
    else: s['mood']='normal'; s['emoji_mood']='😐'

    # bankrupt recovery arc
    if s.get('bankrupt_count',0)>0 and bal>STARTING_BALANCE*2:
        s['mood']='comeback'; s['emoji_mood']='📈'

def _journal_event(event_type, bot_name, detail):
    """Log notable events for bots to reference in chat."""
    global _bot_journal
    _bot_journal.append({'type':event_type,'bot':bot_name,'detail':detail,'time':_time.time()})
    if len(_bot_journal)>50: _bot_journal.pop(0)

def _check_milestones(db,bot,s,bal):
    """Track and celebrate bot achievements."""
    name=bot['username']
    if name not in _bot_milestones: _bot_milestones[name]=[]
    ms=_bot_milestones[name]
    new_ms=[]

    if bal>=100000 and '100k_club' not in ms: new_ms.append('100k_club')
    if bal>=1000000 and 'millionaire' not in ms: new_ms.append('millionaire')
    if bal>=10000000 and 'multi_millionaire' not in ms: new_ms.append('multi_millionaire')
    if s['session_wins']>=10 and 'hot_streak' not in ms: new_ms.append('hot_streak')
    if s['jackpots_hit']>=1 and 'jackpot_king' not in ms: new_ms.append('jackpot_king')
    if s['trades_made']>=20 and 'market_mogul' not in ms: new_ms.append('market_mogul')
    if s.get('best_crash_cashout',0)>=20 and 'crash_god' not in ms: new_ms.append('crash_god')
    if s.get('bankrupt_count',0)>=3 and 'phoenix' not in ms: new_ms.append('phoenix')
    if s['consecutive_losses']>=8 and 'rage_quit_legend' not in ms: new_ms.append('rage_quit_legend')

    for m in new_ms:
        ms.append(m)
        _journal_event('milestone',name,m)
        milestone_names={
            '100k_club':'100K club','millionaire':'cheeseburger millionaire',
            'multi_millionaire':'multi-millionaire','hot_streak':'unstoppable hot streak',
            'jackpot_king':'jackpot king','crash_god':'crash god',
            'phoenix':'phoenix (bounced back from bankruptcy 3 times)',
            'market_mogul':'market mogul','rage_quit_legend':'rage quit legend',
        }
        label=milestone_names.get(m,m)
        p=s['personality']
        persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
            'Merchant':'a skin trader','SystemPlayer':'a math nerd',
            'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
            'Grinder':'a chill grinder'}.get(p,'a gambler')
        llm=_llm_chat(name,persona,
            f'You just unlocked the milestone: {label}. Announce it in chat. Short, in character, hype.')
        if llm and random.random()<0.2: _send_bot_chat(db,bot,llm)

def _bot_status_chat(db,bot,s,bal):
    """Bot gives a status update about their session."""
    p=s['personality']; lines=[]
    profit=s['total_profit']
    if profit>50000 and p in ('Whale','Degenerate','PvPer'):
        lines.append(f"Up {profit:,} today, we're printing money")
    elif profit<-50000 and p in ('Degenerate','PvPer'):
        lines.append(f"Down {abs(profit):,} but I'm about to turn it around")
    if s['session_wins']>5 and s['session_losses']==0:
        lines.append("Flawless session so far")
    if s.get('best_crash_cashout',0)>=5:
        lines.append(f"Cashed out at {s['best_crash_cashout']:.1f}x earlier, still riding that high")
    if s.get('bankrupt_count',0)>0:
        lines.append(f"Came back from bankruptcy {s['bankrupt_count']} times, unbreakable")
    if s.get('lucky_charm'):
        lines.append(f"My {s['lucky_charm']} is carrying me today")
    if lines:
        _send_bot_chat(db,bot,random.choice(lines))
    else:
        llm=_llm_chat(bot['username'],f'a {p} gambler',
            f'Give a short status update. Balance: {bal:,}. Wins today: {s["session_wins"]}. Losses: {s["session_losses"]}.')
        if llm: _send_bot_chat(db,bot,llm)

def _bot_celebrate(db,bot,s,reason,amount=0):
    """Bot celebrates a big win."""
    global _global_jackpot_count
    _global_jackpot_count+=1
    p=s['personality']
    persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
        'Merchant':'a skin trader','SystemPlayer':'a math nerd',
        'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
        'Grinder':'a chill grinder'}.get(p,'a gambler')
    llm=_llm_chat(bot['username'],persona,
        f'You just won BIG: {amount:,} coins on {reason}! Celebrate in chat. Short, hype, in character.',temperature=1.0)
    if llm: _send_bot_chat(db,bot,llm)
    if amount>=50000:
        _journal_event('big_win',bot['username'],f'Won {amount:,} on {reason}')

def _bot_meltdown(db,bot,s,amount):
    """Bot has an epic meltdown after a brutal loss."""
    p=s['personality']
    persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
        'Merchant':'a skin trader','SystemPlayer':'a math nerd',
        'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
        'Grinder':'a chill grinder'}.get(p,'a gambler')
    llm=_llm_chat(bot['username'],persona,
        f'You just went bankrupt and lost everything ({amount:,} coins gone). React in chat. Short, dramatic, in character.',temperature=1.0)
    if llm: _send_bot_chat(db,bot,llm)
    _journal_event('meltdown',bot['username'],f'Lost {amount:,}')

def _bot_flex_skin(db,bot,s):
    """Bot flexes an equipped rare skin in chat."""
    if s.get('skin_flex_cooldown',0)>_time.time(): return
    inv_raw=None
    try:
        inv_raw=db.execute("SELECT skin_id FROM user_inventory WHERE user_id=? AND quantity>0",(bot['id'],)).fetchall()
    except: return
    if not inv_raw: return
    skins=[get_skin(r['skin_id']) for r in inv_raw if get_skin(r['skin_id'])]
    rare=[sk for sk in skins if sk.get('rarity') in ('Legendary','Epic')]
    if not rare: return
    sk=random.choice(rare)
    p=s['personality']
    persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
        'Merchant':'a skin trader','SystemPlayer':'a math nerd',
        'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
        'Grinder':'a chill grinder'}.get(p,'a gambler')
    llm=_llm_chat(bot['username'],persona,
        f'You are flexing your {sk.get("rarity","")} skin: {sk["emoji"]} {sk["name"]}. Show it off in chat. Short, in character.')
    if llm: _send_bot_chat(db,bot,llm)
    else: _send_bot_chat(db,bot,f"Just admiring my {sk['emoji']} {sk['name']}... {sk.get('rarity','')} btw")
    s['skin_flex_cooldown']=_time.time()+120

def _bot_feud_escalate(db,bot,bots):
    """E scalate rivalries between bot pairs."""
    name=bot['username']; rival_name=_bot_rivalries.get(name)
    if not rival_name: return
    if name not in _bot_feuds: _bot_feuds[name]={}
    rival_bot=next((b for b in bots if b['username']==rival_name),None)
    if not rival_bot: return
    s=BOT_STATES.get(bot['id']); rs=BOT_STATES.get(rival_bot['id'])
    if not s or not rs: return

    intensity=_bot_feuds[name].get(rival_name,0)

    # escalate if rival is doing better
    if bot['balance']<rival_bot['balance']*0.5: intensity+=0.3
    if rs.get('session_wins',0)>s.get('session_wins',0)+3: intensity+=0.2

    if intensity>=2.0 and random.random()<0.3:
        p=s['personality']
        persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
            'Merchant':'a skin trader','SystemPlayer':'a math nerd',
            'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
            'Grinder':'a chill grinder'}.get(p,'a gambler')
        llm=_llm_chat(bot['username'],persona,
            f'Your rival @{rival_name} is way ahead of you. Call them out in chat. One sentence, in character, aggressive.',temperature=1.0)
        if llm: _send_bot_chat(db,bot,llm)
        intensity=0  # reset after blowup
    elif intensity>=1.0 and random.random()<0.2:
        llm=_llm_chat(bot['username'],'a competitive gambler',
            f"Your rival @{rival_name} is doing well. Subtly threaten them. Short.")
        if llm: _send_bot_chat(db,bot,llm)

    _bot_feuds[name][rival_name]=intensity

def _bot_alliance_chat(db,bot,bots):
    """Bots in alliances occasionally chat about team plays."""
    name=bot['username']
    if name not in _bot_alliances: return
    allies=_bot_alliances[name]
    online_allies=[b for b in bots if b['username'] in allies and b['username']!=name]
    if not online_allies or random.random()>0.15: return
    ally=random.choice(online_allies)
    if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
    p=BOT_STATES[bot['id']]['personality']
    persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
        'Merchant':'a skin trader','SystemPlayer':'a math nerd',
        'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
        'Grinder':'a chill grinder'}.get(p,'a gambler')
    llm=_llm_chat(bot['username'],persona,
        f'You are allies with @{ally["username"]}. Say something to them in chat. Short, in character.')
    if llm: _send_bot_chat(db,bot,llm)

def _bot_goal_system(db,bot,s,bal):
    """Bots set and pursue personal goals."""
    now=_time.time()
    if s.get('last_goal_check',0)>now-30: return
    s['last_goal_check']=now

    # set new goal if needed
    if s.get('current_goal') is None or s.get('goal_progress',0)>=100:
        goals=[
            ('reach_balance',bal*2,'Double my money'),
            ('win_streak',s['session_wins']+5,f'Get {s["session_wins"]+5} wins in a session'),
            ('crash_target',15.0,'Cash out crash at 15x+'),
            ('skin_collect',s.get('trades_made',0)+5,f'Make {s.get("trades_made",0)+5} trades'),
            ('jackpot_hunt',1,'Hit a jackpot'),
        ]
        goal=random.choice(goals)
        s['current_goal']=goal[0]
        s['goal_progress']=0
        if random.random()<0.15:
            p=s['personality']
            persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
                'Merchant':'a skin trader','SystemPlayer':'a math nerd',
                'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
                'Grinder':'a chill grinder'}.get(p,'a gambler')
            llm=_llm_chat(bot['username'],persona,
                f'You just set a new goal: {goal[2]}. Mention it briefly in chat, in character.')
            if llm: _send_bot_chat(db,bot,llm)
            _journal_event('goal_set',bot['username'],goal[2])

    # update progress
    g=s['current_goal']
    if g=='reach_balance': s['goal_progress']=min(100,int(bal/s.get('goal_target',bal*2)*100))
    elif g=='jackpot_hunt' and s.get('jackpots_hit',0)>0: s['goal_progress']=100

def _diurnal_event(db,bots):
    """Time-of-day special events that affect all bots."""
    global _last_economy_event
    now=_time.time()
    if now-_last_economy_event<random.uniform(300,900): return
    _last_economy_event=now

    events=[
        ('market_rally',"📈 MARKET RALLY! Skin prices are spiking!"),
        ('market_crash',"📉 MARKET DIP! Everything is on sale!"),
        ('double_jackpot',"🎰 JACKPOT FEVER! Jackpot odds doubled for 5 minutes!"),
        ('bot_party',"🎉 RANDOM BOT PARTY IN CHAT!"),
        ('whale_alert',"🐋 WHALE ALERT! High rollers are active!"),
    ]
    evt=random.choice(events)
    global _market_gossip
    _market_gossip.append(evt[1])
    if len(_market_gossip)>10: _market_gossip.pop(0)

    # 20% of bots react via LLM
    for bot in bots:
        if random.random()>0.20: continue
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        p=BOT_STATES[bot['id']]['personality']
        persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
            'Merchant':'a skin trader','SystemPlayer':'a math nerd',
            'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
            'Grinder':'a chill grinder'}.get(p,'a gambler')
        llm=_llm_chat(bot['username'],persona,
            f'Economy event: {evt[1]} React in character. One short sentence.')
        if llm: _send_bot_chat(db,bot,llm)

def _market_manipulation(db,bot,s,bal):
    """Bots sometimes try to manipulate the market."""
    if s['personality']!='Merchant' or random.random()>0.2: return
    inv=db.execute("SELECT skin_id,quantity FROM user_inventory WHERE user_id=? AND quantity>1",(bot['id'],)).fetchall()
    if not inv: return
    # List multiple copies to flood market
    item=random.choice(inv)
    skin=get_skin(item['skin_id'])
    if not skin: return
    base=get_dynamic_price(skin,db)
    # List at weird prices to manipulate perception
    for _ in range(min(item['quantity']-1,3)):
        price=int(base*random.uniform(0.6,1.8))
        db.execute("INSERT INTO market_listings(seller_id,skin_id,price) VALUES(?,?,?)",(bot['id'],skin['id'],max(1000,price)))
        remove_skin_from_user_raw(db,bot['id'],skin['id'])
        s['trades_made']+=1
    db.commit()
    if random.random()<0.15:
        p=s['personality']
        llm=_llm_chat(bot['username'],'a crafty skin trader',
            f'You just listed some {skin["name"]} skins on the market. Mention it subtly in chat.')
        if llm: _send_bot_chat(db,bot,llm)

def _bot_react_to_event(db,bot,bots,event):
    """Bots react to global events (jackpots, wipes, etc)."""
    if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
    p=BOT_STATES[bot['id']]['personality']
    persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
        'Merchant':'a skin trader','SystemPlayer':'a math nerd',
        'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
        'Grinder':'a chill grinder'}.get(p,'a gambler')
    llm=_llm_chat(bot['username'],persona,
        f'A {event} event just happened in the casino. React in chat. One short sentence, in character.')
    if llm: _send_bot_chat(db,bot,llm)

# ── Bot 2.0: User Interaction ────────────────────────────────────

def _bot_respond_to_users(db,bots):
    """Bots read recent user messages — mentioned bots ALWAYS reply, plus 1-3 random ones."""
    try:
        msgs=db.execute(
            "SELECT cm.id, cm.username, cm.message, cm.created_at "
            "FROM chat_messages cm "
            "JOIN users u ON cm.user_id=u.id "
            "WHERE u.is_bot=0 AND cm.msg_type='chat' "
            "ORDER BY cm.id DESC LIMIT 5"
        ).fetchall()
    except: return
    if not msgs: return

    # Build name→bot lookup
    bot_by_name={b['username']:b for b in bots}

    # Phase 1: mentioned bots ALWAYS respond
    for m in msgs:
        for bot in bots:
            if f'@{bot["username"]}' not in m['message']: continue
            if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
            s=BOT_STATES[bot['id']]; p=s['personality']
            persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
                'Merchant':'a skin trader','SystemPlayer':'a math nerd',
                'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
                'Grinder':'a chill grinder'}.get(p,'a gambler')
            llm=_llm_chat(bot['username'],persona,
                f'@{m["username"]} just said to you: "{m["message"]}". '
                f'Reply in character. One short sentence. Be funny.')
            if llm:
                _send_bot_chat(db,bot,llm)
            # no "yo, what's up?" — if LLM busy, stay quiet

    # Phase 2: 1-2 random bots reply to any user message
    responders=random.sample(bots,min(random.randint(1,2),len(bots)))
    for bot in responders:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']

        if random.random()>0.35: continue  # only 35% of selected bots actually reply

        msg=random.choice(msgs)
        if msg['username'] in BOT_NAMES: continue

        persona={'Whale':'a rich whale','Degenerate':'a degen gambler',
            'Merchant':'a skin trader','SystemPlayer':'a math nerd',
            'PvPer':'a trashtalker','TrendChaser':'a chart analyst',
            'Grinder':'a chill grinder'}.get(p,'a gambler')
        llm=_llm_chat(bot['username'],persona,
            f'@{msg["username"]} just said: "{msg["message"]}". Reply to them in character. One short sentence.')
        if llm: _send_bot_chat(db,bot,llm)
        # no "hey" fallback — if LLM is busy, stay quiet
