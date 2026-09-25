import bpy
from . import ui_panel, ui_preset, ui_format

classes = []
classes += ui_panel.classes
classes += ui_preset.classes
classes += ui_format.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
