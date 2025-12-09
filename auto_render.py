import json
import math
import os
import random
import uuid
from mathutils import Vector
import datetime
import colorsys

import bpy
from bpy_extras.object_utils import world_to_camera_view


SAMPLES_NUMBER = 2  # number os samples to be generated
# x and y resolution
X_RES = 640
Y_RES = 480

# number of background samples to be generated based on the total samples
# BACKGROUND_SAMPLES = int(SAMPLES_NUMBER*0.005)
BACKGROUND_SAMPLES = 1

IS_OCLUSSION_ENABLE = True  # occlusion toggle

# file paths
BACKGROUND_PATH = "./backgrounds"
MODELS_PATH = "./models"
BASE_RENDERS_PATH = "./renders"
now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
RENDERS_PATH = f"{BASE_RENDERS_PATH}/renders_auto_{now}"

# rendering settings

USE_GPU = True  # GPU or CPU rendering
CYCLES = 512  # number of cycles
ENGINE = "CYCLES"  # BLENDER_EEVEE_NEXT or CYCLES

# multi object spawn settings
MIN_SPAWN_DISTANCE = 1
MAX_SPAWN_ATTEMPTS = 50

os.makedirs(RENDERS_PATH, exist_ok=True)


# set the proper engine
bpy.context.scene.render.engine = ENGINE
bpy.context.scene.cycles.device = "GPU" if USE_GPU else "CPU"
bpy.context.scene.cycles.samples = CYCLES
bpy.context.scene.render.resolution_x = X_RES
bpy.context.scene.render.resolution_y = Y_RES
bpy.context.scene.view_settings.look = "AgX - Very High Contrast"


# load a random background
backgrounds = os.listdir(BACKGROUND_PATH)
filered_backgrounds = []

for file in backgrounds:
    if file.endswith(".exr"):
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

    on_screen_coordinates = [
        p
        for p in visible_coordinates
        if p.x >= 0.0 and p.x <= 1.0 and p.y >= 0.0 and p.y <= 1.0
    ]

    if not on_screen_coordinates or not visible_coordinates:
        return None

    visibility_percent = len(on_screen_coordinates) / len(visible_coordinates)

    MIN_VISIBILITY_THRESHOLD = 0.15

    if visibility_percent < MIN_VISIBILITY_THRESHOLD:
        # 0.02 is less than 0.05, so this is a "sliver"
        print(
            f"Skipping {obj.name}: Only {visibility_percent*100:.1f}% of vertices are visible."
        )
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

    width_px = box_max_x - box_min_x
    height_px = box_max_y - box_min_y

    # Check width and height SEPARATELY
    if width_px <= 0 or height_px <= 0:
        return None

    return {
        "min_x": box_min_x,
        "max_x": box_max_x,
        "min_y": box_min_y,
        "max_y": box_max_y,
    }


def denormalize_coord(x1, x2, y1, y2):
    """ "
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
        "max_y": denormalized_max_y,
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

    target_area = (target_bb["max_x"] - target_bb["min_x"]) * (
        target_bb["max_y"] - target_bb["min_y"]
    )

    if not target_area:
        return 0.0  # Target is not visible

    # Calculate intersection
    xA = max(target_bb["min_x"], occluder_bb["min_x"])
    yA = max(target_bb["min_y"], occluder_bb["min_y"])
    xB = min(target_bb["max_x"], occluder_bb["max_x"])
    yB = min(target_bb["max_y"], occluder_bb["max_y"])

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
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)


def create_random_occluder():
    shape = random.choice(["plane", "cube", "sphere", "cylinder"])
    if shape == "plane":
        bpy.ops.mesh.primitive_plane_add(size=1)
    elif shape == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1)
    elif shape == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
    elif shape == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=0.5)
    occluder = bpy.context.active_object
    occluder.name = "Occluder"

    mat_occ = bpy.data.materials.new(name="OccluderMaterial")
    occluder.data.materials.append(mat_occ)
    mat_occ.use_nodes = True
    shader_occ = mat_occ.node_tree.nodes.get("Principled BSDF")

    shader_occ.inputs["Base Color"].default_value = (
        random.random(),
        random.random(),
        random.random(),
        1,
    )
    shader_occ.inputs["Roughness"].default_value = random.uniform(0.1, 0.9)

    return occluder


def remove_occluder():
    objs = bpy.data.objects
    objs.remove(objs["Occluder"], do_unlink=True)


def camera_positioning(cluster_max_dimension=10):
    # random camera position
    # 1. Pick random spherical coordinates
    # ideally the more furthest distance would rely in the object size,
    # but for the arms shots it's not
    trashhold_camera_distance = 50
    min_camera_distance = cluster_max_dimension * 2.5
    max_calculated_distance = cluster_max_dimension * 8
    max_camera_distance = (
        max_calculated_distance
        if max_calculated_distance < trashhold_camera_distance
        else trashhold_camera_distance
    )

    distance = random.triangular(
        min_camera_distance, max_camera_distance, min_camera_distance
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

    return distance


def setup_background_and_randomization(background_node, shader_node):
    # load random background
    img_path = os.path.join(
        BACKGROUND_PATH, random.choice(filered_backgrounds))
    img = bpy.data.images.load(img_path)
    env_texture_node.image = img

    # light randomization
    background_node.inputs["Strength"].default_value = random.uniform(0.8, 2.5)
    # roughness randomization
    shader_node.inputs["Subsurface Weight"].default_value = random.uniform(
        0.0, 0.05)
    shader_node.inputs["Roughness"].default_value = random.uniform(0.3, 0.5)


def jitter_camera_occluder_position(
    occluder, camera, scene_center, cluster_max_dimension
):
    """
    Places the occluder at a random point between the camera
    and the scene_center, with some random jitter.
    """

    # 1. Get a point 20-40% of the way from the camera *to the target*
    cam_loc = camera.location
    target_loc = scene_center.location
    t = random.uniform(0.2, 0.4)

    # Vector math: Point = A + (B - A) * t
    base_point_on_line = cam_loc + (target_loc - cam_loc) * t

    # 2. Get camera's "right" and "up" vectors
    cam_right_vec = camera.matrix_world.col[0].xyz
    cam_up_vec = camera.matrix_world.col[1].xyz

    # 3. Add random jitter based on the cluster size
    jitter_x_amount = random.uniform(
        -cluster_max_dimension * 0.7, cluster_max_dimension * 0.7
    )
    jitter_y_amount = random.uniform(
        -cluster_max_dimension * 0.7, cluster_max_dimension * 0.7
    )

    occluder.location = (
        base_point_on_line
        + (cam_right_vec * jitter_x_amount)
        + (cam_up_vec * jitter_y_amount)
    )


def check_visibility_raycast(obj, camera, scene, max_rays=100):
    """
    Casts rays from the camera to random vertices of the object.
    Returns a visibility ratio (0.0 to 1.0).
    0.0 = Fully Occluded (Invisible)
    1.0 = Fully Visible
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # Get mesh data with world transformations applied
    # We use a temporary evaluated object to get the actual shape in the scene
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.data
    matrix_world = obj.matrix_world
    cam_loc = camera.location

    # optimization: Don't check every single vertex, just a sample
    num_vertices = len(mesh.vertices)
    sample_indices = list(range(num_vertices))

    if num_vertices > max_rays:
        sample_indices = random.sample(sample_indices, max_rays)

    visible_points = 0
    total_points = len(sample_indices)

    for i in sample_indices:
        # Get global coordinate of the vertex
        v_loc = matrix_world @ mesh.vertices[i].co

        # Direction vector from Camera -> Vertex
        direction = v_loc - cam_loc
        distance = direction.length
        direction.normalize()

        # Cast the ray
        # We cast slightly shorter than the full distance to avoid self-intersection issues at the exact vertex point
        success, location, normal, index, hit_obj, matrix = scene.ray_cast(
            depsgraph,
            origin=cam_loc,
            direction=direction,
            distance=distance - 0.001,  # Stop slightly before the vertex
        )

        # Logic:
        # If we hit NOTHING (success=False), it means the path is clear to the vertex -> Visible
        # If we hit THE SAME OBJECT (hit_obj == obj), it's visible (self-intersection handled by distance check usually, but good safety)
        # If we hit SOMETHING ELSE, it's occluded.

        if not success:
            visible_points += 1
        elif hit_obj.name == obj.name:
            visible_points += 1

    return visible_points / total_points


def randomize_material_advanced(obj):
    """
    Generates DARK, GRITTY, and INDUSTRIAL colors.
    Eliminates pastel/candy colors by crushing the Value (Brightness).
    """
    if not obj.data.materials:
        return

    # --- 1. GENERATE DARK COLOR VALUES ---

    # HUE: Random
    h = random.random()

    # SATURATION: 0.0 (Grey) to 0.7 (Rich Color).
    # Avoids 0.8-1.0 which looks like "Candy/Neon".
    s = random.random()

    # VALUE (BRIGHTNESS): 0.05 (Almost Black) to 0.35 (Dark).
    # CRITICAL: Keeping this below 0.5 prevents "Pastel" looks.
    v = random.uniform(0.005, 0.2)

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    random_color = (r, g, b, 1.0)

    # Metallic: Dark metal is very common in industrial datasets
    if random.random() > 0.7:
        random_metallic = random.uniform(0.7, 1.0)
    else:
        random_metallic = 0.0

    # Noise/Grunge Params
    noise_scale = random.uniform(5.0, 40.0)

    # Roughness: Dark objects shouldn't be perfect mirrors, or they look grey.
    # We want matte darks or semi-glossy darks.
    rough_min = random.uniform(0.3, 0.6)
    rough_max = random.uniform(rough_min, 0.9)

    # --- 2. APPLY TO NODES ---
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not bsdf:
            continue

        base_color_socket = bsdf.inputs['Base Color']

        # --- TEXTURE LOGIC (DARKENING) ---
        if base_color_socket.is_linked:
            link = base_color_socket.links[0]
            prev_node = link.from_node

            # Find or Create Mix Node
            if prev_node.type == 'MIX_RGB' and prev_node.label == "AutoDarken":
                mix_node = prev_node
            else:
                mix_node = nodes.new('ShaderNodeMixRGB')
                mix_node.label = "AutoDarken"
                mix_node.blend_type = 'MULTIPLY'
                mix_node.location = (bsdf.location.x - 300, bsdf.location.y)

                # Connect: Texture -> MixRGB(Color1) -> BSDF
                prev_socket = link.from_socket
                links.new(prev_socket, mix_node.inputs[1])
                links.new(mix_node.outputs['Color'], base_color_socket)

            # Apply the DARK color to Input 2
            mix_node.inputs[2].default_value = random_color

            # FORCE HIGH FACTOR: 0.85 to 1.0
            # This ensures the texture gets heavily darkened by our color.
            # If this is 0.5, a white texture will still look light grey (pastel).
            mix_node.inputs['Fac'].default_value = random.uniform(0.85, 1.0)

        # --- FLAT COLOR LOGIC ---
        else:
            base_color_socket.default_value = random_color

        # --- METALLIC & ROUGHNESS ---
        bsdf.inputs['Metallic'].default_value = random_metallic

        # Grunge Setup (Noise -> Roughness)
        noise_tex = nodes.get("RandomNoise")
        if not noise_tex:
            noise_tex = nodes.new('ShaderNodeTexNoise')
            noise_tex.name = "RandomNoise"
            noise_tex.location = (bsdf.location.x - 600, bsdf.location.y - 200)

        color_ramp = nodes.get("RandomRamp")
        if not color_ramp:
            color_ramp = nodes.new('ShaderNodeValToRGB')
            color_ramp.name = "RandomRamp"
            color_ramp.location = (bsdf.location.x - 300,
                                   bsdf.location.y - 200)
            links.new(noise_tex.outputs['Fac'], color_ramp.inputs['Fac'])
            links.new(color_ramp.outputs['Color'], bsdf.inputs['Roughness'])

        noise_tex.inputs['Scale'].default_value = noise_scale

        # Set Roughness Ramp
        # Being darker, we can afford slightly higher roughness to avoid "wet" look
        color_ramp.color_ramp.elements[0].position = 0.0
        color_ramp.color_ramp.elements[0].color = (
            rough_min, rough_min, rough_min, 1)

        color_ramp.color_ramp.elements[1].position = 1.0
        color_ramp.color_ramp.elements[1].color = (
            rough_max, rough_max, rough_max, 1)


def create_random_lights(num_lights_to_add):
    """
    Creates a specified number of random Point or Area lights
    in the scene and returns a list of them for later cleanup.
    """
    created_lights = []
    for i in range(num_lights_to_add):
        # Choose light type
        light_type = random.choice(['POINT', 'AREA'])
        light_data = bpy.data.lights.new(
            name=f"RandomLight_{i}", type=light_type)

        # Randomize power
        if light_type == 'POINT':
            light_data.energy = random.uniform(100, 1000)
        else:  # AREA light
            light_data.energy = random.uniform(100, 3000)
            light_data.shape = 'SQUARE'
            light_data.size = random.uniform(0.5, 3.0)

        # Randomize color (slightly warm to slightly cool)
        light_data.color = (
            random.uniform(0.8, 1.0),
            random.uniform(0.8, 1.0),
            random.uniform(0.8, 1.0)
        )

        # Create the light object
        light_object = bpy.data.objects.new(
            name=f"RandomLightObj_{i}", object_data=light_data)

        # Place it randomly in the scene (always above Z=2 to act as studio lights)
        light_object.location = (
            random.uniform(-10, 10),
            random.uniform(-10, 10),
            random.uniform(2, 10)
        )

        # Add to scene and our tracking list
        scene.collection.objects.link(light_object)
        created_lights.append(light_object)

    return created_lights


def save_bboxes(new_data):
    os.makedirs('bboxes', exist_ok=True)
    path = f'bboxes/renders_auto_{now}.json'

    with open(path, 'w') as f:
        json.dump(new_data, f, indent=4)


background_node = nodes.new(type="ShaderNodeBackground")
env_texture_node = nodes.new(type="ShaderNodeTexEnvironment")
output_node = nodes.new(type="ShaderNodeOutputWorld")
texture_node = nodes.new(type="ShaderNodeTexCoord")
mapping_node = nodes.new(type="ShaderNodeMapping")

# linking all the nodes
node_tree.links.new(
    texture_node.outputs["Generated"], mapping_node.inputs["Vector"])
node_tree.links.new(
    mapping_node.outputs["Vector"], env_texture_node.inputs["Vector"])
node_tree.links.new(
    env_texture_node.outputs["Color"], background_node.inputs["Color"])
node_tree.links.new(
    background_node.outputs["Background"], output_node.inputs["Surface"]
)

# list that will be exported to json
export_json = []

all_model_files = [f for f in os.listdir(MODELS_PATH) if f.endswith(".blend")]
print(f"Found {len(all_model_files)} .blend files to use as models.")

count_dict = {model.replace(".blend", ""): 0 for model in all_model_files}

# It runs SAMPLES_NUMBER times, creating one unique scene per loop.
while min(count_dict.values()) < SAMPLES_NUMBER:

    bb_count = 0
    acc_bb_area = 0
    acc_distance = 0
    try:
        filteres_models = []
        for models in all_model_files:
            model_name = models.replace(".blend", "")
            if count_dict[model_name] < SAMPLES_NUMBER:
                filteres_models.append(models)
        num_objects = random.gauss(3, 2)
        # num_objects = 5  # remove later

        num_objects = max(1, int(num_objects))
        num_objects = min(num_objects, 15)
        num_objects = int(num_objects)

        num_to_sample = min(num_objects, len(filteres_models))
        models_to_load_paths = random.sample(filteres_models, num_to_sample)

        current_scene_objects = []  # Keep track of objects to delete later
        all_bb_data_for_this_image = []  # Store all BBs for this one image

        # 3. Load and place all chosen models
        for model_file in models_to_load_paths:
            filepath = os.path.join(MODELS_PATH, model_file)

            with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
                data_to.objects = [
                    name for name in data_from.objects if bpy.data.objects.get(name) is None
                ]

            all_dimensions = []
            for obj in data_to.objects:
                if obj and obj.type == "MESH":
                    obj.scale = (0.066, 0.066, 0.066)

                    is_position_safe = False
                    attempts = 0

                    while not is_position_safe and attempts < MAX_SPAWN_ATTEMPTS:
                        attempts += 1
                        is_position_safe = True  # Assume this spot is good

                        # 1. Get a new random trial position
                        trial_location = (
                            random.uniform(-10, 10),
                            random.uniform(-10, 10),
                            random.uniform(0, 5),
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
                                random.uniform(0, 2 * math.pi),
                            )
                            scene.collection.objects.link(obj)
                            current_scene_objects.append(obj)
                            all_dimensions.append(obj.dimensions)
                            # randomize color and roughness
                            randomize_material_advanced(obj)
                            break  # Exit the 'while' loop

                    if not is_position_safe:
                        print(
                            f"Warning: Could not find clear spot for {obj.name}. Skipping it."
                        )

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

        avg_location = Vector((0, 0, 0))
        for obj in current_scene_objects:
            avg_location += obj.location
        avg_location /= len(current_scene_objects)

        # 2. Move our "SceneCenter" Empty to that new average location
        scene_center.location = avg_location

        # 3. Calculate the "bounding box" of the entire cluster
        all_locations = [obj.location for obj in current_scene_objects]
        min_x = min(loc.x for loc in all_locations)
        max_x = max(loc.x for loc in all_locations)
        min_y = min(loc.y for loc in all_locations)
        max_y = max(loc.y for loc in all_locations)

        # Get the largest dimension of the spawn area
        cluster_width = max_x - min_x
        cluster_height = max_y - min_y
        max_cluster_dimension = max(cluster_width, cluster_height)

        # Add the size of the first object as a buffer
        # This prevents the camera from clipping if there's only one object
        max_cluster_dimension += max(current_scene_objects[0].dimensions)

        camera.constraints.clear()
        camera.constraints.new(type="TRACK_TO")
        camera.constraints["Track To"].target = scene_center
        camera.constraints["Track To"].track_axis = "TRACK_NEGATIVE_Z"
        camera.constraints["Track To"].up_axis = "UP_Y"

        bpy.context.view_layer.update()
        object_dimens = current_scene_objects[0].dimensions

        distance = camera_positioning()  # Your function should now work fine
        bpy.context.view_layer.update()

        active_scene_lights = create_random_lights(random.randint(1, 3))

        bpy.context.view_layer.update()
        furtherst_point = 0
        camera_location = camera.location
        for obj in current_scene_objects:
            distance = (obj.location - camera_location).length
            if distance > furtherst_point:
                furtherst_point = distance

        # 5. Set up Lighting
        # We need to find a shader_node, let's just use the first object's
        mat = current_scene_objects[0].material_slots[0].material
        shader_node = mat.node_tree.nodes.get("Principled BSDF")
        setup_background_and_randomization(background_node, shader_node)
        mapping_node.inputs["Rotation"].default_value[2] = random.uniform(
            0, math.pi * 2)

        # 6. Set up Occluder
        occluder = None
        max_dimentsion = max(object_dimens)
        if IS_OCLUSSION_ENABLE:
            occluder = create_random_occluder()
            occluder.hide_render = True
            occluder.hide_viewport = True

            if random.uniform(0, 1) > 0.5:
                occluder.hide_render = False
                occluder.hide_viewport = False
                jitter_camera_occluder_position(
                    occluder, camera, scene_center, max_cluster_dimension
                )

                occ_size = max_dimentsion * random.uniform(0.2, 0.7)

                # Set scale. We set Z scale to something small but non-zero
                # if it's a cube/sphere, or 1 if it's a plane.
                if occluder.data.name == "Plane":
                    occluder.scale = (occ_size, occ_size, 1)
                else:
                    # Make it a box/sphere
                    occluder.scale = (occ_size, occ_size, occ_size * 0.5)

        # 7. Get Bounding Boxes for ALL objects
        bpy.context.view_layer.update()

        furtherst_point = 0
        had_and_occluder_object = False
        for obj in current_scene_objects:
            bbox = get_2d_bounding_box(cam=camera, obj=obj, scene=scene)

            if len(current_scene_objects) > 1:
                visibility_ratio = check_visibility_raycast(obj, camera, scene)

            if not bbox:
                continue

            visibility_ratio = check_visibility_raycast(obj, camera, scene)

            if visibility_ratio < 0.2:
                had_and_occluder_object = True
                bbox = None
                print(
                    f"Skipping {obj.name}: only {visibility_ratio*100:.1f}% visible (Occluded)."
                )
                continue

            # Check occlusion against the main occluder
            occlusion_percentage = 0.0
            if IS_OCLUSSION_ENABLE and not occluder.hide_render:
                occlusion_percentage = calculate_occlusion(
                    target=obj, occluder=occluder, cam=camera, scene=scene
                )

            # Skip if the conditions is aren't met
            if occlusion_percentage > 0.75:
                print(
                    f"Skipping {obj.name}: {occlusion_percentage*100}% occluded.")
                continue

            if any(cord < 0 for cord in bbox.values()):
                print("Invalid, bounding box for {obj.name}, skipping.")
                continue

            height = bbox["max_y"] - bbox["min_y"]
            width = bbox["max_x"] - bbox["min_x"]
            area = width * height

            if area < 0.0002:
                print(
                    f"Invalid, bounding box too small, area = {area} for {obj.name}, skipping."
                )
                continue

            # make all the bb in the same object per image
            bb_data = {
                "min_x": bbox["min_x"],
                "max_x": bbox["max_x"],
                "min_y": bbox["min_y"],
                "max_y": bbox["max_y"],
                "model_name": obj.name.split(".")[0],  # Clean up name
                "distance_from_the_camera": (obj.location - camera.location).length,
                "camera_set_to": distance,
                "area": area,
                "obj_location": {
                    "x": obj.location.x,
                    "y": obj.location.y,
                    "z": obj.location.z,
                },
            }

            bb_count = bb_count + 1
            acc_bb_area = acc_bb_area + area
            acc_distance = acc_distance + distance

            all_bb_data_for_this_image.append(bb_data)

            distance = (obj.location - camera.location).length
            if distance > furtherst_point:
                furtherst_point = distance

            model_name_clean = obj.name.split(".")[0]

        # Check if it's a model we're tracking
        if model_name_clean in count_dict:
            count_dict[model_name_clean] += 1

        bpy.data.cameras["Camera"].clip_end = furtherst_point + 30

        # 8. Render the Scene
        if not all_bb_data_for_this_image:
            print("No objects were visible or passed occlusion. Skipping render.")

        file_name = f"scene-{uuid.uuid4()}.png"
        file_path = f"{RENDERS_PATH}/{file_name}"
        had_and_occluder_object = False
        bpy.context.scene.render.filepath = file_path
        bpy.ops.render.render(write_still=True)

        # 9. Save all BB data, pointing to the same file
        bb_data = {
            "file_path": file_path,
            "file_name": file_name,
            "bboxes": all_bb_data_for_this_image,
            "quantity": len(all_bb_data_for_this_image),
            "all_objects": [obj.name for obj in current_scene_objects],
        }
        if had_and_occluder_object:
            print(json.dumps(bb_data, indent=4))
        export_json.append(bb_data)

    finally:
        print("Cleaning up the scene for the next render...")
        # 1. Clean up Models
        for obj in current_scene_objects:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)

        # 2. Clean up Occluder
        if occluder and occluder.name in bpy.data.objects:
            bpy.data.objects.remove(occluder, do_unlink=True)

        # 3. Clean up Lights
        for light_obj in active_scene_lights:
            if light_obj.name in bpy.data.objects:
                light_data = light_obj.data
                bpy.data.objects.remove(
                    light_obj, do_unlink=True)  # Remove Object
                if light_data:
                    bpy.data.lights.remove(
                        light_data, do_unlink=True)  # Remove Data


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
    background_node.inputs["Strength"].default_value = random.uniform(0.8, 2.5)

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

avg_bb_area = acc_bb_area / bb_count
avg_distance = acc_distance / bb_count

export_json.append(
    {
        "statistics": {
            "average_bb_area": avg_bb_area,
            "average_distance_from_camera": avg_distance,
        }
    }
)


save_bboxes(export_json)

print("------- finished -------")
print(f"total counts: {count_dict}")
