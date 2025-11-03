import json
import matplotlib.patches as ptc
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.widgets import Slider

with open("bb_fixed_with_bg.json") as f:
    data = json.load(f)


# Assuming 'data' is your list of render dictionaries
# data = [...]

# --- Create the Figure and Main Axes ---
fig, ax = plt.subplots()
# Adjust the plot to make room for the slider
plt.subplots_adjust(bottom=0.25)

# --- Define the Update Function ---
# This function will run every time the slider value changes


def update(slider_val):
    # Get the integer index from the slider
    index = int(slider_val)
    render = data[index]

    # Clear the axes to draw the new image
    ax.clear()

    try:
        im = Image.open(render["file_path"])

        res_x = im.width
        res_y = im.height

        ax.imshow(im, origin='lower')

        min_x_norm = render["min_x"]
        max_x_norm = render["max_x"]
        min_y_norm = render["min_y"]
        max_y_norm = render["max_y"]

        x = min_x_norm * res_x
        y = (1 - max_y_norm) * res_y
        width = (max_x_norm - min_x_norm) * res_x
        height = (max_y_norm - min_y_norm) * res_y

        rect = ptc.Rectangle((x, y), width, height, linewidth=1,
                             edgecolor='r', facecolor="none")

        ax.add_patch(rect)
        ax.set_title(f"Image Index: {index}")

    except FileNotFoundError:
        ax.set_title(f"Image Index: {index} (File Not Found)")
    except Exception as e:
        ax.set_title(f"Image Index: {index} (Error)")
        print(f"Error processing index {index}: {e}")

    # Redraw the figure
    fig.canvas.draw_idle()


# --- Create the Slider Widget ---
# Define the axes for the slider [left, bottom, width, height]
ax_slider = plt.axes([0.25, 0.1, 0.65, 0.03])

# Create the slider
slider = Slider(
    ax=ax_slider,
    label='Image Index',
    valmin=0,                  # Start index
    valmax=len(data) - 1,      # End index
    valinit=0,                 # Starting index
    valstep=1                  # Move one index at a time (integer steps)
)

# --- Connect the Slider to the Update Function ---
slider.on_changed(update)

# --- Show the First Image ---
# Call update() once manually to show the initial image
update(0)

# --- Show the Interactive Window ---
plt.show()
