from collections import deque

import polars as pl

df = pl.scan_ndjson("temp/fullfiletimelist-archive-dl-fedoraproject.jsonl.zst")
# print(df.select(pl.col("size")).sum().collect())
deque(map(print, df.select(pl.col("path")).collect().to_series()), maxlen=0)
