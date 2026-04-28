# Pattern: FastAPI CRUD Resource

**Use when**: Adding a CRUD resource to the FastAPI backend (e.g., items, posts, entries).

## Model

```python
# app/models/item.py
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base
import uuid

class Item(Base):
    __tablename__ = "items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

## Schemas

```python
# app/schemas/item.py
from datetime import datetime
from pydantic import BaseModel

class ItemCreate(BaseModel):
    title: str
    description: str | None = None

class ItemResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

## Router

```python
# app/api/items.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemResponse
from app.auth.dependencies import get_current_user
import uuid

router = APIRouter()

@router.get("/", response_model=list[ItemResponse])
async def list_items(db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user)):
    result = await db.execute(select(Item).where(Item.user_id == user_id))
    return result.scalars().all()

@router.post("/", response_model=ItemResponse, status_code=201)
async def create_item(body: ItemCreate, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user)):
    item = Item(id=str(uuid.uuid4()), user_id=user_id, **body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: str, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user)):
    result = await db.execute(select(Item).where(Item.id == item_id, Item.user_id == user_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Not found")
    await db.delete(item)
    await db.commit()
```
