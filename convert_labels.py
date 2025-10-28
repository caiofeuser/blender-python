import os
import json

with open("classes.json") as f:
    classes = json.load(f)

with open("bb_fixed.json") as f:
    data = json.load(f)

export_json = []

for item in data:
    width = item['max_x'] - item['min_x']
    heigth = item['max_y'] - item['min_y']
    center_x = item['max_x'] - width / 2
    center_y = item['max_y'] - heigth / 2
    model_name = item['model_name']
    img_name = item['file_name']

    model_class = classes[model_name]
    export_string = f'{model_class} {center_x} {center_y} {width} {heigth}'

    print(export_string)

    with open(f'./labels/{img_name}.txt', 'w') as f:
        f.write(export_string)
