import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_DB_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'fusiondex_user')}"
    f":{os.getenv('POSTGRES_PASSWORD', 'changeme')}"
    f"@{os.getenv('POSTGRES_HOST', 'db')}"
    f":{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{os.getenv('POSTGRES_DB', 'fusiondex_db')}"
)

engine = create_engine(
    _DB_URL,
    pool_size=5,        # persistent connections
    max_overflow=10,    # burst up to 15 total connections
    pool_timeout=30,    # max wait time to obtain a connection
    pool_pre_ping=True, # validate connection before use (avoids errors after idle)
)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
