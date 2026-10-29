import time

import numpy as np
import bpy
import blf
import gpu
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader

from ... import __package__ as ADDON_MODULE_NAME


HISTOGRAM_BINS = 128
MAX_SAMPLE_DIMENSION = 512
MAX_PIXEL_BUFFER_BYTES = 512 * 1024 * 1024
MIN_INTERVAL = 1.0 / 30.0
LIVE_UPDATE_IDLE = 0.025
HIST_HEADROOM = 1
WAVE_COLUMNS = 256
WAVE_GAIN = 32.0
SCALE_MAX = 1023  # DaVinci Resolve と同じ10bitコード値表示
SCALE_TICKS = (0, 256, 512, 768, 1023)

CHANNEL_COLORS = (
    (1.0, 0.18, 0.16),
    (0.2, 0.95, 0.28),
    (0.2, 0.48, 1.0),
    (1.0, 1.0, 1.0),
)

_LUMA = np.array((0.2126, 0.7152, 0.0722), dtype=np.float32)

_batches = None  # None=画像なし / ()=ピークなし / tuple=描画用
_force = True
_trailing = False
_last_time = 0.0
_last_update_request = 0.0
_visible = True
_registered = False
_draw_handler = None
_shader = None
_rect_batch = None
_grid_batch = None
_vgrid_batch = None
_pixel_buffer = None
_waveforms = None
_image_shader = None
_image_batch = None


def _get_addon_preferences(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(ADDON_MODULE_NAME)
    return addon.preferences if addon else None


def _tag_image_editors() -> None:
    wm = bpy.context.window_manager
    if wm is None:
        return
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.tag_redraw()


def _kick() -> None:
    """再計算を要求し、変更中は30fpsで追従再描画する。"""
    global _force, _last_update_request
    _force = True
    _last_update_request = time.monotonic()
    _tag_image_editors()
    if _registered and not bpy.app.timers.is_registered(_live_update_tick):
        bpy.app.timers.register(_live_update_tick, first_interval=MIN_INTERVAL)


def _live_update_tick():
    global _force
    if not _registered or not is_histogram_visible():
        return None
    _force = True
    _tag_image_editors()
    if time.monotonic() - _last_update_request >= LIVE_UPDATE_IDLE:
        return None
    return MIN_INTERVAL


def update_histogram_settings(self, context) -> None:
    _tag_image_editors()


def update_histogram_resolution(self, context) -> None:
    request_histogram_update()


def update_histogram_mode(self, context) -> None:
    request_histogram_update()


def update_histogram_visibility(self, context) -> None:
    global _batches
    if self.show_histogram_overlay:
        _kick()
    else:
        _batches = None
        _tag_image_editors()


def request_histogram_update(delay: float = 0.0) -> None:
    _kick()


def is_histogram_visible() -> bool:
    settings = _get_addon_preferences()
    return getattr(settings, "show_histogram_overlay", _visible)


def toggle_histogram() -> None:
    global _visible
    settings = _get_addon_preferences()
    if settings is not None:
        settings.show_histogram_overlay = not settings.show_histogram_overlay
        return
    _visible = not _visible
    if _visible:
        _kick()
    else:
        _tag_image_editors()


def _encode_srgb(v):
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(v, 1.0 / 2.4) - 0.055)


def _sample_image(image: bpy.types.Image):
    """画像を間引きサンプリングして (h, w, 3) の float32 を返す。"""
    global _pixel_buffer
    width, height = image.size
    if width <= 0 or height <= 0:
        return None

    step_x = max(1, (width + MAX_SAMPLE_DIMENSION - 1) // MAX_SAMPLE_DIMENSION)
    step_y = max(1, (height + MAX_SAMPLE_DIMENSION - 1) // MAX_SAMPLE_DIMENSION)
    size = width * height * 4

    if size * 4 <= MAX_PIXEL_BUFFER_BYTES:
        if _pixel_buffer is None or _pixel_buffer.size != size:
            _pixel_buffer = np.empty(size, dtype=np.float32)
        image.pixels.foreach_get(_pixel_buffer)
        rgb = _pixel_buffer.reshape(height, width, 4)[::step_y, ::step_x, :3]
    else:
        _pixel_buffer = None
        rows = [
            np.asarray(image.pixels[y * width * 4 : (y + 1) * width * 4], dtype=np.float32).reshape(width, 4)[::step_x, :3]
            for y in range(0, height, max(step_y, (height + 63) // 64))
        ]
        rgb = np.stack(rows)

    return np.nan_to_num(rgb, nan=0.0, posinf=1.0, neginf=0.0)


def _histograms_from_rgb(rgb, bins: int):
    flat = rgb.reshape(-1, 3)
    values = np.concatenate((flat, (flat @ _LUMA)[:, None]), axis=1)
    values = _encode_srgb(np.clip(values, 0.0, 1.0))
    idx = np.clip((values * bins).astype(np.int32), 0, bins - 1)
    return tuple(tuple(np.bincount(idx[:, c], minlength=bins).tolist()) for c in range(4))


def calculate_histogram(image: bpy.types.Image, bins: int = HISTOGRAM_BINS):
    rgb = _sample_image(image)
    if rgb is None:
        return None
    return _histograms_from_rgb(rgb, bins)


def _build_waveforms(rgb, bins: int):
    """RGBパレード波形: 横=画像の列, 縦=値, 明るさ=密度 のテクスチャをチャンネルごとに作る。"""
    height, width, _ = rgb.shape
    col_step = max(1, (width + WAVE_COLUMNS - 1) // WAVE_COLUMNS)
    rgb = rgb[:, ::col_step]
    width = rgb.shape[1]

    encoded = _encode_srgb(np.clip(rgb, 0.0, 1.0))
    idx = np.clip((encoded * bins).astype(np.int32), 0, bins - 1)
    cols = np.arange(width, dtype=np.int32)[None, :]
    gain = WAVE_GAIN * bins / (HISTOGRAM_BINS * max(height, 1))

    textures = []
    for c in range(3):
        flat = (idx[:, :, c] * width + cols).ravel()
        counts = np.bincount(flat, minlength=bins * width).reshape(bins, width)
        rgba = np.empty((bins, width, 4), dtype=np.float32)
        rgba[..., 0] = CHANNEL_COLORS[c][0]
        rgba[..., 1] = CHANNEL_COLORS[c][1]
        rgba[..., 2] = CHANNEL_COLORS[c][2]
        rgba[..., 3] = 1.0 - np.exp(-counts * gain)
        buf = gpu.types.Buffer("FLOAT", width * bins * 4, rgba.ravel().tolist())
        textures.append(gpu.types.GPUTexture((width, bins), format="RGBA32F", data=buf))
    return tuple(textures)


def _ensure_static_batches() -> None:
    global _shader, _rect_batch, _grid_batch, _vgrid_batch, _image_shader, _image_batch
    if _shader is not None:
        return
    _shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    _image_shader = gpu.shader.from_builtin("IMAGE_COLOR")
    _image_batch = batch_for_shader(
        _image_shader,
        "TRI_FAN",
        {
            "pos": ((0, 0), (1, 0), (1, 1), (0, 1)),
            "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
        },
    )
    _rect_batch = batch_for_shader(_shader, "TRI_FAN", {"pos": ((0, 0), (1, 0), (1, 1), (0, 1))})
    hgrid = []
    vgrid = []
    for code in SCALE_TICKS:
        t = code / SCALE_MAX
        hgrid += [(0.0, t), (1.0, t)]
        vgrid += [(t, 0.0), (t, 1.0)]
    _grid_batch = batch_for_shader(_shader, "LINES", {"pos": hgrid})
    _vgrid_batch = batch_for_shader(_shader, "LINES", {"pos": vgrid})


def _build_batches(histograms):
    smoothed = []
    for histogram in histograms:
        values = np.asarray(histogram, dtype=np.float32)
        if not values.size:
            smoothed.append(values)
            continue
        sigma = len(histogram) / HISTOGRAM_BINS
        radius = max(1, int(np.ceil(3 * sigma)))
        offsets = np.arange(-radius, radius + 1, dtype=np.float32)
        kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
        kernel /= kernel.sum()
        padded = np.pad(values, radius, mode="edge")
        smoothed.append(np.convolve(padded, kernel, mode="valid"))

    if not any(float(np.max(h)) > 0 for h in smoothed if len(h)):
        return ()
    inv_span = 1.0 / max(len(smoothed[0]) - 1, 1)
    lines = []
    for h in smoothed:
        inner_peak = float(np.max(h[1:-1])) if len(h) > 2 else 0
        peak = inner_peak or (float(np.max(h)) if len(h) else 0)
        inv_peak = 1.0 / (peak * HIST_HEADROOM) if peak else 0
        points = [(i * inv_span, min(c * inv_peak, 1.0)) for i, c in enumerate(h)]
        lines.append(batch_for_shader(_shader, "LINE_STRIP", {"pos": points}))
    return tuple(lines)


def _recompute(settings) -> None:
    global _batches, _waveforms
    image = bpy.data.images.get("Viewer Node")
    rgb = None if image is None else _sample_image(image)
    if rgb is None:
        _batches = None
        _waveforms = None
        return
    bins = getattr(settings, "histogram_resolution", HISTOGRAM_BINS)
    if getattr(settings, "histogram_mode", "LINE") == "PARADE":
        _waveforms = _build_waveforms(rgb, bins)
        _batches = ()
    else:
        _waveforms = None
        _batches = _build_batches(_histograms_from_rgb(rgb, bins))


def _trailing_redraw():
    global _trailing
    _trailing = False
    if _registered:
        _tag_image_editors()
    return None


def _draw_batch(batch, color, x: float, y: float, sx: float, sy: float) -> None:
    gpu.matrix.push()
    gpu.matrix.translate((x, y))
    gpu.matrix.scale((sx, sy))
    _shader.uniform_float("color", color)
    batch.draw(_shader)
    gpu.matrix.pop()


def _draw_texture(texture, color, x: float, y: float, sx: float, sy: float) -> None:
    gpu.matrix.push()
    gpu.matrix.translate((x, y))
    gpu.matrix.scale((sx, sy))
    _image_shader.bind()
    _image_shader.uniform_sampler("image", texture)
    _image_shader.uniform_float("color", color)
    _image_batch.draw(_image_shader)
    gpu.matrix.pop()


def _draw_scale_labels_x(font_id, left: float, width: float, y: float, opacity: float) -> None:
    blf.size(font_id, 10)
    blf.color(font_id, 0.95, 0.95, 0.95, opacity)
    for code in SCALE_TICKS:
        text = str(code)
        text_w, _ = blf.dimensions(font_id, text)
        px = left + code / SCALE_MAX * width
        if code == SCALE_TICKS[0]:
            tx = px
        elif code == SCALE_TICKS[-1]:
            tx = px - text_w
        else:
            tx = px - text_w / 2
        blf.position(font_id, tx, y, 0)
        blf.draw(font_id, text)


def _draw_scale_labels_y(font_id, x: float, bottom: float, height: float, opacity: float) -> None:
    blf.size(font_id, 9)
    blf.color(font_id, 0.95, 0.95, 0.95, opacity)
    for code in SCALE_TICKS:
        blf.position(font_id, x, bottom + code / SCALE_MAX * height - 4, 0)
        blf.draw(font_id, str(code))


def _draw_overlay() -> None:
    global _force, _last_time, _trailing
    settings = _get_addon_preferences()
    if not getattr(settings, "show_histogram_overlay", _visible):
        return

    region = bpy.context.region
    if region is None or region.type != "WINDOW":
        return

    _ensure_static_batches()

    now = time.monotonic()
    wait = _last_time + MIN_INTERVAL - now
    if _force or wait <= 0.0:
        _force = False
        _last_time = now
        _recompute(settings)
    elif not _trailing:
        _trailing = True
        bpy.app.timers.register(_trailing_redraw, first_interval=wait)

    if _batches is None:
        return
    lines = _batches if _batches else ()

    panel_width = getattr(settings, "histogram_width", 276)
    panel_width = min(panel_width, max(120, region.width - 24))
    panel_height = getattr(settings, "histogram_height", 140)
    panel_height = min(panel_height, max(60, region.height - 48))
    opacity = getattr(settings, "histogram_opacity", 0.85)
    mode = getattr(settings, "histogram_mode", "LINE")

    x = 12
    top = region.height - 36
    bottom = top - panel_height
    left = x + 12 + (20 if mode == "PARADE" else 0)
    right = x + panel_width - 12
    graph_top = top - 12
    graph_bottom = bottom + 12
    graph_height = graph_top - graph_bottom
    graph_width = right - left
    grid_color = (0.45, 0.48, 0.52, opacity * 0.35)
    label_y = bottom + 8
    font_id = 0

    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(1.5)
    _shader.bind()

    _draw_batch(_rect_batch, (0.015, 0.02, 0.03, opacity * 0.88), x, bottom, panel_width, panel_height)

    if mode == "PARADE":
        if _waveforms:
            gap = 8
            seg = (graph_width - gap * 2) / 3
            for c in range(3):
                sx = left + c * (seg + gap)
                _draw_batch(_grid_batch, grid_color, sx, graph_bottom, seg, graph_height)
            for c in range(3):
                sx = left + c * (seg + gap)
                _draw_texture(_waveforms[c], (1.0, 1.0, 1.0, opacity), sx, graph_bottom, seg, graph_height)
            _draw_scale_labels_y(font_id, x + 4, graph_bottom, graph_height, opacity)
    else:
        # _draw_batch(_vgrid_batch, grid_color, left, graph_bottom, graph_width, graph_height)
        for batch, color in zip(lines, CHANNEL_COLORS):
            _draw_batch(batch, (*color, opacity), left, graph_bottom, graph_width, graph_height)
        # _draw_scale_labels_x(font_id, left, graph_width, label_y, opacity)

    gpu.state.blend_set("NONE")
    gpu.state.line_width_set(1.0)


@persistent
def _on_depsgraph(scene, depsgraph) -> None:
    if is_histogram_visible() and len(depsgraph.updates):
        _kick()


@persistent
def _on_load_post(*args) -> None:
    _kick()


def register() -> None:
    global _draw_handler, _registered, _force
    if _registered:
        return

    _registered = True
    _force = True
    _draw_handler = bpy.types.SpaceImageEditor.draw_handler_add(_draw_overlay, (), "WINDOW", "POST_PIXEL")
    if _on_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph)
    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)
    _tag_image_editors()


def unregister() -> None:
    global _draw_handler, _batches, _pixel_buffer, _registered
    global _shader, _rect_batch, _grid_batch, _trailing
    global _waveforms, _image_shader, _image_batch, _vgrid_batch
    if not _registered:
        return

    _registered = False
    if _on_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph)
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
    if bpy.app.timers.is_registered(_live_update_tick):
        bpy.app.timers.unregister(_live_update_tick)
    if _draw_handler is not None:
        bpy.types.SpaceImageEditor.draw_handler_remove(_draw_handler, "WINDOW")
        _draw_handler = None

    _batches = None
    _pixel_buffer = None
    _shader = None
    _rect_batch = None
    _grid_batch = None
    _waveforms = None
    _image_shader = None
    _image_batch = None
    _vgrid_batch = None
    _trailing = False
