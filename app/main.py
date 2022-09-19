import os
import json
import string
import random
import sqlite3
import requests
from hashlib import sha512
from base64 import b64encode
from rich.console import Console
from datetime import datetime, timezone
from flask import Flask, g, request, render_template, redirect, send_file


DATABASE = "app/database.db"
QUERIES = 100
CLEAR_TOKEN = "5e325d89a5fceb1ba257f50d7e7c1a807ae8b19756e252c326c44e84e357749d3e780b7db1fb32ec029e7850d3b0bba032a33611d2a54a1db8097c81f2b23814"
ADMIN_TOKEN = "9ad0d01d1766bb60025ba3403e851d1493a1ce2f14bdcf14d198f4a49e083f4547a6e5f9908444aad02d8d2383fbc74af021c7ee797ea13254c6603de76291b8"

app = Flask(__name__, static_folder="static")
console = Console()


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
    print("Fetching IP details")
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
            headers = json.dumps(dict(request.headers))
            remote_addr = request.headers.get("x-forwarded-for")  # request.remote_addr
            req_date = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S (%Z)")
            location = None  # json.dumps({'ip': remote_addr, })  # geo_locate_ip(remote_addr)
            user_agent = request.user_agent
            plat = user_agent.platform
            browser = user_agent.browser
            browser_version = user_agent.version
            com = "INSERT INTO records(hook, req_date, remote_addr, platform, browser, browser_version, user_agent, headers) VALUES(?,?,?,?,?,?,?,?)"
            cur.execute(
                com,
                (
                    request.path,
                    req_date,
                    remote_addr,
                    plat,
                    browser,
                    browser_version,
                    user_agent.string,
                    headers,
                ),
            )
            db.commit()
            # best_match = request.accept_mimetypes.best_match(["text/html", "image/*"])
            # if best_match == "text/html":
            # return render_template("hook.html")
            return send_file("static/1x1.png", mimetype="image/png")
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
            if data:
                if content_type == "application/json":
                    return {x: data[x] for x in range(0, len(data))}
                headers = [json.loads(x.pop("headers")) for x in data]
                return render_template("seeker.html", data=data, headers=headers)
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
def main():
    global app
    content_type = request.headers.get("Content-Type")
    db = get_db()
    if request.method == "POST":
        console.log("request method: POST")
        if request.form.get("show_database"):
            if sha512(request.form.get("admin_token").encode()).hexdigest() == ADMIN_TOKEN:
                console.log(f"Show database: {request.form.get('show_database')}")
                console.log(f"Admin Token: {request.form.get('admin_token')}")
                com = "SELECT * FROM links"
                data = db.cursor().execute(com).fetchall()
                return render_template("database.html", data=data)
            return redirect(request.url)

        elif request.form.get("clear_database"):
            console.log(f"Clear database: {request.form.get('clear_database')}")
            console.log(f"clear Token: {request.form.get('clear_token')}")
            if sha512(request.form.get("clear_token").encode()).hexdigest() == CLEAR_TOKEN:
                print("clearing")
                clear_database(db)
            return redirect(request.url)

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

    if request.method == "GET":
        com = "SELECT COUNT(id) FROM links"
        db_rows = db.cursor().execute(com).fetchone().get("COUNT(id)", 0)
        return render_template("index.html", db_rows=db_rows, QUERIES=QUERIES)
