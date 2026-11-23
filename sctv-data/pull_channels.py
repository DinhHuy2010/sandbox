import polars as pl

import libsctv

out = libsctv.fetch_channels()
ls = out["DSKenh"]
df = pl.DataFrame(ls)
df.write_parquet("channels.parquet", compression="zstd", compression_level=3)
