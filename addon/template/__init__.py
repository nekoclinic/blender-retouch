import bpy
from . import template


def register():
    template.install_app_template()


def unregister():
    pass
#     アプリケーションテンプレートを削除する場合は以下を実行します。
#     template.uninstall_app_template()
