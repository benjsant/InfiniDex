import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_REQUIRED = ("POSTGRES_PASSWORD",)
_missing = [v for v in _REQUIRED if not os.getenv(v)]
if _missing:
    raise RuntimeError(
        f"Missing required environment variable(s): {', '.join(_missing)}. "
        "Set them in your .env file or Docker environment."
    )

# Driver explicite : depuis SQLAlchemy 2.1, `postgresql://` résout vers psycopg
# (v3), alors que seul psycopg2 est installé.
_DB_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'infinidex_user')}"
    f":{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST', 'db')}"
    f":{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{os.getenv('POSTGRES_DB', 'infinidex_db')}"
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
