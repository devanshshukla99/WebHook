from app.main import init_db

workers = 1
worker_class = "sync"
worker_connections = 100


def pre_fork(server, worker):
    init_db()
    server.log.info("Database created")
    return
