import fastapi
import sqlmodel


class Pastebin(sqlmodel.SQLModel, table=True):
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    title: str
    content: str


engine = sqlmodel.create_engine("sqlite:///pastebin.db")
sqlmodel.SQLModel.metadata.create_all(engine)


def create_pastebin(title: str, content: str) -> Pastebin:
    with sqlmodel.Session(engine) as session:
        pastebin = Pastebin(title=title, content=content)
        session.add(pastebin)
        session.commit()
        session.refresh(pastebin)
        return pastebin


def get_pastebin(pastebin_id: int) -> Pastebin | None:
    with sqlmodel.Session(engine) as session:
        pastebin = session.get(Pastebin, pastebin_id)
        return pastebin


def delete_pastebin(pastebin_id: int) -> bool:
    with sqlmodel.Session(engine) as session:
        pastebin = session.get(Pastebin, pastebin_id)
        if pastebin:
            session.delete(pastebin)
            session.commit()
            return True
        return False


def list_pastebins() -> list[Pastebin]:
    with sqlmodel.Session(engine) as session:
        pastebins = session.exec(sqlmodel.select(Pastebin)).scalars().all()
        return pastebins


def update_pastebin(
    pastebin_id: int, title: str | None = None, content: str | None = None
) -> Pastebin | None:
    with sqlmodel.Session(engine) as session:
        pastebin = session.get(Pastebin, pastebin_id)
        if pastebin:
            if title is not None:
                pastebin.title = title
            if content is not None:
                pastebin.content = content
            session.commit()
            session.refresh(pastebin)
            return pastebin
        return None


def search_pastebins(query: str) -> list[Pastebin]:
    with sqlmodel.Session(engine) as session:
        pastebins = (
            session.exec(sqlmodel.select(Pastebin))
            .where(
                sqlmodel.or_(
                    Pastebin.title.contains(query), Pastebin.content.contains(query)
                )
            )
            .all()
        )
        return pastebins


def count_pastebins() -> int:
    with sqlmodel.Session(engine) as session:
        count = session.exec(sqlmodel.select(sqlmodel.func.count(Pastebin.id))).scalar()
        return count


app = fastapi.FastAPI()


@app.post("/pastebin/")
def create_pastebin_endpoint(title: str, content: str) -> Pastebin:
    return create_pastebin(title, content)


@app.get("/pastebin/{pastebin_id}")
def get_pastebin_endpoint(pastebin_id: int) -> Pastebin | None:
    return get_pastebin(pastebin_id)


@app.delete("/pastebin/{pastebin_id}")
def delete_pastebin_endpoint(pastebin_id: int) -> bool:
    return delete_pastebin(pastebin_id)


@app.get("/pastebin/")
def list_pastebins_endpoint() -> list[Pastebin]:
    return list_pastebins()


@app.put("/pastebin/{pastebin_id}")
def update_pastebin_endpoint(
    pastebin_id: int, title: str | None = None, content: str | None = None
) -> Pastebin | None:
    return update_pastebin(pastebin_id, title, content)


@app.get("/pastebin/search/")
def search_pastebins_endpoint(query: str) -> list[Pastebin]:
    return search_pastebins(query)


@app.get("/pastebin/count/")
def count_pastebins_endpoint() -> int:
    return count_pastebins()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
