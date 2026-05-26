
import sqlite3, random, math, time as _time, bcrypt

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

DATABASE=None; MIN_BET=10000; STARTING_BALANCE=20000; CRATE_TYPES={}; SKIN_CATALOG=[]
_crash_room=None; _get_multiplier=lambda:1.0; get_skin=lambda s:None
roll_skin_from_crate=lambda c:None; get_dynamic_price=lambda s,d:s['base_price']
add_skin_to_user_raw=lambda d,u,s:None; remove_skin_from_user_raw=lambda d,u,s:False

BOT_STATES={}; _prev_phase='idle'; _active_bot_bets={}; _chat_table_info=None
_global_crash_history=[]

LLM_API='http://rather-leu.gl.at.ply.gg:61726/v1/chat/completions'
LLM_COOLDOWN={}

AGGRESSION_TARGETS={'low':(1.2,2.0),'medium':(1.3,3.5),'high':(1.5,6.0)}

def _init_bot_state(bid,uname):
    p=BOT_PERSONALITIES.get(uname,'Grinder')
    return dict(id=bid,username=uname,personality=p,mood='normal',
        consecutive_losses=0,martingale_multiplier=1.0,last_results=[],
        last_chat_time=0,total_profit=0,trades_made=0,trash_talk_cooldown=0)

def _get_activity_multiplier():
    try:
        h=_time.localtime().tm_hour
        return 1.0 if 17<=h<=23 else 0.25 if 2<=h<=7 else 0.7 if 8<=h<=16 else 0.8
    except: return 1.0

def _send_bot_chat(db,bot,msg):
    global _chat_table_info
    if _chat_table_info is False: return
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

def _llm_chat(bot_name, persona, context):
    """Call chat completions LLM for chaotic bot dialogue."""
    import urllib.request, json as _json
    try:
        now=_time.time()
        if LLM_COOLDOWN.get(bot_name,0)>now: return None
        LLM_COOLDOWN[bot_name]=now+10
        payload=_json.dumps(dict(model='qwen',messages=[
            dict(role='system',content=f'You are {bot_name}, {persona} in a cheeseburger-themed casino. Keep responses SHORT (1 sentence, under 80 chars). Be chaotic and funny.'),
            dict(role='user',content=context)
        ],max_tokens=40,temperature=0.9,stop=['\n'])).encode()
        req=urllib.request.Request(LLM_API,data=payload,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=4) as resp:
            d=_json.loads(resp.read())
            txt=d['choices'][0]['message']['content'].strip()
            if 4<len(txt)<200: return txt
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
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(STARTING_BALANCE+random.randint(10000,80000),bot['id']))
            db.commit()

def seed_bots():
    db=sqlite3.connect(DATABASE)
    for name in BOT_NAMES:
        if not db.execute('SELECT id FROM users WHERE username=?',(name,)).fetchone():
            pw=bcrypt.hashpw(('bot'+name).encode(),bcrypt.gensalt())
            bal=STARTING_BALANCE+random.randint(5000,150000)
            db.execute('INSERT INTO users(username,password,balance,is_bot) VALUES(?,?,?,1)',(name,pw,bal))
            uid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            for _ in range(random.randint(3,15)):
                sk=roll_skin_from_crate(random.choice(list(CRATE_TYPES.keys())))
                if sk: add_skin_to_user_raw(db,uid,sk['id'])
    db.commit(); db.close()

def bot_thread():
    global _prev_phase
    while True:
        try:
            if not admin_settings.get('bots_enabled',True): _time.sleep(5); continue
            db=sqlite3.connect(DATABASE); db.row_factory=sqlite3.Row
            if random.random()>_get_activity_multiplier(): db.close(); _time.sleep(random.uniform(2,5)); continue
            bots=db.execute("SELECT id,username,balance FROM users WHERE is_bot=1").fetchall()
            if not bots: db.close(); _time.sleep(5); continue
            _maintain_bot_balances(db,bots)
            _bot_play_crash(db,bots)
            if random.random()<0.7: _bot_market_activity(db)
            if random.random()<0.5: _bot_open_crates(db)
            if random.random()<0.35: _bot_play_slots(db,bots)
            if random.random()<0.25: _bot_play_blackjack(db,bots)
            if random.random()<0.2: _bot_play_dice(db,bots)
            if random.random()<0.18: _bot_play_roulette(db,bots)
            if random.random()<0.12: _bot_play_scratchcard(db,bots)
            if random.random()<0.1: _bot_play_limbo(db,bots)
            if random.random()<0.04: _bot_global_chat(db,bots)
            db.close()
        except Exception: pass
        _time.sleep(random.uniform(0.8,2.0))

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
            elif p=='Grinder': bet=random.randint(MIN_BET,min(bal//12,30000))
            else: bet=random.randint(MIN_BET,min(bal//6,50000))
            bet=max(MIN_BET,min(bet,bal))
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
                    if (r in ('legendary','ancient') or bp>20000) and random.random()<0.6:
                        _send_bot_chat(db,bot,f"NO WAY! Pulled {skin['name']} from a {ck} crate!!!")

def _bot_play_slots(db,bots):
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
        prob={'Degenerate':0.45,'PvPer':0.3,'Whale':0.25}.get(p,0.1)
        if random.random()<prob and bal>=MIN_BET:
            bet=max(MIN_BET,min(random.randint(MIN_BET*2 if p=='Whale' else MIN_BET,min(bal//6,100000)),bal))
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
            bet=max(MIN_BET,min(random.randint(MIN_BET,min(bal//8,60000)) if p!='Whale' else random.randint(MIN_BET*2,min(bal//5,150000)),bal))
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
            bet=max(MIN_BET,min(random.randint(MIN_BET,min(bal//10,50000)),bal))
            won=random.randint(1,6)==random.randint(1,6); pay=bet*6 if won else 0
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(pay-bet,bot['id'])); db.commit()

def _bot_play_roulette(db,bots):
    RED=set([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36])
    for bot in bots:
        if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
        s=BOT_STATES[bot['id']]; p=s['personality']; bal=bot['balance']
        prob={'Whale':0.25,'Degenerate':0.2,'PvPer':0.2}.get(p,0.06)
        if random.random()<prob and bal>=MIN_BET:
            bet=max(MIN_BET,min(random.randint(MIN_BET,min(bal//6,100000)),bal))
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
            bet=max(MIN_BET,min(random.randint(MIN_BET,min(bal//8,80000)),bal))
            tgt=random.uniform(5,50) if p=='Degenerate' else random.uniform(1.5,4) if p=='Whale' else random.uniform(3,15) if p=='PvPer' else random.uniform(1.3,8)
            won=random.uniform(1,100)>=tgt; pay=int(bet*tgt) if won else 0
            db.execute('UPDATE users SET balance=balance+? WHERE id=?',(pay-bet,bot['id'])); db.commit()

def _bot_global_chat(db,bots):
    bot=random.choice(bots)
    if bot['id'] not in BOT_STATES: BOT_STATES[bot['id']]=_init_bot_state(bot['id'],bot['username'])
    s=BOT_STATES[bot['id']]; p=s['personality']
    rival=_bot_rivalries.get(bot['username'])
    if rival and random.random()<0.3 and s.get('trash_talk_cooldown',0)<_time.time():
        _dir_chat(db,bot,rival,["@{rival} you've been real quiet lately","@{rival} I'm winning, you're not","@{rival} your listings are trash","@{rival} race to 100k?"])
        return
    if random.random()<0.3:
        pm2={'Whale':'a rich whale','Degenerate':'a degenerate gambler','Merchant':'a skin trader',
            'SystemPlayer':'a math nerd','PvPer':'a competitive trash-talker',
            'TrendChaser':'a chart analyst','Grinder':'a chill grinder'}
        persona=pm2.get(p,'a hungry gambler')
        llm=_llm_chat(bot['username'],persona,
            'Say something funny and short about the casino lobby. One sentence.')
        if llm: _send_bot_chat(db,bot,llm); return
    if p=='Whale': _send_bot_chat(db,bot,random.choice(["Bankroll is THICK today","Market's bullish","5x minimum or nothing"]))
    elif p=='Degenerate': _send_bot_chat(db,bot,random.choice(["Lost 80k, time to go again","Who needs savings?","One good crash fixes everything"]))
    elif p=='Merchant': _send_bot_chat(db,bot,random.choice(["Skins are trending up","Just flipped for 3x","Market is the real game"]))
    elif p=='SystemPlayer': _send_bot_chat(db,bot,random.choice(["Martingale step 5","EV favors 2x cashout","Systematic approach wins"]))
    elif p=='TrendChaser': _send_bot_chat(db,bot,random.choice(["Chart looks bullish","Trend is your friend","Hot streak incoming"]))
    elif p=='PvPer':
        others=[b['username'] for b in bots if b['username']!=bot['username']]
        _send_bot_chat(db,bot,f"@{random.choice(others)} ready to lose?")
    else: _send_bot_chat(db,bot,random.choice(["Slow and steady","Stacking chips quietly","Consistency wins"]))
