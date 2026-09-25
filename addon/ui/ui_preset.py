import os

from bpy.types import Panel

from ..utils.preset import get_preset_dir, normalize_folder, get_subfolders, get_preset_files
from .ui_panel import RetouchPanelMixin


class RETOUCH_PT_preset(RetouchPanelMixin, Panel):
    bl_idname = "RETOUCH_PT_preset"
    bl_label = "Preset"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        retouch = context.scene.retouch

        outer = layout.column(align=False)

        self._draw_save_row(outer, retouch)

        preset_root = get_preset_dir()

        current_folder = normalize_folder(getattr(retouch, "retouch_preset_folder", ""))
        current_dir = self._resolve_current_dir(preset_root, current_folder)
        os.makedirs(current_dir, exist_ok=True)

        outer.separator(factor=1)
        self._draw_breadcrumbs(outer, current_folder)

        subfolders = get_subfolders(current_dir)
        preset_files = get_preset_files(current_dir)
        self._draw_browser(outer, current_folder, subfolders, preset_files)

    @staticmethod
    def _draw_save_row(layout, retouch):
        row = layout.row(align=True)
        row.scale_y = 1.2

        row.operator("retouch.save_preset", text="Save Preset", icon="NEWFOLDER")
        row.operator("retouch.import_preset", text="Import", icon="IMPORT")

    @staticmethod
    def _resolve_current_dir(preset_root, current_folder):
        if current_folder:
            return os.path.join(preset_root, current_folder)
        return preset_root

    def _draw_breadcrumbs(self, layout, current_folder):
        row = layout.row()

        crumb = row.row(align=True)
        crumb.alignment = "LEFT"
        crumb.scale_y = 0.5

        home_op = crumb.operator("retouch.open_preset_folder", text="Presets", emboss=False)
        home_op.folder_path = ""

        if current_folder:
            parts = current_folder.split("/")
            accum = ""
            for part in parts:
                accum = f"{accum}/{part}" if accum else part
                crumb.label(text="", icon="RIGHTARROW_THIN")
                seg_op = crumb.operator("retouch.open_preset_folder", text=part, emboss=False)
                seg_op.folder_path = accum

        action = row.row(align=True)
        action.alignment = "RIGHT"
        new_folder_op = action.operator("retouch.create_preset_folder", text="", icon="NEWFOLDER")
        new_folder_op.create_same_level = False

    def _draw_browser(self, layout, current_folder, subfolders, preset_files):
        if not subfolders and not preset_files and not current_folder:
            # layout.label(text="No presets yet", icon="INFO")
            return

        col = layout.column(align=False)

        if current_folder:
            parent = os.path.dirname(current_folder)
            up_row = col.row()
            up_row.scale_y = 1.1
            up_op = up_row.operator("retouch.open_preset_folder", text="...", icon="FILE_PARENT", emboss=False)
            up_op.folder_path = parent
            col.separator(factor=0.4)

        for entry in subfolders:
            sub_path = f"{current_folder}/{entry}" if current_folder else entry

            row = col.row()
            row.scale_y = 1.15

            left = row.row(align=True)
            left.alignment = "LEFT"
            open_op = left.operator("retouch.open_preset_folder", text=entry, icon="FILE_FOLDER", emboss=False)
            open_op.folder_path = sub_path

            right = row.row(align=True)
            right.alignment = "RIGHT"
            rename_op = right.operator("retouch.rename_preset_folder", text="", icon="GREASEPENCIL")
            rename_op.folder_path = sub_path
            delete_op = right.operator("retouch.delete_preset_folder", text="", icon="TRASH")
            delete_op.folder_path = sub_path

        if subfolders and preset_files:
            col.separator(factor=0.6)

        for filename in preset_files:
            base_name = os.path.splitext(filename)[0]
            preset_name = self._to_full_preset_name(current_folder, base_name)

            row = col.row()
            row.scale_y = 1.15

            left = row.row(align=True)
            left.alignment = "LEFT"
            left.label(text=base_name, icon="PRESET")

            right = row.row(align=True)
            right.alignment = "RIGHT"

            load_op = right.operator("retouch.load_preset", text="", icon="APPEND_BLEND")
            load_op.preset_name = preset_name

            export_op = right.operator("retouch.export_preset", text="", icon="EXPORT")
            export_op.preset_name = preset_name

            rename_op = right.operator("retouch.rename_preset", text="", icon="GREASEPENCIL")
            rename_op.preset_name = preset_name

            delete_op = right.operator("retouch.delete_preset", text="", icon="TRASH")
            delete_op.preset_name = preset_name

    @staticmethod
    def _to_full_preset_name(current_folder: str, base_name: str) -> str:
        if current_folder:
            return f"{current_folder}/{base_name}"
        return base_name


classes = (
    RETOUCH_PT_preset,
)

