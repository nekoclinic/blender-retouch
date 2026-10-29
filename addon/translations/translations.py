import bpy

from .. import __package__ as ADDON_MODULE_NAME


_INTERFACE_TRANSLATIONS = {
    "BLENDER RETOUCH": "BLENDER RETOUCH",
    "Blender Retouch": "Blender Retouch",
    "Load Image": "画像を読み込む",
    "Presets": "プリセット",
    "Image Only": "画像のみ",
    "Monochrome": "モノクロ",
    "Natural Saturation": "自然な彩度",
    "Grain": "粒子",
    "Format Settings": "フォーマット設定",
    "Save Preset": "プリセットを保存",
    "Presets": "プリセット",
    "Name": "名前",
    "Rename": "名前を変更",
    "Folder Name": "フォルダー名",
    "Folder Path": "フォルダーのパス",
    "Histogram": "ヒストグラム",
    "Show Histogram": "ヒストグラムを表示",
    "Histogram Width": "ヒストグラムの横幅",
    "Histogram Opacity": "ヒストグラムの不透明度",
    "Histogram Resolution": "ヒストグラムの解像度",
}

_OPERATOR_TRANSLATIONS = {
    "Load Image": "画像を読み込む",
    "Presets": "プリセット",
    "Toggle Histogram": "ヒストグラム表示切替",
    "Hide Histogram": "ヒストグラムを隠す",
    "Show Histogram": "ヒストグラムを表示",
    "Histogram Width": "ヒストグラムの横幅",
    "Histogram Opacity": "ヒストグラムの不透明度",
    "Histogram Resolution": "ヒストグラムの解像度",
    "Save Preset": "プリセットを保存",
    "Load Preset": "プリセットを読み込む",
    "Create Folder": "フォルダーを作成",
    "Open Folder": "フォルダーを開く",
    "Delete Folder": "フォルダーを削除",
    "Delete Preset": "プリセットを削除",
    "Rename Preset": "プリセット名を変更",
    "Rename Folder": "フォルダー名を変更",
    "Export Preset": "プリセットを書き出す",
    "Import Preset": "プリセットを読み込む",
    "Remove template": "テンプレートを削除",
    "Toggle Nodes": "ノードの有効/無効を切り替え",
}

_DESCRIPTION_TRANSLATIONS = {
    "Add nodes": "ノードを追加",
    "Show or hide the histogram overlay": "ヒストグラムのオーバーレイを表示または非表示にする",
    "Show the histogram overlay in the Image Editor": "画像エディターにヒストグラムのオーバーレイを表示",
    "Width of the histogram overlay in pixels": "ヒストグラムオーバーレイの幅（ピクセル）",
    "Opacity of the histogram overlay": "ヒストグラムオーバーレイの不透明度",
    "Number of histogram samples across the tonal range": "階調範囲のヒストグラム分割数",
    "Save the current compositor node setup and values as a preset": "現在のコンポジター設定をプリセットとして保存",
    "Load a saved compositor preset": "保存したコンポジタープリセットを読み込む",
    "Create a new preset folder": "新しいプリセットフォルダーを作成",
    "Open a preset folder": "プリセットフォルダーを開く",
    "Delete a preset folder and everything inside it": "プリセットフォルダーとその中身を削除",
    "Delete a saved compositor preset": "保存したコンポジタープリセットを削除",
    "Rename a saved compositor preset": "保存したコンポジタープリセットの名前を変更",
    "Rename a preset folder": "プリセットフォルダーの名前を変更",
    "Export a preset .brp file": "プリセットを.brpファイルとして書き出す",
    "Import a preset .brp file": "プリセットの.brpファイルを読み込む",
    "Remove template": "テンプレートを削除",
}

_TRANSLATIONS = {
    "ja_JP": {
        **{(bpy.app.translations.contexts.default, source): translated for source, translated in _INTERFACE_TRANSLATIONS.items()},
        **{(bpy.app.translations.contexts.operator_default, source): translated for source, translated in _OPERATOR_TRANSLATIONS.items()},
        **{(bpy.app.translations.contexts.default, source): translated for source, translated in _DESCRIPTION_TRANSLATIONS.items()},
    },
}


def register() -> None:
    bpy.app.translations.unregister(ADDON_MODULE_NAME)
    bpy.app.translations.register(ADDON_MODULE_NAME, _TRANSLATIONS)


def unregister() -> None:
    bpy.app.translations.unregister(ADDON_MODULE_NAME)
