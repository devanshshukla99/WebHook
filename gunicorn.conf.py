from app.main import init_db

def pre_fork(server, worker):
    init_db()
    server.log.info("Database created")
    return
