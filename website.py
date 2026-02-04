from flask import Flask, render_template
from threading import Thread
import json
import logging

# Suppress Flask server logs to keep console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

def get_db():
    try:
        with open('user_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

@app.route('/')
def dashboard():
    data = get_db()
    users = []
    
    # Process data for the template
    for discord_id, info in data.items():
        # Handle simple string (old format) vs dict (new format)
        if isinstance(info, str):
            users.append({
                'username': info, 
                'solved': 0, 
                'breakdown': [0,0,0], 
                'discord_id': discord_id, 
                'status': False
            })
        else:
            users.append({
                'username': info.get('leetcode_username', 'Unknown'),
                'solved': info.get('total_solved', 0),
                'breakdown': info.get('breakdown', [0,0,0]), # [Easy, Med, Hard]
                'discord_id': discord_id,
                'status': info.get('last_status', False)
            })
    
    # Sort for Leaderboard (Most solved first)
    users.sort(key=lambda x: x['solved'], reverse=True)
    
    return render_template('index.html', users=users)

def run():
    app.run(host='0.0.0.0', port=8080)

def start_website():
    t = Thread(target=run)
    t.start()