import os
import random
import string
from flask import Flask, g, request, render_template
import sqlite3
from base64 import b64encode

DATABASE = "app/database.db"
QUERIES = 2

app = Flask(__name__)


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()
    return


def get_db():
    db = getattr(g, "db", None)
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
    return b64encode(os.urandom(length)).decode("utf-8")


@app.route("/<url>", methods=["GET"])
def blanket(url):
    db = get_db()
    com = "INSERT INTO records(username, remote_addr) VALUES(?,?)"
    db.execute(com, (request.path, request.remote_addr))
    db.commit()
    return ("", 204)


@app.route("/<hook>/<token>", methods=["GET"])
def cover(hook, token):
    cur = get_db().cursor()
    com = "SELECT * FROM links where link=?"
    auth = cur.execute(com, ("/" + hook,)).fetchone()
    print(auth)
    if auth:
        if auth[2] == token:
            print("YES")
            com = "SELECT * FROM records where username=?"
            data = cur.execute(com, ("/" + hook,)).fetchall()
            data_to_send = {x[0]: {"url": x[1], "remote_addr": x[2]} for x in data}
            return data_to_send
    print("AUTH FAILED!")
    return ("", 404)


def listener():
    db = get_db()
    com = "INSERT INTO records(username, remote_addr) VALUES(?,?)"
    db.execute(com, (request.path, request.remote_addr))
    db.commit()
    return ("", 200)  # "Hey there! You found me"


def seeker():
    url = request.path
    print(f"URL:{url}")
    _, hook, token = url.split("/")
    cur = get_db().cursor()
    com = "SELECT * FROM links where link=?"
    auth = cur.execute(com, ("/" + hook,)).fetchone()
    if auth[2] == token:
        com = "SELECT * FROM records where username=?"
        data = cur.execute(com, ("/" + hook,)).fetchall()
        data_to_send = {x[0]: {"url": x[1], "remote_addr": x[2]} for x in data}
        return data_to_send
    print("AUTH FAILED!")
    return "{}"


@app.route("/site-map")
def site_map():
    rules = []
    urls = []
    print(app.url_map)
    for rule in app.url_map.iter_rules():
        # Filter out rules we can't navigate to in a browser
        # and rules that require parameters
        if "GET" in rule.methods:
            # url = url_for(rule.endpoint, **(rule.defaults or {}))
            rules.append(str(rule))
            urls.append(rule.endpoint)
    return {"rules": rules, "urls": urls}


@app.route("/")
def webhook():
    global app

    webhk = "/" + get_random_string()
    token = get_token()
    token = token.replace("/", "")
    token_link = "/".join([webhk, token])

    # app.route(webhk, methods=["GET"])(listener)
    # app.route(token_link, methods=["GET"])(seeker)

    db = get_db()
    com = f"INSERT INTO links(link, token) VALUES(?,?)"
    db.execute(com, (webhk, token))
    db.commit()

    com = f"""DELETE FROM links WHERE id NOT IN (
                SELECT id FROM links ORDER BY id DESC LIMIT {QUERIES})"""
    yeeted_links = db.cursor().execute(com).fetchall()

    com = "SELECT COUNT(id) FROM links"
    db_rows = db.cursor().execute(com).fetchone()[0]
    print(db_rows)
    db.commit()
    return render_template(
        "hook.html", hook=webhk, token=token, db_rows=db_rows, QUERIES=QUERIES
    )
