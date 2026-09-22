# Conrad — Gemini-powered version

Same website as the Anthropic version, but the AI replies come from Google's
Gemini API instead of Claude.

## Run it locally
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="your-key-from-aistudio.google.com"
export SECRET_KEY="any-long-random-string"
python server.py
```
Open http://localhost:5000

## Deploy
- **Labskraft or any Linux VM:** see `DEPLOY_LABSKRAFT.md`.
- **PythonAnywhere:** upload this folder, `pip3.12 install --user google-genai flask`,
  then use `pythonanywhere_wsgi.py` (fill in your username and Gemini key).

## Customise
Conrad's personality, modes and emotional-intensity settings are all in `server.py`
(`PERSONA`, `MODES`, `INT`) — identical to the Claude version. The model name is set by
`CONRAD_MODEL`, default `gemini-2.5-flash`.
