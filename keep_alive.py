from flask import Flask
from threading import Thread
import logging

app = Flask(__name__)

# Flask loglarini yashirish (terminalni to'ldirib tashlamasligi uchun)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return "Bot ishladi va Render taslim bo'ldi! (Cryptohajm + WatcherBot)"

import os

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
