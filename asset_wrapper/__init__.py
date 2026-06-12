bl_info = {
    "name": "Asset Wrapper",
    "author": "Blue Moon Virtual",
    "version": (0, 5, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Asset Wrapper",
    "description": (
        "Wrap any selection or collection into a linked collection asset, "
        "with rendered thumbnails and a per-project asset library."
    ),
    "doc_url": "https://github.com/Blue-Moon-Virtual/asset-wrapper",
    "tracker_url": "https://github.com/Blue-Moon-Virtual/asset-wrapper/issues",
    "category": "Object",
}

from . import addon_updater_ops, asset_io, operators, preferences, properties, ui


classes = (
    preferences.AssetWrapperPreferences,
    properties.AWAssetLibraryItem,
    properties.AssetWrapperSettings,
    operators.AW_OT_wrap,
    operators.AW_OT_refresh_library,
    operators.AW_OT_open_library_folder,
    operators.AW_OT_remove_asset_file,
    operators.AW_OT_set_custom_folder,
    operators.AW_OT_reset_folder,
    operators.AW_OT_disconnect_library,
    operators.AW_OT_delete_library,
    ui.AW_UL_assets,
    ui.AW_MT_library,
    ui.AW_PT_main,
    ui.AW_PT_library,
)


def register():
    import bpy

    # Register the CGCookie updater first so its operators/properties exist.
    addon_updater_ops.register(bl_info)

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.asset_wrapper = bpy.props.PointerProperty(
        type=properties.AssetWrapperSettings
    )

    if asset_io.autodetect_project_library_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(asset_io.autodetect_project_library_handler)

    # Pick up the file that is already open when the addon gets enabled.
    bpy.app.timers.register(asset_io.autodetect_project_library, first_interval=0.5)


def unregister():
    import bpy

    if asset_io.autodetect_project_library_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(asset_io.autodetect_project_library_handler)

    del bpy.types.Scene.asset_wrapper

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    addon_updater_ops.unregister()
