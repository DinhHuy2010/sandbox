
import polars as pl

path = "out/sctv-out-snapshot-20261102-074800.parquet"

df = (
    pl.scan_parquet(path)
    .with_columns(
        pl.col("date_aspnet_str")
        .str.extract(r"/Date\((-?\d+)", 1)
        .cast(pl.Int64, strict=False)
        .alias("timestamp_ms")
    )
    .with_columns(
        pl.from_epoch("timestamp_ms", time_unit="ms")
        .dt.replace_time_zone("UTC")
        .dt.convert_time_zone("Asia/Ho_Chi_Minh")
        .dt.date()
        .alias("broadcast_date")
    )
)

coverage = (
    df.group_by("channel_id")
    .agg(
        pl.len().alias("events"),
        pl.col("broadcast_date").min().alias("first_date"),
        pl.col("broadcast_date").max().alias("last_date"),
        pl.col("broadcast_date").drop_nulls().n_unique()
          .alias("covered_days"),
        pl.col("broadcast_date").null_count()
          .alias("unparsed_dates"),
    )
    .with_columns(
        (
            (pl.col("last_date") - pl.col("first_date"))
            .dt.total_days() + 1
        ).alias("span_days")
    )
    .with_columns(
        (pl.col("span_days") - pl.col("covered_days"))
        .alias("missing_days")
    )
    .sort("channel_id")
    .collect()
)

print(coverage)
print("Channels:", coverage.height)
print("Total events:", coverage["events"].sum())
print("Earliest:", coverage["first_date"].min())
print("Latest:", coverage["last_date"].max())
print("Unparsed dates:", coverage["unparsed_dates"].sum())

