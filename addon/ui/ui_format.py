from bpy.types import Panel

from .ui_panel import RetouchPanelMixin


class RETOUCH_PT_format(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_format"
    bl_label = "Format Settings"
    bl_order = 0
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.prop(context.scene.render, "resolution_x", text="Resolution X")
        col.prop(context.scene.render, "resolution_y", text="Y")
        col.prop(context.scene.render, "resolution_percentage", text="%")

        col = layout.column(align=True)
        col.prop(context.scene.render, "pixel_aspect_x", text="Aspect X")
        col.prop(context.scene.render, "pixel_aspect_y", text="Y")


classes = (
    RETOUCH_PT_format,
)
