import bpy  # the main module
import math

# bpy.context  the current state of the user interaction
# bpt.data storage of blender objects, anything inside of there, is somehting that the user can view
# i.e: cameras, meshes, lights, etc.
# bpt.ops function that can be invked in the interfacem

# DRAW A BOUND BOX ARROUND THE SELECTED OBJECT
my_ac_object = bpy.context.active_object

active_vertices = my_ac_object.data.vertices

xV = []
yV = []
zV = []

for v in active_vertices:
    xV.append(v.co)
    yV.append(v.co)
    zV.append(v.co)

minX = min(xV)
minY = min(yV)
minZ = min(zV)

maxX = max(xV)
maxY = max(yV)
maxZ = max(zV)
