import json


with open("query-syndey-constraint.json", "r") as f:
    file_content = f.read()
d = json.loads(file_content)
for result in d["results"]["bindings"]:
    item = result["item"]["value"].replace("http://www.wikidata.org/entity/", "")
    label = result["itemLabel"]["value"]
    # stmt_id = "$".join(result["stmt"]["value"].replace("http://www.wikidata.org/entity/statement/", "").split("-", 1))
    # print(f"{item}\t{label}\t{stmt_id}")
    print(f"-{item} | P131 | Q3130 | /* Remove Syndey from P131, fixing constraint violation */")
    print(f"{item} | P131 | Q3224 | /* Adding New South Wales to P131, replacing Syndey */")
    print(f"{item} | P276 | Q3130 | /* Add Syndey to P276 */")
