# Sarthak34 - license website + theme installer

## 1. License website (server side)
    cd server
    python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt
    export ADMIN_USER=sarthak ADMIN_PASS='strong-password' SECRET_KEY="$(python3 -c 'import secrets;print(secrets.token_hex(32))')" PUBLIC_URL=https://license.yourdomain.com
    gunicorn -b 127.0.0.1:8080 app:app
Put it behind your Cloudflare Tunnel / nginx with HTTPS. Open `/admin/login`, create a license for a customer's email, and give them the key.
Run it as a systemd service with the same env vars so it survives reboots. Keep `licenses.db` backed up.

## 2. Customer install (panel server)
    curl -sSL https://license.yourdomain.com/install.sh | sudo bash
It asks for **license key + email**, verifies on your server, then downloads and installs the theme.

## 3. Commands
    sarthak34 status
    sarthak34 update
    sarthak34 ext list
    sarthak34 ext install announcement-bar
    sarthak34 ext remove announcement-bar
    sarthak34 uninstall

## Add your own extension
Create `server/packages/extensions/<name>/` with `ext.json` ({"name","description"}) and `ext.css` and/or `ext.js`. It shows up in `ext list` immediately.
Edit the banner text in `announcement-bar/ext.js` before use.

## Security note
Files are delivered only after the server verifies key + email + domain, so that is the real protection. Anything already downloaded
to a customer's panel is plain CSS/JS and can be copied, so keep truly private logic on the server.
