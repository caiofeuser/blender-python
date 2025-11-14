import json
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as ptc
import sys

# --- End of user settings ---


def draw_boxes_on_image(image_path, json_data_string):
    """
    Draws bounding boxes on an image using Matplotlib.
    """
    try:
        # --- 1. Parse JSON ---
        # Clean up the input string
        json_data_string = json_data_string.strip()
        if json_data_string.endswith(','):
            json_data_string = json_data_string[:-1]
        if not json_data_string.startswith('['):
            json_data_string = f"[{json_data_string}]"

        try:
            data = json.loads(json_data_string)
            print(f"Successfully parsed {len(data)} bounding box(es).")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON data: {e}")
            print("Data received for parsing:\n", json_data_string)
            return

        # --- 2. Load Image ---
        try:
            im = Image.open(image_path)
            res_x = im.width
            res_y = im.height
            print(
                f"Successfully loaded image: {image_path} (Width: {res_x}, Height: {res_y})")
        except FileNotFoundError:
            print(f"Error: Image file not found at '{image_path}'")
            print("Please check the IMAGE_PATH variable at the top of the script.")
            return
        except Exception as e:
            print(f"Error loading image: {e}")
            return

        # --- 3. Setup Matplotlib ---
        fig, ax = plt.subplots()
        # Use origin='lower' to match (0,0) at bottom-left
        ax.imshow(im, origin='lower')

        # --- 4. Draw Boxes ---
        for i, render in enumerate(data):
            try:
                min_x_norm = render["min_x"]
                max_x_norm = render["max_x"]
                min_y_norm = render["min_y"]
                max_y_norm = render["max_y"]
                model_name = render.get('model_name', f'Box {i}')

                # --- Use the correct logic from your working example ---
                x = min_x_norm * res_x
                y = (1 - max_y_norm) * res_y
                width = (max_x_norm - min_x_norm) * res_x
                height = (max_y_norm - min_y_norm) * res_y
                # ---

                print(
                    f"  - Drawing '{model_name}': x={x:.0f}, y={y:.0f}, w={width:.0f}, h={height:.0f}")

                rect = ptc.Rectangle((x, y), width, height, linewidth=1,
                                     edgecolor='r', facecolor="none")
                ax.add_patch(rect)

                # Add text label
                # ax.text(x + 5, y + 5, model_name,
                #         color='white', backgroundcolor='red',
                #         fontsize=8, ha='left', va='bottom')

            except KeyError as e:
                print(
                    f"Error: Your JSON object is missing an expected key: {e}")
            except Exception as e:
                print(f"Error processing a box: {e}")

        ax.set_title("Bounding Box Result")
        plt.show()

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# --- 2. RUN THE SCRIPT ---
def main():
    """
    Main function to get user input and run the visualizer.
    """
    print("--- Bounding Box Visualizer ---")
    print("You will need 'Pillow' and 'Matplotlib':")
    print("pip install Pillow matplotlib")

    # 1. Get Image Path
    image_path = input(
        "Enter the path to your image file (e.g., images/my_photo.jpg): ").strip()

    # 2. Get JSON data
    print("\nPaste your coordinate data below.")
    print("You can paste one or multiple objects.")
    print("When finished, type 'END' on a new line and press Enter:")

    json_lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == 'END':
                break
            json_lines.append(line)
        except EOFError:
            # This handles pasting and pressing Ctrl+Z (Windows) or Ctrl+D (Linux/macOS)
            break

    json_data_string = "\n".join(json_lines)

    if not image_path or not json_data_string:
        print("Error: Both image path and coordinate data are required.")
        return

    # 3. Process the image
    draw_boxes_on_image(image_path, json_data_string)
    print("--- Done ---")


if __name__ == "__main__":
    main()
