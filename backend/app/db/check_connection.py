from sqlalchemy import text
from backend.app.db.session import engine

if __name__ == "__main__":
    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar()
        print(f"✅ Connected to MySQL {version}")