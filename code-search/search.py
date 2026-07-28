import argparse
import os

from tantivy import Index, SchemaBuilder

# 1. Re-reconstruct Schema to open the existing Tantivy index
schema_builder = SchemaBuilder()
schema_builder.add_text_field("filepath", stored=True)
schema_builder.add_text_field("name", stored=True)
schema_builder.add_text_field("type", stored=True)
schema_builder.add_integer_field("line", stored=True)
schema_builder.add_integer_field("col", stored=True)
schema_builder.add_text_field("code", stored=True)
schema = schema_builder.build()


def search_index(
    index_path: str = "./tantivy_index", query_str: str = "", limit: int = 10
):
    if not os.path.exists(index_path):
        print(
            f"[Error] Index directory '{index_path}' does not exist. Run the indexer first!"
        )
        return

    index = Index(schema, path=index_path)

    # Acquire Searcher
    index.reload()
    searcher = index.searcher()

    if not query_str.strip():
        print("Please enter a query.")
        return

    # 2. Parse Query across multiple target fields by default
    # default_fields = ["filepath", "name", "code", "type"]
    try:
        query = index.parse_query(query_str)
    except Exception as e:
        print(f"[Query Error] Failed to parse query '{query_str}': {e}")
        return

    # 3. Search and display results
    search_results = searcher.search(query, limit=10000)

    print(
        f"\n🔍 Found {len(search_results.hits)} result(s) for query: '{query_str}'\n"
        + "=" * 60
    )

    for score, doc_address in search_results.hits:
        doc = searcher.doc(doc_address)

        sym_type = doc["type"][0].upper()
        sym_name = doc["name"][0]
        filepath = doc["filepath"][0]
        line = doc["line"][0]
        code_snippet = doc["code"][0]

        # Header: File path and line number
        print(f"📌 [{sym_type}] \033[1;34m{sym_name}\033[0m")
        print(f"   └── \033[90m{filepath}:{line}\033[0m  (Score: {score:.2f})")

        # Code Snippet Preview (First 4 lines)
        preview_lines = code_snippet.splitlines()[:4]
        print("   ┌── [Code Preview]")
        for l in preview_lines:
            print(f"   │   {l}")
        if len(code_snippet.splitlines()) > 4:
            print("   │   ...")
        print("-" * 60)


def interactive_cli(index_path: str = "./tantivy_index"):
    """Runs a continuous prompt for testing queries."""
    print(f"--- Codebase Search Engine Active (Index: {index_path}) ---")
    print("Query Syntax Examples:")
    print("  • 'name:parse'             -> Search symbol names")
    print("  • 'docstring:Tantivy'      -> Search docstrings")
    print("  • 'type:function AND code:return' -> Field boolean filters")
    print("  • 'type:class'             -> List classes")
    print("  • 'exit' or 'q'            -> Exit\n")

    while True:
        try:
            q = input("\n🔎 search > ")
            if q.strip().lower() in ("exit", "q"):
                break
            search_index(index_path=index_path, query_str=q)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search indexed Python codebase with Tantivy."
    )
    parser.add_argument("-q", "--query", type=str, help="Single query to execute.")
    parser.add_argument(
        "-i",
        "--index",
        type=str,
        default="./tantivy_index",
        help="Path to Tantivy index folder.",
    )
    parser.add_argument(
        "-l", "--limit", type=int, default=10, help="Max results to return."
    )

    args = parser.parse_args()

    if args.query:
        search_index(index_path=args.index, query_str=args.query)
    else:
        interactive_cli(index_path=args.index)
