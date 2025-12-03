import cv2
import numpy as np
import random
import os


def apply_motion_blur(image_path, max_kernel_size=10):  # Increased from 10 to 30
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


if __name__ == "__main__":
    apply_motion_blur(
        "renders/renders_auto_20251124_220241/scene-7de571aa-5ec3-4b61-8aa8-c552911c5746.png")
