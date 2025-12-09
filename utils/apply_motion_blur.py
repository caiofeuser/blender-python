import cv2
import numpy as np
import random
import os
import sys
import glob


def apply_motion_blur(image_path, max_kernel_size=10):
    """
    Reads an image, applies AGGRESSIVE random motion blur, and overwrites it.
    """
    # 1. Read the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error reading {image_path} for blur")
        return

    # 2. Decide if we should blur (Increase chance to 100% temporarily for testing)
    if random.random() > 0.7:  # 70% chance to skip (30% chance to blur)
        return

    # 3. Generate a Motion Blur Kernel
    # Minimum size 10 makes it visible. Max 30 makes it strong.
    kernel_size = random.randint(10, max_kernel_size)

    # Kernel size must be odd
    if kernel_size % 2 == 0:
        kernel_size += 1

    kernel = np.zeros((kernel_size, kernel_size))

    # Random direction: Horizontal, Vertical, or Diagonal
    direction = random.choice(['h', 'v', 'd'])

    if direction == 'h':
        kernel[int((kernel_size-1)/2), :] = np.ones(kernel_size)
    elif direction == 'v':
        kernel[:, int((kernel_size-1)/2)] = np.ones(kernel_size)
    else:  # Diagonal
        np.fill_diagonal(kernel, 1)

    kernel /= kernel_size

    # 4. Apply the filter
    blurred = cv2.filter2D(img, -1, kernel)

    # 5. Overwrite the file
    cv2.imwrite(image_path, blurred)
    print(
        f"Applied {direction}-blur (size {kernel_size}) to {os.path.basename(image_path)}")


def apply_motion_blur_to_folder(folder_path, max_kernel_size=10):
    """
    Applies motion blur to all images in the specified folder.
    """
    # Supported image extensions
    image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']
    
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder_path, ext)))
    
    if not image_files:
        print(f"No images found in {folder_path}")
        return
    
    print(f"Found {len(image_files)} images in {folder_path}")
    print(f"Applying motion blur with max kernel size: {max_kernel_size}")
    
    for image_path in image_files:
        apply_motion_blur(image_path, max_kernel_size)
    
    print(f"\nProcessing complete!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_motion_blur.py <folder_path> [max_kernel_size]")
        print("Example: python apply_motion_blur.py renders/renders_auto_20251124_220241 30")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    max_kernel_size = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory")
        sys.exit(1)
    
    apply_motion_blur_to_folder(folder_path, max_kernel_size)
