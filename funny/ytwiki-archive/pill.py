"""
ETL: Wikitubia YouTuber infobox extraction -> CSV for OpenRefine.

Covers all three infobox templates documented at WT:INFB
(https://youtube.fandom.com/wiki/WT:INFB):

    {{YouTuber}}   -- username = /user/ ID
    {{YouTuber1}}  -- username = /channel/ ID
    {{YouTuber2}}  -- username = @handle

Per WT:INFB, the three templates "differ in their usage of the username
parameter" only -- the rest of the parameter set is shared. That shared
set (below) was assembled from Template:YouTuber's "All parameters"
block plus two fields documented on WT:INFB that weren't present in that
block (`associates`, `wiki raw`), so the schema below is a superset:
any parameter a given article's template call doesn't use is emitted as
an empty string, per your request.

NOTE ON SCRAPING: Template:YouTuber1 and Template:YouTuber2's own pages
returned ROBOTS_DISALLOWED when fetched directly, so their parameter
lists couldn't be independently re-verified against the live page --
this script relies on the WT:INFB statement that the schema is shared.
If you want to double check, log in and view-source those two pages
yourself; if they've drifted from YouTuber's param list, add/remove
columns in CANONICAL_PARAMS below.
"""

import csv

import polars as pl
import wikitextparser as wtp

INFOBOX_TEMPLATES = {"YouTuber", "YouTuber1", "YouTuber2"}

# Shared parameter schema across all three templates (see module docstring).
# Order matches Template:YouTuber's documented "All parameters" block,
# with `associates` and `wiki raw` appended from WT:INFB.
CANONICAL_PARAMS = [
    "title",
    "image",
    "username",
    "channel",
    "style",
    "join date",
    "withdrawal",
    "Twitter",
    "Twitter2",
    "Twitter3",
    "Twitter4",
    "Twitter5",
    "Bluesky",
    "Bluesky name",
    "Bluesky2",
    "Bluesky3",
    "Bluesky4",
    "Bluesky5",
    "Facebook",
    "Facebook name",
    "Facebook2",
    "Facebook3",
    "Facebook4",
    "Facebook5",
    "Instagram",
    "Instagram2",
    "Instagram3",
    "Instagram4",
    "Instagram5",
    "Threads",
    "Threads2",
    "Threads3",
    "Threads4",
    "Threads5",
    "other media",
    "vids",
    "update",
    "status",
    "associates",
    "full name",
    "nationality",
    "location",
    "pronouns",
    "channel trailer",
    "most viewed video",
    "first video",
    "wiki",
    "wikiname",
    "wiki raw",
]

# lowercase, whitespace-collapsed lookup so "Join Date"/"join_date"/etc.
# still land in the right column; article editors are not always consistent.
_NORMALIZED_LOOKUP = {p.lower().replace("_", " ").strip(): p for p in CANONICAL_PARAMS}


def all_categories_under_parent(df: pl.DataFrame, category: str) -> list[str]:
    p = df.filter(
        pl.col("namespace") == 14,
        pl.col("title").str.split(":").list.get(0) == "Category",
        pl.col("categories").list.contains(category),
    )
    if p.is_empty():
        return []
    initial = p.select(pl.col("title").str.split(":").list.get(1)).to_series().to_list()
    cats = set()
    for i in initial:
        cats.add(i)
        cats.update(all_categories_under_parent(df, i))
    return list(cats)


def extract_params(template: wtp.Template) -> dict[str, str]:
    """Map a template call's arguments onto the canonical column set."""
    row = {p: "" for p in CANONICAL_PARAMS}
    for arg in template.arguments:
        raw_name = arg.name.strip()
        key = _NORMALIZED_LOOKUP.get(raw_name.lower().replace("_", " "))
        if key is None:
            # Unknown/positional/typo'd parameter -- don't silently drop it,
            # stash it so nothing is lost; OpenRefine can triage these.
            key = f"unmapped:{raw_name}"
            row.setdefault(key, "")
        row[key] = arg.value.strip()
    return row


def main() -> None:
    df = pl.read_parquet("fandom-youtube-articles.parquet")
    categories = all_categories_under_parent(df, "YouTubers")
    yts = df.filter(
        pl.col("namespace") == 0,
        pl.col("categories").list.set_intersection(categories).list.len() > 0,
    ).select(pl.col("title"), pl.col("text"), pl.col("categories"))

    rows: list[dict] = []
    extra_cols: list[str] = []  # unmapped params discovered along the way

    for d in yts.to_dicts():
        parsed = wtp.parse(d["text"])
        instance_num = 0  # resets per article; increments per infobox found on it
        for template in parsed.templates:
            name = template.name.strip().strip("\n")
            if name not in INFOBOX_TEMPLATES:
                continue
            instance_num += 1
            params = extract_params(template)
            for key in params:
                if key.startswith("unmapped:") and key not in extra_cols:
                    extra_cols.append(key)
            row = {
                # Unique per template instance -- use this as the record key
                # in OpenRefine (e.g. for Transpose/Columnize), not `title`,
                # since a page can carry more than one infobox.
                "page_title": d["title"],
                "infobox_instance_id": f"{d['title']}#{instance_num}",
                "categories": "|".join(d["categories"]),
                "template": name,
                **params,
            }
            rows.append(row)

    fieldnames = [
        "page_title",
        "infobox_instance_id",
        "categories",
        "template",
        *CANONICAL_PARAMS,
        *extra_cols,
    ]

    with open("youtubers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Wrote {len(rows)} infobox rows ({len(fieldnames)} columns) to youtubers.csv"
    )
    if extra_cols:
        print(f"Unmapped parameters found (added as extra columns): {extra_cols}")


if __name__ == "__main__":
    main()
