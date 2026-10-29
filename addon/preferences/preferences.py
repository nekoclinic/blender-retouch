import bpy
from bpy.types import AddonPreferences

from ... import __package__ as ADDON_MODULE_NAME, addon_updater_ops
from ..utils.histogram import (
    update_histogram_mode,
    update_histogram_resolution,
    update_histogram_settings,
    update_histogram_visibility,
)


@addon_updater_ops.make_annotations
class BRPreferences(AddonPreferences):
    bl_idname = ADDON_MODULE_NAME

    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True,
    )

    show_histogram_overlay = bpy.props.BoolProperty(
        name="Show Histogram",
        description="Show the histogram overlay in the Image Editor",
        default=True,
        update=update_histogram_visibility,
    )

    histogram_mode = bpy.props.EnumProperty(
        name="Histogram Mode",
        description="Display style of the histogram",
        items=(
            ("LINE", "Line", "Overlaid RGB and luma lines"),
            ("PARADE", "RGB Parade", "RGB parade waveform, R, G and B side by side (DaVinci Resolve style)"),
        ),
        default="LINE",
        update=update_histogram_mode,
    )

    histogram_width = bpy.props.IntProperty(
        name="Histogram Width",
        description="Width of the histogram overlay in pixels",
        default=276,
        min=180,
        max=800,
        update=update_histogram_settings,
    )

    histogram_height = bpy.props.IntProperty(
        name="Histogram Height",
        description="Height of the histogram overlay in pixels",
        default=140,
        min=80,
        max=600,
        update=update_histogram_settings,
    )

    histogram_opacity = bpy.props.FloatProperty(
        name="Histogram Opacity",
        description="Opacity of the histogram overlay",
        default=0.85,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
        update=update_histogram_settings,
    )

    histogram_resolution = bpy.props.IntProperty(
        name="Histogram Resolution",
        description="Number of histogram samples across the tonal range",
        default=128,
        min=32,
        max=256,
        step=32,
        update=update_histogram_resolution,
    )

    updater_interval_months = bpy.props.IntProperty(
        name="Months",
        description="Number of months between checking for updates",
        default=0,
        min=0,
    )

    updater_interval_days = bpy.props.IntProperty(
        name="Days",
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31,
    )

    updater_interval_hours = bpy.props.IntProperty(
        name="Hours",
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23,
    )

    updater_interval_minutes = bpy.props.IntProperty(
        name="Minutes",
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59,
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Histogram", icon="IMAGE_DATA")
        box.prop(self, "show_histogram_overlay")
        for prop in (
            "histogram_mode",
            "histogram_width",
            "histogram_height",
            "histogram_opacity",
            "histogram_resolution",
        ):
            row = box.row()
            row.enabled = self.show_histogram_overlay
            row.prop(self, prop)

        box = layout.box()
        box.label(text="Template", icon="FILE_BLEND")
        col = box.column(align=True)
        col.scale_y = 2
        col.operator("retouch.uninstall_template", icon="TRASH")

        # Works best if a column, or even just self.layout.
        mainrow = layout.row()
        col = mainrow.column()

        # Updater draw function, could also pass in col as third arg.
        addon_updater_ops.update_settings_ui(self, context)

        # Alternate draw function, which is more condensed and can be
        # placed within an existing draw function. Only contains:
        #   1) check for update/update now buttons
        #   2) toggle for auto-check (interval will be equal to what is set above)
        # addon_updater_ops.update_settings_ui_condensed(self, context, col)

        # Adding another column to help show the above condensed ui as one column
        # col = mainrow.column()
        # col.scale_y = 2
        # ops = col.operator("wm.url_open","Open webpage ")
        # ops.url=addon_updater_ops.updater.website


classes = (BRPreferences,)
