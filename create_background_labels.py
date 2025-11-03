import json
import os
from pprintpp import pprint as pp
# get the actual bb_fixed
# get all the images that are from background
# append in the bb_fixed
# generate the labels


with open("bb_fixed.json") as f:
    prev_data = json.load(f)

all_renders = os.listdir('./renders')
background_renders = list(
    filter(lambda img: img.startswith("background"), all_renders))

for img in background_renders:
    payload = {
        "min_x": None,
        "max_x": None,
        "min_y": None,
        "max_y": None,
        "file_path": f'./renders/{img}',
        "file_name": img,
        "model_name": None
    }

    prev_data.append(payload)
    file_name = img.replace('png', 'txt')

    print(file_name)

    # with open(f"./labels/{img.replace('png', 'txt')}", 'w') as f:
    #     f.write('')

with open('bb_fixed_with_bg.json', 'w') as f:
    json.dump(prev_data, f)
