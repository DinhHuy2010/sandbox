import os
from base64 import b64decode
from binascii import Error as Base64DecodeError
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import sqlmodel
from pydantic import BaseModel, EmailStr
import bcrypt

SECRET_JWT_KEY = os.getenv(
    "SECRET_JWT_KEY", "change-this-development-secret-key-32-bytes-minimum"
)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


class User(sqlmodel.SQLModel, table=True):
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    name: str
    email: EmailStr = sqlmodel.Field(index=True, unique=True)
    hashed_password: str


class UserCreateForm(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserUpdateForm(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr


class LoginForm(BaseModel):
    email: EmailStr
    password: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    password_bytes = password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")

    try:
        if bcrypt.checkpw(password_bytes, hash_bytes):
            return True
    except ValueError:
        pass

    try:
        legacy_hash_bytes = b64decode(hash_bytes, validate=True)
    except (Base64DecodeError, ValueError):
        return False

    try:
        return bcrypt.checkpw(password_bytes, legacy_hash_bytes)
    except ValueError:
        return False


def create_user(db: sqlmodel.Session, user_form: UserCreateForm) -> User:
    if get_user_by_email(db, user_form.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    hashed_password = hash_password(user_form.password)
    user = User(
        name=user_form.name, email=user_form.email, hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: sqlmodel.Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: sqlmodel.Session, email: str) -> User | None:
    return db.exec(sqlmodel.select(User).where(User.email == email)).first()


def update_user(
    db: sqlmodel.Session, user_id: int, user_form: UserUpdateForm
) -> User | None:
    user = db.get(User, user_id)
    if not user:
        return None
    if user_form.name is not None:
        user.name = user_form.name
    if user_form.email is not None:
        existing_user = get_user_by_email(db, user_form.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )
        user.email = user_form.email
    if user_form.password is not None:
        user.hashed_password = hash_password(user_form.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: sqlmodel.Session, user_id: int) -> bool:
    user = db.get(User, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


def authenticate_user(db: sqlmodel.Session, email: str, password: str) -> str | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    jwt_token = jwt.encode(
        {
            "user": user.id,
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        },
        SECRET_JWT_KEY,
        algorithm=JWT_ALGORITHM,
    )
    return jwt_token


def decode_jwt_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_JWT_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_from_token(db: sqlmodel.Session, token: str) -> User | None:
    payload = decode_jwt_token(token)
    if not payload:
        return None
    user_id = payload.get("user")
    if not isinstance(user_id, int):
        return None
    return get_user_by_id(db, user_id)


def list_users(db: sqlmodel.Session) -> list[User]:
    return db.exec(sqlmodel.select(User)).all()


def delete_user_by_id(db: sqlmodel.Session, user_id: int) -> bool:
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


def delete_user_by_email(db: sqlmodel.Session, email: str) -> bool:
    user = get_user_by_email(db, email)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


def change_user_password(db: sqlmodel.Session, user_id: int, new_password: str) -> bool:
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.commit()
    return True


def change_user_email(db: sqlmodel.Session, user_id: int, new_email: str) -> bool:
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    user.email = new_email
    db.add(user)
    db.commit()
    return True


def change_user_name(db: sqlmodel.Session, user_id: int, new_name: str) -> bool:
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    user.name = new_name
    db.add(user)
    db.commit()
    return True


def get_user_count(db: sqlmodel.Session) -> int:
    return db.exec(sqlmodel.select(sqlmodel.func.count(User.id))).one()


def get_db():
    with sqlmodel.Session(app.state.engine) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = sqlmodel.create_engine(
        "sqlite:///users.db",
        connect_args={"check_same_thread": False},
    )
    sqlmodel.SQLModel.metadata.create_all(app.state.engine)
    yield
    app.state.engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    db: Annotated[sqlmodel.Session, Depends(get_db)], user_form: UserCreateForm
):
    return create_user(db, user_form)


@app.get("/users", response_model=list[UserRead])
def list_users_endpoint(db: Annotated[sqlmodel.Session, Depends(get_db)]):
    return list_users(db)


@app.get("/users/count")
def user_count_endpoint(db: Annotated[sqlmodel.Session, Depends(get_db)]):
    return {"count": get_user_count(db)}


@app.get("/users/{user_id}", response_model=UserRead)
def get_user_endpoint(user_id: int, db: Annotated[sqlmodel.Session, Depends(get_db)]):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@app.put("/users/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: int,
    db: Annotated[sqlmodel.Session, Depends(get_db)],
    user_form: UserUpdateForm,
):
    user = update_user(db, user_id, user_form)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@app.delete("/users/{user_id}")
def delete_user_endpoint(
    user_id: int, db: Annotated[sqlmodel.Session, Depends(get_db)]
):
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return {"message": "User deleted successfully"}


@app.post("/auth/login")
def login_endpoint(
    db: Annotated[sqlmodel.Session, Depends(get_db)],
    login_form: LoginForm,
):
    token = authenticate_user(db, login_form.email, login_form.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserRead)
def me_endpoint(
    db: Annotated[sqlmodel.Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(f"{__name__}:app", host="127.0.0.1", port=8000, reload=True)
