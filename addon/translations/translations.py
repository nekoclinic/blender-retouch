import bpy

from .. import __package__ as ADDON_MODULE_NAME


_INTERFACE_TRANSLATIONS = {
    "BLENDER RETOUCH": "BLENDER RETOUCH",
    "Blender Retouch": "Blender Retouch",
    "Load Image": "画像を読み込む",
    "Import": "インポート",
    "Presets": "プリセット",
    "Image Only": "画像のみ",
    "Color Space": "カラースペース",
    "Light": "ライト",
    "Exposure": "露出",
    "Brightness/Contrast": "明るさ/コントラスト",
    "Contrast": "コントラスト",
    "Color Correction": "カラー補正",
    "Highlight": "ハイライト",
    "Shadow": "シャドウ",
    "White Level": "白レベル",
    "Black Level": "黒レベル",
    "Lift/Gamma/Gain": "リフト/ガンマ/ゲイン",
    "Lift": "リフト",
    "Gamma": "ガンマ",
    "Gain": "ゲイン",
    "RGB Curves": "RGBカーブ",
    "Factor": "係数",
    "Color": "カラー",
    "Monochrome": "モノクロ",
    "White Balance": "ホワイトバランス",
    "Temperature": "色温度",
    "Tint": "色かぶり補正",
    "Saturation": "彩度",
    "Natural Saturation": "自然な彩度",
    "Hue Correct": "色相補正",
    "Color Balance": "カラーバランス",
    "Offset": "オフセット",
    "Strength": "強さ",
    "Effect": "エフェクト",
    "Effects": "効果",
    "Vignette": "ビネット",
    "Grain": "粒子",
    "Texture": "テクスチャ",
    "Clarity": "明瞭度",
    "Feather": "ぼかし",
    "Corner Roundness": "角の丸み",
    "Scale": "スケール",
    "Film Grain": "フィルムグレイン",
    "Custom": "カスタム",
    "Style": "スタイル",
    "Animated": "アニメーション",
    "Custom Style": "カスタムスタイル",
    "ISO": "ISO感度",
    "Softness": "柔らかさ",
    "Acutance": "鮮鋭度",
    "Coarseness": "粒子の粗さ",
    "Patchiness": "粒状のむら",
    "Luma bias": "輝度バイアス",
    "Texture Scale": "テクスチャのスケール",
    "Format Settings": "フォーマット設定",
    "Resolution X": "解像度 X",
    "Aspect X": "ピクセル比 X",
    "Preset": "プリセット",
    "Save Preset": "プリセットを保存",
    "Import": "インポート",
    "Presets": "プリセット",
    "Name": "名前",
    "Rename": "名前を変更",
    "Folder Name": "フォルダー名",
    "Folder Path": "フォルダーのパス",
}

_OPERATOR_TRANSLATIONS = {
    "Load Image": "画像を読み込む",
    "Import": "インポート",
    "Presets": "プリセット",
    "Add nodes": "ノードを追加",
    "Save Preset": "プリセットを保存",
    "Save the current compositor node values as a preset": "現在のコンポジター設定をプリセットとして保存",
    "Load Preset": "プリセットを読み込む",
    "Load a saved compositor preset": "保存したコンポジタープリセットを読み込む",
    "Create Folder": "フォルダーを作成",
    "Create a new preset folder": "新しいプリセットフォルダーを作成",
    "Open Folder": "フォルダーを開く",
    "Open a preset folder": "プリセットフォルダーを開く",
    "Delete Folder": "フォルダーを削除",
    "Delete a preset folder and everything inside it": "プリセットフォルダーとその中身を削除",
    "Delete Preset": "プリセットを削除",
    "Delete a saved compositor preset": "保存したコンポジタープリセットを削除",
    "Rename Preset": "プリセット名を変更",
    "Rename a saved compositor preset": "保存したコンポジタープリセットの名前を変更",
    "Rename Folder": "フォルダー名を変更",
    "Rename a preset folder": "プリセットフォルダーの名前を変更",
    "Export Preset": "プリセットを書き出す",
    "Export a preset .brp file": "プリセットを.brpファイルとして書き出す",
    "Import Preset": "プリセットを読み込む",
    "Import a preset .brp file": "プリセットの.brpファイルを読み込む",
    "Remove template": "テンプレートを削除",
    "Toggle Nodes": "ノードの有効/無効を切り替え",
}

_TRANSLATIONS = {
    "ja_JP": {
        **{(bpy.app.translations.contexts.default, source): translated for source, translated in _INTERFACE_TRANSLATIONS.items()},
        **{(bpy.app.translations.contexts.operator_default, source): translated for source, translated in _OPERATOR_TRANSLATIONS.items()},
    },
}


def register() -> None:
    bpy.app.translations.unregister(ADDON_MODULE_NAME)
    bpy.app.translations.register(ADDON_MODULE_NAME, _TRANSLATIONS)


def unregister() -> None:
    bpy.app.translations.unregister(ADDON_MODULE_NAME)
