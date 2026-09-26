import os

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from ..utils.compositor import (
    NODETREE_NAME,
    create_compositor_nodes,
    set_scene_resolution,
    find_or_create_image_node,
    connect_to_outputs,
    apply_retouch_to_scene,
)


class RETOUCH_OT_add_nodes(Operator, ImportHelper):
    bl_idname = "retouch.add_nodes"
    bl_label = "Load Image"
    bl_description = "Add nodes"
    bl_options = {"REGISTER", "UNDO"}

    filter_glob: StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.exr*;*.hdr;*.tga;*.dng",
        options={"HIDDEN"},
        maxlen=255,
    )
    filepath: StringProperty(
        name="File Path",
        description="Path to the selected image",
        subtype="FILE_PATH",
        maxlen=1024,
        default="",
    )

    def execute(self, context):
        if not self.filepath:
            self.report({"ERROR"}, "No image selected.")
            return {"CANCELLED"}

        # 「画像のみ」では新規ノードツリーを作り、それ以外では同梱テンプレートを適用します。
        if context.scene.retouch_image_only:
            try:
                image = bpy.data.images.load(self.filepath, check_existing=True)
                scene = context.scene
                node_tree = create_compositor_nodes(scene)

                img_node = find_or_create_image_node(node_tree, image.name)
                img_node.image = image

                set_scene_resolution(scene, image)
                connect_to_outputs(node_tree, img_node.outputs["Image"])

                self.report({"INFO"}, f"Loaded: {image.name}")
                return {"FINISHED"}

            except Exception as e:
                self.report({"ERROR"}, f"Load error: {e}")
                return {"CANCELLED"}

        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        blend_file_path = os.path.join(addon_dir, "assets", "node.blend")

        if not os.path.exists(blend_file_path):
            self.report({"ERROR"}, f"Template blend file not found: {blend_file_path}")
            return {"CANCELLED"}

        scene = apply_retouch_to_scene(self, context, self.filepath, blend_file_path, NODETREE_NAME)
        if scene is None:
            return {"CANCELLED"}
        return {"FINISHED"}


classes = (
    RETOUCH_OT_add_nodes,
)
