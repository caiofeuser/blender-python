import random
import bpy
import os
import math


# set the proper engine
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.scene.cycles.samples = 128
bpy.context.scene.render.resolution_x = 640
bpy.context.scene.render.resolution_y = 480
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
world = bpy.context.scene.world
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


for i in range(10):

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

    print({f'Generating images, current: {i}'})
    # rotate the model randomly
    active_model.rotation_euler.x = random.uniform(0, 2 * math.pi)
    active_model.rotation_euler.y = random.uniform(0, 2 * math.pi)
    active_model.rotation_euler.z = random.uniform(0, 2 * math.pi)
    mapping_node.inputs['Rotation'].default_value[2] = random.uniform(
        0, math.pi * 2)

    bpy.context.scene.render.filepath = f"/Users/caiofeuser/Documents/inspire/renders/D{active_model.name}-{i}-v5.png"
    bpy.ops.render.render(write_still=True)
