from pydantic import BaseModel


class ItemBase(BaseModel):
    title: str
    description: str


class ItemCreate(ItemBase):
    pass


class Item(ItemBase):
    id: int

    class Config:
        from_attributes = True  # Pydantic v2 replacement for orm_mode
