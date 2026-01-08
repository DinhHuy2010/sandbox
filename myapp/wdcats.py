from collections.abc import Callable
from typing import TypedDict, get_args
import httpx
from pydantic import BaseModel

from wblangs import WikibaseLanguage, WikidataConnectedWikis
from wikibase_rest_api_models import (
    Aliases,
    Descriptions,
    Item,
    Labels,
    Sitelink,
    Statement,
)

USER_AGENT = "wdcats/1.0 (https://www.wikidata.org/wiki/User:DinhHuy2010)"
LANGS = sorted(get_args(WikibaseLanguage.__value__))

client = httpx.Client(headers={"User-Agent": USER_AGENT})

# label_handler(context: Context, langauge: str, label: str)
type WikibaseLabelHandler = Callable[
    ["ItemVisitorContext", WikibaseLanguage, str], None
]
# description_handler(context: Context, langauge: str, description: str)
type WikibaseDescriptionHandler = Callable[
    ["ItemVisitorContext", WikibaseLanguage, str], None
]
# alias_handler(context: Context, langauge: str, alias: list[str])
type WikibaseAliasHandler = Callable[
    ["ItemVisitorContext", WikibaseLanguage, list[str]], None
]
# sitelink_handler(context: Context, wiki: str, sitelink: Sitelink)
type WikibaseSitelinkHandler = Callable[
    ["ItemVisitorContext", WikidataConnectedWikis, Sitelink], None
]
# statement(context: Context, statement: Statement)
type WikibaseStatementHandler = Callable[["ItemVisitorContext", Statement], None]


type SimpleCallbackDict[Key, Callback] = dict[Key | None, Callback]


class HandlerContext(TypedDict, total=False):
    labels: SimpleCallbackDict[WikibaseLanguage, WikibaseLabelHandler]
    descriptions: SimpleCallbackDict[WikibaseLanguage, WikibaseDescriptionHandler]
    aliases: SimpleCallbackDict[WikibaseLanguage, WikibaseAliasHandler]
    sitelinks: SimpleCallbackDict[WikidataConnectedWikis, WikibaseSitelinkHandler]
    statements: SimpleCallbackDict[str, WikibaseStatementHandler]


class ItemVisitorContext(BaseModel):
    item: Item


def fetch_wikidata_item(entity_id: str) -> Item:
    url = f"https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items/{entity_id}"
    response = client.get(url)
    response.raise_for_status()
    data = response.json()
    return Item.model_validate(data)


def noop(*args: object, **kwargs: object):
    pass


def visit_labels(
    ctx: ItemVisitorContext,
    labels: Labels,
    table: SimpleCallbackDict[WikibaseLanguage, WikibaseLabelHandler],
) -> None:
    for lang_code in LANGS:
        label = labels.root.get(lang_code)
        if label is None:
            continue
        handler = table.get(lang_code, table.get(None, noop))
        handler(ctx, lang_code, label)


def visit_descriptions(
    ctx: ItemVisitorContext,
    descriptions: Descriptions,
    table: SimpleCallbackDict[WikibaseLanguage, WikibaseDescriptionHandler],
) -> None:
    for lang_code in LANGS:
        description = descriptions.root.get(lang_code)
        if description is None:
            continue
        handler = table.get(lang_code, table.get(None, noop))
        handler(ctx, lang_code, description)


def visit_aliases(
    ctx: ItemVisitorContext,
    aliases: Aliases,
    table: SimpleCallbackDict[WikibaseLanguage, WikibaseAliasHandler],
) -> None:
    for lang_code in LANGS:
        alias_list = aliases.root.get(lang_code)
        if alias_list is None:
            continue
        handler = table.get(lang_code, table.get(None, noop))
        handler(ctx, lang_code, alias_list)


def visit_sitelinks(
    ctx: ItemVisitorContext,
    sitelinks: dict[WikidataConnectedWikis, Sitelink],
    table: SimpleCallbackDict[WikidataConnectedWikis, WikibaseSitelinkHandler],
) -> None:
    for wiki_code, sitelink in sitelinks.items():
        handler = table.get(wiki_code, table.get(None, noop))
        handler(ctx, wiki_code, sitelink)


def visit_statements(
    ctx: ItemVisitorContext,
    statements: dict[str, list[Statement]],
    table: SimpleCallbackDict[str, WikibaseStatementHandler],
) -> None:
    for property_id, statements_list in statements.items():
        handler = table.get(property_id, table.get(None, noop))
        for statement in statements_list:
            handler(ctx, statement)


def visit_item(ctx: ItemVisitorContext, handlers: HandlerContext) -> None:
    item = ctx.item
    if item.labels and "labels" in handlers:
        visit_labels(ctx, item.labels, handlers["labels"])
    if item.descriptions and "descriptions" in handlers:
        visit_descriptions(ctx, item.descriptions, handlers["descriptions"])
    if item.aliases and "aliases" in handlers:
        visit_aliases(ctx, item.aliases, handlers["aliases"])
    if item.statements and "statements" in handlers:
        visit_statements(ctx, item.statements, handlers["statements"])
    if item.sitelinks and "sitelinks" in handlers:
        visit_sitelinks(ctx, item.sitelinks, handlers["sitelinks"])


def generate_categories(item: Item) -> list[str]:
    categories: list[str] = []

    # Wikibase REST API, not action API
    # Placeholder logic for category generation
    def visit_labels(ctx: ItemVisitorContext, lang: WikibaseLanguage, label: str):
        categories.append(f"Items with label in language {lang}")

    def visit_descriptions(
        ctx: ItemVisitorContext, lang: WikibaseLanguage, description: str
    ):
        categories.append(f"Items with description in language {lang}")

    def visit_aliases(
        ctx: ItemVisitorContext, lang: WikibaseLanguage, aliases: list[str]
    ):
        categories.append(f"Items with aliases in language {lang}")

    def visit_sitelinks(
        ctx: ItemVisitorContext, wiki: WikidataConnectedWikis, sitelink: Sitelink
    ):
        categories.append(f"Items with sitelink to {wiki}")

    ctx = ItemVisitorContext(item=item)
    visit_item(
        ctx,
        {
            "labels": {None: visit_labels},
            "descriptions": {None: visit_descriptions},
            "aliases": {None: visit_aliases},
            "sitelinks": {None: visit_sitelinks},
        },
    )
    return categories


if __name__ == "__main__":
    item = fetch_wikidata_item("Q42")
    cats = generate_categories(item)
    for cat in cats:
        print(cat)
