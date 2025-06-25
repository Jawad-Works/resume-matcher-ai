from sqlalchemy.orm import Session
from app.database.models import Item
from app import schemas

def get_items(db: Session):
    return db.query(Item).all()

def create_item(db: Session, item: schemas.ItemCreate):
    db_item = Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
