import bpy

from . import preferences
from ..utils.histogram import register as register_histogram_overlay
from ..utils.histogram import unregister as unregister_histogram_overlay

classes = []
classes += preferences.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_histogram_overlay()


def unregister():
    unregister_histogram_overlay()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
