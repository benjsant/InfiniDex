import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_DB_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'fusiondex_user')}"
    f":{os.getenv('POSTGRES_PASSWORD', 'fusiondex_password')}"
    f"@{os.getenv('POSTGRES_HOST', 'db')}"
    f":{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{os.getenv('POSTGRES_DB', 'fusiondex_db')}"
)

engine = create_engine(
    _DB_URL,
    pool_size=5,        # connexions persistantes
    max_overflow=10,    # burst jusqu'à 15 connexions totales
    pool_timeout=30,    # attente max pour obtenir une connexion
    pool_pre_ping=True, # valide la connexion avant usage (évite les erreurs après idle)
)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
