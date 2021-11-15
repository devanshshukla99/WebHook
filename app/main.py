import os
import random
import string
from flask import Flask, g, request, render_template
import sqlite3
from base64 import b64encode

DATABASE = "app/database.db"

app = Flask(__name__)

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()
    return

def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "db", None)
    if db is not None:
        db.close()

def get_random_string(length=20):
    return "".join([random.choice(string.ascii_lowercase) for x in range(0, length)])

def get_token(length=16):
    return b64encode(os.urandom(length)).decode('utf-8')

def listener():
    db = get_db()
    com = "INSERT INTO records(username, remote_addr) VALUES(?,?)"
    db.execute(com, (request.path, request.remote_addr))
    db.commit()
    return "Hey there! You found me"

def seeker():
    url = request.path
    print(f"URL:{url}")
    _, username, token = url.split("/")
    cur = get_db().cursor()
    com = "SELECT * FROM links where link=?"
    auth = cur.execute(com, ("/" + username, )).fetchone()
    if auth[2] == token:
        com = "SELECT * FROM records where username=?"
        data = cur.execute(com, ("/" + username,)).fetchall()
        data_to_send = {x[0]: {"url": x[1], "remote_addr": x[2] } for x in data}
        return data_to_send
    print("AUTH FAILED!")   
    return "{}"

@app.route("/")
def webhook():
    global app
    webhk = "/" + get_random_string()
    token = get_token()
    token = token.replace("/", "")
    app.route(webhk)(listener)
    app.route("/".join([webhk, token]))(seeker)
    db = get_db()
    com = f"INSERT INTO links(link, token) VALUES(?,?)"
    db.execute(com, (webhk, token))
    db.commit()
    return render_template("hook.html", hook=webhk, token=token)

