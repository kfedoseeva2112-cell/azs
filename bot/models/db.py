from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .db_models import Base

# Используем абсолютный путь для стабильности в фоновых процессах
DATABASE_URL = "sqlite:////home/ubuntu/azs/fuel-map-bot/fuelmap.db"

# Настройка пула соединений согласно ТЗ
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)

# Используем scoped_session для потокобезопасности
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_db():
    Base.metadata.create_all(bind=engine)
