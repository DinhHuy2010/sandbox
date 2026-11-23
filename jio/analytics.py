from time import perf_counter

import polars as pl

epg = pl.scan_parquet(
    "out_analytical/programs/**/*.parquet",
    hive_partitioning=True,
)

# start = perf_counter()

# result = (
#     epg.group_by("channel_id")
#     .agg(
#         pl.len().alias("broadcasts"),
#         pl.col("showId").n_unique().alias("unique_shows"),
#     )
#     .sort("broadcasts", descending=True)
#     .limit(10)
#     .collect()
# )

# print(result)
# print(f"Elapsed: {perf_counter() - start:.3f}s")
