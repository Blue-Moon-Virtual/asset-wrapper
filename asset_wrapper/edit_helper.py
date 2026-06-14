"""Run inside a Blender launched to edit a single Asset Wrapper asset file.

Links the asset collection into the scene so it is visible/editable, and adds
an "Asset Wrapper" sidebar panel with a one-click 'Render Thumbnail & Save'.
Invoked via:  blender <asset>.asset.blend --python edit_helper.py
"""
import bpy


def _asset_collection():
    marked = [c for c in bpy.data.collections if c.asset_data is not None]
    if marked:
        return marked[0]
    return bpy.data.collections[0] if bpy.data.collections else None


class AW_OT_finish_edit(bpy.types.Operator):
    bl_idname = "asset_wrapper.finish_edit"
    bl_label = "Render Thumbnail & Save"
    bl_description = "Re-render the asset's thumbnail from the current view and save the file"
    bl_options = {"REGISTER"}

    def execute(self, context):
        col = _asset_collection()
        if col is None:
            self.report({"ERROR"}, "No asset collection found in this file.")
            return {"CANCELLED"}

        try:
            import os
            from asset_wrapper import asset_io

            png = asset_io.render_preview_png(col)
            if png and os.path.exists(png):
                image = bpy.data.images.load(png)
                pixels = list(image.pixels)
                bpy.data.images.remove(image)
                size = asset_io.preview_size_from_preferences()
                preview = col.preview_ensure()
                preview.image_size = (size, size)
                preview.image_pixels_float = pixels
                preview.is_image_custom = True
                preview.icon_size = (size, size)
                preview.icon_pixels_float = pixels
                preview.is_icon_custom = True
                try:
                    os.remove(png)
                except OSError:
                    pass
        except Exception as exc:  # noqa: BLE001
            self.report({"WARNING"}, f"Thumbnail not updated: {exc}")

        bpy.ops.wm.save_mainfile()
        self.report(
            {"INFO"},
            "Saved. In your project: Asset Library menu -> Reload Asset Libraries.",
        )
        return {"FINISHED"}


class AW_PT_edit(bpy.types.Panel):
    bl_idname = "AW_PT_edit"
    bl_label = "Editing Asset"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Asset Wrapper"

    def draw(self, context):
        layout = self.layout
        col = _asset_collection()
        layout.label(text=col.name if col else "asset", icon="OUTLINER_OB_GROUP_INSTANCE")
        layout.separator()
        layout.label(text="Edit the objects, then:")
        big = layout.row()
        big.scale_y = 1.5
        big.operator("asset_wrapper.finish_edit", icon="CHECKMARK")
        box = layout.box()
        box.label(text="Keep it in this collection.", icon="INFO")
        box.label(text="Don't rename the collection.")
        box.label(text="Then close this window.")


def _setup():
    col = _asset_collection()
    if col is None:
        return
    scene = bpy.context.scene
    if col.name not in scene.collection.children:
        try:
            scene.collection.children.link(col)
        except Exception:
            pass

    if bpy.app.background:
        return  # no viewport to frame in background mode

    def _frame():
        try:
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == "VIEW_3D":
                        for region in area.regions:
                            if region.type == "WINDOW":
                                with bpy.context.temp_override(
                                    window=window, area=area, region=region
                                ):
                                    bpy.ops.object.select_all(action="DESELECT")
                                    bpy.ops.view3d.view_all()
        except Exception:
            pass
        return None

    bpy.app.timers.register(_frame, first_interval=0.4)


for _cls in (AW_OT_finish_edit, AW_PT_edit):
    try:
        bpy.utils.register_class(_cls)
    except Exception:
        pass

_setup()
