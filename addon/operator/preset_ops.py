import os
import shutil

from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper, ImportHelper

from ..utils.compositor import ensure_compositor_nodes
from ..utils.preset import (
    sanitize_preset_name,
    capture_preset,
    normalize_folder,
    get_preset_path,
    write_preset_file,
    load_preset_file,
    restore_node_state,
    get_preset_dir,
    get_preset_extension,
    is_version_supported,
    is_valid_preset_version,
    MIN_SUPPORTED_PRESET_VERSION,
)


class RETOUCH_OT_save_preset(Operator):
    bl_idname = "retouch.save_preset"
    bl_label = "Save Preset"
    bl_description = "Save the current compositor node values as a preset"

    preset_name: StringProperty(name="Preset Name", default="")

    def invoke(self, context, event):
        self.preset_name = ""
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset_name", text="Name")

    def execute(self, context):
        scene = context.scene
        retouch_props = getattr(scene, "retouch", None)

        preset_name = sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        folder = normalize_folder(getattr(retouch_props, "retouch_preset_folder", ""))

        tree = ensure_compositor_nodes(scene)
        payload = capture_preset(tree)
        payload["name"] = preset_name
        target_path = get_preset_path(f"{folder}/{preset_name}" if folder else preset_name)
        write_preset_file(target_path, payload)

        if retouch_props and hasattr(retouch_props, "retouch_preset_name"):
            retouch_props.retouch_preset_name = ""

        self.report({"INFO"}, f"Saved preset: {preset_name}")
        return {"FINISHED"}


class RETOUCH_OT_load_preset(Operator):
    bl_idname = "retouch.load_preset"
    bl_label = "Load Preset"
    bl_description = "Load a saved compositor preset"
    bl_options = {"UNDO"}

    preset_name: StringProperty(name="Preset Name", default="")

    def execute(self, context):
        scene = context.scene
        preset_name = sanitize_preset_name(self.preset_name or getattr(getattr(scene, "retouch", None), "retouch_preset_name", ""))
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        tree = ensure_compositor_nodes(scene)
        path = get_preset_path(preset_name)
        payload = load_preset_file(path)
        if payload is None:
            self.report({"ERROR"}, f"Preset not found: {preset_name}")
            return {"CANCELLED"}

        preset_version = payload.get("version")
        version_warning = None
        # 古い形式を即座に拒否せず、復元可能な場合は警告付きで読み込みます。
        if preset_version is not None and not is_valid_preset_version(preset_version):
            version_warning = f"preset version {preset_version!r} is invalid or unrecognized"
        elif preset_version is not None and not is_version_supported(preset_version):
            version_warning = f"preset version {preset_version} is older than the minimum supported version {MIN_SUPPORTED_PRESET_VERSION}"

        node_lookup = {node.name: node for node in tree.nodes}
        restored_count = 0
        missing_nodes = []
        for node_data in payload.get("nodes", []):
            node_name = node_data.get("name")
            node = node_lookup.get(node_name)
            if node is None:
                missing_nodes.append(node_name)
                continue
            restore_node_state(node, node_data)
            restored_count += 1

        messages = []
        if version_warning:
            messages.append(version_warning)
        if missing_nodes:
            messages.append(f"{restored_count} nodes restored, {len(missing_nodes)} not found in scene: {', '.join(missing_nodes)}")

        if messages:
            self.report({"WARNING"}, f"Loaded preset: {preset_name} ({'; '.join(messages)})")
        else:
            self.report({"INFO"}, f"Loaded preset: {preset_name}")
        return {"FINISHED"}


class RETOUCH_OT_create_preset_folder(Operator):
    bl_idname = "retouch.create_preset_folder"
    bl_label = "Create Folder"
    bl_description = "Create a new preset folder"

    folder_name: StringProperty(name="Folder Name", default="")
    create_same_level: BoolProperty(default=False)

    def invoke(self, context, event):
        self.folder_name = ""
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "folder_name", text="Name")

    def execute(self, context):
        retouch_props = getattr(context.scene, "retouch", None)
        if retouch_props is None:
            return {"CANCELLED"}

        folder_name = sanitize_preset_name(self.folder_name)
        if not folder_name:
            self.report({"ERROR"}, "Folder name is empty.")
            return {"CANCELLED"}

        current_folder = normalize_folder(getattr(retouch_props, "retouch_preset_folder", ""))
        base_folder = current_folder
        if self.create_same_level:
            base_folder = os.path.dirname(current_folder) if current_folder else ""

        new_folder = f"{base_folder}/{folder_name}" if base_folder else folder_name
        target_dir = os.path.join(get_preset_dir(), *new_folder.split("/"))

        os.makedirs(target_dir, exist_ok=True)
        retouch_props.retouch_preset_folder = new_folder
        self.report({"INFO"}, f"Created folder: {folder_name}")
        return {"FINISHED"}


class RETOUCH_OT_open_preset_folder(Operator):
    bl_idname = "retouch.open_preset_folder"
    bl_label = "Open Folder"
    bl_description = "Open a preset folder"

    folder_path: StringProperty(default="")

    def execute(self, context):
        retouch_props = getattr(context.scene, "retouch", None)
        if retouch_props is None:
            return {"CANCELLED"}
        retouch_props.retouch_preset_folder = normalize_folder(self.folder_path)
        return {"FINISHED"}


class RETOUCH_OT_delete_preset_folder(Operator):
    bl_idname = "retouch.delete_preset_folder"
    bl_label = "Delete Folder"
    bl_description = "Delete a preset folder and everything inside it"

    folder_path: StringProperty(name="Folder Path", default="")
    confirmed: BoolProperty(default=False)

    def invoke(self, context, event):
        if self.confirmed:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Delete folder '{self.folder_path}'?", icon="ERROR")

    def execute(self, context):
        folder_path = normalize_folder(self.folder_path)
        if not folder_path:
            self.report({"ERROR"}, "Cannot delete the presets root folder.")
            return {"CANCELLED"}

        safe_path = sanitize_preset_name(folder_path)
        target_dir = os.path.join(get_preset_dir(), safe_path)

        if not os.path.isdir(target_dir):
            self.report({"WARNING"}, f"Folder not found: {folder_path}")
            return {"CANCELLED"}

        try:
            shutil.rmtree(target_dir)
        except Exception as e:
            self.report({"ERROR"}, f"Failed to delete folder: {e}")
            return {"CANCELLED"}

        retouch_props = getattr(context.scene, "retouch", None)
        if retouch_props is not None:
            current_folder = normalize_folder(getattr(retouch_props, "retouch_preset_folder", ""))
            if current_folder == folder_path or current_folder.startswith(f"{folder_path}/"):
                retouch_props.retouch_preset_folder = os.path.dirname(folder_path)

        self.report({"INFO"}, f"Deleted folder: {folder_path}")
        return {"FINISHED"}


class RETOUCH_OT_delete_preset(Operator):
    bl_idname = "retouch.delete_preset"
    bl_label = "Delete Preset"
    bl_description = "Delete a saved compositor preset"

    preset_name: StringProperty(name="Preset Name", default="")
    confirmed: BoolProperty(default=False)

    def invoke(self, context, event):
        if self.confirmed:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Delete preset '{self.preset_name}'?", icon="ERROR")

    def execute(self, context):
        preset_name = sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        path = get_preset_path(preset_name)
        if os.path.exists(path):
            os.remove(path)
            self.report({"INFO"}, f"Deleted preset: {preset_name}")
        else:
            self.report({"WARNING"}, f"Preset not found: {preset_name}")
        return {"FINISHED"}


class RETOUCH_OT_rename_preset(Operator):
    bl_idname = "retouch.rename_preset"
    bl_label = "Rename Preset"
    bl_description = "Rename a saved compositor preset"

    preset_name: StringProperty(name="Preset Name", default="")
    new_name: StringProperty(name="Rename", default="")

    def invoke(self, context, event):
        base_name = self.preset_name.rsplit("/", 1)[-1]
        self.new_name = base_name
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "new_name", text="Rename")

    def execute(self, context):
        preset_name = sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        new_base_name = sanitize_preset_name(self.new_name)
        if not new_base_name or "/" in new_base_name:
            self.report({"ERROR"}, "Invalid new name.")
            return {"CANCELLED"}

        source_path = get_preset_path(preset_name)
        if not os.path.exists(source_path):
            self.report({"ERROR"}, f"Preset not found: {preset_name}")
            return {"CANCELLED"}

        folder = preset_name.rsplit("/", 1)[0] if "/" in preset_name else ""
        new_preset_name = f"{folder}/{new_base_name}" if folder else new_base_name
        dest_path = get_preset_path(new_preset_name)

        if os.path.exists(dest_path):
            self.report({"ERROR"}, f"Preset already exists: {new_base_name}")
            return {"CANCELLED"}

        try:
            # 正常なプリセットは内容を更新して保存し直し、読めない場合はバイナリをそのまま移動します。
            payload = load_preset_file(source_path)
            if payload is not None and isinstance(payload, dict):
                payload["name"] = new_base_name
                write_preset_file(dest_path, payload)
                os.remove(source_path)
            else:
                shutil.move(source_path, dest_path)
        except Exception as e:
            self.report({"ERROR"}, f"Rename failed: {e}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Renamed preset to: {new_base_name}")
        return {"FINISHED"}


class RETOUCH_OT_rename_preset_folder(Operator):
    bl_idname = "retouch.rename_preset_folder"
    bl_label = "Rename Folder"
    bl_description = "Rename a preset folder"

    folder_path: StringProperty(name="Folder Path", default="")
    new_name: StringProperty(name="Rename", default="")

    def invoke(self, context, event):
        base_name = normalize_folder(self.folder_path).rsplit("/", 1)[-1]
        self.new_name = base_name
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "new_name", text="Rename")

    def execute(self, context):
        folder_path = normalize_folder(self.folder_path)
        if not folder_path:
            self.report({"ERROR"}, "Cannot rename the presets root folder.")
            return {"CANCELLED"}

        new_base_name = sanitize_preset_name(self.new_name)
        if not new_base_name or "/" in new_base_name:
            self.report({"ERROR"}, "Invalid new name.")
            return {"CANCELLED"}

        safe_path = sanitize_preset_name(folder_path)
        source_dir = os.path.join(get_preset_dir(), safe_path)
        if not os.path.isdir(source_dir):
            self.report({"ERROR"}, f"Folder not found: {folder_path}")
            return {"CANCELLED"}

        parent = folder_path.rsplit("/", 1)[0] if "/" in folder_path else ""
        new_folder_path = f"{parent}/{new_base_name}" if parent else new_base_name
        dest_dir = os.path.join(get_preset_dir(), *new_folder_path.split("/"))

        if os.path.exists(dest_dir):
            self.report({"ERROR"}, f"Folder already exists: {new_base_name}")
            return {"CANCELLED"}

        try:
            shutil.move(source_dir, dest_dir)
        except Exception as e:
            self.report({"ERROR"}, f"Rename failed: {e}")
            return {"CANCELLED"}

        retouch_props = getattr(context.scene, "retouch", None)
        if retouch_props is not None:
            current_folder = normalize_folder(getattr(retouch_props, "retouch_preset_folder", ""))
            if current_folder == folder_path:
                retouch_props.retouch_preset_folder = new_folder_path
            elif current_folder.startswith(f"{folder_path}/"):
                retouch_props.retouch_preset_folder = new_folder_path + current_folder[len(folder_path) :]

        self.report({"INFO"}, f"Renamed folder to: {new_base_name}")
        return {"FINISHED"}


class RETOUCH_OT_export_preset(Operator, ExportHelper):
    bl_idname = "retouch.export_preset"
    bl_label = "Export Preset"
    bl_description = "Export a preset .brp file"

    filename_ext = get_preset_extension()
    filter_glob: StringProperty(default="*.brp", options={"HIDDEN"})
    preset_name: StringProperty(default="", options={"HIDDEN"})

    def invoke(self, context, event):
        preset_name = sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        base_name = os.path.basename(os.path.normpath(preset_name)) or "preset"
        self.filepath = f"{base_name}{get_preset_extension()}"
        return super().invoke(context, event)

    def execute(self, context):
        preset_name = sanitize_preset_name(self.preset_name)
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        source_path = get_preset_path(preset_name)
        if not os.path.exists(source_path):
            self.report({"ERROR"}, f"Preset not found: {preset_name}")
            return {"CANCELLED"}

        filepath = self.filepath
        # 拡張子を省略しても .brp として保存できるように補います。
        if not filepath.lower().endswith(get_preset_extension()):
            filepath = f"{filepath}{get_preset_extension()}"

        try:
            with open(source_path, "rb") as src:
                payload = src.read()
            with open(filepath, "wb") as dst:
                dst.write(payload)
            self.report({"INFO"}, f"Exported preset: {preset_name}")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Export failed: {e}")
            return {"CANCELLED"}


class RETOUCH_OT_import_preset(Operator, ImportHelper):
    bl_idname = "retouch.import_preset"
    bl_label = "Import Preset"
    bl_description = "Import a preset .brp file"

    filename_ext = get_preset_extension()
    filter_glob: StringProperty(default="*.brp", options={"HIDDEN"})
    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        if not self.filepath.lower().endswith(get_preset_extension()):
            self.report({"ERROR"}, f"Only {get_preset_extension()} files are supported.")
            return {"CANCELLED"}

        try:
            payload = load_preset_file(self.filepath)
        except Exception as e:
            self.report({"ERROR"}, f"Failed to import preset: {e}")
            return {"CANCELLED"}

        preset_name = sanitize_preset_name(os.path.splitext(os.path.basename(self.filepath))[0])
        if not preset_name:
            self.report({"ERROR"}, "Preset name is empty.")
            return {"CANCELLED"}

        # ファイル名をプリセット名として採用し、現在開いているフォルダーへ保存します。
        payload["name"] = preset_name

        retouch_props = getattr(context.scene, "retouch", None)
        folder = normalize_folder(getattr(retouch_props, "retouch_preset_folder", ""))

        dest_path = get_preset_path(f"{folder}/{preset_name}" if folder else preset_name)
        write_preset_file(dest_path, payload)

        self.report({"INFO"}, f"Imported preset: {preset_name}")
        return {"FINISHED"}


classes = (
    RETOUCH_OT_save_preset,
    RETOUCH_OT_load_preset,
    RETOUCH_OT_create_preset_folder,
    RETOUCH_OT_open_preset_folder,
    RETOUCH_OT_delete_preset_folder,
    RETOUCH_OT_delete_preset,
    RETOUCH_OT_rename_preset,
    RETOUCH_OT_rename_preset_folder,
    RETOUCH_OT_export_preset,
    RETOUCH_OT_import_preset,
)
