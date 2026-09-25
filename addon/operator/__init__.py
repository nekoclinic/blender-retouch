import bpy

from . import add_nodes, preset_ops, template, toggle_nodes

classes = []
classes += add_nodes.classes
classes += preset_ops.classes
classes += template.classes
classes += toggle_nodes.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
