from sqlmodel import SQLModel, create_engine
from models import User, Conversation  # Import your models

DATABASE_URL = "postgresql://postgres:mypassword@localhost:5432/mydb"

engine = create_engine(DATABASE_URL, echo=True)

def create_tables():
    SQLModel.metadata.create_all(engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables()