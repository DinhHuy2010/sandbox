import polars as pl
import wikitextparser as wtp


def all_categories_under_parent(df: pl.DataFrame, category: str) -> list[str]:
    p = df.filter(
        pl.col("namespace") == 14,
        pl.col("title").str.split(":").list.get(0) == "Category",
        pl.col("categories").list.contains(category),
    )
    if p.is_empty():
        return []
    inital = p.select(pl.col("title").str.split(":").list.get(1)).to_series().to_list()
    cats = set()
    for i in inital:
        cats.add(i)
        cats.update(all_categories_under_parent(df, i))
    return list(cats)


df = pl.read_parquet("fandom-youtube-articles.parquet")
categories = all_categories_under_parent(df, "YouTubers")
yts = df.filter(
    pl.col("namespace") == 0,
    pl.col("categories").list.set_intersection(categories).list.len() > 0,
).select(pl.col("title"), pl.col("text"), pl.col("categories"))
data = yts.to_dicts()
for d in data:
    t = wtp.parse(d["text"])
    print("Title: ", d["title"])
    for template in t.templates:
        name = template.name.strip().strip("\n")
        if name not in {"YouTuber", "YouTuber1", "YouTuber2"}:
            # print("Template ignored: ", template.name)
            continue
        print(template)
