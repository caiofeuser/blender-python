import cv2
import os

# --- CONFIGURATION ---
# Replace with your actual video file name
FOLDER = "videos" 

# Where to save the images
OUTPUT_FOLDER = "new_validation"

# Save 1 frame every N frames. 
# 30fps video / 15 = 2 images per second.
FRAME_INTERVAL = 15 

# Resize images to this dimension (square). 
# Set to None to keep original resolution.
RESIZE_DIM = None 
# ---------------------
videos = os.listdir(FOLDER)
def extract_frames():
   saved_count = 0

   for video in videos:
        # 3. Open Video
        cap = cv2.VideoCapture(os.path.join(FOLDER, video))
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            
            # If no frame is returned, we've reached the end
            if not ret:
                break

            # 4. Check interval
            if frame_count % FRAME_INTERVAL == 0:
                
                # 5. Resize (Optional but recommended for YOLO)
                if RESIZE_DIM:
                    # Resize to square 640x640 (this might stretch the image slightly
                    # if your video is 16:9, which is fine for YOLO, or you can
                    # adjust to resize keeping aspect ratio if you prefer).
                    frame = cv2.resize(frame, (RESIZE_DIM, RESIZE_DIM))
                
                # 6. Save Image
                filename = f"real_val_{saved_count:04d}.jpg"
                filepath = os.path.join(OUTPUT_FOLDER, filename)
                cv2.imwrite(filepath, frame)
                
                if saved_count % 10 == 0:
                    print(f"Saved {filename}...")
                
                saved_count += 1

            frame_count += 1

        cap.release()
        cv2.destroyAllWindows()
        print(f"✅ Done! Extracted {saved_count} images.")

if __name__ == "__main__":
    extract_frames()