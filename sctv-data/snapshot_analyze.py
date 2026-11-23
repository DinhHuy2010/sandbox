import pathlib
from datetime import UTC, datetime

import orjson
from tqdm import tqdm


def aspnet_date_str_to_datetime(s: str):
    if s is None:
        return None
    if not s.startswith("/Date(") or not s.endswith(")/"):
        raise ValueError(f"Invalid ASP.NET date string: {s}")
    timestamp = int(s[6:-2]) / 1000

    return datetime.fromtimestamp(timestamp, tz=UTC)

if __name__ == "__main__":
    BASE_PATH = pathlib.Path("out-snapshot-20261102-074800/out/raw").resolve()
    with (BASE_PATH / "status.json").open("rb") as f:
        status = orjson.loads(f.read())
        
    total_files = status["progress"]["total"]
    print(f"--> Total files: {total_files}")
    for f in tqdm(BASE_PATH.glob("data/*/*/*.json"), total=total_files):
        with f.open("rb") as ff:
            data = orjson.loads(ff.read())
        if data["LichPhatSong"] is None:
            continue
