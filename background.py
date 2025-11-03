import json
import math
import os
import random
import uuid


import bpy
from bpy_extras.object_utils import world_to_camera_view

SAMPLES_NUMBER = 400
X_RES = 640
Y_RES = 480
BACKGROUND_PATH = './backgrounds'
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


for item in range(0, SAMPLES_NUMBER):

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

    print({f'Generating images, current: {item}'})
    # update the matrix_world from the last shot
    bpy.context.view_layer.update()

    file_name = f"background-{uuid.uuid4()}v11.png"
    file_path = f"{RENDERS_PATH}/{file_name}"

    bpy.context.scene.render.filepath = file_path
    bpy.ops.render.render(write_still=True)

    # @TODO: fix model_name to prevent pos-processing to train YOLO
    bb_data = {
        "file_path": file_path,
        "file_name": file_name,
    }

    export_json.append(bb_data)
# Also delete any other leftover meshes from the append

with open("bb_fixed.json") as f:
    prev_data = json.load(f)


# with open('bb.json', 'w') as f:
#     json.dump(export_json, f)

print("------- finished -------")
