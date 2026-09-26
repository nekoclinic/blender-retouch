import json
import os
import re
import zlib

import bpy

IGNORED_NODE_TYPES = {"IMAGE", "VIEWER", "GROUP_OUTPUT"}

# プリセットのバージョン
PRESET_FORMAT_VERSION = 1

# プリセットの最小サポートバージョン
MIN_SUPPORTED_PRESET_VERSION = 1


def is_valid_preset_version(preset_version) -> bool:
    try:
        int(preset_version)
    except (TypeError, ValueError):
        return False
    return True


def is_version_supported(preset_version: int, min_version: int = MIN_SUPPORTED_PRESET_VERSION) -> bool:
    try:
        return int(preset_version) >= int(min_version)
    except (TypeError, ValueError):
        return False


# --- パスとフォルダーの管理 ---


def get_preset_dir() -> str:
    addon_name = __name__.split(".")[0]

    base_dir = os.path.expanduser("~")

    # 設定された保存先を使い、未設定または無効な場合はユーザーホームへ戻します。
    try:
        prefs = bpy.context.preferences.addons.get(addon_name)
        if prefs and hasattr(prefs.preferences, "preset_prefs"):
            custom_dir = prefs.preferences.preset_prefs.custom_preset_dir
            if custom_dir:
                abs_custom_dir = bpy.path.abspath(custom_dir)
                if abs_custom_dir and os.path.exists(os.path.dirname(abs_custom_dir)):
                    base_dir = abs_custom_dir
    except Exception:
        pass

    preset_dir = os.path.join(base_dir, "blender-retouch_data", "presets")

    try:
        if not os.path.exists(preset_dir):
            os.makedirs(preset_dir, exist_ok=True)
    except Exception as e:
        print(f"Blender Retouch: Failed to create preset directory. {e}")

    return preset_dir


def normalize_folder(folder: str | None) -> str:
    folder = (folder or "").replace("\\", "/").strip("/")
    if folder == "presets":
        return ""
    return folder


def get_preset_extension() -> str:
    return ".brp"


def sanitize_preset_name(name: str) -> str:
    if not name:
        return "preset"

    # フォルダー階層は維持しつつ、各要素からパス移動に使える文字を取り除きます。
    parts = []
    for raw_part in str(name).replace("\\", "/").split("/"):
        if not raw_part or raw_part in {".", ".."}:
            continue
        safe_part = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_part).strip("._-")
        parts.append(safe_part or "preset")

    return "/".join(parts) if parts else "preset"


def get_preset_path(preset_name: str) -> str:
    safe_name = sanitize_preset_name(preset_name)
    preset_dir = get_preset_dir()

    if "/" in safe_name:
        folder_parts = safe_name.split("/")[:-1]
        file_name = safe_name.split("/")[-1]
        target_dir = os.path.join(preset_dir, *folder_parts)
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, f"{file_name}{get_preset_extension()}")

    return os.path.join(preset_dir, f"{safe_name}{get_preset_extension()}")


def get_preset_files(preset_dir: str) -> list[str]:
    if not os.path.isdir(preset_dir):
        return []
    preset_files = [f for f in os.listdir(preset_dir) if f.endswith(get_preset_extension()) and os.path.isfile(os.path.join(preset_dir, f))]
    return sorted(preset_files)


def get_subfolders(preset_dir: str) -> list[str]:
    if not os.path.isdir(preset_dir):
        return []
    return sorted(entry for entry in os.listdir(preset_dir) if os.path.isdir(os.path.join(preset_dir, entry)))


# --- ファイル入出力 ---


def write_preset_file(path: str, payload: dict) -> None:
    json_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressed_data = zlib.compress(json_bytes, level=6)
    with open(path, "wb") as handle:
        handle.write(compressed_data)


def load_preset_file(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        raw_data = handle.read()
    # 新形式は圧縮済みですが、旧形式の非圧縮 JSON も読み込めるようにします。
    try:
        json_bytes = zlib.decompress(raw_data)
    except zlib.error:
        json_bytes = raw_data
    try:
        return json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return None


# --- シリアライズとデシリアライズ ---


def serialize_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (tuple, list)):
        return [serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize_value(v) for k, v in value.items()}
    # Blender の Vector などは通常の JSON 型ではないため、利用可能な変換 API を順に試します。
    if hasattr(value, "to_list"):
        try:
            return [serialize_value(v) for v in value.to_list()]
        except Exception:
            pass
    if hasattr(value, "to_tuple"):
        try:
            return [serialize_value(v) for v in value.to_tuple()]
        except Exception:
            pass
    if hasattr(value, "__len__") and not hasattr(value, "bl_rna"):
        try:
            return [serialize_value(v) for v in value]
        except TypeError:
            return None
    return None


def serialize_curve_mapping(mapping) -> dict:
    if not mapping:
        return {}

    curves_data = []
    for curve in getattr(mapping, "curves", []):
        points = []
        for point in getattr(curve, "points", []):
            try:
                location = point.location
                points.append([float(location[0]), float(location[1])])
            except Exception:
                continue
        curves_data.append({"points": points})

    payload = {"type": "CurveMapping", "curves": curves_data}
    for attr in ("black_level", "white_level"):
        try:
            value = getattr(mapping, attr)
        except Exception:
            continue
        if value is None:
            continue
        try:
            payload[attr] = list(value)
        except TypeError:
            payload[attr] = value

    for attr in ("clip", "use_clip"):
        try:
            payload[attr] = bool(getattr(mapping, attr))
        except Exception:
            continue

    return payload


def serialize_node(node: bpy.types.Node) -> dict:
    data = {
        "name": node.name,
        "type": node.bl_idname,
        "label": node.label,
        "location": [node.location.x, node.location.y],
        "inputs": [],
        "properties": {},
    }

    for socket in node.inputs:
        default_value = getattr(socket, "default_value", None)
        data["inputs"].append(
            {
                "name": socket.name,
                "identifier": socket.identifier,
                "default_value": serialize_value(default_value),
            }
        )

    # 接続関係や読み取り専用値は復元対象ではないため、変更可能な設定だけを保存します。
    for prop in node.bl_rna.properties:
        if prop.identifier in {
            "name",
            "label",
            "location",
            "inputs",
            "outputs",
            "type",
            "parent",
            "id_data",
        }:
            continue
        try:
            value = getattr(node, prop.identifier)
        except Exception:
            continue
        if value is None:
            continue
        if prop.identifier == "mapping" and getattr(getattr(value, "bl_rna", None), "identifier", None) == "CurveMapping":
            data["properties"][prop.identifier] = serialize_curve_mapping(value)
            continue
        if prop.identifier.startswith("_") or prop.is_readonly:
            continue
        if hasattr(value, "bl_rna") and not isinstance(value, (str, int, float, bool)):
            continue
        if isinstance(value, (str, int, float, bool)):
            data["properties"][prop.identifier] = value
            continue
        serialized = serialize_value(value)
        if serialized is not None:
            data["properties"][prop.identifier] = serialized

    return data


def capture_preset(tree: bpy.types.NodeTree | None) -> dict:
    if tree is None:
        return {"version": PRESET_FORMAT_VERSION, "nodes": []}

    # 画像ノードなどは現在のシーンに依存するため、プリセットには含めません。
    return {
        "version": PRESET_FORMAT_VERSION,
        "nodes": [serialize_node(node) for node in tree.nodes if getattr(node, "bl_idname", None) and node.type not in IGNORED_NODE_TYPES],
    }


def restore_curve_mapping(mapping, data: dict) -> None:
    if not mapping or not isinstance(data, dict):
        return

    for attr in ("black_level", "white_level"):
        if attr not in data:
            continue
        try:
            setattr(mapping, attr, data[attr])
        except Exception:
            continue

    for attr in ("clip", "use_clip"):
        if attr in data:
            try:
                setattr(mapping, attr, bool(data[attr]))
            except Exception:
                continue

    # 保存時と現在の Blender でカーブ数が異なっても、共通する範囲だけを復元します。
    curves_data = data.get("curves", [])
    curves = getattr(mapping, "curves", None)
    if not curves or not curves_data:
        return

    count = min(len(curves), len(curves_data))
    for index in range(count):
        curve = curves[index]
        curve_data = curves_data[index]
        points_data = curve_data.get("points", [])

        if not points_data:
            continue

        for p_idx in range(len(curve.points) - 1, -1, -1):
            try:
                curve.points.remove(curve.points[p_idx])
            except Exception:
                pass

        for point_index, point_data in enumerate(points_data):
            try:
                x, y = float(point_data[0]), float(point_data[1])

                if point_index < len(curve.points):
                    curve.points[point_index].location = (x, y)
                else:
                    curve.points.new(x, y)
            except Exception:
                continue

    try:
        mapping.update()
    except Exception:
        pass


def restore_node_state(node: bpy.types.Node, node_data: dict) -> None:
    # ソケット識別子を優先し、形式の異なる古いプリセットにはソケット名で対応します。
    input_lookup = {socket.identifier: socket for socket in node.inputs}
    input_lookup.update({socket.name: socket for socket in node.inputs})

    for socket_data in node_data.get("inputs", []):
        socket = input_lookup.get(socket_data.get("identifier")) or input_lookup.get(socket_data.get("name"))
        if socket is None:
            continue
        if "default_value" in socket_data and socket_data["default_value"] is not None:
            try:
                if hasattr(socket, "default_value"):
                    socket.default_value = socket_data["default_value"]
            except Exception:
                pass

    for prop_name, value in node_data.get("properties", {}).items():
        if prop_name == "mapping" and isinstance(value, dict):
            try:
                restore_curve_mapping(getattr(node, prop_name, None), value)
            except Exception:
                continue
            continue
        try:
            setattr(node, prop_name, value)
        except Exception:
            continue


def get_preset_files(preset_dir: str) -> list[str]:
    if not os.path.isdir(preset_dir):
        return []

    preset_files = [
        filename for filename in os.listdir(preset_dir) if filename.endswith(".brp") and os.path.isfile(os.path.join(preset_dir, filename))
    ]
    return sorted(preset_files)
