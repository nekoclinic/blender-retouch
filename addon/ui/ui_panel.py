from bpy.types import Panel

from ..utils.ui import nodes_toggle, get_node_or_input, get_node_prop_path, prop


class RetouchPanelMixin:
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_context = ""
    bl_category = "BLENDER RETOUCH"


class RETOUCH_PT_main(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_main"
    bl_label = "Blender Retouch"
    bl_order = 0

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.scale_y = 2.0
        row.operator("retouch.add_nodes", text="Load Image", icon="FILE_IMAGE")

        layout.prop(context.scene, "retouch_image_only")

        image_node = get_node_or_input(context, "Image")
        if image_node and image_node.bl_idname == "CompositorNodeImage" and image_node.image:
            layout.prop(image_node.image.colorspace_settings, "name", text="Color Space")


class RETOUCH_PT_light(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_light"
    bl_label = "Light"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 1

    def draw_header(self, context):
        self.layout.label(text="", icon="OUTLINER_DATA_LIGHT")

    def draw_header_preset(self, context):
        nodes_toggle(self.layout, context, ("Exposure", "Brightness/Contrast", "Color Correction"))

    def draw(self, context):
        layout = self.layout
        prop(layout, context, "Exposure", 1, "Exposure")
        prop(layout, context, "Brightness/Contrast", 2, "Contrast")
        prop(layout, context, "Color Correction", 10, "Highlight")
        prop(layout, context, "Color Correction", 20, "Shadow")
        prop(layout, context, "Color Correction", 9, "White Level")
        prop(layout, context, "Color Correction", 19, "Black Level")


class RETOUCH_PT_lift_gamma_gain(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_lift_gamma_gain"
    bl_label = "Lift/Gamma/Gain"
    bl_parent_id = RETOUCH_PT_light.bl_idname
    bl_order = 2
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header_preset(self, context):
        nodes_toggle(self.layout, context, ("Color Balance",))

    def draw(self, context):
        layout = self.layout
        prop(layout, context, "Color Balance", 3, "Lift")
        prop(layout, context, "Color Balance", 5, "Gamma")
        prop(layout, context, "Color Balance", 7, "Gain")


class RETOUCH_PT_curves(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_curves"
    bl_label = "RGB Curves"
    bl_parent_id = RETOUCH_PT_light.bl_idname
    bl_order = 3
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header_preset(self, context):
        nodes_toggle(self.layout, context, ("RGB Curves",))

    def draw(self, context):
        layout = self.layout
        if curves_node := get_node_or_input(context, "RGB Curves"):
            layout.template_curve_mapping(curves_node, "mapping", type="COLOR", show_tone=True)
        prop(layout, context, "RGB Curves", 1, "Factor")


class RETOUCH_PT_color(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color"
    bl_label = "Color"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 4

    def draw_header(self, context):
        self.layout.label(text="", icon="SHADING_RENDERED")

    def draw_header_preset(self, context):
        nodes_toggle(self.layout, context, ("Color Balance.001", "BR_Color", "Switch"))

    def draw(self, context):
        layout = self.layout
        prop(layout, context, "Switch", 0, "Monochrome")

        if wb_node := get_node_or_input(context, "Color Balance.001"):
            row = layout.row(align=True)
            row.label(text="White Balance")
            row.operator("ui.eyedropper_color", text="", icon="EYEDROPPER").prop_data_path = get_node_prop_path(context, wb_node, "input_whitepoint")

        prop(layout, context, "Color Balance.001", 15, "Temperature")
        prop(layout, context, "Color Balance.001", 16, "Tint")
        prop(layout, context, "BR_Color", 1, "Saturation")
        prop(layout, context, "BR_Color", 2, "Natural Saturation")


class RETOUCH_PT_hue_correct(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_hue_correct"
    bl_label = "Hue Correct"
    bl_parent_id = RETOUCH_PT_color.bl_idname
    bl_order = 5
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header_preset(self, context):
        nodes_toggle(self.layout, context, ("Hue Correct",))

    def draw(self, context):
        if curves_node := get_node_or_input(context, "Hue Correct"):
            self.layout.template_curve_mapping(curves_node, "mapping", type="HUE")


class RETOUCH_PT_color_balance(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_color_balance"
    bl_label = "Color Balance"
    bl_parent_id = RETOUCH_PT_color.bl_idname
    bl_order = 6
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header_preset(self, context):
        nodes_toggle(self.layout, context, ("Color Balance.002", "Mix"))

    def draw(self, context):
        layout = self.layout
        prop(layout, context, "Color Balance.002", 4, "Lift")
        prop(layout, context, "Color Balance.002", 6, "Gamma")
        prop(layout, context, "Color Balance.002", 8, "Gain")
        prop(layout, context, "Mix", 7, "Offset")
        prop(layout, context, "Color Balance.002", 1, "Strength")


class RETOUCH_PT_effect(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_effect"
    bl_label = "Effect"
    bl_parent_id = RETOUCH_PT_main.bl_idname
    bl_order = 7

    def draw_header(self, context):
        self.layout.label(text="", icon="RENDER_RESULT")

    def draw_header_preset(self, context):
        nodes_toggle(self.layout, context, ("BR_Effect", "Vignette", "Film Grain"))

    def draw(self, context):
        layout = self.layout
        retouch = context.scene.retouch

        row = layout.row(align=True)
        row.prop(retouch, "panel_tabs", expand=True)

        col = layout.column(align=True)
        tabs = retouch.panel_tabs

        if tabs == "Effects":
            prop(layout, context, "BR_Effect", 1, "Texture")
            prop(layout, context, "BR_Effect", 2, "Clarity")
        elif tabs == "Vignette":
            prop(col, context, "Vignette", 1, "Strength")
            prop(col, context, "Vignette", 2, "Feather")
            prop(col, context, "Vignette", 3, "Corner Roundness")
            prop(col, context, "Vignette", 4, "Scale")
        elif tabs == "Grain":
            prop(layout, context, "Film Grain", 1, "Strength")
            prop(layout, context, "Film Grain", 2, "")

            type_socket = get_node_or_input(context, "Film Grain", 2)
            if type_socket is not None and type_socket.default_value == "Custom":
                layout.prop(get_node_or_input(context, "Film Grain", 3), "default_value", text="Scale", expand=True)
                prop(layout, context, "Film Grain", 4, "Style")

            prop(layout, context, "Film Grain", 5, "Animated")

            custom_socket = get_node_or_input(context, "Film Grain", 4)
            if custom_socket is not None and custom_socket.default_value == "Custom Style" and type_socket.default_value == "Custom":
                prop(layout, context, "Film Grain", 6, "ISO")
                prop(layout, context, "Film Grain", 7, "Softness")
                prop(layout, context, "Film Grain", 8, "Acutance")
                prop(layout, context, "Film Grain", 9, "Coarseness")
                prop(layout, context, "Film Grain", 10, "Patchiness")
                prop(layout, context, "Film Grain", 11, "Saturation")
                prop(layout, context, "Film Grain", 12, "Luma bias")
                prop(layout, context, "Film Grain", 13, "Texture Scale")


classes = (
    RETOUCH_PT_main,
    RETOUCH_PT_light,
    RETOUCH_PT_curves,
    RETOUCH_PT_lift_gamma_gain,
    RETOUCH_PT_color,
    RETOUCH_PT_hue_correct,
    RETOUCH_PT_color_balance,
    RETOUCH_PT_effect,
)
