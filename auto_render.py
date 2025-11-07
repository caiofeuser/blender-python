import json
import math
import os
import random
import uuid


import bpy
from bpy_extras.object_utils import world_to_camera_view

SAMPLES_NUMBER = 5
X_RES = 640
Y_RES = 480
BACKGROUND_SAMPLES = int(SAMPLES_NUMBER*0.25)
IS_OCLUSSION_ENABLE = True
BACKGROUND_PATH = './backgrounds'
MODELS_PATH = "./models"
RENDERS_PATH = './renders'
USE_GPU = True
CYCLES = 128
# ENGINE = 'CYCLES'
ENGINE = 'BLENDER_EEVEE_NEXT'


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

    if not visible_coordinates:
        return None  # Object is not in view

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

    # Calculate pixel width and height for area
    width_px = (box_max_x - box_min_x)
    height_px = (box_max_y - box_min_y)
    area_px = width_px * height_px

    if area_px <= 0:
        return None  # Object is visible but outside the clamped frame

    return {
        'min_x': box_min_x,
        'max_x': box_max_x,
        'min_y': box_min_y,
        'max_y': box_max_y,
    }


def denormalize_coord(x1, x2, y1, y2):
    """"
    Denormalize the bounding box coordinates from (0-1) to pixel values based on the render resolution."""
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
    # ideally the more furthest distance would rely in the object size, but for the arms shots it's not
    trashhold_camera_distance = 100
    min_camera_distance = max_dimension * 3
    max_calculated_distance = max_dimension * 30
    max_camera_distance = max_calculated_distance if max_calculated_distance < trashhold_camera_distance else trashhold_camera_distance

    distance = random.uniform(
        min_camera_distance,
        max_camera_distance
    )

    # make sure that the obj always show in the render
    bpy.data.cameras["Camera"].clip_end = distance + 20

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

models = [f for f in os.listdir(MODELS_PATH) if f.endswith('.blend')]
print(f"Found {len(models)} .blend files to process.")

for model in models:
    print(f"--- Processing file: {model} ---")
    filepath = os.path.join(MODELS_PATH, model)

    # load the current blender file
    appended_objects = []
    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        data_to.objects = data_from.objects

    # append the mesh into the scene
    for obj in data_to.objects:
        if obj and obj.type == 'MESH':
            appended_objects.append(obj)
            scene.collection.objects.link(obj)

    if not appended_objects:
        print(f"No MESH objects found in {model}. Skipping.")
        continue

    # TODO: implement logic fot when we have more then one model per file => Assembly file
    active_model = appended_objects[0]
    if len(appended_objects) > 1:
        print(
            f"Warning: File has {len(appended_objects)} objects. Only processing {active_model.name}.")

    print(f"Processing object: {active_model.name}")

    # set the active object
    bpy.context.view_layer.objects.active = active_model

    # set origin to geometry center and the scale
    set_obj_to_origin(active_model)
    active_model.scale = (0.066, 0.066, 0.066)

    bpy.context.view_layer.update()  # Make sure dimensions are calculated
    object_dimens = active_model.dimensions
    max_dimension = max(object_dimens)

    # get material that should be already applied manually
    mat = active_model.material_slots[0].material
    mat.use_nodes = True

    # initial setup of the camera
    camera.constraints.clear()  # remove any existing constraints on the
    camera.constraints.new(type='TRACK_TO')
    camera.constraints['Track To'].target = active_model
    camera.constraints['Track To'].track_axis = 'TRACK_NEGATIVE_Z'
    camera.constraints['Track To'].up_axis = 'UP_Y'

    # nodes
    shader_node = mat.node_tree.nodes.get("Principled BSDF")
    index = 0

    while index < SAMPLES_NUMBER:
        # occluder setup
        occluder = None
        shader_occ = None
        # TODO: it's always the same occluder per model
        if IS_OCLUSSION_ENABLE:
            occluder = create_random_occluder()

        # setup background and lighting randomization
        setup_background_and_randomization(background_node, shader_node)
        # setup the camera position rotation
        camera_positioning()

        occluder.hide_render = True
        # occluder randomization
        if IS_OCLUSSION_ENABLE:
            randomChangeOclusion = random.uniform(0, 1)

            if randomChangeOclusion > 0.5:
                occluder.hide_render = False
                jitter_camera_occluder_position(occluder=occluder)

                for c in occluder.constraints:
                    occluder.constraints.remove(c)

                track_to = occluder.constraints.new(type='TRACK_TO')
                track_to.target = camera
                track_to.track_axis = 'TRACK_NEGATIVE_Z'
                track_to.up_axis = 'UP_Y'

                occ_size = max_dimension * \
                    random.uniform(0.2, 0.7)
                occluder.scale = (occ_size, occ_size, 1)

        print(
            {f'Generating images, current: {index} of {SAMPLES_NUMBER} from  {model}'})
        # rotate the model randomly
        active_model.rotation_euler.x = random.uniform(0, 2 * math.pi)
        active_model.rotation_euler.y = random.uniform(0, 2 * math.pi)
        active_model.rotation_euler.z = random.uniform(0, 2 * math.pi)
        mapping_node.inputs['Rotation'].default_value[2] = random.uniform(
            0, math.pi * 2)

        # update the matrix_world from the last shot
        bpy.context.view_layer.update()

        active_model_coord = get_2d_bounding_box(
            cam=camera, obj=active_model, scene=scene)

        denorm_coord_values = denormalize_coord(
            active_model_coord["min_x"],
            active_model_coord["max_x"],
            active_model_coord["min_y"],
            active_model_coord["max_y"]
        )

        occlusion_percentage = 0.0

        if IS_OCLUSSION_ENABLE and occluder.hide_render == False:
            occlusion_percentage = calculate_occlusion(
                target=active_model,
                occluder=occluder,
                cam=camera,
                scene=scene
            )

            # if occlusion is too high, skip this render
            if occlusion_percentage > 0.55:
                remove_occluder()
                continue

        index += 1

        width = denorm_coord_values["max_x"] - denorm_coord_values["min_x"]
        height = denorm_coord_values["max_y"] - denorm_coord_values["min_y"]

        file_name = f"{active_model.name}-{uuid.uuid4()}.png"
        file_path = f"{RENDERS_PATH}/{file_name}"

        bpy.context.scene.render.filepath = file_path
        bpy.context.view_layer.objects.active = active_model
        bpy.ops.render.render(write_still=True)

        background_data = {
            "min_x": active_model_coord["min_x"],
            "max_x": active_model_coord["max_x"],
            "min_y": active_model_coord["min_y"],
            "max_y": active_model_coord["max_y"],
            "file_path": file_path,
            "file_name": file_name,
            "model_name": active_model.name,
        }

        # print(bb_data)
        export_json.append(background_data)

        # Also delete any other leftover meshes from the append
        if IS_OCLUSSION_ENABLE:
            remove_occluder()

    bpy.data.objects.remove(active_model, do_unlink=True)


# Generate pure background images so we prevent so meuch false positives during training
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
        "min_x": None,
        "max_x": None,
        "min_y": None,
        "max_y": None,
    }

    export_json.append(background_data)


load_and_merge_previous_data(export_json)

print("------- finished -------")
