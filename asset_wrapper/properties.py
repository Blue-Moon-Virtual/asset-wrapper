import bpy


class AWAssetLibraryItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default="")
    filename: bpy.props.StringProperty(name="Filename", default="")
    filepath: bpy.props.StringProperty(name="Filepath", subtype="FILE_PATH", default="")
    size_text: bpy.props.StringProperty(name="Size", default="")


class AssetWrapperSettings(bpy.types.PropertyGroup):
    target_asset_library_dir: bpy.props.StringProperty(
        name="Asset Library Folder",
        description=(
            "Project asset library folder. Leave empty to use the 'asset_library' "
            "folder next to the .blend file (recommended, travels with the project)"
        ),
        subtype="DIR_PATH",
        default="",
    )

    use_cursor_pivot: bpy.props.BoolProperty(
        name="3D Cursor as Pivot",
        description=(
            "Place the asset pivot at the 3D cursor. "
            "When off, the pivot is the bottom center of the combined bounding box"
        ),
        default=False,
    )

    asset_library_items: bpy.props.CollectionProperty(type=AWAssetLibraryItem)

    active_asset_library_item_index: bpy.props.IntProperty(
        name="Active Asset",
        default=0,
        min=0,
    )
