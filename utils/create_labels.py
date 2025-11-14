import json


def process_labels():
    with open("classes.json") as f:
        classes = json.load(f)

    with open("bb.json") as f:
        data = json.load(f)

    for item in data:
        labels = []
        for bb in item['bboxes']:
            if bb['model_name'] != 'background':
                width = bb['max_x'] - bb['min_x']
                heigth = bb['max_y'] - bb['min_y']
                center_x = bb['max_x'] - width / 2
                center_y = 1 - (bb['max_y'] - heigth / 2)
                model_name = bb['model_name']

                model_class = classes[model_name]

                labels.append(
                    f'{model_class} {center_x} {center_y} {width} {heigth}'
                )
        if labels:
            export_string = "\n".join(labels)

        else:
            export_string = ""

        print(export_string)

        with open(f'./labels/{item['file_name'].replace("png", "txt")}', 'w') as f:
            f.write(export_string)


# when we call a file trough terminal, this code will be executed, therfore, we call the main function
if __name__ == "__main__":
    process_labels()
