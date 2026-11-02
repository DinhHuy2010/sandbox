import contextlib
import pathlib
from datetime import datetime

import orjson
import polars as pl
from tqdm import tqdm

path = pathlib.Path(__file__).parent / "out/raw"

total = []

with contextlib.ExitStack() as stack:
    files = sorted(path.glob("*.json"))
    for item in tqdm(files):
        f = stack.enter_context(item.open("rb"))
        data = orjson.loads(f.read())
        total.extend([i for d in data["data"] for i in d["items"]])
pl.DataFrame(total).write_parquet(
    pathlib.Path(__file__).parent / f"out/vtvcab_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
    compression="zstd",
    compression_level=9,
)
