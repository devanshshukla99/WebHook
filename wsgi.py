from app.main import app, init_db

if __name__ == "__main__":
    init_db()
    app.run()

