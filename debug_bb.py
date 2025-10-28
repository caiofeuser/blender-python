import json
import matplotlib.patches as ptc
import matplotlib.pyplot as plt
from PIL import Image

with open("fixed_bb.json") as f:
    data = json.load(f)

for render in data:
    im = Image.open(render["file_path"])
    fig, ax = plt.subplots()

    res_x = im.width
    res_y = im.height

    ax.imshow(im, origin='lower')

    min_x_norm = render["min_x"]
    max_x_norm = render["max_x"]
    min_y_norm = render["min_y"]
    max_y_norm = render["max_y"]

    x = min_x_norm * res_x

    y = (1 - max_y_norm) * res_y

    width = (max_x_norm - min_x_norm) * res_x
    height = (max_y_norm - min_y_norm) * res_y

    print("denormalized", {
        "x": x,
        "width": width,
        "y": y,
        "height": height
    })

    rect = ptc.Rectangle((x, y), width, height, linewidth=1,
                         edgecolor='r', facecolor="none")

    ax.add_patch(rect)

    plt.show()

    plt.close(fig)
