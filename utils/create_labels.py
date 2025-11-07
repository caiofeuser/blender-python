import json


def __main__():
    with open("classes.json") as f:
        classes = json.load(f)

    with open("bb.json") as f:
        data = json.load(f)

    for item in data:
        if item['model_name'] != 'background':
            width = item['max_x'] - item['min_x']
            heigth = item['max_y'] - item['min_y']
            center_x = item['max_x'] - width / 2
            center_y = item['max_y'] - heigth / 2
            model_name = item['model_name']

            model_class = classes[model_name]
            export_string = f'{model_class} {center_x} {center_y} {width} {heigth}'

        else:
            export_string = ""

        print(export_string)

        with open(f'./labels/{item['file_name'].replace("png", "txt")}', 'w') as f:
            f.write(export_string)
