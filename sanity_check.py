import cv2
import os

# --- CONFIGURATION ---
IMAGE_DIR = 'renders/renders_auto_20251203_140940' # Check your path
LABEL_DIR = 'labels'
# ---------------------

def main():
    # 1. Gather all images first
    image_files = sorted([
        f for f in os.listdir(IMAGE_DIR) 
        if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('background')
    ])

    if not image_files:
        print("No images found in", IMAGE_DIR)
        return

    print(f"Found {len(image_files)} images.")
    print("CONTROLS: [D]=Next, [A]=Prev, [X]=DELETE, [Q]=Quit")

    index = 0

    while index < len(image_files):
        img_file = image_files[index]
        img_path = os.path.join(IMAGE_DIR, img_file)
        
        # Construct label path (supports .png -> .txt)
        label_file = os.path.splitext(img_file)[0] + '.txt'
        label_path = os.path.join(LABEL_DIR, label_file)

        # --- Load Image ---
        img = cv2.imread(img_path)
        if img is None:
            print(f"Could not load {img_file}, skipping/removing from list...")
            del image_files[index]
            continue

        h, w, _ = img.shape

        # --- Draw Bounding Boxes ---
        box_count = 0
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    # YOLO Format: x_center, y_center, width, height (Normalized)
                    n_xc, n_yc, n_w, n_h = map(float, parts[1:5])

                    # Convert to Pixels (Top-Left Origin)
                    # x_center_px = n_xc * w
                    # y_center_px = n_yc * h
                    # width_px = n_w * w
                    # height_px = n_h * h
                    
                    x1 = int((n_xc - n_w / 2) * w)
                    y1 = int((n_yc - n_h / 2) * h)
                    x2 = int((n_xc + n_w / 2) * w)
                    y2 = int((n_yc + n_h / 2) * h)

                    # Draw Box
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Draw Class ID
                    cv2.putText(img, f"ID: {class_id}", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    box_count += 1
        else:
            # No label file = Background image
            cv2.putText(img, "BACKGROUND (No Label)", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # --- UI Overlay ---
        info_text = f"[{index+1}/{len(image_files)}] {img_file} | Boxes: {box_count}"
        cv2.putText(img, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4) # Shadow
        cv2.putText(img, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2) # Text

        # Show Image
        cv2.imshow('Dataset Cleaner', img)

        # --- Controls ---
        key = cv2.waitKey(0) & 0xFF

        if key == ord('d') or key == 83: # 'd' or Right Arrow
            index += 1
        
        elif key == ord('a') or key == 81: # 'a' or Left Arrow
            index = max(0, index - 1)
        
        elif key == ord('x'): # 'x' to DELETE
            print(f"🗑️ DELETING: {img_file}")
            
            # 1. Delete Image
            if os.path.exists(img_path):
                os.remove(img_path)
            
            # 2. Delete Label
            if os.path.exists(label_path):
                os.remove(label_path)
            
            # 3. Remove from list so we don't see it again
            del image_files[index]
            
            # Don't increment index (the next image slides into this slot)
            # Just check bounds
            if index >= len(image_files):
                index = len(image_files) - 1

        elif key == ord('q') or key == 27: # 'q' or ESC
            break

    cv2.destroyAllWindows()
    print("Cleaning finished.")

if __name__ == "__main__":
    main()
