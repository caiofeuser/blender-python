import json
import math
import os
import random
import uuid


import bpy
from bpy_extras.object_utils import world_to_camera_view

SAMPLES_NUMBER = 3
X_RES = 640
Y_RES = 480
IS_OCLUSSION_ENABLE = True
BACKGROUND_PATH = './backgrounds'
MODELS_PATH = "./models"
RENDERS_PATH = './renders'
USE_GPU = True
CYCLES = 128
ENGINE = 'CYCLES'

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

# world nodes
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

    appended_objects = []
    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        data_to.objects = data_from.objects

    for obj in data_to.objects:
        if obj and obj.type == 'MESH':
            appended_objects.append(obj)
            scene.collection.objects.link(obj)

    if not appended_objects:
        print(f"No MESH objects found in {model}. Skipping.")
        continue

    active_model = appended_objects[0]

    # TODO: implement logic fot when we have more then one model per file => Assembly file
    active_model = appended_objects[0]
    if len(appended_objects) > 1:
        print(
            f"  Warning: File has {len(appended_objects)} objects. Only processing {active_model.name}.")

    print(f"  Processing object: {active_model.name}")

    bpy.context.view_layer.objects.active = active_model

    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    active_model.location = (0, 0, 0)
    active_model.rotation_euler = (0, 0, 0)
    active_model.scale = (0.066, 0.066, 0.066)

    bpy.context.view_layer.update()  # Make sure dimensions are calculated
    object_dimens = active_model.dimensions
    max_dimension = max(object_dimens)

    # get material that should be already applied manually
    mat = active_model.material_slots[0].material
    mat.use_nodes = True

    # set up camera
    camera.constraints.clear()  # remove any existing constraints on the
    camera.constraints.new(type='TRACK_TO')
    camera.constraints['Track To'].target = active_model
    camera.constraints['Track To'].track_axis = 'TRACK_NEGATIVE_Z'
    camera.constraints['Track To'].up_axis = 'UP_Y'

    # --- Occluder Setup (MODIFIED FOR SHAPE VARIETY) ---
    occluder = None
    shader_occ = None
    if IS_OCLUSSION_ENABLE:
        occluder_shapes = ['plane', 'cube', 'sphere', 'cylinder']
        chosen_shape = random.choice(occluder_shapes)

        if chosen_shape == 'plane':
            bpy.ops.mesh.primitive_plane_add(size=1)
        elif chosen_shape == 'cube':
            bpy.ops.mesh.primitive_cube_add(size=1)
        elif chosen_shape == 'sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=1)  # Spheres are added with radius
        elif chosen_shape == 'cylinder':
            # Cylinders have radius and depth
            bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=0.5)

        occluder = bpy.context.active_object
        occluder.name = "Occluder"
        mat_occ = bpy.data.materials.new(name="OccluderMaterial")
        occluder.data.materials.append(mat_occ)
        mat_occ.use_nodes = True
        shader_occ = mat_occ.node_tree.nodes.get("Principled BSDF")

    # nodes
    shader_node = mat.node_tree.nodes.get("Principled BSDF")

    for i in range(SAMPLES_NUMBER):

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

        # random camera position
        # 1. Pick random spherical coordinates
        distance = random.uniform(max_dimension * 3, max_dimension * 5.0)
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

        # occluder randomization
        if IS_OCLUSSION_ENABLE:
            if random.random() > 0.0:
                occluder.hide_render = False

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

                for c in occluder.constraints:
                    occluder.constraints.remove(c)
                track_to = occluder.constraints.new(type='TRACK_TO')
                track_to.target = camera
                track_to.track_axis = 'TRACK_NEGATIVE_Z'
                track_to.up_axis = 'UP_Y'

                occ_size = max_dimension * \
                    random.uniform(0.2, 0.7)
                occluder.scale = (occ_size, occ_size, 1)

                shader_occ.inputs["Base Color"].default_value = (
                    random.random(), random.random(), random.random(), 1)
                shader_occ.inputs["Roughness"].default_value = random.uniform(
                    0.1, 0.9)

        print({f'Generating images, current: {i}'})
        # rotate the model randomly
        active_model.rotation_euler.x = random.uniform(0, 2 * math.pi)
        active_model.rotation_euler.y = random.uniform(0, 2 * math.pi)
        active_model.rotation_euler.z = random.uniform(0, 2 * math.pi)
        mapping_node.inputs['Rotation'].default_value[2] = random.uniform(
            0, math.pi * 2)

        # update the matrix_world from the last shot
        bpy.context.view_layer.update()

        mesh_vertices = [v.co for v in active_model.data.vertices]
        matrix_world = active_model.matrix_world

        # Apply the global transformation to EVERY vertex
        global_coordinates = [matrix_world @ v for v in mesh_vertices]

        normalized_coordinates = [
            world_to_camera_view(scene=scene, obj=camera, coord=axis)
            for axis in global_coordinates
        ]

        visible_coordinates = [
            coord for coord in normalized_coordinates if coord.z > 0]

        x_values = [vector.x for vector in visible_coordinates]
        y_values = [vector.y for vector in visible_coordinates]

        min_x = min(x_values)
        max_x = max(x_values)
        min_y = min(y_values)
        max_y = max(y_values)

        denormalized_min_x = min_x * X_RES
        denormalized_min_y = min_y * Y_RES
        denormalized_max_x = max_x * X_RES
        denormalized_max_y = max_y * Y_RES

        width = denormalized_max_x - denormalized_min_x
        height = denormalized_max_y - denormalized_min_y

        file_name = f"{active_model.name}-{uuid.uuid4()}-{'occluded-' if IS_OCLUSSION_ENABLE else ''}v10.png"
        file_path = f"{RENDERS_PATH}/{file_name}"

        bpy.context.scene.render.filepath = file_path
        bpy.context.view_layer.objects.active = active_model
        bpy.ops.render.render(write_still=True)

        bb_data = {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "file_path": file_path,
            "file_name": file_name,
            "model_name": active_model.name
        }

        print(bb_data)
        export_json.append(bb_data)
        # Also delete any other leftover meshes from the append

    if IS_OCLUSSION_ENABLE:
        objs = bpy.data.objects
        objs.remove(objs["Occluder"], do_unlink=True)

    bpy.data.objects.remove(active_model, do_unlink=True)

with open('bb.json', 'w') as f:
    json.dump(export_json, f)

print("------- finished -------")
