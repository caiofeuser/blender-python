import json
import os
from glob import glob

# --- CONFIGURATION ---
# UPDATE THESE PATHS TO MATCH YOUR FOLDERS
IMAGE_DIR = 'new_validation_labeled/images'  # Where your images are
LABEL_DIR = 'new_validation_labeled/labels'  # Where your .txt files are
CLASSES_PATH = 'classes.json'                       # Your classes.json file
# The file to drag into Label Studio
OUTPUT_JSON = 'label_studio_import.json'
# ---------------------


def convert_yolo_to_ls():
    # 1. Load Classes
    if not os.path.exists(CLASSES_PATH):
        print(f"Error: {CLASSES_PATH} not found.")
        return

    with open(CLASSES_PATH, 'r') as f:
        class_map = json.load(f)  # e.g. {"head": 0, "armleft": 1}

    # Invert map to get Name by ID (e.g. {0: "head", 1: "armleft"})
    id_to_label = {v: k for k, v in class_map.items()}

    tasks = []

    # Get all images
    if not os.path.exists(IMAGE_DIR):
        print(f"Error: {IMAGE_DIR} not found.")
        return

    image_files = sorted([
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])

    print(f"Found {len(image_files)} images. Converting...")

    for img_file in image_files:
        # Construct label path
        label_file = os.path.splitext(img_file)[0] + '.txt'
        label_path = os.path.join(LABEL_DIR, label_file)

        # Base task structure
        # NOTE: This assumes you are using Local Storage in Label Studio.
        # It creates a path like /data/local-files/?d=images/my_image.jpg
        # You might need to adjust the path prefix based on your specific LS setup.
        task = {
            "data": {
                # This points to the file relative to the root you serve in Label Studio
                "image": f"/data/local-files/?d={IMAGE_DIR}/{img_file}"
            },
            "predictions": []
        }

        if os.path.exists(label_path):
            result = []
            with open(label_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    x_c, y_c, w, h = map(float, parts[1:5])

                    # --- CONVERSION MATH ---
                    # YOLO: x_center, y_center (0-1)
                    # LS: top_left_x, top_left_y (0-100%)

                    x = (x_c - w / 2) * 100
                    y = (y_c - h / 2) * 100
                    width = w * 100
                    height = h * 100

                    label_name = id_to_label.get(class_id, "unknown")

                    # Add bbox entry
                    result.append({
                        "from_name": "label",
                        "to_name": "image",
                        "type": "rectanglelabels",
                        "value": {
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "rotation": 0,
                            "rectanglelabels": [label_name]
                        }
                    })

            # Add results to task as a "prediction" (pre-label)
            # If the file was empty (background), this list is empty, which is correct.
            task["predictions"].append({
                "model_version": "yolo_v8_prelabel",
                "score": 1.0,
                "result": result
            })

        tasks.append(task)

    # Save JSON
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(tasks, f, indent=4)

    print(f"Saved {len(tasks)} tasks to {OUTPUT_JSON}")


if __name__ == "__main__":
    convert_yolo_to_ls()
