import bpy
from . import (translations,
               ui,
               operator,
               scene,
               template,
               preferences)


modules = (
    translations,
    ui,
    operator,
    scene,
    template,
    preferences
)


def register():
    translations.register()
    for mod in modules:
        mod.register()


def unregister():
    for mod in reversed(modules):
        mod.unregister()