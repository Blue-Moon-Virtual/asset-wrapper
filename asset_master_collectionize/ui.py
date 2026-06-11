import bpy

from . import asset_io


class AM_UL_asset_library_items(bpy.types.UIList):
    def draw_item(
        self,
        context,
        layout,
        data,
        item,
        icon,
        active_data,
        active_propname,
        index,
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text=item.name, icon="OUTLINER_COLLECTION")
            size = row.row()
            size.alignment = "RIGHT"
            size.label(text=item.size_text)
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="FILE_BLEND")


class AM_PT_collectionize(bpy.types.Panel):
    bl_idname = "AM_PT_collectionize"
    bl_label = "Collectionize"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Asset Master"

    def draw_header(self, context):
        self.layout.label(text="", icon="ASSET_MANAGER")

    def draw(self, context):
        layout = self.layout
        settings = context.scene.am_collectionize

        col = layout.column(align=True)
        col.label(text="Create Linked Asset From")
        row = col.row(align=True)
        row.scale_y = 1.5
        row.enabled = context.mode == "OBJECT"

        op = row.operator(
            "asset_master.collectionize",
            text="Selection",
            icon="RESTRICT_SELECT_OFF",
        )
        op.source = "SELECTION"

        op = row.operator(
            "asset_master.collectionize",
            text="Collection",
            icon="OUTLINER_COLLECTION",
        )
        op.source = "COLLECTION"

        col.separator(factor=0.6)
        col.prop(settings, "use_cursor_pivot", icon="PIVOT_CURSOR")

        if context.mode != "OBJECT":
            layout.label(text="Switch to Object Mode to create assets", icon="INFO")


class AM_PT_asset_library_manager(bpy.types.Panel):
    bl_idname = "AM_PT_asset_library_manager"
    bl_label = "Asset Library"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Asset Master"
    bl_parent_id = "AM_PT_collectionize"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.am_collectionize
        directory = asset_io.asset_library_dir_from_settings(context)

        if not directory:
            box = layout.box()
            box.label(text="Save the .blend file first", icon="ERROR")
            box.label(text="The library is created next to it.")
            return

        library = asset_io.find_registered_asset_library(directory)

        box = layout.box()
        box.prop(settings, "target_asset_library_dir", text="", icon="FILE_FOLDER")

        status = box.row(align=True)
        if not settings.target_asset_library_dir.strip():
            status.label(text=f"Auto: //{asset_io.ASSET_DIR_NAME}", icon="CHECKMARK")

        if library is None:
            box.label(text="Not connected in Preferences", icon="UNLINKED")
        else:
            box.label(text=library.name, icon="LINKED")

        tools = box.row(align=True)
        tools.operator(
            "asset_master.refresh_asset_library",
            text="Refresh",
            icon="FILE_REFRESH",
        )
        tools.operator(
            "asset_master.open_asset_library_folder",
            text="Open",
            icon="FILE_FOLDER",
        )

        row = layout.row()
        row.template_list(
            "AM_UL_asset_library_items",
            "",
            settings,
            "asset_library_items",
            settings,
            "active_asset_library_item_index",
            rows=5,
        )

        actions = row.column(align=True)
        remove_row = actions.row(align=True)
        remove_row.enabled = bool(settings.asset_library_items)
        remove_row.operator(
            "asset_master.remove_asset_file",
            text="",
            icon="TRASH",
        )

        if not settings.asset_library_items:
            layout.label(text="Press Refresh to list asset files", icon="INFO")

        library_actions = layout.row(align=True)
        library_actions.operator(
            "asset_master.disconnect_asset_library",
            icon="UNLINKED",
            text="Disconnect",
        )
        library_actions.operator(
            "asset_master.delete_asset_library",
            icon="TRASH",
            text="Delete Folder",
        )

        footer = layout.row()
        footer.alignment = "CENTER"
        footer.enabled = False
        footer.label(text="Asset Master · Blue Moon Virtual")
