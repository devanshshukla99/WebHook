import os
from app.main import app, init_db

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if not os.path.isfile("app/database.db"):
        init_db()
    app.run(host="0.0.0.0", port=port)
