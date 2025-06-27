from fastapi import APIRouter
from app import schemas

router = APIRouter()

# Simple in-memory storage for items
items_storage = []


@router.get("/items", response_model=list[schemas.Item])
def read_items():
    return items_storage


@router.post("/items", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate):
    new_item = schemas.Item(
        id=len(items_storage) + 1, title=item.title, description=item.description
    )
    items_storage.append(new_item)
    return new_item
