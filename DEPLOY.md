# Deploying Conrad

## 1. Prepare
1. Get an API key at console.anthropic.com and set a monthly spending limit there. Every chat message costs credits.
2. Test locally first: `pip install -r requirements.txt`, set ANTHROPIC_API_KEY and SECRET_KEY, run `python server.py`, open http://localhost:5000.

## 2. Put the code on GitHub
```bash
cd conrad-app
git init && git add . && git commit -m "Conrad"
# create an empty private repo on github.com, then:
git remote add origin https://github.com/YOUR-NAME/conrad.git
git branch -M main && git push -u origin main
```
`.gitignore` already keeps your database, venv and .env out of the repo. Never commit your API key.

## 3a. Deploy on Render (recommended, keeps data)
1. render.com > New > **Blueprint** > pick your repo. It reads `render.yaml`.
2. When asked, paste your `ANTHROPIC_API_KEY`. SECRET_KEY is generated for you.
3. Click Apply. After the build, open the URL Render gives you (https://conrad-xxxx.onrender.com).
4. Sign up with the 18+ box ticked, and send Conrad a message.
The plan is paid because accounts and chats live in a SQLite file on a persistent disk (/var/data). Free plans erase files on every deploy.

## 3b. Deploy on Railway (alternative)
1. railway.app > New Project > Deploy from GitHub repo.
2. Add a **Volume** to the service and mount it at `/data`.
3. Variables: ANTHROPIC_API_KEY, SECRET_KEY (any long random text), CONRAD_DB=/data/conrad.db, COOKIE_SECURE=1.
4. Settings > Networking > Generate Domain. The `Procfile` supplies the start command.

## 4. Custom domain
Add your domain in the host's dashboard, create the DNS record it shows you, and wait for HTTPS to turn on automatically.

## 5. After launch
- Back up `conrad.db` regularly (download it from the disk or add a scheduled copy).
- Add a privacy policy and terms page. Chats are personal and emotional data.
- Watch usage in the Anthropic console. Add per-user daily message limits before sharing widely.
- Still missing for a public launch: email verification, password reset, and Postgres if you outgrow SQLite.

## Browser-only deploy (no installs): PythonAnywhere
See pythonanywhere_wsgi.py. Steps: upload conrad-app.zip in the Files tab, run `unzip conrad-app.zip` in a Bash console,
`pip3.12 install --user flask anthropic`, create a Manual-configuration web app (same Python version) with source
directory /home/YOURUSERNAME/conrad-app, paste pythonanywhere_wsgi.py into the WSGI file, Reload.
