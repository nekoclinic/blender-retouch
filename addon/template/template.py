import hashlib
import os
import shutil

import bpy

TEMPLATE_NAME = "Blender Retouch"
MARKER_NAME = ".installed_by_blender_retouch"
MARKER_READ_ERROR = object()


def get_template_dir():
    user_scripts = bpy.utils.user_resource("SCRIPTS")
    return os.path.join(user_scripts, "startup", "bl_app_templates_user", TEMPLATE_NAME)


def _file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_marker(marker_path):
    if not os.path.isfile(marker_path):
        return None

    # マーカーは、このアドオンが管理しているテンプレートかを判定するために使います。
    try:
        with open(marker_path, "r") as f:
            lines = f.read().splitlines()
    except OSError:
        return MARKER_READ_ERROR

    if not lines:
        return MARKER_READ_ERROR
    installed_digest = lines[0].strip()
    source_digest = lines[1].strip() if len(lines) > 1 else ""
    return installed_digest, source_digest


def _install_atomically(src_blend, dst_blend, marker_path, src_digest):
    dst_existed = os.path.isfile(dst_blend)
    backup_path = dst_blend + ".bak" if dst_existed else None

    # 途中で失敗しても既存テンプレートを壊さないよう、バックアップと一時マーカーを使います。
    if dst_existed:
        shutil.copy(dst_blend, backup_path)

    try:
        shutil.copy(src_blend, dst_blend)
        digest = _file_digest(dst_blend)
        tmp_marker = marker_path + ".tmp"
        with open(tmp_marker, "w") as f:
            f.write(f"{digest}\n{src_digest}\n")
        os.replace(tmp_marker, marker_path)
    except OSError:
        if dst_existed:
            shutil.copy(backup_path, dst_blend)
        elif os.path.isfile(dst_blend):
            os.remove(dst_blend)
        raise
    finally:
        if backup_path and os.path.isfile(backup_path):
            os.remove(backup_path)


def install_app_template():
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_blend = os.path.join(addon_dir, "assets", "startup.blend")

    if not os.path.isfile(src_blend):
        print(f"[{TEMPLATE_NAME}] Error: startup.blend not found at '{src_blend}'")
        return False

    try:
        src_digest = _file_digest(src_blend)
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error reading bundled startup.blend: {e}")
        return False

    template_dir = get_template_dir()
    dst_blend = os.path.join(template_dir, "startup.blend")
    marker_path = os.path.join(template_dir, MARKER_NAME)

    if os.path.isfile(dst_blend):
        marker = _read_marker(marker_path)

        if marker is None:
            # 手動で配置されたテンプレートは所有権がないため、上書きしません。
            print(f"[{TEMPLATE_NAME}] Existing user startup.blend found at '{template_dir}', leaving it untouched.")
            return True

        if marker is MARKER_READ_ERROR:
            print(f"[{TEMPLATE_NAME}] Error reading ownership marker at '{marker_path}', leaving startup.blend untouched.")
            return False

        installed_digest, source_digest_at_install = marker
        try:
            current_digest = _file_digest(dst_blend)
        except OSError as e:
            print(f"[{TEMPLATE_NAME}] Error reading installed startup.blend: {e}")
            return False

        if installed_digest != current_digest:
            # インストール後にユーザーが編集した場合も、その変更を保護します。
            print(f"[{TEMPLATE_NAME}] startup.blend at '{template_dir}' was modified by the user, leaving it untouched.")
            return True

        if source_digest_at_install == src_digest:
            print(f"[{TEMPLATE_NAME}] Template already installed at '{template_dir}', skipping copy.")
            return True

        try:
            _install_atomically(src_blend, dst_blend, marker_path, src_digest)
            print(f"[{TEMPLATE_NAME}] Success: Template refreshed at '{template_dir}'")
            return True
        except OSError as e:
            print(f"[{TEMPLATE_NAME}] Error refreshing template: {e}")
            return False

    try:
        os.makedirs(template_dir, exist_ok=True)
        _install_atomically(src_blend, dst_blend, marker_path, src_digest)
        print(f"[{TEMPLATE_NAME}] Success: Template installed to '{template_dir}'")
        return True
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error installing template: {e}")
        return False


def uninstall_app_template():
    template_dir = get_template_dir()
    dst_blend = os.path.join(template_dir, "startup.blend")
    marker_path = os.path.join(template_dir, MARKER_NAME)

    if not os.path.isfile(dst_blend):
        print(f"[{TEMPLATE_NAME}] Warning: Template not found, nothing to uninstall.")
        return "missing"

    marker = _read_marker(marker_path)

    if marker is None:
        print(f"[{TEMPLATE_NAME}] Warning: startup.blend was not installed by this add-on, leaving it untouched.")
        return "not_owned"

    if marker is MARKER_READ_ERROR:
        print(f"[{TEMPLATE_NAME}] Error reading ownership marker at '{marker_path}'.")
        return "failed"

    installed_digest, _source_digest_at_install = marker
    try:
        current_digest = _file_digest(dst_blend)
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error verifying template ownership: {e}")
        return "failed"

    if installed_digest != current_digest:
        print(f"[{TEMPLATE_NAME}] Warning: startup.blend was modified since installation, leaving it untouched.")
        return "not_owned"

    try:
        os.remove(dst_blend)
        os.remove(marker_path)

        try:
            if not os.listdir(template_dir):
                os.rmdir(template_dir)
        except OSError:
            pass

        print(f"[{TEMPLATE_NAME}] Success: Template uninstalled.")
        return "removed"
    except OSError as e:
        print(f"[{TEMPLATE_NAME}] Error uninstalling template: {e}")
        return "failed"
