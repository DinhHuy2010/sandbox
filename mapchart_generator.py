import json
import random

with open("mapchart_list.txt", "r") as f:
    data = [i.strip() for i in f]

BASE_DATA = {
    "title": "Alternate History",
    "hidden": [],
    "background": "#252525",
    "borders": "#252525",
    "legendFont": "Alegreya Sans:500",
    "legendFontColor": "#d9d9d9",
    "legendBorderColor": "#00000000",
    "legendBgColor": "#00000000",
    "legendWidth": 163.4188232421875,
    "legendBoxShape": "square",
    "legendTitleMode": "attached",
    "areBordersShown": True,
    "defaultColor": "#737373",
    "labelsColor": "#d9d9d9",
    "labelsFont": "Arial",
    "strokeWidth": "medium",
    "areLabelsShown": False,
    "uncoloredScriptColor": "#4393c3",
    "zoomLevel": "1.00",
    "zoomX": "-3451.14",
    "zoomY": "-304.85",
    "v6": True,
    "mapTitleScale": 1,
    "page": "world-subdivisions",
    "mapVersion": None,
    "legendPosition": "custom",
    "legendX": 17.978947419450993,
    "legendY": 131.83712280701766,
    "legendSize": "custom",
    "legendScale": 0.751665245042879,
    "legendTranslateX": "0.00",
    "legendStatus": "show",
    "scalingPatterns": True,
    "legendRowsSameColor": True,
    "legendColumnCount": 1,
    "showDefaultColorInLegend": False,
}

arr_8bit=list(range(256))

def gen_rgb():
    rgb = random.choices(arr_8bit, k=3)
    return "#" + bytes(rgb).hex()


groups = int(input("Enter number of groups: "))
gdata = {}
print("Generating groups...")
for _ in range(groups):
    color = gen_rgb()
    while color in gdata:
        color = gen_rgb()
    gdata[color] = {"label": color, "paths": []}
colors = list(gdata)
random.shuffle(data)
print("Placing entitles...")
for i, gid in enumerate(data):
    color = colors[i % len(colors)]
    gdata[color]["paths"].append(gid)
with open("out.txt", "w") as f:
    json.dump({**BASE_DATA, "groups": gdata}, f, ensure_ascii=False)
print("done!")