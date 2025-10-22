# Blender Python Scripts

A collection of Python scripts for automating rendering in Blender, with a focus on generating synthetic training data with randomized parameters.

## Features

- Automatic rendering with randomized parameters
- GPU-accelerated rendering using Cycles engine
- Random background image loading
- Camera position randomization
- Material and lighting adjustments
- Optional occlusion generation
- High-quality output configuration

## Requirements

- Blender 3.x
- Python 3.x
- Required Python packages:
  ```
  fake-bpy-module-latest==20251003
  ```

## Setup

1. Install Blender on your system
2. Create a Python virtual environment:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install requirements:
   ```sh
   pip install -r requirements.txt
   ```

## Usage

1. Open your 3D model in Blender
2. Ensure your model has at least one material assigned
3. Configure the script parameters in `auto_render.py`:
   - `SAMPLES_NUMBER`: Number of renders to generate
   - `X_RES`, `Y_RES`: Output resolution
   - `IS_OCLUSSION_ENABLE`: Toggle occlusion generation

4. Run the script in Blender's Python console or via command line:
   ```sh
   blender your_model.blend --python auto_render.py
   ```

## Configuration

- Default render settings:
  - Resolution: 640x480
  - Samples: 128
  - Color profile: AgX - High Contrast
  - Engine: Cycles (GPU)

## Output

Rendered images will be saved to the specified output directory with the following naming convention:
```
D{model_name}-{index}-v7.png
```

## License

This project is open-source. Feel free to use and modify as needed.