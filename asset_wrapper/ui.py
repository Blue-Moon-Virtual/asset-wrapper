import bpy

from . import asset_io


class AW_UL_assets(bpy.types.UIList):
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
            row.label(text=item.name, icon="OUTLINER_OB_GROUP_INSTANCE")
            size = row.row()
            size.alignment = "RIGHT"
            size.active = False
            size.label(text=item.size_text)
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text="", icon="FILE_BLEND")


class AW_MT_library(bpy.types.Menu):
    bl_idname = "AW_MT_library"
    bl_label = "Library Actions"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.asset_wrapper

        layout.operator("asset_wrapper.refresh_library", icon="FILE_REFRESH")
        layout.operator("asset_wrapper.open_library_folder", icon="FILE_FOLDER")

        layout.separator()
        layout.operator("asset_wrapper.set_custom_folder", icon="FILEBROWSER")
        if settings.target_asset_library_dir.strip():
            layout.operator("asset_wrapper.reset_folder", icon="LOOP_BACK")

        layout.separator()
        layout.operator("asset_wrapper.disconnect_library", icon="UNLINKED")
        layout.operator("asset_wrapper.delete_library", icon="TRASH")


class AW_PT_main(bpy.types.Panel):
    bl_idname = "AW_PT_main"
    bl_label = "Asset Wrapper"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Asset Wrapper"

    def draw_header(self, context):
        self.layout.label(text="", icon="OUTLINER_OB_GROUP_INSTANCE")

    def draw(self, context):
        layout = self.layout
        settings = context.scene.asset_wrapper

        column = layout.column(align=True)
        column.scale_y = 1.5
        column.enabled = context.mode == "OBJECT"
        row = column.row(align=True)
        row.operator(
            "asset_wrapper.wrap", text="Selection", icon="RESTRICT_SELECT_OFF"
        ).source = "SELECTION"
        row.operator(
            "asset_wrapper.wrap", text="Collection", icon="OUTLINER_COLLECTION"
        ).source = "COLLECTION"

        layout.prop(settings, "use_cursor_pivot", icon="PIVOT_CURSOR")

        if context.mode != "OBJECT":
            layout.label(text="Object Mode required", icon="INFO")


class AW_PT_library(bpy.types.Panel):
    bl_idname = "AW_PT_library"
    bl_label = "Asset Library"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Asset Wrapper"
    bl_parent_id = "AW_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.asset_wrapper
        directory = asset_io.asset_library_dir_from_settings(context)

        if not directory:
            layout.label(text="Save the .blend file first", icon="ERROR")
            return

        # Single, compact action row replaces the old stack of status lines
        # and management buttons.
        header = layout.row(align=True)
        if settings.target_asset_library_dir.strip():
            header.label(text="Custom folder", icon="FILEBROWSER")
        else:
            header.label(text="Auto library", icon="CHECKMARK")
        header.menu("AW_MT_library", text="", icon="DOWNARROW_HLT")

        body = layout.row()
        body.template_list(
            "AW_UL_assets",
            "",
            settings,
            "asset_library_items",
            settings,
            "active_asset_library_item_index",
            rows=5,
        )

        side = body.column(align=True)
        side.operator("asset_wrapper.refresh_library", text="", icon="FILE_REFRESH")
        remove = side.row(align=True)
        remove.enabled = bool(settings.asset_library_items)
        remove.operator("asset_wrapper.remove_asset_file", text="", icon="TRASH")

        if not settings.asset_library_items:
            layout.label(text="No assets yet — wrap a selection", icon="INFO")
