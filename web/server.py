"""
web/server.py — Ghost Squad unified web server

Routes:
  /          Public leaderboard and stats site (no login required)
  /admin     Password-protected admin panel
  /api/...   JSON and action endpoints

Render-compatible: reads the PORT environment variable automatically.
"""

import threading
import os
import asyncio
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, render_template_string, request, redirect,
    url_for, session, jsonify
)

app = Flask(__name__)
app.secret_key = os.urandom(32)

_db       = None
_bot      = None
_password = "ghostsquad@admin"

# ---------------------------------------------------------------------------
# SHARED CSS
# ---------------------------------------------------------------------------

PUBLIC_CSS = """
<style>
:root {
  --bg: #0f0f13; --surface: #18181f; --card: #1e1e27; --border: #2a2a38;
  --accent: #7c3aed; --accent2: #a855f7; --green: #22c55e; --red: #ef4444;
  --yellow: #f59e0b; --blue: #3b82f6; --text: #e8e8f0; --muted: #7a7a94;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
a { color: var(--accent); text-decoration: none; }
a:hover { opacity: .8; }

.pub-nav {
  background: rgba(24,24,31,.9); backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 0 2rem; display: flex; align-items: center;
  justify-content: space-between; height: 60px;
  position: sticky; top: 0; z-index: 100;
}
.pub-nav .logo { font-size: 1.1rem; font-weight: 800; }
.pub-nav .logo span { color: var(--accent2); }
.pub-nav .nav-right { display: flex; gap: 1.5rem; font-size: .9rem; }
.pub-nav .nav-right a { color: var(--muted); transition: color .2s; }
.pub-nav .nav-right a:hover { color: var(--text); }

.hero { text-align: center; padding: 4rem 1.5rem 2rem; }
.hero h1 { font-size: clamp(2rem, 5vw, 3.2rem); font-weight: 900; line-height: 1.1; }
.hero h1 .hl { color: var(--accent2); }
.hero p { color: var(--muted); font-size: 1rem; margin-top: .75rem; max-width: 500px; margin-inline: auto; }

.container { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }

.stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2.5rem; }
.stat-card {
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  padding: 1.5rem; text-align: center; transition: border-color .2s;
}
.stat-card:hover { border-color: var(--accent); }
.stat-card .val { font-size: 2.2rem; font-weight: 800; }
.stat-card .lbl { font-size: .78rem; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-top: .25rem; }
.c-green { color: var(--green); } .c-yellow { color: var(--yellow); }
.c-blue { color: var(--blue); } .c-purple { color: var(--accent2); }

.sec-title { font-size: 1rem; font-weight: 700; margin-bottom: 1.25rem; }

.tcard { background: var(--card); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; margin-bottom: 2rem; }
.tcard-head { padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border); font-weight: 700; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th { text-align: left; padding: .75rem 1.25rem; background: rgba(255,255,255,.02); color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid var(--border); }
td { padding: .85rem 1.25rem; border-bottom: 1px solid rgba(255,255,255,.03); vertical-align: middle; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(255,255,255,.02); }

.pill { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: .75rem; font-weight: 600; }
.pill-green { background: rgba(34,197,94,.12); color: var(--green); }
.pill-red   { background: rgba(239,68,68,.12);  color: var(--red); }

.prog-bar-wrap { margin-bottom: 2.5rem; }
.prog-bar-wrap .label-row { display: flex; justify-content: space-between; font-size: .88rem; margin-bottom: .4rem; }
.prog-track { background: var(--surface); border-radius: 99px; height: 10px; overflow: hidden; border: 1px solid var(--border); }
.prog-fill  { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 99px; transition: width .5s; }

.tip-card { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem; }
.tip-date { font-size: .75rem; color: var(--muted); margin-bottom: .5rem; }
.tip-body { font-size: .9rem; line-height: 1.6; }

footer { text-align: center; padding: 2rem; color: var(--muted); font-size: .82rem; border-top: 1px solid var(--border); margin-top: 2rem; }

.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); display: inline-block; animation: blink 2s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
"""

ADMIN_CSS = """
<style>
:root {
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --accent: #7c3aed; --green: #22c55e; --red: #ef4444;
  --yellow: #f59e0b; --text: #e6edf3; --muted: #8b949e; --blue: #3b82f6;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
a { color: var(--accent); text-decoration: none; }

nav { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 2rem; display: flex; align-items: center; justify-content: space-between; height: 56px; position: sticky; top: 0; z-index: 100; }
.logo { font-size: 1rem; font-weight: 700; }
.badge { background: var(--accent); color: #fff; font-size: .65rem; padding: 2px 7px; border-radius: 99px; font-weight: 700; margin-left: .4rem; }
.nav-links { display: flex; gap: 1.25rem; font-size: .87rem; }
.nav-links a { color: var(--muted); transition: color .2s; }
.nav-links a:hover, .nav-links a.active { color: var(--text); }

.container { max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }
.page-title { font-size: 1.4rem; font-weight: 700; margin-bottom: 1.5rem; }
.grid { display: grid; gap: 1.25rem; }
.grid-2 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
.grid-4 { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.4rem; }
.card-title { font-size: .72rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; margin-bottom: .4rem; }
.card-value { font-size: 1.9rem; font-weight: 700; }
.card-sub { font-size: .82rem; color: var(--muted); margin-top: .2rem; }
.stat-blue { color: var(--blue); } .stat-green { color: var(--green); }
.stat-yellow { color: var(--yellow); }

.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .87rem; }
th { text-align: left; padding: .7rem 1rem; background: rgba(255,255,255,.03); color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid var(--border); }
td { padding: .75rem 1rem; border-bottom: 1px solid rgba(255,255,255,.04); vertical-align: middle; }
tr:hover td { background: rgba(255,255,255,.02); }

.pill { display: inline-block; padding: 2px 9px; border-radius: 99px; font-size: .73rem; font-weight: 600; }
.pill-green { background: rgba(34,197,94,.15); color: var(--green); }
.pill-red   { background: rgba(239,68,68,.15);  color: var(--red); }
.pill-yellow{ background: rgba(245,158,11,.15); color: var(--yellow); }
.pill-blue  { background: rgba(59,130,246,.15); color: var(--blue); }

.form-group { margin-bottom: 1.1rem; }
label { display: block; font-size: .83rem; color: var(--muted); margin-bottom: .35rem; font-weight: 500; }
input, select, textarea {
  width: 100%; padding: .6rem .85rem; background: var(--bg);
  border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); font-size: .87rem; outline: none; transition: border-color .2s;
}
input:focus, select:focus, textarea:focus { border-color: var(--accent); }
textarea { resize: vertical; min-height: 80px; }

.btn { display: inline-flex; align-items: center; gap: .4rem; padding: .55rem 1.1rem; border-radius: 8px; font-size: .87rem; font-weight: 600; cursor: pointer; border: none; transition: opacity .2s; }
.btn:hover { opacity: .85; text-decoration: none; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-danger  { background: var(--red);    color: #fff; }
.btn-outline { background: transparent;   border: 1px solid var(--border); color: var(--text); }
.btn-sm      { padding: .32rem .75rem; font-size: .78rem; }

.alert { padding: .7rem 1rem; border-radius: 8px; margin-bottom: 1rem; font-size: .87rem; }
.alert-success { background: rgba(34,197,94,.1);  border: 1px solid rgba(34,197,94,.3); color: var(--green); }
.alert-error   { background: rgba(239,68,68,.1);  border: 1px solid rgba(239,68,68,.3); color: var(--red); }

.login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.login-card { width: 100%; max-width: 370px; }
.sec-title { font-size: .95rem; font-weight: 700; margin-bottom: 1rem; padding-bottom: .5rem; border-bottom: 1px solid var(--border); }
.actions { display: flex; gap: .75rem; flex-wrap: wrap; margin-bottom: 1.5rem; }

.online-dot { width: 8px; height: 8px; background: var(--green); border-radius: 50%; display: inline-block; margin-right: 6px; animation: p 2s infinite; }
@keyframes p { 0%,100%{opacity:1} 50%{opacity:.3} }

::-webkit-scrollbar { width: 5px; } ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
"""

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def _flash(msg):
    session.setdefault('_flash', []).append(msg)

def _pop_flash():
    msgs = session.pop('_flash', [])
    return ''.join(f'<div class="alert alert-success">{m}</div>' for m in msgs)

def _admin_nav(active=''):
    tabs = [
        ('d', '/admin',           'Dashboard'),
        ('u', '/admin/users',     'Users'),
        ('r', '/admin/reminders', 'Reminders'),
        ('p', '/admin/placement', 'Placement'),
        ('s', '/admin/settings',  'Settings'),
    ]
    links = ''
    for key, href, label in tabs:
        cls = 'active' if active == key else ''
        links += f'<a href="{href}" class="{cls}">{label}</a>'
    links += '<a href="/admin/logout">Logout</a>'
    return f"""
{ADMIN_CSS}
<nav>
  <div class="logo">Ghost Squad <span class="badge">Admin</span></div>
  <div class="nav-links">{links}</div>
</nav>"""

# ---------------------------------------------------------------------------
# PUBLIC SITE
# ---------------------------------------------------------------------------

@app.route('/')
def public_home():
    users   = _db.get_all_users()
    total   = len(users)
    active  = sum(1 for u in users.values() if u.get('last_status'))
    solved  = sum(u.get('total_solved', 0) for u in users.values())
    pct     = int(active / total * 100) if total else 0

    sorted_users = sorted(users.values(), key=lambda x: x.get('total_solved', 0), reverse=True)

    rows = ''
    for i, u in enumerate(sorted_users, 1):
        status = '<span class="pill pill-green">Done</span>' if u.get('last_status') else '<span class="pill pill-red">Pending</span>'
        e, m, h = u.get('breakdown', [0, 0, 0])
        rows += f"""<tr>
          <td><strong>#{i}</strong></td>
          <td>{u.get('leetcode_username', '?')}</td>
          <td class="c-green">{u.get('total_solved', 0)}</td>
          <td>{e} / {m} / {h}</td>
          <td>{status}</td>
        </tr>"""

    placement_log = _db.get_placement_log(3)
    tip_cards = ''
    for p in placement_log:
        date    = p.get('posted_at', '')[:10]
        content = p.get('content', '')[:200].replace('<', '&lt;').replace('\n', '<br>')
        tip_cards += f"""
        <div class="tip-card">
          <div class="tip-date">{date}</div>
          <div class="tip-body">{content}...</div>
        </div>"""

    return render_template_string(f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ghost Squad — Leaderboard</title>
{PUBLIC_CSS}
</head><body>

<nav class="pub-nav">
  <div class="logo">Ghost <span>Squad</span></div>
  <div class="nav-right">
    <a href="#leaderboard">Leaderboard</a>
    <a href="#tips">Placement Tips</a>
  </div>
</nav>

<div class="hero">
  <h1>The <span class="hl">Ghost Squad</span> Grind Board</h1>
  <p>Daily LeetCode accountability and placement prep for the whole squad.</p>
</div>

<div class="container">

  <div class="stat-row">
    <div class="stat-card"><div class="val c-blue">{total}</div><div class="lbl">Members</div></div>
    <div class="stat-card"><div class="val c-green">{active}</div><div class="lbl">Done Today</div></div>
    <div class="stat-card"><div class="val c-yellow">{solved}</div><div class="lbl">Total Solved</div></div>
    <div class="stat-card"><div class="val c-purple">{pct}%</div><div class="lbl">Daily Rate</div></div>
  </div>

  <div class="prog-bar-wrap">
    <div class="label-row">
      <span>Today's progress</span>
      <span style="color:var(--muted)">{active} of {total} completed</span>
    </div>
    <div class="prog-track">
      <div class="prog-fill" style="width:{pct}%"></div>
    </div>
  </div>

  <div id="leaderboard" class="tcard">
    <div class="tcard-head">Leaderboard <span style="color:var(--muted);font-weight:400;font-size:.85rem">— sorted by total problems solved</span></div>
    <div class="table-wrap">
      <table>
        <tr><th>Rank</th><th>Username</th><th>Solved</th><th>Easy / Med / Hard</th><th>Today</th></tr>
        {rows or '<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--muted)">No members yet. Join via Discord!</td></tr>'}
      </table>
    </div>
  </div>

  <div id="tips">
    <div class="sec-title">Latest Placement Tips</div>
    {tip_cards or '<p style="color:var(--muted);font-size:.9rem">No tips posted yet. Check back soon.</p>'}
  </div>

</div>

<footer>
  <span class="live-dot"></span> Ghost Squad Bot is live &nbsp;|&nbsp; Data refreshed every 24 hours
</footer>

</body></html>""")


@app.route('/leaderboard')
def public_leaderboard():
    return redirect('/#leaderboard')

# ---------------------------------------------------------------------------
# ADMIN AUTH
# ---------------------------------------------------------------------------

@app.route('/admin')
def admin_root():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        if request.form.get('password') == _password:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Incorrect password.'
    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Admin Login</title>{ADMIN_CSS}</head><body>
<div class="login-wrap">
  <div class="login-card card">
    <div style="text-align:center;font-size:1.3rem;font-weight:800;margin-bottom:.25rem">Ghost Squad Admin</div>
    <div style="text-align:center;color:var(--muted);font-size:.85rem;margin-bottom:1.75rem">Enter your admin password to continue</div>
    {f'<div class="alert alert-error">{error}</div>' if error else ''}
    <form method="POST">
      <div class="form-group">
        <label>Password</label>
        <input type="password" name="password" placeholder="Password" autofocus required>
      </div>
      <button class="btn btn-primary" style="width:100%" type="submit">Sign In</button>
    </form>
    <div style="text-align:center;margin-top:1.25rem">
      <a href="/" style="color:var(--muted);font-size:.82rem">Back to public site</a>
    </div>
  </div>
</div></body></html>""")


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# ---------------------------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------------------------

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    users    = _db.get_all_users()
    total    = len(users)
    active   = sum(1 for u in users.values() if u.get('last_status'))
    solved   = sum(u.get('total_solved', 0) for u in users.values())
    rems     = _db.get_all_reminders()
    settings = _db.get_all_settings()
    pl_log   = _db.get_placement_log(5)

    top5 = sorted(users.values(), key=lambda x: x.get('total_solved', 0), reverse=True)[:5]
    rows = ''
    for u in top5:
        s = '<span class="pill pill-green">Done</span>' if u.get('last_status') else '<span class="pill pill-red">Pending</span>'
        e, m, h = u.get('breakdown', [0, 0, 0])
        rows += f"<tr><td><strong>{u.get('leetcode_username','?')}</strong></td><td>{u.get('discord_name','?')}</td><td>{u.get('total_solved',0)}</td><td>{e}/{m}/{h}</td><td>{s}</td></tr>"

    pl_rows = ''
    for p in pl_log:
        ts  = p.get('posted_at', '')[:16].replace('T', ' ')
        pre = p.get('content', '')[:80].replace('<', '&lt;')
        pl_rows += f'<tr><td style="white-space:nowrap">{ts}</td><td>{pre}...</td></tr>'

    flash_html = _pop_flash()

    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Dashboard — Ghost Squad Admin</title></head><body>
{_admin_nav('d')}
<div class="container">
  <div class="page-title"><span class="online-dot"></span>Dashboard</div>
  {flash_html}

  <div class="grid grid-4" style="margin-bottom:1.5rem">
    <div class="card"><div class="card-title">Members</div><div class="card-value stat-blue">{total}</div></div>
    <div class="card"><div class="card-title">Active Today</div><div class="card-value stat-green">{active}</div></div>
    <div class="card"><div class="card-title">Total Solved</div><div class="card-value stat-yellow">{solved}</div></div>
    <div class="card"><div class="card-title">Active Reminders</div><div class="card-value stat-blue">{len(rems)}</div></div>
  </div>

  <div class="actions">
    <form method="POST" action="/api/admin/force_check"><button class="btn btn-primary" type="submit">Run LeetCode Check Now</button></form>
    <form method="POST" action="/api/admin/force_placement"><button class="btn btn-outline" type="submit">Post Placement Tip Now</button></form>
    <a href="/admin/users" class="btn btn-outline">Manage Users</a>
    <a href="/" class="btn btn-outline" target="_blank">View Public Site</a>
  </div>

  <div class="grid grid-2">
    <div class="card">
      <div class="sec-title">Top 5 Members</div>
      <div class="table-wrap"><table>
        <tr><th>LeetCode</th><th>Discord</th><th>Solved</th><th>E/M/H</th><th>Today</th></tr>
        {rows or '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:1.5rem">No users yet</td></tr>'}
      </table></div>
    </div>
    <div class="card">
      <div class="sec-title">Schedule</div>
      <div style="display:flex;flex-direction:column;gap:.9rem">
        <div style="display:flex;justify-content:space-between">
          <span>Daily Check</span>
          <span class="pill pill-green">{settings.get('check_time','21:30')} IST</span>
        </div>
        <div style="display:flex;justify-content:space-between">
          <span>Placement Post</span>
          <span class="pill pill-blue">{settings.get('placement_time','10:00')} IST</span>
        </div>
        <div style="display:flex;justify-content:space-between">
          <span>Daily Check</span>
          <span class="pill {'pill-green' if settings.get('daily_check_enabled',True) else 'pill-red'}">{'On' if settings.get('daily_check_enabled',True) else 'Off'}</span>
        </div>
        <div style="display:flex;justify-content:space-between">
          <span>Placement Auto-post</span>
          <span class="pill {'pill-green' if settings.get('placement_enabled',True) else 'pill-red'}">{'On' if settings.get('placement_enabled',True) else 'Off'}</span>
        </div>
      </div>
      <div style="margin-top:1rem"><a href="/admin/settings" class="btn btn-outline btn-sm">Edit Settings</a></div>
    </div>
  </div>

  <div class="card" style="margin-top:1.25rem">
    <div class="sec-title">Recent Placement Posts</div>
    <div class="table-wrap"><table>
      <tr><th>Time (UTC)</th><th>Preview</th></tr>
      {pl_rows or '<tr><td colspan="2" style="color:var(--muted);text-align:center;padding:1.5rem">No posts yet</td></tr>'}
    </table></div>
    <div style="margin-top:1rem"><a href="/admin/placement" class="btn btn-outline btn-sm">View All</a></div>
  </div>
</div></body></html>""")

# ---------------------------------------------------------------------------
# ADMIN — USERS
# ---------------------------------------------------------------------------

@app.route('/admin/users')
@admin_required
def admin_users():
    users = _db.get_all_users()
    rows = ''
    for uid, u in users.items():
        s = '<span class="pill pill-green">Done</span>' if u.get('last_status') else '<span class="pill pill-red">Pending</span>'
        e, m, h = u.get('breakdown', [0, 0, 0])
        reg = u.get('registered_date', '')[:10]
        rows += f"""<tr>
          <td><code style="font-size:.78rem">{uid[:12]}...</code></td>
          <td><strong>{u.get('leetcode_username','?')}</strong></td>
          <td>{u.get('discord_name','?')}</td>
          <td>{u.get('total_solved',0)}</td>
          <td>{e}/{m}/{h}</td>
          <td>{s}</td>
          <td>{reg}</td>
          <td>
            <form method="POST" action="/api/admin/remove_user" onsubmit="return confirm('Remove this user?')">
              <input type="hidden" name="uid" value="{uid}">
              <button class="btn btn-danger btn-sm" type="submit">Remove</button>
            </form>
          </td>
        </tr>"""
    flash_html = _pop_flash()
    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Users — Ghost Squad Admin</title></head><body>
{_admin_nav('u')}
<div class="container">
  <div class="page-title">Registered Users ({len(users)})</div>
  {flash_html}
  <div class="card">
    <div class="table-wrap"><table>
      <tr><th>Discord ID</th><th>LeetCode</th><th>Discord</th><th>Solved</th><th>E/M/H</th><th>Today</th><th>Joined</th><th></th></tr>
      {rows or '<tr><td colspan="8" style="color:var(--muted);text-align:center;padding:2rem">No users registered yet</td></tr>'}
    </table></div>
  </div>
</div></body></html>""")

# ---------------------------------------------------------------------------
# ADMIN — REMINDERS
# ---------------------------------------------------------------------------

@app.route('/admin/reminders')
@admin_required
def admin_reminders():
    reminders = _db.get_all_reminders()
    now = datetime.now(timezone.utc)
    rows = ''
    for r in sorted(reminders, key=lambda x: x.get('fire_at', '')):
        fire_at = datetime.fromisoformat(r['fire_at'])
        if fire_at.tzinfo is None:
            fire_at = fire_at.replace(tzinfo=timezone.utc)
        remaining = fire_at - now
        mins = int(remaining.total_seconds() // 60)
        time_left = f"in {mins}m" if mins > 0 else "overdue"
        fire_str  = fire_at.strftime('%Y-%m-%d %H:%M UTC')
        rows += f"""<tr>
          <td><code>{r['id']}</code></td>
          <td><code style="font-size:.8rem">{r['user_id']}</code></td>
          <td>{r['message'][:80]}</td>
          <td style="white-space:nowrap">{fire_str}</td>
          <td><span class="pill {'pill-yellow' if mins>0 else 'pill-red'}">{time_left}</span></td>
          <td>
            <form method="POST" action="/api/admin/cancel_reminder">
              <input type="hidden" name="rid" value="{r['id']}">
              <button class="btn btn-danger btn-sm" type="submit">Cancel</button>
            </form>
          </td>
        </tr>"""
    flash_html = _pop_flash()
    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Reminders — Ghost Squad Admin</title></head><body>
{_admin_nav('r')}
<div class="container">
  <div class="page-title">Reminders</div>
  {flash_html}

  <div class="card" style="margin-bottom:1.5rem">
    <div class="sec-title">Set a New Reminder</div>
    <form method="POST" action="/api/admin/add_reminder">
      <div class="grid grid-2">
        <div class="form-group">
          <label>Discord User ID</label>
          <input type="text" name="user_id" placeholder="e.g. 123456789012345678" required>
        </div>
        <div class="form-group">
          <label>Time from now (e.g. 30m, 2h, 1d)</label>
          <input type="text" name="time_str" placeholder="30m" required>
        </div>
      </div>
      <div class="form-group">
        <label>Message</label>
        <input type="text" name="message" placeholder="Complete the daily challenge!" required>
      </div>
      <button class="btn btn-primary" type="submit">Set Reminder</button>
    </form>
  </div>

  <div class="card">
    <div class="sec-title">Active Reminders ({len(reminders)})</div>
    <div class="table-wrap"><table>
      <tr><th>ID</th><th>User ID</th><th>Message</th><th>Fire At</th><th>Status</th><th></th></tr>
      {rows or '<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:2rem">No active reminders</td></tr>'}
    </table></div>
  </div>
</div></body></html>""")

# ---------------------------------------------------------------------------
# ADMIN — PLACEMENT
# ---------------------------------------------------------------------------

@app.route('/admin/placement')
@admin_required
def admin_placement():
    log      = _db.get_placement_log(50)
    settings = _db.get_all_settings()
    enabled  = settings.get('placement_enabled', True)

    rows = ''
    for p in log:
        ts      = p.get('posted_at', '')[:16].replace('T', ' ')
        content = p.get('content', '').replace('<', '&lt;').replace('\n', '<br>')
        rows += f"""<tr>
          <td style="white-space:nowrap">{ts}</td>
          <td><details><summary style="cursor:pointer;color:var(--accent)">View</summary>
          <div style="margin-top:.5rem;padding:.7rem;background:var(--bg);border-radius:6px;font-size:.82rem">{content}</div>
          </details></td>
        </tr>"""

    flash_html = _pop_flash()
    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Placement Feed — Ghost Squad Admin</title></head><body>
{_admin_nav('p')}
<div class="container">
  <div class="page-title">Placement Feed</div>
  {flash_html}

  <div class="grid grid-2" style="margin-bottom:1.5rem">
    <div class="card">
      <div class="sec-title">Post Actions</div>
      <form method="POST" action="/api/admin/force_placement" style="margin-bottom:1rem">
        <button class="btn btn-primary" type="submit">Post AI Tip Now</button>
      </form>
      <div class="sec-title" style="margin-top:1.25rem">Post Custom Tip</div>
      <form method="POST" action="/api/admin/custom_placement">
        <div class="form-group">
          <textarea name="content" placeholder="Write a custom placement or internship tip..."></textarea>
        </div>
        <button class="btn btn-outline" type="submit">Post to Discord</button>
      </form>
    </div>
    <div class="card">
      <div class="sec-title">Auto-post Status</div>
      <p>Status: <span class="pill {'pill-green' if enabled else 'pill-red'}">{'Enabled' if enabled else 'Disabled'}</span></p>
      <p style="margin-top:.5rem;color:var(--muted);font-size:.83rem">Scheduled: {settings.get('placement_time','10:00')} IST daily</p>
      <form method="POST" action="/api/admin/toggle_placement" style="margin-top:1rem">
        <button class="btn {'btn-danger' if enabled else 'btn-primary'} btn-sm" type="submit">
          {'Disable' if enabled else 'Enable'} Auto-post
        </button>
      </form>
    </div>
  </div>

  <div class="card">
    <div class="sec-title">Post History ({len(log)})</div>
    <div class="table-wrap"><table>
      <tr><th>Time (UTC)</th><th>Content</th></tr>
      {rows or '<tr><td colspan="2" style="color:var(--muted);text-align:center;padding:2rem">No posts yet</td></tr>'}
    </table></div>
  </div>
</div></body></html>""")

# ---------------------------------------------------------------------------
# ADMIN — SETTINGS
# ---------------------------------------------------------------------------

@app.route('/admin/settings')
@admin_required
def admin_settings():
    settings   = _db.get_all_settings()
    flash_html = _pop_flash()
    def ck(key): return 'checked' if settings.get(key, True) else ''
    return render_template_string(f"""<!DOCTYPE html><html><head>
<title>Settings — Ghost Squad Admin</title></head><body>
{_admin_nav('s')}
<div class="container">
  <div class="page-title">Settings</div>
  {flash_html}
  <form method="POST" action="/api/admin/save_settings">
    <div class="grid grid-2">
      <div class="card">
        <div class="sec-title">Schedule (IST, 24-hour)</div>
        <div class="form-group">
          <label>Daily LeetCode Check Time</label>
          <input type="time" name="check_time" value="{settings.get('check_time','21:30')}">
        </div>
        <div class="form-group">
          <label>Placement Post Time</label>
          <input type="time" name="placement_time" value="{settings.get('placement_time','10:00')}">
        </div>
      </div>
      <div class="card">
        <div class="sec-title">Feature Toggles</div>
        <div class="form-group" style="display:flex;align-items:center;gap:.6rem">
          <input type="checkbox" name="daily_check_enabled" id="dce" style="width:auto" {ck('daily_check_enabled')}>
          <label for="dce" style="margin:0">Daily LeetCode Check</label>
        </div>
        <div class="form-group" style="display:flex;align-items:center;gap:.6rem">
          <input type="checkbox" name="placement_enabled" id="pe" style="width:auto" {ck('placement_enabled')}>
          <label for="pe" style="margin:0">Placement Auto-posting</label>
        </div>
        <div class="form-group" style="display:flex;align-items:center;gap:.6rem">
          <input type="checkbox" name="welcome_enabled" id="we" style="width:auto" {ck('welcome_enabled')}>
          <label for="we" style="margin:0">Welcome Messages</label>
        </div>
      </div>
    </div>
    <div style="margin-top:1rem"><button class="btn btn-primary" type="submit">Save Settings</button></div>
  </form>

  <div class="card" style="margin-top:1.5rem">
    <div class="sec-title">Change Admin Password</div>
    <form method="POST" action="/api/admin/change_password">
      <div class="grid grid-2">
        <div class="form-group">
          <label>Current Password</label>
          <input type="password" name="current" required>
        </div>
        <div class="form-group">
          <label>New Password (minimum 6 characters)</label>
          <input type="password" name="new_password" required>
        </div>
      </div>
      <button class="btn btn-outline" type="submit">Change Password</button>
    </form>
  </div>
</div></body></html>""")

# ---------------------------------------------------------------------------
# ADMIN API ENDPOINTS
# ---------------------------------------------------------------------------

@app.route('/api/admin/force_check', methods=['POST'])
@admin_required
def api_force_check():
    try:
        asyncio.run_coroutine_threadsafe(_trigger_check(), _bot.loop)
    except Exception as e:
        print(f"Force check error: {e}")
    _flash("LeetCode check triggered.")
    return redirect(url_for('admin_dashboard'))


@app.route('/api/admin/force_placement', methods=['POST'])
@admin_required
def api_force_placement():
    try:
        asyncio.run_coroutine_threadsafe(_post_placement_now(), _bot.loop)
    except Exception as e:
        print(f"Force placement error: {e}")
    _flash("Placement tip posted.")
    return redirect(request.referrer or url_for('admin_dashboard'))


@app.route('/api/admin/custom_placement', methods=['POST'])
@admin_required
def api_custom_placement():
    content = request.form.get('content', '').strip()
    if content:
        try:
            asyncio.run_coroutine_threadsafe(_post_custom_placement(content), _bot.loop)
            _db.log_placement_post(content)
            _flash("Custom tip posted to Discord.")
        except Exception as e:
            print(f"Custom placement error: {e}")
    return redirect(url_for('admin_placement'))


@app.route('/api/admin/toggle_placement', methods=['POST'])
@admin_required
def api_toggle_placement():
    current = _db.get_setting('placement_enabled', True)
    _db.set_setting('placement_enabled', not current)
    _flash(f"Placement auto-post {'disabled' if current else 'enabled'}.")
    return redirect(url_for('admin_placement'))


@app.route('/api/admin/remove_user', methods=['POST'])
@admin_required
def api_remove_user():
    uid = request.form.get('uid', '')
    if uid:
        _db.delete_user(uid)
        _flash("User removed.")
    return redirect(url_for('admin_users'))


@app.route('/api/admin/cancel_reminder', methods=['POST'])
@admin_required
def api_cancel_reminder():
    rid = request.form.get('rid', '')
    if rid:
        from database import REMINDERS_FILE, _save
        reminders = [r for r in _db._reminders() if r['id'] != rid]
        _save(REMINDERS_FILE, reminders)
        _flash(f"Reminder {rid} cancelled.")
    return redirect(url_for('admin_reminders'))


@app.route('/api/admin/add_reminder', methods=['POST'])
@admin_required
def api_add_reminder():
    from cogs.reminders import parse_time
    user_id  = request.form.get('user_id', '').strip()
    time_str = request.form.get('time_str', '').strip()
    message  = request.form.get('message', '').strip()
    if user_id and time_str and message:
        delta = parse_time(time_str)
        if delta:
            fire_at = datetime.now(timezone.utc) + delta
            rid = _db.add_reminder(user_id, message, fire_at)
            _flash(f"Reminder {rid} set for user {user_id}.")
        else:
            _flash("Invalid time format. Use 30m, 2h, or 1d.")
    return redirect(url_for('admin_reminders'))


@app.route('/api/admin/save_settings', methods=['POST'])
@admin_required
def api_save_settings():
    _db.set_setting('check_time',          request.form.get('check_time', '21:30'))
    _db.set_setting('placement_time',      request.form.get('placement_time', '10:00'))
    _db.set_setting('daily_check_enabled', 'daily_check_enabled' in request.form)
    _db.set_setting('placement_enabled',   'placement_enabled' in request.form)
    _db.set_setting('welcome_enabled',     'welcome_enabled' in request.form)
    _flash("Settings saved.")
    return redirect(url_for('admin_settings'))


@app.route('/api/admin/change_password', methods=['POST'])
@admin_required
def api_change_password():
    global _password
    current = request.form.get('current', '')
    new_pw  = request.form.get('new_password', '')
    if current == _password and len(new_pw) >= 6:
        _password = new_pw
        _db.set_setting('admin_password', new_pw)
        _flash("Password changed.")
    else:
        _flash("Incorrect current password, or new password is too short (minimum 6 characters).")
    return redirect(url_for('admin_settings'))


@app.route('/api/stats')
def api_stats():
    """Public JSON endpoint for live stats."""
    users = _db.get_all_users()
    return jsonify({
        'total_users':  len(users),
        'active_today': sum(1 for u in users.values() if u.get('last_status')),
        'total_solved': sum(u.get('total_solved', 0) for u in users.values()),
    })

# ---------------------------------------------------------------------------
# ASYNC HELPERS (called from web thread onto bot's event loop)
# ---------------------------------------------------------------------------

async def _trigger_check():
    from app import CHANNEL_ID, run_check_logic
    channel = _bot.get_channel(CHANNEL_ID)
    if channel:
        await run_check_logic(channel)


async def _post_placement_now():
    from app import PLACEMENT_CH_ID
    from ai_helper import get_placement_post
    import discord as _d
    channel = _bot.get_channel(PLACEMENT_CH_ID)
    if channel:
        tip = await get_placement_post()
        embed = _d.Embed(title="Placement Tip (Admin Post)", description=tip, color=0xf39c12)
        await channel.send(embed=embed)
        _db.log_placement_post(tip)


async def _post_custom_placement(content: str):
    from app import PLACEMENT_CH_ID
    import discord as _d
    channel = _bot.get_channel(PLACEMENT_CH_ID)
    if channel:
        embed = _d.Embed(title="Placement Tip", description=content, color=0x27ae60)
        embed.set_footer(text="Ghost Squad")
        await channel.send(embed=embed)

# ---------------------------------------------------------------------------
# STARTUP
# ---------------------------------------------------------------------------

def start_server(db, bot, password: str, port: int = 8080):
    global _db, _bot, _password
    _db      = db
    _bot     = bot
    _password = db.get_setting('admin_password', password)

    def run():
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

    threading.Thread(target=run, daemon=True).start()
