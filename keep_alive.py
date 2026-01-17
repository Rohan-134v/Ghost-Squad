from flask import Flask
from threading import Thread
import requests
import time

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def ping_self():
    while True:
        try:
            requests.get('http://localhost:8080')
        except:
            pass
        time.sleep(300)  # Ping every 5 minutes

def keep_alive():
    t = Thread(target=run)
    t.start()
    ping_thread = Thread(target=ping_self)
    ping_thread.daemon = True
    ping_thread.start()