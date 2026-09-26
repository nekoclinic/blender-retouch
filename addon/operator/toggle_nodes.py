import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..utils.ui import get_nodes


class RETOUCH_OT_toggle_nodes(Operator):
    bl_idname = "retouch.toggle_nodes"
    bl_label = "Toggle Nodes"
    bl_options = {"REGISTER", "UNDO"}

    node_names: StringProperty(options={"HIDDEN"})

    def execute(self, context):
        nodes = get_nodes(context, self.node_names.split(","))
        if not nodes:
            return {"CANCELLED"}

        enabled = not all(node.mute is False for node in nodes)
        for node in nodes:
            node.mute = not enabled
        return {"FINISHED"}

classes = (
    RETOUCH_OT_toggle_nodes,
)