import json
import math
import os
import random
import uuid
from mathutils import Vector


import bpy
from bpy_extras.object_utils import world_to_camera_view


SAMPLES_NUMBER = 20  # number os samples to be generated
# x and y resolution
X_RES = 640
Y_RES = 480

# number of background samples to be generated based on the total samples
# BACKGROUND_SAMPLES = int(SAMPLES_NUMBER*0.005)
BACKGROUND_SAMPLES = 2

IS_OCLUSSION_ENABLE = True  # occlusion toggle

# file paths
BACKGROUND_PATH = './backgrounds'
MODELS_PATH = "./models"
RENDERS_PATH = './renders'

# rendering settings

USE_GPU = True  # GPU or CPU rendering
CYCLES = 128  # number of cycles
ENGINE = 'CYCLES'  # BLENDER_EEVEE_NEXT or CYCLES

# multi object spawn settings
MIN_SPAWN_DISTANCE = 1
MAX_SPAWN_ATTEMPTS = 50


# set the proper engine
bpy.context.scene.render.engine = ENGINE
bpy.context.scene.cycles.device = 'GPU' if USE_GPU else 'CPU'
bpy.context.scene.cycles.samples = CYCLES
bpy.context.scene.render.resolution_x = X_RES
bpy.context.scene.render.resolution_y = Y_RES
bpy.context.scene.view_settings.look = 'AgX - High Contrast'


# load a random background
backgrounds = os.listdir(BACKGROUND_PATH)
filered_backgrounds = []

for file in backgrounds:
    if file.endswith('.exr'):
        filered_backgrounds.append(file)

# set up world enviroment
scene = bpy.context.scene
world = scene.world
world.use_nodes = True
node_tree = world.node_tree
nodes = node_tree.nodes

# delete the initial cube
if bpy.context.active_object:
    bpy.ops.object.delete()

# clear possible nodes
for node in nodes:
    nodes.remove(node)

camera = bpy.context.scene.camera


def get_2d_bounding_box(obj, scene, cam):
    """
    Calculates the 2D bounding box and area of an object.

    Returns a dictionary {
        'min_x': (normalized 0-1),
        'max_x': (normalized 0-1),
        'min_y': (normalized 0-1),
        'max_y': (normalized 0-1),
    }
    or None if the object is not visible.
    """

    mesh_vertices = [v.co for v in obj.data.vertices]
    matrix_world = obj.matrix_world
    global_coordinates = [matrix_world @ v for v in mesh_vertices]

    normalized_coordinates = [
        world_to_camera_view(scene=scene, obj=cam, coord=axis)
        for axis in global_coordinates
    ]

    visible_coordinates = [
        coord for coord in normalized_coordinates if coord.z > 0]

    on_screen_coordinates = [p for p in visible_coordinates
                             if p.x >= 0.0 and p.x <= 1.0 and p.y >= 0.0 and p.y <= 1.0]

    if not on_screen_coordinates or not visible_coordinates:
        return None

    visibility_percent = len(on_screen_coordinates) / len(visible_coordinates)

    MIN_VISIBILITY_THRESHOLD = 0.1

    if visibility_percent < MIN_VISIBILITY_THRESHOLD:
        # 0.02 is less than 0.05, so this is a "sliver"
        print(
            f"Skipping {obj.name}: Only {visibility_percent*100:.1f}% of vertices are visible.")
        return None  # Skip the sliver

    x_values = [vector.x for vector in visible_coordinates]
    y_values = [vector.y for vector in visible_coordinates]

    # Get min/max in normalized (0-1) space
    min_x = min(x_values)
    max_x = max(x_values)
    min_y = min(y_values)
    max_y = max(y_values)

    # Clamp to screen edges (0.0 to 1.0)
    box_min_x = max(0.0, min_x)
    box_max_x = min(1.0, max_x)
    box_min_y = max(0.0, min_y)
    box_max_y = min(1.0, max_y)

    width_px = (box_max_x - box_min_x)
    height_px = (box_max_y - box_min_y)

    # Check width and height SEPARATELY
    if width_px <= 0 or height_px <= 0:
        return None

    return {
        'min_x': box_min_x,
        'max_x': box_max_x,
        'min_y': box_min_y,
        'max_y': box_max_y,
    }


def denormalize_coord(x1, x2, y1, y2):
    """"
    Denormalize the bounding box coordinates from (0-1) to pixel values based
    on the render resolution."""
    denormalized_min_x = x1 * X_RES
    denormalized_min_y = y1 * Y_RES
    denormalized_max_x = x2 * X_RES
    denormalized_max_y = y2 * Y_RES

    return {
        "min_x": denormalized_min_x,
        "max_x": denormalized_max_x,
        "min_y": denormalized_min_y,
        "max_y": denormalized_max_y
    }


def calculate_occlusion(target, occluder, cam, scene):
    """
    Calculate the occlusion percentage of the target object by the occluder from the camera's perspective.
    Returns a float between 0.0 (not occluded) and 1.0 (fully occluded).
    """
    target_bb = get_2d_bounding_box(target, scene, cam)
    occluder_bb = get_2d_bounding_box(occluder, scene, cam)

    if not target_bb or not occluder_bb:
        return 0.0

    target_area = (target_bb['max_x'] - target_bb['min_x']) * \
        (target_bb['max_y'] - target_bb['min_y'])

    if not target_area:
        return 0.0  # Target is not visible

    # Calculate intersection
    xA = max(target_bb['min_x'], occluder_bb['min_x'])
    yA = max(target_bb['min_y'], occluder_bb['min_y'])
    xB = min(target_bb['max_x'], occluder_bb['max_x'])
    yB = min(target_bb['max_y'], occluder_bb['max_y'])

    width = xB - xA
    height = yB - yA

    if width > 0 and height > 0:
        intersection_area = width * height
        return intersection_area / target_area
    else:
        return 0.0  # No occlusion

    # world nodes


def set_obj_to_origin(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)


def create_random_occluder():
    shape = random.choice(['plane', 'cube', 'sphere', 'cylinder'])
    if shape == 'plane':
        bpy.ops.mesh.primitive_plane_add(size=1)
    elif shape == 'cube':
        bpy.ops.mesh.primitive_cube_add(size=1)
    elif shape == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
    elif shape == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=0.5)
    occluder = bpy.context.active_object
    occluder.name = "Occluder"

    mat_occ = bpy.data.materials.new(name="OccluderMaterial")
    occluder.data.materials.append(mat_occ)
    mat_occ.use_nodes = True
    shader_occ = mat_occ.node_tree.nodes.get("Principled BSDF")

    shader_occ.inputs["Base Color"].default_value = (
        random.random(), random.random(), random.random(), 1)
    shader_occ.inputs["Roughness"].default_value = random.uniform(
        0.1, 0.9)

    return occluder


def remove_occluder():
    objs = bpy.data.objects
    objs.remove(objs["Occluder"], do_unlink=True)


def camera_positioning():
    # random camera position
    # 1. Pick random spherical coordinates
    # ideally the more furthest distance would rely in the object size,
    # but for the arms shots it's not
    trashhold_camera_distance = 100
    min_camera_distance = max_dimension * 2
    max_calculated_distance = max_dimension * 15
    max_camera_distance = max_calculated_distance if max_calculated_distance < trashhold_camera_distance else trashhold_camera_distance

    distance = random.triangular(
        min_camera_distance,
        max_camera_distance,
        min_camera_distance
    )
    # Horizontal angle (0-360 deg)
    phi = random.uniform(0, 2 * math.pi)
    # Vertical angle (10-80 deg)
    theta = random.uniform(math.radians(10), math.radians(80))

    # 2. Convert spherical to (X, Y, Z) for Blender
    cam_x = distance * math.sin(theta) * math.cos(phi)
    cam_y = distance * math.sin(theta) * math.sin(phi)
    cam_z = distance * math.cos(theta)

    # 3. Set the camera's location
    camera.location = (cam_x, cam_y, cam_z)
    camera.data.shift_x = random.uniform(-0.3, 0.3)
    camera.data.shift_y = random.uniform(-0.3, 0.3)


def setup_background_and_randomization(background_node, shader_node):
    # load random background
    img_path = os.path.join(
        BACKGROUND_PATH, random.choice(filered_backgrounds))
    img = bpy.data.images.load(img_path)
    env_texture_node.image = img

    # light randomization
    background_node.inputs['Strength'].default_value = random.uniform(
        0.8, 2.5)
    # roughness randomization
    shader_node.inputs["Subsurface Weight"].default_value = random.uniform(
        0.0, 0.05)
    shader_node.inputs["Roughness"].default_value = random.uniform(
        0.3, 0.5)


def jitter_camera_occluder_position(occluder):
    t = random.uniform(0.2, 0.4)
    base_point_on_line = camera.location * t

    cam_right_vec = camera.matrix_world.col[0].xyz
    cam_up_vec = camera.matrix_world.col[1].xyz

    jitter_x_amount = random.uniform(-max_dimension *
                                     0.7, max_dimension * 0.7)
    jitter_y_amount = random.uniform(-max_dimension *
                                     0.7, max_dimension * 0.7)

    occluder.location = base_point_on_line + \
        (cam_right_vec * jitter_x_amount) + \
        (cam_up_vec * jitter_y_amount)


def load_and_merge_previous_data(new_data):
    prev_data = []
    try:
        with open("bb.json", 'r') as f:
            prev_data = json.load(f)
            if not isinstance(prev_data, list):
                prev_data = []

        print(f"Loaded {len(prev_data)} previous bounding boxes.")

    except (FileNotFoundError, json.JSONDecodeError):
        # This block runs if the file doesn't exist OR is empty/corrupted
        print("bb.json not found or is empty. Starting a new one.")
        prev_data = []

    # --- The rest of your code is fine ---
    print(f"Adding {len(export_json)} new bounding boxes.")
    export_json.extend(prev_data)

    with open('bb.json', 'w') as f:
        json.dump(export_json, f, indent=4)  # Added indent=4 for readability


background_node = nodes.new(type='ShaderNodeBackground')
env_texture_node = nodes.new(type='ShaderNodeTexEnvironment')
output_node = nodes.new(type='ShaderNodeOutputWorld')
texture_node = nodes.new(type="ShaderNodeTexCoord")
mapping_node = nodes.new(type="ShaderNodeMapping")

# linking all the nodes
node_tree.links.new(
    texture_node.outputs["Generated"], mapping_node.inputs["Vector"])
node_tree.links.new(
    mapping_node.outputs["Vector"], env_texture_node.inputs["Vector"])
node_tree.links.new(
    env_texture_node.outputs['Color'], background_node.inputs['Color'])
node_tree.links.new(
    background_node.outputs['Background'], output_node.inputs['Surface'])

# list that will be exported to json
export_json = []

all_model_files = [f for f in os.listdir(MODELS_PATH) if f.endswith('.blend')]
print(f"Found {len(all_model_files)} .blend files to use as models.")

count_dict = {
    model.replace(".blend", ''): 0 for model in all_model_files
}

# It runs SAMPLES_NUMBER times, creating one unique scene per loop.
while min(count_dict.values()) < SAMPLES_NUMBER:

    filteres_models = []
    for models in all_model_files:
        model_name = models.replace(".blend", '')
        if count_dict[model_name] < SAMPLES_NUMBER:
            filteres_models.append(models)

    num_objects = random.gauss(3, 2)

    num_objects = max(1, int(num_objects))
    num_objects = min(num_objects, 15)
    num_objects = int(num_objects)

    num_to_sample = min(num_objects, len(filteres_models))
    models_to_load_paths = random.sample(
        filteres_models, num_to_sample)

    current_scene_objects = []  # Keep track of objects to delete later
    all_bb_data_for_this_image = []  # Store all BBs for this one image

    # 3. Load and place all chosen models
    for model_file in models_to_load_paths:
        filepath = os.path.join(MODELS_PATH, model_file)

        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            data_to.objects = [
                name for name in data_from.objects if bpy.data.objects.get(name) is None]

        for obj in data_to.objects:
            if obj and obj.type == 'MESH':
                obj.scale = (0.066, 0.066, 0.066)

                is_position_safe = False
                attempts = 0

                while not is_position_safe and attempts < MAX_SPAWN_ATTEMPTS:
                    attempts += 1
                    is_position_safe = True  # Assume this spot is good

                    # 1. Get a new random trial position
                    trial_location = (
                        random.gauss(5, 7),
                        random.gauss(5, 7),
                        random.uniform(0, 2)
                    )

                    # 2. Check it against all previously placed objects
                    for placed_obj in current_scene_objects:
                        distance = (Vector(trial_location) -
                                    placed_obj.location).length

                        if distance < MIN_SPAWN_DISTANCE:
                            is_position_safe = False  # This spot is too close
                            break  # Stop checking, try a new spot

                    # 3. If we looped all objects and it's still safe, we're done
                    if is_position_safe:
                        obj.location = trial_location
                        obj.rotation_euler = (
                            random.uniform(0, 2 * math.pi),
                            random.uniform(0, 2 * math.pi),
                            random.uniform(0, 2 * math.pi)
                        )
                        scene.collection.objects.link(obj)
                        current_scene_objects.append(obj)
                        break  # Exit the 'while' loop

                if not is_position_safe:
                    print(
                        f"Warning: Could not find clear spot for {obj.name}. Skipping it.")

                    bpy.data.objects.remove(obj, do_unlink=True)

    if not current_scene_objects:
        print("No models were loaded for this scene. Skipping.")
        continue

    # 4. Set up Camera
    # Create or get an Empty at the origin
    if "SceneCenter" not in bpy.data.objects:
        bpy.ops.object.empty_add(location=(0, 0, 0))
        bpy.context.active_object.name = "SceneCenter"
    scene_center = bpy.data.objects["SceneCenter"]

    camera.constraints.clear()
    camera.constraints.new(type='TRACK_TO')
    camera.constraints['Track To'].target = scene_center
    camera.constraints['Track To'].track_axis = 'TRACK_NEGATIVE_Z'
    camera.constraints['Track To'].up_axis = 'UP_Y'

    # Use the max_dimension of the first object to guide camera distance
    object_dimens = current_scene_objects[0].dimensions
    max_dimension = max(object_dimens)  # Use this for camera_positioning

    camera_positioning()  # Your function should now work fine
    bpy.context.view_layer.update()

    # 5. Set up Lighting
    # We need to find a shader_node, let's just use the first object's
    mat = current_scene_objects[0].material_slots[0].material
    shader_node = mat.node_tree.nodes.get("Principled BSDF")
    setup_background_and_randomization(background_node, shader_node)
    mapping_node.inputs['Rotation'].default_value[2] = random.uniform(
        0, math.pi * 2)

    # 6. Set up Occluder (This logic can be mostly the same)
    occluder = None
    if IS_OCLUSSION_ENABLE:
        occluder = create_random_occluder()
        occluder.hide_render = True

        if random.uniform(0, 1) > 0.5:
            occluder.hide_render = False
            jitter_camera_occluder_position(occluder=occluder)

            occ_size = max_dimension * random.uniform(0.2, 0.7)
            occluder.scale = (occ_size, occ_size, 1)

    # 7. Get Bounding Boxes for ALL objects
    bpy.context.view_layer.update()

    furtherst_point = 0
    for obj in current_scene_objects:
        bbox = get_2d_bounding_box(cam=camera, obj=obj, scene=scene)

        if not bbox:
            continue  # Object is not visible

        # Check occlusion against the main occluder
        occlusion_percentage = 0.0
        if IS_OCLUSSION_ENABLE and not occluder.hide_render:
            occlusion_percentage = calculate_occlusion(
                target=obj,
                occluder=occluder,
                cam=camera,
                scene=scene
            )

        # Skip if the conditions is aren't met
        if occlusion_percentage > 0.75:
            print(
                f"Skipping {obj.name}: {occlusion_percentage*100}% occluded.")
            continue

        if any(cord < 0 for cord in bbox.values()):
            print('Invalid, bounding box for {obj.name}, skipping.')
            continue

        height = bbox["max_y"] - bbox["min_y"]
        width = bbox["max_x"] - bbox["min_x"]
        area = width * height

        if area < 0.0002:
            print(
                f'Invalid, bounding box too small, area = {area} for {obj.name}, skipping.')
            continue

        # make all the bb in the same object per image
        bb_data = {
            "min_x": bbox["min_x"],
            "max_x": bbox["max_x"],
            "min_y": bbox["min_y"],
            "max_y": bbox["max_y"],
            "model_name": obj.name.split(".")[0],  # Clean up name
        }

        all_bb_data_for_this_image.append(bb_data)

        distance = (obj.location - camera.location).length
        if distance > furtherst_point:
            furtherst_point = distance

        count_dict[obj.name] = count_dict[obj.name] + 1

    bpy.data.cameras["Camera"].clip_end = furtherst_point + 30

    # 8. Render the Scene
    if not all_bb_data_for_this_image:
        print("No objects were visible or passed occlusion. Skipping render.")
        # Cleanup and continue
        for obj in current_scene_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        if occluder:
            remove_occluder()
        continue

    file_name = f"scene-{uuid.uuid4()}.png"
    file_path = f"{RENDERS_PATH}/{file_name}"

    bpy.context.scene.render.filepath = file_path
    bpy.ops.render.render(write_still=True)

    # 9. Save all BB data, pointing to the same file
    bb_data = {
        "file_path": file_path,
        "file_name": file_name,
        "bboxes": all_bb_data_for_this_image,
    }

    print(json.dumps(all_bb_data_for_this_image, indent=4))
    export_json.append(bb_data)

    # 10. Clean up the scene for the next loop
    for obj in current_scene_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    if occluder:
        remove_occluder()


# Generate pure background images so we prevent false positives during training
for background_sample in range(0, BACKGROUND_SAMPLES):
    camera.constraints.clear()
    # Random rotation for the camera in all axes
    camera.rotation_euler[0] = random.uniform(0, 2 * math.pi)  # X rotation
    camera.rotation_euler[1] = random.uniform(0, 2 * math.pi)  # Y rotation
    camera.rotation_euler[2] = random.uniform(0, 2 * math.pi)  # Z rotation

    # load random background
    img_path = os.path.join(
        BACKGROUND_PATH, random.choice(filered_backgrounds))
    img = bpy.data.images.load(img_path)
    env_texture_node.image = img

    # light randomization
    background_node.inputs['Strength'].default_value = random.uniform(
        0.8, 2.5)

    # update the matrix_world from the last shot
    bpy.context.view_layer.update()

    file_name = f"background-{uuid.uuid4()}.png"
    file_path = f"{RENDERS_PATH}/{file_name}"

    bpy.context.scene.render.filepath = file_path
    bpy.ops.render.render(write_still=True)

    background_data = {
        "file_path": file_path,
        "file_name": file_name,
        "model_name": "background",
        "bboxes": [],
    }

    export_json.append(background_data)


load_and_merge_previous_data(export_json)

print("------- finished -------")
print(f'total counts: {count_dict}')
