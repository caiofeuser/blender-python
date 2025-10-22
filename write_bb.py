import json

import matplotlib.patches as ptc
import matplotlib.pyplot as plt
from PIL import Image

with open("bb.json") as f:
    data = json.load(f)

im = Image.open(data["file"])
fig, ax = plt.subplots()

res_x = im.width
res_y = im.height
ax.imshow(im)

x_norm = data["min_x"]
y_norm = data["min_y"]
x_lenth_norm = data["max_x"] - x_norm
y_lenth_norm = data["max_y"] - y_norm

x = x_norm * res_x
y = y_norm * res_y
x_lenth = x_lenth_norm * res_x
y_lenth = y_lenth_norm * res_y

print("denormalized", {
    "x": x,
    "width": x_lenth,
    "y": y,
    "height": y_lenth
})

rect = ptc.Rectangle((x, y), x_lenth, y_lenth, linewidth=1,
                     edgecolor='r', facecolor="none")

ax.add_patch(rect)

plt.show()
