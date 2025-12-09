from ultralytics import YOLO
import os
import shutil

MODEL_PATH = "./best_float32.tflite"
SOURCE_IMAGES_PATH = "./new_validation/"
OUTPUT = "new_validation_labeled"

TRESHHOLD = 0.4


def auto_label():
    if not os.path.exists(MODEL_PATH):
        print(f"model not found at {MODEL_PATH}")
        return

    model = YOLO(MODEL_PATH)

    if os.path.exists("temp_inference"):
        shutil.rmtree("temp_inference")

    resuls = model.predict(
        source=SOURCE_IMAGES_PATH,
        conf=TRESHHOLD,
        save_txt=True,
        save_conf=True,
        project="temp_inference",
        name="results",
        exist_ok=True,
        verbose=False
    )

    # 3. organize the output

    output_img_dir = os.path.join(OUTPUT, "images")
    output_label_dir = os.path.join(OUTPUT, "labels")

    os.makedirs(output_img_dir, exist_ok=True)
    os.makedirs(output_label_dir, exist_ok=True)

    generate_labels_dir = os.path.join("temp_inference", "results", "labels")

    count = 0
    if os.path.exists(generate_labels_dir):
        for file_name in os.listdir(generate_labels_dir):
            if file_name.endswith(".txt"):
                src = os.path.join(generate_labels_dir, file_name)
                dst = os.path.join(output_label_dir, file_name)
                shutil.move(src, dst)
                count += 1

    count_img = 0
    if os.path.exists(SOURCE_IMAGES_PATH):
        for file in os.listdir(SOURCE_IMAGES_PATH):
            if file.endswith((".jpg", ".jpeg", ".png")):
                src = os.path.join(SOURCE_IMAGES_PATH, file)
                dst = os.path.join(output_img_dir, file)
                shutil.copy(src, dst)
                count_img += 1

   # 4. Cleanup
    if os.path.exists("temp_inference"):
        shutil.rmtree("temp_inference")

    print("-" * 30)
    print(f"✅ Auto-labeling complete!")
    print(f"   - Processed Images: {count_img}")
    print(f"   - Labels Generated: {count}")
    print(f"   - Output Folder:    {OUTPUT}")
    print("-" * 30)
    print("NEXT STEPS:")
    print("1. Open 'yolo_to_ls.py'")
    print(f"2. Change IMAGE_DIR to '{count_img}'")
    print(f"3. Change LABEL_DIR to '{count}'")
    print("4. Run it to generate your Label Studio import file.")


if __name__ == "__main__":
    auto_label()
