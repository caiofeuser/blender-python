import json
from pprintpp import pprint as pp
import os
import random
import shutil

BASE_DIR = "./YOLO/dataset"

IN_IMAGE_PATH = f'./renders'
IN_LABEL_PATH = f'./labels'

OUT_IMAGE_PATH = f'{BASE_DIR}/images'
OUT_LABEL_PATH = f'{BASE_DIR}/labels'

with open("classes.json") as f:
    classes = json.load(f)

models = list(classes.keys())

schema = {}
all_images = os.listdir(IN_IMAGE_PATH)
all_labels = os.listdir(IN_LABEL_PATH)

filtered_all_images = [image for image in all_images if image.endswith('.png')]
filtered_all_labels = [label for label in all_labels if label.endswith('.txt')]

ratio_train = 0.9
train_image_protion = len(filtered_all_images) * ratio_train


schema = {model: [] for model in models}

for image in filtered_all_images:
    for model in models:
        if image.startswith(model):
            schema[model].append(image)
            break

split_schema = {}
total_train_count = 0
total_val_count = 0

for model, model_images in schema.items():
    random.shuffle(model_images)

    num_images_model = len(model_images)
    num_train_images = int(num_images_model * 0.9)

    train_images = model_images[:num_train_images]
    val_images = model_images[num_train_images:]

    split_schema[model] = {
        "train": train_images,
        "val": val_images
    }

    total_train_count += len(train_images)
    total_val_count += len(val_images)


for model, split in split_schema.items():

    for image in split['train']:
        shutil.copy(f'./renders/{image}',
                    f'./YOLO/dataset/images/train/{image}')
        shutil.copy(f'./labels/{image.replace('.png', '.txt')}',
                    f'./YOLO/dataset/labels/train/{image.replace('.png', '.txt')}')

    for image in split['val']:
        shutil.copy(f'./renders/{image}',
                    f'./YOLO/dataset/images/val/{image}')
        shutil.copy(f'./labels/{image.replace('.png', '.txt')}',
                    f'./YOLO/dataset/labels/val/{image.replace('.png', '.txt')}')
