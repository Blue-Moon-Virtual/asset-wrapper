bl_info = {
    "name": "Asset Master Collectionize",
    "author": "Blue Moon Virtual",
    "version": (0, 4, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Asset Master",
    "description": (
        "One-click conversion of selections or collections into linked "
        "collection assets with rendered thumbnails and a per-project library."
    ),
    "doc_url": "https://github.com/bluemoonvirtual/asset-master-collectionize",
    "tracker_url": "https://github.com/bluemoonvirtual/asset-master-collectionize/issues",
    "category": "Object",
}

from . import asset_io, operators, preferences, properties, ui


classes = (
    preferences.AMCollectionizePreferences,
    properties.AMAssetLibraryItem,
    properties.AMCollectionizeSettings,
    operators.AM_OT_collectionize,
    operators.AM_OT_refresh_asset_library,
    operators.AM_OT_open_asset_library_folder,
    operators.AM_OT_remove_asset_file,
    operators.AM_OT_disconnect_asset_library,
    operators.AM_OT_delete_asset_library,
    ui.AM_UL_asset_library_items,
    ui.AM_PT_collectionize,
    ui.AM_PT_asset_library_manager,
)


def register():
    import bpy

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.am_collectionize = bpy.props.PointerProperty(
        type=properties.AMCollectionizeSettings
    )

    if asset_io.autodetect_project_library_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(asset_io.autodetect_project_library_handler)

    # Pick up the file that is already open when the addon gets enabled.
    bpy.app.timers.register(asset_io.autodetect_project_library, first_interval=0.5)


def unregister():
    import bpy

    if asset_io.autodetect_project_library_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(asset_io.autodetect_project_library_handler)

    del bpy.types.Scene.am_collectionize

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
