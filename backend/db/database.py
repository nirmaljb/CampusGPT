# database.py
from sqlmodel import create_engine, Session,SQLModel

DATABASE_URL = "postgresql://postgres:mypassword@localhost:5432/mydb"

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session