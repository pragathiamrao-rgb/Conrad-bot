# Conrad, romantic AI companion website

## Run it
```bash
cd conrad-app
python3 -m venv venv && source venv/bin/activate       # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key"                     # Windows: set ANTHROPIC_API_KEY=your-key
export SECRET_KEY="any-long-random-string"              # keeps logins alive across restarts
python server.py
```
Open http://localhost:5000

## Features
- Landing page, signup / login (hashed passwords, 30-day sessions), light and dark theme
- Real-boyfriend Conrad: full emotional range, split texts, his own feeling shown next to yours
- Background scene, falling or floating effects and emoji suggestions change with your mood
- Enter sends the message. Right-now panel shows your mood and Conrad's
- Weekly mood journal, daily note, streak stats, situations and moments buttons
- About me: nickname and things Conrad should remember (saved on the server)
- Clear chat, log out

## Customise
- Personality: `PERSONA` and `MODES` in `server.py`. Scenes and emoji sets: `SCENES` and `EMO` in `static/index.html`.

## Before going public
HTTPS, email verification and password reset, Postgres instead of SQLite, per-user usage limits (every message costs API credits).
