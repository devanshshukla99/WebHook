import os
import json
import random
import string
import requests
from flask import Flask, g, request, render_template, redirect
import sqlite3
from base64 import b64encode


DATABASE = "app/database.db"
QUERIES = 100
CLEAR_TOKEN = "batman"

app = Flask(__name__, static_folder="static")


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()
    return


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db():
    db = getattr(g, "db", None)
    if db is None:
        db = g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = dict_factory  # sqlite3.Row
    return db


def clear_database(db):
    cur = db.cursor()
    com = "DELETE FROM links"
    cur.execute(com)
    com = "DELETE FROM records"
    cur.execute(com)
    db.commit()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "db", None)
    if db is not None:
        db.close()


def get_random_string(length=20):
    return "".join([random.choice(string.ascii_lowercase) for x in range(0, length)])


def get_token(length=18):
    return b64encode(os.urandom(length)).decode("utf-8")


def geo_locate_ip(addr):
    if not addr:
        return None
    url = f"https://ipinfo.io/{addr}/json"
    headers = {
        "accept": "json",
        "pragma": "no-cache",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
    }
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.content
    print(f"Exception occurred: {r.content}")
    return None


@app.route("/<url>", methods=["GET"])
def blanket(url):
    db = get_db()
    cur = db.cursor()
    com = "SELECT link FROM links where link=?"
    hooks = cur.execute(com, ("/" + url,)).fetchall()
    for u in hooks:
        if u.get("link")[1:] == url:
            print("YO")
            remote_addr = request.headers.get("x-forwarded-for")  # request.remote_addr
            location = geo_locate_ip(remote_addr)
            user_agent = request.user_agent
            plat = user_agent.platform
            browser = user_agent.browser
            browser_version = user_agent.version
            com = "INSERT INTO records(hook, remote_addr, location, platform, browser, browser_version, user_agent) VALUES(?,?,?,?,?,?,?)"
            cur.execute(
                com,
                (
                    request.path,
                    remote_addr,
                    location,
                    plat,
                    browser,
                    browser_version,
                    user_agent.string,
                ),
            )
            db.commit()
            return render_template("hook.html")
    return ("", 200)


@app.route("/<hook>/<token>", methods=["GET"])
def cover(hook, token):
    content_type = request.headers.get("Content-Type")

    db = get_db()
    cur = db.cursor()

    com = "SELECT * FROM links where link=?"
    auth = cur.execute(com, ("/" + hook,)).fetchone()
    if auth:
        if auth.get("token") == token:
            com = "SELECT * FROM records where hook=?"
            data = cur.execute(com, ("/" + hook,)).fetchall()
            try:
                for req in data:
                    req["location"] = json.loads(req.get("location"))
            except Exception as e:
                print(f"Exception occured: {e}")
            if data:
                if content_type == "application/json":
                    return {x: data[x] for x in range(0, len(data))}
                return render_template("seeker.html", data=data)
    print("AUTH FAILED!")
    return ("", 404)


# @app.route("/site-map")
def site_map():
    rules = []
    urls = []
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods:
            rules.append(str(rule))
            urls.append(rule.endpoint)
    return {"rules": rules, "urls": urls}


def cleanup_past(db):
    cur = db.cursor()
    com = f"""SELECT link FROM links WHERE id NOT IN (
            SELECT id FROM links ORDER BY id DESC LIMIT {QUERIES})"""
    yeeted_links = cur.execute(com).fetchall()
    com = f"""DELETE FROM links WHERE id NOT IN (
                SELECT id FROM links ORDER BY id DESC LIMIT {QUERIES})"""
    cur.execute(com).fetchall()
    com = "DELETE FROM records WHERE hook=?"
    if yeeted_links:
        for link in yeeted_links[0]:
            cur.execute(com, (link,))
    return


@app.route("/", methods=["GET", "POST"])
def webhook():
    global app
    content_type = request.headers.get("Content-Type")
    db = get_db()
    if request.method == "POST":
        if request.form.get("clear_database"):
            if request.form.get("clear_token") == CLEAR_TOKEN:
                print("clearing")
                clear_database(db)
            return redirect(request.url)

    if request.method == "GET":
        hook = "/" + get_random_string()
        token = get_token()
        token = token.replace("/", "")
        data = {"hook": hook, "token": token}

        com = f"INSERT INTO links(link, token) VALUES(?,?)"
        db.execute(com, (hook, token))
        db.commit()
        cleanup_past(db)

        com = "SELECT COUNT(id) FROM links"
        db_rows = db.cursor().execute(com).fetchone().get("COUNT(id)", 0)
        if content_type == "application/json":
            print("yo-json")
            return json.dumps(data)
        return render_template("index.html", data=data, db_rows=db_rows, QUERIES=QUERIES)
