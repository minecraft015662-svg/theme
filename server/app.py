"""Sarthak34 license server: website (admin) + API used by the `sarthak34` CLI."""
import os, io, json, re, sqlite3, secrets, tarfile, hmac, sys
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, session, redirect, render_template_string, Response, abort

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "licenses.db")
PKG = os.path.join(BASE, "packages")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
if not ADMIN_PASS:
    sys.exit("Set ADMIN_PASS (and SECRET_KEY, PUBLIC_URL) environment variables first.")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or sys.exit("Set SECRET_KEY (random long string).")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=PUBLIC_URL.startswith("https"))

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c
def init():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS licenses(id INTEGER PRIMARY KEY, key TEXT UNIQUE, email TEXT, plan TEXT,
            max_domains INTEGER DEFAULT 1, status TEXT DEFAULT 'active', created_at TEXT, expires_at TEXT);
        CREATE TABLE IF NOT EXISTS activations(id INTEGER PRIMARY KEY, license_id INTEGER, domain TEXT, ip TEXT,
            first_seen TEXT, last_seen TEXT, UNIQUE(license_id, domain));""")
init()

def client_ip(): return request.headers.get("CF-Connecting-IP") or request.remote_addr
def same(a, b): return hmac.compare_digest(a.encode(), b.encode())
def new_key():
    p = lambda: secrets.token_hex(2).upper()
    return f"S34-{p()}-{p()}-{p()}-{p()}"

def check(key, email, domain):
    key = (key or "").strip().upper(); email = (email or "").strip().lower(); domain = (domain or "").strip().lower()
    if not (key and email and domain): return None, "missing license, email or domain"
    c = db()
    lic = c.execute("SELECT * FROM licenses WHERE key=?", (key,)).fetchone()
    if not lic or not same(lic["email"], email): return None, "invalid license or email"
    if lic["status"] != "active": return None, "license is revoked"
    if lic["expires_at"] and lic["expires_at"] < now(): return None, "license expired"
    act = c.execute("SELECT id FROM activations WHERE license_id=? AND domain=?", (lic["id"], domain)).fetchone()
    if act:
        c.execute("UPDATE activations SET last_seen=?, ip=? WHERE id=?", (now(), client_ip(), act["id"]))
    else:
        n = c.execute("SELECT COUNT(*) FROM activations WHERE license_id=?", (lic["id"],)).fetchone()[0]
        if n >= lic["max_domains"]: return None, f"domain limit reached ({lic['max_domains']})"
        c.execute("INSERT INTO activations(license_id,domain,ip,first_seen,last_seen) VALUES(?,?,?,?,?)",
                  (lic["id"], domain, client_ip(), now(), now()))
    c.commit()
    return lic, None

def authed():
    d = request.get_json(silent=True) or {}
    return check(d.get("license"), d.get("email"), d.get("domain"))

# ---------------- API ----------------
@app.post("/api/activate")
def api_activate():
    lic, err = authed()
    if err: return jsonify(ok=False, error=err), 403
    return jsonify(ok=True, plan=lic["plan"], expires=lic["expires_at"])

@app.post("/api/extensions")
def api_extensions():
    lic, err = authed()
    if err: return jsonify(ok=False, error=err), 403
    out = []
    root = os.path.join(PKG, "extensions")
    for n in sorted(os.listdir(root)):
        try: out.append(json.load(open(os.path.join(root, n, "ext.json"))))
        except Exception: pass
    return jsonify(ok=True, extensions=out)

@app.post("/api/package/<name>")
def api_package(name):
    lic, err = authed()
    if err: return jsonify(ok=False, error=err), 403
    if not re.fullmatch(r"[a-z0-9-]+", name): abort(404)
    folder = os.path.join(PKG, "theme") if name == "theme" else os.path.join(PKG, "extensions", name)
    if not os.path.isdir(folder): return jsonify(ok=False, error="package not found"), 404
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for r, _, files in os.walk(folder):
            for f in files:
                full = os.path.join(r, f); t.add(full, arcname=os.path.relpath(full, folder))
    return Response(buf.getvalue(), mimetype="application/gzip")

@app.get("/install.sh")
def install_sh():
    s = open(os.path.join(BASE, "..", "client", "sarthak34")).read()
    return Response(s.replace("__API__", PUBLIC_URL or request.host_url.rstrip("/")), mimetype="text/x-shellscript")

# ---------------- website ----------------
CSS = """
:root{--ink:#0d1020;--slate:#151a33;--edge:#2a3160;--v:#8f7bff;--r:#ff7eb6;--t:#e8eaff;--m:#9aa1c9}
*{box-sizing:border-box}body{margin:0;font-family:Manrope,system-ui,sans-serif;background:var(--ink);color:var(--t);
background-image:radial-gradient(800px 460px at 10% -10%,rgba(143,123,255,.22),transparent 60%)}
main{max-width:1040px;margin:0 auto;padding:32px 20px}h1{margin:0 0 6px;font-size:28px}h2{font-size:17px;margin:0 0 14px}
p{color:var(--m);line-height:1.6}.card{background:rgba(27,33,66,.75);border:1px solid var(--edge);border-radius:12px;padding:20px;margin:18px 0}
label{display:block;font-size:13px;color:var(--m);margin-bottom:4px}input,select{width:100%;padding:10px;border-radius:8px;border:1px solid var(--edge);background:#10142a;color:var(--t);font:inherit}
input:focus,select:focus{outline:2px solid var(--v);border-color:var(--v)}.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
button{background:var(--v);color:#10102a;border:0;border-radius:8px;padding:10px 16px;font:inherit;font-weight:700;cursor:pointer}
button.ghost{background:transparent;color:var(--t);border:1px solid var(--edge);padding:5px 10px;font-weight:600;font-size:12px}
button.danger{color:var(--r);border-color:rgba(255,126,182,.4)}table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--edge)}th{color:var(--m);font-weight:600}.wrap{overflow-x:auto}
code{font-family:'JetBrains Mono',monospace;background:#10142a;padding:2px 6px;border-radius:6px;word-break:break-all}
.ok{color:#6ee7a8}.bad{color:var(--r)}.flash{border-color:var(--v)}a{color:var(--v)}.bar{display:flex;justify-content:space-between;align-items:center;gap:12px}
"""
PAGE = """<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>{{title}}</title><link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=JetBrains+Mono&display=swap" rel=stylesheet>
<style>{{css|safe}}</style></head><body><main>{{body|safe}}</main></body></html>"""
def page(title, body): return render_template_string(PAGE, title=title, css=CSS, body=body)

@app.get("/")
def home():
    base = PUBLIC_URL or request.host_url.rstrip("/")
    return page("Sarthak34", f"""<h1>Sarthak34 theme for Pterodactyl</h1>
<p>Licensed panel theme with installable extensions. Licenses are issued by the owner and tied to your email and panel domain.</p>
<div class=card><h2>Install on your panel server</h2><p>Run as root, then enter your license and email when asked:</p>
<p><code>curl -sSL {base}/install.sh | sudo bash</code></p></div>""")

def csrf():
    if "csrf" not in session: session["csrf"] = secrets.token_hex(16)
    return session["csrf"]
def need_admin():
    if not session.get("admin"): return redirect("/admin/login")
def check_csrf():
    if not same(request.form.get("csrf", ""), session.get("csrf", "x")): abort(400)

LOGIN = """<div style="max-width:380px;margin:12vh auto"><div class=card><h1>Admin login</h1><p>Sarthak34 license manager</p>
<form method=post><input type=hidden name=csrf value="{{c}}"><label>Username</label><input name=u autocomplete=username required>
<label style="margin-top:12px">Password</label><input name=p type=password autocomplete=current-password required>
{% if err %}<p class=bad>{{err}}</p>{% endif %}<p><button>Sign in</button></p></form></div></div>"""

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    err = None
    if request.method == "POST":
        check_csrf()
        if same(request.form.get("u", ""), ADMIN_USER) and same(request.form.get("p", ""), ADMIN_PASS):
            session.clear(); session["admin"] = True; return redirect("/admin")
        err = "Wrong username or password"
    return page("Admin login", render_template_string(LOGIN, c=csrf(), err=err))

@app.get("/admin/logout")
def logout(): session.clear(); return redirect("/admin/login")

DASH = """<div class=bar><div><h1>Licenses</h1><p>Create a key for a customer's email. Each key works on a limited number of panel domains.</p></div><a href="/admin/logout">Sign out</a></div>
{% if new %}<div class="card flash"><h2>License created</h2><p>Email: <b>{{new.email}}</b></p><p>Key: <code>{{new.key}}</code></p></div>{% endif %}
<div class=card><h2>Create license</h2><form method=post action="/admin/create"><input type=hidden name=csrf value="{{c}}">
<div class=row><div><label>Customer email</label><input type=email name=email required></div>
<div><label>Plan</label><select name=plan><option>standard</option><option>pro</option></select></div>
<div><label>Valid days (0 = lifetime)</label><input type=number name=days value=0 min=0></div>
<div><label>Max panel domains</label><input type=number name=max value=1 min=1></div></div><p><button>Generate license</button></p></form></div>
<div class="card wrap"><table><tr><th>Key</th><th>Email</th><th>Plan</th><th>Status</th><th>Expires</th><th>Domains</th><th></th></tr>
{% for l in rows %}<tr><td><code>{{l.key}}</code></td><td>{{l.email}}</td><td>{{l.plan}}</td>
<td class="{{'ok' if l.status=='active' else 'bad'}}">{{l.status}}</td><td>{{l.expires_at or 'lifetime'}}</td>
<td>{{l.domains or '-'}} ({{l.n}}/{{l.max_domains}})</td><td><form method=post action="/admin/toggle/{{l.id}}" style="display:inline">
<input type=hidden name=csrf value="{{c}}"><button class=ghost>{{'Revoke' if l.status=='active' else 'Reactivate'}}</button></form>
<form method=post action="/admin/reset/{{l.id}}" style="display:inline"><input type=hidden name=csrf value="{{c}}"><button class=ghost>Reset domains</button></form>
<form method=post action="/admin/delete/{{l.id}}" style="display:inline" onsubmit="return confirm('Delete this license?')"><input type=hidden name=csrf value="{{c}}"><button class="ghost danger">Delete</button></form></td></tr>
{% else %}<tr><td colspan=7>No licenses yet. Create the first one above.</td></tr>{% endfor %}</table></div>"""

@app.get("/admin")
def admin():
    r = need_admin()
    if r: return r
    rows = db().execute("""SELECT l.*, (SELECT COUNT(*) FROM activations a WHERE a.license_id=l.id) n,
        (SELECT group_concat(domain, ', ') FROM activations a WHERE a.license_id=l.id) domains
        FROM licenses l ORDER BY l.id DESC""").fetchall()
    new = session.pop("new", None)
    return page("Licenses", render_template_string(DASH, rows=rows, c=csrf(), new=new))

@app.post("/admin/create")
def create():
    r = need_admin()
    if r: return r
    check_csrf()
    email = request.form.get("email", "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email): abort(400)
    days = max(0, int(request.form.get("days", 0) or 0)); mx = max(1, int(request.form.get("max", 1) or 1))
    plan = "pro" if request.form.get("plan") == "pro" else "standard"
    exp = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S") if days else None
    key = new_key()
    with db() as c:
        c.execute("INSERT INTO licenses(key,email,plan,max_domains,created_at,expires_at) VALUES(?,?,?,?,?,?)",
                  (key, email, plan, mx, now(), exp))
    session["new"] = {"key": key, "email": email}
    return redirect("/admin")

@app.post("/admin/toggle/<int:i>")
def toggle(i):
    r = need_admin()
    if r: return r
    check_csrf()
    with db() as c: c.execute("UPDATE licenses SET status=CASE status WHEN 'active' THEN 'revoked' ELSE 'active' END WHERE id=?", (i,))
    return redirect("/admin")

@app.post("/admin/reset/<int:i>")
def reset(i):
    r = need_admin()
    if r: return r
    check_csrf()
    with db() as c: c.execute("DELETE FROM activations WHERE license_id=?", (i,))
    return redirect("/admin")

@app.post("/admin/delete/<int:i>")
def delete(i):
    r = need_admin()
    if r: return r
    check_csrf()
    with db() as c:
        c.execute("DELETE FROM activations WHERE license_id=?", (i,)); c.execute("DELETE FROM licenses WHERE id=?", (i,))
    return redirect("/admin")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8080)))
