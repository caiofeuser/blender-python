import json
import math
import os
import random

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

SAMPLES_NUMBER = 2
X_RES = 640
Y_RES = 480
IS_OCLUSSION_ENABLE = False

# set the proper engine
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.scene.cycles.samples = 128
bpy.context.scene.render.resolution_x = X_RES
bpy.context.scene.render.resolution_y = Y_RES
bpy.context.scene.view_settings.look = 'AgX - High Contrast'

# set the active models
active_model = bpy.context.active_object
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
active_model.location = (0, 0, 0)
active_model.rotation_euler = (0, 0, 0)

# set the proper dimenions
active_model.scale[0] = 0.066
active_model.scale[1] = 0.066
active_model.scale[2] = 0.066

bpy.context.view_layer.update()  # Make sure dimensions are calculated
object_dimens = active_model.dimensions
max_dimension = max(object_dimens)


# load a random background
backgrounds_path = '/Users/caiofeuser/Documents/inspire/backgrounds'
backgrounds = os.listdir(backgrounds_path)


# set up world enviroment
scene = bpy.context.scene
world = scene.world
world.use_nodes = True
node_tree = world.node_tree
nodes = node_tree.nodes

# get material that should be already applied manually
mat = active_model.material_slots[0].material
mat.use_nodes = True

for node in nodes:
    nodes.remove(node)

# set up camera
camera = bpy.context.scene.camera
camera.constraints.clear()  # remove any existing constraints on the
camera.constraints.new(type='TRACK_TO')
camera.constraints['Track To'].target = active_model
camera.constraints['Track To'].track_axis = 'TRACK_NEGATIVE_Z'
camera.constraints['Track To'].up_axis = 'UP_Y'

if IS_OCLUSSION_ENABLE:
    bpy.ops.mesh.primitive_plane_add(size=1)
    occluder = bpy.context.active_object
    occluder.name = "Occluder"

    mat_occ = bpy.data.materials.new(name="OccluderMaterial")
    occluder.data.materials.append(mat_occ)
    mat_occ.use_nodes = True
    shader_occ = mat_occ.node_tree.nodes.get("Principled BSDF")


# nodes
background_node = nodes.new(type='ShaderNodeBackground')
env_texture_node = nodes.new(type='ShaderNodeTexEnvironment')
output_node = nodes.new(type='ShaderNodeOutputWorld')
texture_node = nodes.new(type="ShaderNodeTexCoord")
mapping_node = nodes.new(type="ShaderNodeMapping")
shader_node = mat.node_tree.nodes.get("Principled BSDF")

# linking all the nodes
node_tree.links.new(
    texture_node.outputs["Generated"], mapping_node.inputs["Vector"])
node_tree.links.new(
    mapping_node.outputs["Vector"], env_texture_node.inputs["Vector"])
node_tree.links.new(
    env_texture_node.outputs['Color'], background_node.inputs['Color'])
node_tree.links.new(
    background_node.outputs['Background'], output_node.inputs['Surface'])

export_json = []


for i in range(SAMPLES_NUMBER):

    # load a random image
    img_path = os.path.join(backgrounds_path, random.choice(backgrounds))
    img = bpy.data.images.load(img_path)
    env_texture_node.image = img
    print('Loaded image:', img_path)

    # light randomization
    background_node.inputs['Strength'].default_value = random.uniform(0.8, 2.5)

    # roughness randomization
    shader_node.inputs["Subsurface Weight"].default_value = random.uniform(
        0.0, 0.05)
    shader_node.inputs["Roughness"].default_value = random.uniform(0.3, 0.5)

    # random camera position
    # 1. Pick random spherical coordinates
    distance = random.uniform(max_dimension * 3, max_dimension * 5.0)
    phi = random.uniform(0, 2 * math.pi)  # Horizontal angle (0-360 deg)
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
        # e.g., 20% to 60% of the way to the camera
        t = random.uniform(0.2, 0.6)
        # t = random.uniform(0.2, 0)
        occluder.location = camera.location * t
        occ_size = max_dimension * random.uniform(0.5, 1.5)
        occluder.scale = (occ_size, occ_size, 1)

        # Random color and material
        shader_occ.inputs["Base Color"].default_value = (
            random.random(), random.random(), random.random(), 1)
        shader_occ.inputs["Roughness"].default_value = random.uniform(0.1, 0.9)

    print({f'Generating images, current: {i}'})
    # rotate the model randomly
    active_model.rotation_euler.x = random.uniform(0, 2 * math.pi)
    active_model.rotation_euler.y = random.uniform(0, 2 * math.pi)
    active_model.rotation_euler.z = random.uniform(0, 2 * math.pi)
    mapping_node.inputs['Rotation'].default_value[2] = random.uniform(
        0, math.pi * 2)

    # update the matrix_world from the last shot
    bpy.context.view_layer.update()

    actv_obj_bb = active_model.bound_box
    matrix_world = active_model.matrix_world

    global_coordinates = [matrix_world @ Vector(crd) for crd in actv_obj_bb]

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

    print({
        "x": denormalized_min_x,
        "width": width,
        "y": denormalized_min_y,
        "height": height
    })

    file_name = f"TesteBoundingBoxesD{active_model.name}-{i}-v7.png"
    file_path = f"/Users/caiofeuser/Documents/inspire/renders/{file_name}"

    bpy.context.scene.render.filepath = file_path
    bpy.context.view_layer.objects.active = active_model
    bpy.ops.render.render(write_still=True)

    bb_data = {
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "file_path": file_path,
        "file_name": file_name
    }

    export_json.append(bb_data)

with open('bb.json', 'w') as f:
    json.dump(export_json, f)


if IS_OCLUSSION_ENABLE:
    objs = bpy.data.objects
    objs.remove(objs["Occluder"], do_unlink=True)
