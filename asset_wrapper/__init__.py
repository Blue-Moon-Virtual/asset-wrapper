bl_info = {
    "name": "Asset Wrapper",
    "author": "Blue Moon Virtual",
    "version": (0, 5, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Asset Wrapper",
    "description": (
        "Wrap any selection or collection into a linked collection asset, "
        "with rendered thumbnails and a per-project asset library."
    ),
    "doc_url": "https://github.com/bluemoonvirtual/asset-wrapper",
    "tracker_url": "https://github.com/bluemoonvirtual/asset-wrapper/issues",
    "category": "Object",
}

from . import asset_io, operators, preferences, properties, ui, updater


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
    updater.AW_OT_check_for_updates,
    updater.AW_OT_install_update,
    ui.AW_UL_assets,
    ui.AW_MT_library,
    ui.AW_PT_main,
    ui.AW_PT_library,
)


def register():
    import bpy

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.asset_wrapper = bpy.props.PointerProperty(
        type=properties.AssetWrapperSettings
    )

    if asset_io.autodetect_project_library_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(asset_io.autodetect_project_library_handler)

    # Pick up the file that is already open when the addon gets enabled.
    bpy.app.timers.register(asset_io.autodetect_project_library, first_interval=0.5)

    updater.on_register()


def unregister():
    import bpy

    updater.on_unregister()

    if asset_io.autodetect_project_library_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(asset_io.autodetect_project_library_handler)

    del bpy.types.Scene.asset_wrapper

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
