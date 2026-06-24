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

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()
