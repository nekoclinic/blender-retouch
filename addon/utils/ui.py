from .compositor import NODETREE_NAME

def prop(layout, context, node_name, idx, label, text_prop="default_value"):
        data = get_node_or_input(context, node_name, idx)
        if data is not None:
            layout.prop(data, text_prop, text=label)


def get_compositor_tree(context):
    space = context.space_data
    # ノードエディター編集中のグループを最優先し、通常のシーン参照へフォールバックします。
    if space and space.type == "NODE_EDITOR" and getattr(space, "tree_type", None) == "CompositorNodeTree":
        if getattr(space, "edit_tree", None):
            return space.edit_tree

    if not (scene := context.scene):
        return None

    for attr in ("compositing_node_group", "compositor_node_tree", "node_tree"):
        if tree := getattr(scene, attr, None):
            return tree

    if (comp := getattr(scene, "compositor", None)) and getattr(comp, "node_tree", None):
        return comp.node_tree

    return None


def _find_node_recursive(tree, name):
    # グループ内のノードも検索対象にすることで、テンプレートの内部ノードをパネルから操作できます。
    if not tree:
        return None
    if node := tree.nodes.get(name):
        return node
    for n in tree.nodes:
        if n.type == "GROUP" and n.node_tree:
            if found := _find_node_recursive(n.node_tree, name):
                return found
    return None


def get_node_or_input(context, name, input_index=None):
    node = _find_node_recursive(get_compositor_tree(context), name)
    if not node or input_index is None:
        return node
    if isinstance(input_index, int) and input_index < len(node.inputs):
        return node.inputs[input_index]
    return None


def get_node_prop_path(context, node, prop):
    scene, tree = context.scene, node.id_data
    try:
        rel = node.path_from_id(prop)
    except (TypeError, AttributeError, ValueError):
        # 一部のノードでは Blender が相対パスを生成できないため、手動で補います。
        rel = f'nodes["{node.name}"].{prop}'

    if getattr(scene, "compositing_node_group", None) == tree:
        return f"scene.compositing_node_group.{rel}"
    if getattr(getattr(scene, "compositor", None), "node_tree", None) == tree:
        return f"scene.compositor.node_tree.{rel}"
    return f'bpy.data.node_groups["{tree.name}"].{rel}'


def is_retouch_group_applied(context):
    if not (scene := context.scene):
        return False

    def is_retouch(name):
        return name == NODETREE_NAME or name.startswith(f"{NODETREE_NAME}.")

    if group := getattr(scene, "compositing_node_group", None):
        return is_retouch(group.name)

    if not (tree := get_compositor_tree(context)):
        return False

    return is_retouch(tree.name) or any(is_retouch(n.node_tree.name) for n in tree.nodes if n.type == "GROUP" and n.node_tree)
