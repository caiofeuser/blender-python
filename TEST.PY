import cv2
import os

# --- CONFIG ---
IMAGE_DIR = 'YOLO/dataset/images/train'
LABEL_DIR = 'YOLO/dataset/labels/train'
# ----------------

image_files = [f for f in os.listdir(IMAGE_DIR) if f.endswith('.jpg') or f.endswith('.png')]

for img_file in image_files:
    # Load Image
    img_path = os.path.join(IMAGE_DIR, img_file)
    img = cv2.imread(img_path)
    h, w, _ = img.shape

    # Load corresponding Label file
    label_file = img_file.rsplit('.', 1)[0] + '.txt'
    label_path = os.path.join(LABEL_DIR, label_file)

    if os.path.exists(label_path):
        with open(label_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            class_id = int(parts[0])
            
            # YOLO format is normalized: x_center, y_center, width, height
            x_center, y_center, width, height = map(float, parts[1:])
            
            # Convert to pixel coordinates
            x1 = int((x_center - width / 2) * w)
            y1 = int((y_center - height / 2) * h)
            x2 = int((x_center + width / 2) * w)
            y2 = int((y_center + height / 2) * h)

            # Draw the box (Green)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Show image
    cv2.imshow('Ground Truth Check', img)
    
    # Press 'q' to quit, any other key for next image
    if cv2.waitKey(0) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
