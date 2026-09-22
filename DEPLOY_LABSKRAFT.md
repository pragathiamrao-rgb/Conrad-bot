# Running Conrad (Gemini version) on a Labskraft Linux VM

## 1. Get a free Gemini API key
1. Go to **aistudio.google.com** in a browser, sign in with any Google account.
2. Click **Get API key** > **Create API key**. Copy it — you will paste it in step 4.

## 2. Get the code onto the VM
From your own computer, copy the `conrad-app-gemini` folder to the VM. If you have SCP or the Labskraft file upload panel:
```bash
scp -r conrad-app-gemini youruser@YOUR_VM_IP:~/
```
Or upload the zip through Labskraft's file manager, then on the VM:
```bash
unzip conrad-app-gemini.zip
```

## 3. Install Python and the libraries
On the VM terminal:
```bash
cd conrad-app-gemini
sudo apt update && sudo apt install -y python3 python3-venv python3-pip   # skip if already installed
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Set your keys and run it
```bash
export GEMINI_API_KEY="paste-your-key-here"
export SECRET_KEY="any-long-random-text-30-plus-characters"
python server.py
```
You should see Flask say it's running on port 5000.

## 5. Open it in your browser
- If Labskraft gives your VM a public IP or a forwarded URL, open:
  `http://YOUR_VM_IP:5000`
- If port 5000 doesn't load, check that Labskraft's firewall/security group allows inbound traffic on port 5000 (or whichever port you choose with `PORT=8000 python server.py`).
- Sign up with the 18+ box ticked and chat with Conrad.

## 6. Keep it running after you close the terminal (recommended)
Plain `python server.py` stops the moment you close your terminal or disconnect. Pick one:

**Quick option — nohup:**
```bash
nohup venv/bin/python server.py > conrad.log 2>&1 &
```
Conrad keeps running in the background. Check `conrad.log` if something goes wrong.

**Proper option — systemd (survives VM reboots too):**
1. Edit `conrad.service` in this folder: replace `YOURLINUXUSER` (your VM login name, check with `whoami`) and paste your real Gemini key and a SECRET_KEY.
2. ```bash
   sudo cp conrad.service /etc/systemd/system/conrad.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now conrad
   ```
3. Check it's running: `sudo systemctl status conrad`
4. It now listens on port 8000 (gunicorn), so open `http://YOUR_VM_IP:8000`.

## Notes
- Gemini's free tier has daily and per-minute limits and may use your chats to improve Google's models — fine for testing, not ideal for other people's real chats. Check current limits at ai.google.dev.
- `conrad.db` (accounts and chats) lives in this folder. Back it up if you care about the data.
- For a real domain and HTTPS, put nginx in front of gunicorn and get a free certificate with Certbot — say the word if you want those steps too.
