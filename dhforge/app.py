from dhforge.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", log_config=None)
