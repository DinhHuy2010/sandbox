from uuid import UUID, uuid4
import fastapi
from pydantic import BaseModel
import sqlmodel

app = fastapi.FastAPI()

class BookmarkItem(sqlmodel.SQLModel, table=True):
    id: UUID = sqlmodel.Field(  # type: ignore
        ..., default_factory=uuid4, primary_key=True
    )
    url: str
    title: str
    description: str | None = None
    is_favorite: bool = False
    bookmark_list: UUID = sqlmodel.Field(  # type: ignore
        ..., foreign_key="bookmarklist.id"
    )

class BookmarkList(sqlmodel.SQLModel, table=True):
    id: UUID = sqlmodel.Field(  # type: ignore
        ..., default_factory=uuid4, primary_key=True
    )
    name: str
    description: str | None = None

class BookmarkItemCreate(BaseModel):
    url: str
    title: str
    description: str | None = None
    is_favorite: bool = False
    bookmark_list: str

class BookmarkListCreate(BaseModel):
    name: str
    description: str | None = None

engine = sqlmodel.create_engine("sqlite:///database.db")
sqlmodel.SQLModel.metadata.create_all(engine)
session = sqlmodel.Session(engine)

@app.post("/bookmarks/", response_model=BookmarkItem)
def create_bookmark(item: BookmarkItemCreate):
    db_item = BookmarkItem(**item.model_dump())
    with session:
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
    # Here you would add code to save db_item to the database
    return db_item

@app.post("/bookmark-lists/", response_model=BookmarkList)
def create_bookmark_list(bookmark_list: BookmarkListCreate):
    db_list = BookmarkList(**bookmark_list.model_dump())
    with session:
        session.add(db_list)
        session.commit()
        session.refresh(db_list)
    # Here you would add code to save db_list to the database
    return db_list

@app.get("/bookmarks/{bookmark_id}", response_model=BookmarkItem)
def get_bookmark(bookmark_id: str):
    with session:
        db_item = session.get(BookmarkItem, bookmark_id)
    if not db_item:
        raise fastapi.HTTPException(status_code=404, detail="Bookmark not found")
    return db_item

@app.get("/bookmark-lists/{list_id}", response_model=BookmarkList)
def get_bookmark_list(list_id: str):
    with session:
        db_list = session.get(BookmarkList, list_id)
    if not db_list:
        raise fastapi.HTTPException(status_code=404, detail="Bookmark list not found")
    return db_list

@app.get("/bookmarks/", response_model=list[BookmarkItem])
def list_bookmarks():
    with session:
        db_items = session.exec(sqlmodel.select(BookmarkItem)).all()
    return db_items

@app.get("/bookmark-lists/", response_model=list[BookmarkList])
def list_bookmark_lists():
    with session:
        db_lists = session.exec(sqlmodel.select(BookmarkList)).all()
    return db_lists

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
