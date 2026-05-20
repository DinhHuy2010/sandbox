import textwrap

import httpx
import httpx_sse

client = httpx.Client(headers={"User-Agent": "see.py (example.com)"})
stream_url = "https://stream.wikimedia.org/v2/stream/revision-create"

with httpx_sse.connect_sse(client, "GET", stream_url) as connection:
    for event in connection.iter_sse():
        data = event.json()
        print("New revision created:")
        print(f"  Title: {data['page_title']} (#{data['page_id']})")
        print(f"  Timestamp: {data['rev_timestamp']}")
        print(
            f"  User: {data['performer']['user_text']} (#{data['performer']['user_id']}, {data['performer']['user_edit_count']} edits)"
        )
        comment = data.get("comment")
        if comment is None:
            comment = "(no comment)"
        else:
            comment = textwrap.shorten(comment, width=80, placeholder="...")
        print(f"  Comment: {comment}")
        print(f"  Bot edit: {data['performer']['user_is_bot']}")
        print(f"  Revision ID: #{data['rev_id']}")
