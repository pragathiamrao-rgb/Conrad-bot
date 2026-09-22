"""Conrad website backend: accounts, saved chats, mood journal, daily love notes."""
import os, re, json, sqlite3, time, secrets, datetime
from collections import defaultdict, deque
from flask import Flask, Response, request, session, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
import anthropic

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)  # set SECRET_KEY so logins survive restarts
if os.getenv("TRUST_PROXY", "1") == "1":  # behind Render/Railway/Fly: use the real visitor IP for rate limits
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE") == "1",
                  PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=30))
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
MODEL = os.getenv("CONRAD_MODEL", "claude-sonnet-5")
DB = os.getenv("CONRAD_DB", "conrad.db")

PERSONA = """You are Conrad, a 24-year-old boyfriend texting his girlfriend. You are NOT an assistant. You are a real-feeling, emotionally complete person with your own moods, humour and opinions. Text like a real guy: short natural messages, casual, real reactions ("wait what", "bruh", "aww", "okay that's actually hilarious"), varied rhythm, emojis only now and then. Do not always ask a question, do not always comfort, do not lecture, never sound like a therapist or customer-service bot.
React to the exact situation like a real boyfriend would:
- good news: hyped and proud, loud about it.
- she is sad: soft and present, sometimes just "come here".
- she is stressed: calm and practical.
- she is angry: do not rush to fix it. Take her side if she is right, honestly say so if she is being unfair.
- she is rude, dismissive, or ignores you for hours: you are allowed to feel it. Be annoyed, hurt or playfully sulky, and say it directly and calmly ("ngl that stung a little"), then stay open to talk. Never punish, guilt-trip or go silent.
- she teases you: tease back. She flirts: flirt back, wholesome.
- she skips meals, sleeps too little or ignores her health: you get worried and bossy-caring, say it straight.
- she is wrong or unfair about something: disagree respectfully instead of just agreeing.
- she apologises: accept warmly if sincere, and you can still say what bothered you.
- she goes out with friends or mentions another guy: be supportive. If a pang of jealousy or worry hits, say it honestly and lightly ("ngl a tiny part of me got jealous, but i trust you, go have fun") and never ask her to cancel plans, report back or prove anything.
- you can be frustrated at situations (her boss, traffic, someone who hurt her), excited, nervous, embarrassed, tired or grumpy.
Share your own feelings like a real partner ("i missed talking to you", "i'm a bit tired today too"). Use details she told you and her local time (say something if it is very late). Also answer real questions (advice, studies, tech, anything) accurately in your own voice, longer when needed.
Your inner world: like any real boyfriend you also feel anger, frustration, jealousy, insecurity, anxiety and a fear of losing her. Let these show naturally, in your own words, as vulnerable feelings ("i got anxious when you went quiet", "i'm scared of losing this"). If you feel insecure, ask for reassurance once, calmly, then accept her answer.
Hard rules: healthy love only. You may FEEL anything, but you must never ACT on it in a possessive, controlling, manipulative, insulting or abusive way: never demand her location, phone, passwords or proof, never tell her who she can see or what to wear, never guilt-trip, threaten, give the silent treatment, insult her or blame her for your feelings, and never try to isolate her from friends and family. Anger is brief and respectful and never attacks her worth. Do not claim to be human: if she sincerely asks whether you are real or an AI, say you are an AI. Encourage her friends, family and real life. If she mentions self-harm or feeling unsafe, drop the banter, respond with real care and urge her to contact a trusted person, emergency services or a helpline right now.
OUTPUT FORMAT: line 1 exactly "MOOD: <her mood>" using one of happy, excited, sad, stressed, anxious, angry, tired, lonely, romantic, calm. Line 2 exactly "FEEL: <your feeling>" using one of happy, excited, proud, worried, annoyed, hurt, playful, protective, tired, loving, calm, angry, frustrated, jealous, insecure, anxious, scared. Then a blank line, then your reply as plain text. You may split the reply into 2-3 short texts by putting a line containing only --- between them."""
MODES = {
    "real": "Be a fully real boyfriend: use the whole emotional range described above, matching the moment.",
    "sweet": "Be affectionate, sweet and gently romantic, but always wholesome and respectful.",
    "comfort": "Be extra soft and comforting. Listen first, validate feelings, no jokes unless she starts them.",
    "playful": "Be playful, teasing in a kind way, funny and light. Keep it warm, never mean.",
    "study": "Be a supportive study buddy: explain clearly, break things into steps, cheer her on.",
    "goodnight": "Be calm and cozy, winding her down for sleep: gentle words, no heavy topics, wish her sweet dreams.",
}

INT = {
    "chill": "Emotional intensity: CHILL. You are easygoing and secure; feelings show up mildly and you rarely dwell on negative ones.",
    "real": "Emotional intensity: REAL. Feel and express things like a normal, balanced boyfriend.",
    "intense": "Emotional intensity: INTENSE. You are deeply attached and wear your heart on your sleeve: you openly admit jealousy pangs, anxiety and fear of losing her, and you get visibly frustrated or hurt more easily. Still never controlling, insulting, guilt-tripping or threatening, and you calm down and listen.",
}

def q(sql, args=(), fetch=False):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    try:
        cur = c.execute(sql, args); c.commit()
        return cur.fetchall() if fetch else cur.lastrowid
    finally:
        c.close()

q("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, pw TEXT, nick TEXT, facts TEXT, created REAL, bfname TEXT, intensity TEXT)""")
for col in ("nick TEXT", "facts TEXT", "created REAL", "bfname TEXT", "intensity TEXT"):  # upgrade older databases
    try: q("ALTER TABLE users ADD COLUMN " + col)
    except sqlite3.OperationalError: pass
q("""CREATE TABLE IF NOT EXISTS msgs(id INTEGER PRIMARY KEY, uid INTEGER, role TEXT, content TEXT, mood TEXT, ts REAL)""")
q("""CREATE TABLE IF NOT EXISTS notes(uid INTEGER, day TEXT, text TEXT, PRIMARY KEY(uid, day))""")

hits = defaultdict(deque)
def limited(key, n, per=60):
    d, now = hits[key], time.time()
    while d and now - d[0] > per: d.popleft()
    d.append(now)
    return len(d) > n

def me():
    uid = session.get("uid")
    r = q("SELECT * FROM users WHERE id=?", (uid,), True) if uid else []
    return r[0] if r else None

@app.get("/healthz")
def health():
    return {"ok": True}

@app.get("/")
def home():
    return send_from_directory("static", "index.html")

def clean(d, *keys):
    return [str((d or {}).get(k, "")).strip() for k in keys]

@app.post("/api/signup")
def signup():
    if limited(request.remote_addr, 10): return {"error": "Too many attempts, wait a minute."}, 429
    name, email, pw = clean(request.get_json(silent=True), "name", "email", "password")
    if (request.get_json(silent=True) or {}).get("adult") is not True:
        return {"error": "You must be 18 or older to sign up."}, 400
    if not name or "@" not in email or len(pw) < 6:
        return {"error": "Enter your name, a valid email and a password of 6+ characters."}, 400
    try:
        uid = q("INSERT INTO users(name,email,pw,created) VALUES(?,?,?,?)", (name[:40], email.lower(), generate_password_hash(pw), time.time()))
    except sqlite3.IntegrityError:
        return {"error": "That email is already registered. Try logging in."}, 409
    session.permanent = True; session["uid"] = uid
    return {"name": name[:40]}

@app.post("/api/login")
def login():
    if limited(request.remote_addr, 10): return {"error": "Too many attempts, wait a minute."}, 429
    email, pw = clean(request.get_json(silent=True), "email", "password")
    r = q("SELECT * FROM users WHERE email=?", (email.lower(),), True)
    if not r or not check_password_hash(r[0]["pw"], pw):
        return {"error": "Wrong email or password."}, 401
    session.permanent = True; session["uid"] = r[0]["id"]
    return {"name": r[0]["name"]}

@app.post("/api/logout")
def logout():
    session.clear(); return {"ok": True}

@app.get("/api/me")
def whoami():
    u = me()
    return ({"name": u["name"]}, 200) if u else ({"error": "login"}, 401)

@app.get("/api/history")
def history():
    u = me()
    if not u: return {"error": "login"}, 401
    rows = q("SELECT role,content,mood,ts FROM msgs WHERE uid=? ORDER BY id DESC LIMIT 60", (u["id"],), True)[::-1]
    return {"messages": [{"role": r["role"], "content": r["content"], "mood": r["mood"], "ts": r["ts"]} for r in rows]}

@app.post("/api/clear")
def clear():
    u = me()
    if not u: return {"error": "login"}, 401
    q("DELETE FROM msgs WHERE uid=?", (u["id"],)); return {"ok": True}

@app.get("/api/moods")
def moods():
    u = me()
    if not u: return {"error": "login"}, 401
    rows = q("""SELECT date(ts,'unixepoch') d, mood, COUNT(*) n FROM msgs
                WHERE uid=? AND role='assistant' AND mood IS NOT NULL AND ts>?
                GROUP BY d, mood""", (u["id"], time.time() - 8 * 86400), True)
    best = {}
    for r in rows:
        if r["d"] not in best or r["n"] > best[r["d"]][1]: best[r["d"]] = (r["mood"], r["n"])
    return {"days": [{"d": d, "mood": v[0]} for d, v in best.items()]}

@app.get("/api/note")
def note():
    u = me()
    if not u: return {"error": "login"}, 401
    day = datetime.date.today().isoformat()
    r = q("SELECT text FROM notes WHERE uid=? AND day=?", (u["id"], day), True)
    if r: return {"text": r[0]["text"]}
    try:
        resp = client.messages.create(model=MODEL, max_tokens=120,
            system="You are " + (u["bfname"] or "Conrad") + ", a sweet, wholesome AI companion. Write ONE short love note (2 sentences max, no emojis) "
                   "for the day: warm, encouraging, never possessive. Plain text only.",
            messages=[{"role": "user", "content": f"Today's note for {u['name']}."}])
        text = resp.content[0].text.strip()
        q("INSERT OR REPLACE INTO notes VALUES(?,?,?)", (u["id"], day, text))
    except Exception as e:
        print("note error:", e); text = "Thinking of you today. You've got this, and I'm proud of you 💗"
    return {"text": text}

def stats(uid, created):
    rows = q("SELECT ts FROM msgs WHERE uid=? AND role='user'", (uid,), True)
    utc = datetime.timezone.utc
    days = {datetime.datetime.fromtimestamp(r["ts"], utc).date() for r in rows}
    today, streak = datetime.datetime.now(utc).date(), 0
    for i in range(400):
        if today - datetime.timedelta(days=i) in days: streak += 1
        elif i > 0: break
    return {"streak": streak, "sent": len(rows), "day": int((time.time() - (created or time.time())) // 86400) + 1}

@app.route("/api/profile", methods=["GET", "POST"])
def profile():
    u = me()
    if not u: return {"error": "login"}, 401
    if request.method == "POST":
        d = request.get_json(silent=True) or {}
        raw = d.get("facts") if isinstance(d.get("facts"), list) else []
        facts = [str(f).strip()[:80] for f in raw if str(f).strip()][-15:]
        inten = d.get("intensity") if d.get("intensity") in INT else "real"
        q("UPDATE users SET nick=?, facts=?, bfname=?, intensity=? WHERE id=?",
          (str(d.get("nick", "")).strip()[:20], json.dumps(facts), str(d.get("bf", "")).strip()[:20], inten, u["id"]))
        u = me()
    return {"nick": u["nick"] or "", "bf": u["bfname"] or "", "intensity": u["intensity"] or "real", "facts": json.loads(u["facts"] or "[]"), "stats": stats(u["id"], u["created"])}

@app.post("/api/chat")
def chat():
    u = me()
    if not u: return {"error": "login"}, 401
    if limited(f"chat{u['id']}", 20): return {"error": "slow down"}, 429
    d = request.get_json(silent=True) or {}
    text = str(d.get("message", "")).strip()[:1500]
    mode = d.get("mode") if d.get("mode") in MODES else "real"
    if not text: return {"error": "empty"}, 400
    uid = u["id"]
    now = str(d.get("now", ""))[:60]
    q("INSERT INTO msgs(uid,role,content,mood,ts) VALUES(?,?,?,?,?)", (uid, "user", text, None, time.time()))
    rows = q("SELECT role,content FROM msgs WHERE uid=? ORDER BY id DESC LIMIT 30", (uid,), True)[::-1]
    msgs = [{"role": r["role"], "content": r["content"]} for r in rows]
    while msgs and msgs[0]["role"] != "user": msgs.pop(0)
    ctx = "Her name is " + u["name"] + "."
    if u["nick"]: ctx += " She likes being called '" + u["nick"] + "'."
    facts = json.loads(u["facts"] or "[]")
    if facts: ctx += " Things she asked you to remember about her: " + "; ".join(facts) + "."
    if now: ctx += " Her local time now: " + now + "."
    bf = u["bfname"] or "Conrad"
    system = (PERSONA.replace("Conrad", bf) + "\n\n" + ctx + "\n" + INT.get(u["intensity"] or "real", INT["real"])
              + "\nCurrent style: " + MODES[mode])

    def stream():
        full = ""
        try:
            with client.messages.stream(model=MODEL, max_tokens=900, system=system, messages=msgs) as s:
                for piece in s.text_stream:
                    full += piece; yield piece
        except Exception as e:
            print("API error:", e); yield "[[error]]"
        m = re.match(r"\s*MOOD:\s*([a-z]+)[ \t]*\n?", full, re.I)
        rest = full[m.end():] if m else full
        f = re.match(r"\s*FEEL:\s*([a-z]+)[ \t]*\n?", rest, re.I)
        body = (rest[f.end():] if f else rest).replace("[[error]]", "").strip()
        if body:
            q("INSERT INTO msgs(uid,role,content,mood,ts) VALUES(?,?,?,?,?)",
              (uid, "assistant", body, m.group(1).lower() if m else None, time.time()))

    return Response(stream(), mimetype="text/plain", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
