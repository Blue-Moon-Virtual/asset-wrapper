import os

import bpy

from . import asset_io


def refresh_asset_library_items(context):
    settings = context.scene.am_collectionize
    settings.asset_library_items.clear()

    directory = asset_io.asset_library_dir_from_settings(context)
    if not directory or not os.path.isdir(directory):
        settings.active_asset_library_item_index = 0
        return 0

    for file_info in asset_io.scan_asset_library_files(directory):
        item = settings.asset_library_items.add()
        item.name = file_info["name"]
        item.filename = file_info["filename"]
        item.filepath = file_info["filepath"]
        item.size_text = file_info["size_text"]

    count = len(settings.asset_library_items)
    settings.active_asset_library_item_index = min(
        settings.active_asset_library_item_index,
        max(count - 1, 0),
    )
    return count


def active_asset_library_item(context):
    settings = context.scene.am_collectionize
    index = settings.active_asset_library_item_index

    if index < 0 or index >= len(settings.asset_library_items):
        return None

    return settings.asset_library_items[index]


class AM_OT_collectionize(bpy.types.Operator):
    bl_idname = "asset_master.collectionize"
    bl_label = "Collectionize"
    bl_description = "Convert objects into a linked collection asset stored in the project asset library"
    bl_options = {"REGISTER", "UNDO"}

    source: bpy.props.EnumProperty(
        name="Source",
        items=(
            ("SELECTION", "Selection", "Use the selected objects"),
            (
                "COLLECTION",
                "Collection",
                "Use the whole collection of the active object, "
                "or the active collection from the Outliner",
            ),
        ),
        default="SELECTION",
        options={"SKIP_SAVE"},
    )

    asset_name: bpy.props.StringProperty(
        name="Asset Name",
        description="Name for the generated collection asset",
        default="",
    )

    replace_existing: bpy.props.BoolProperty(
        name="Replace Existing Asset",
        description=(
            "Overwrite the asset file with this name instead of creating a "
            "numbered duplicate"
        ),
        default=True,
        options={"SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def invoke(self, context, event):
        try:
            objects, source_collection = self._gather_source(context)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        if source_collection is not None:
            default_name = source_collection.name
        else:
            active = context.view_layer.objects.active
            default_name = (active if active in objects else objects[0]).name

        self.asset_name = asset_io.sanitize_name(default_name)
        self.replace_existing = source_collection is not None
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "asset_name")
        layout.prop(self, "replace_existing")
        layout.prop(context.scene.am_collectionize, "use_cursor_pivot")

    def execute(self, context):
        try:
            objects, source_collection = self._gather_source(context)
            settings = context.scene.am_collectionize
            context.view_layer.update()
            source_world_matrices = [obj.matrix_world.copy() for obj in objects]

            asset_dir = asset_io.resolve_asset_library_dir(context)
            pivot_matrix = asset_io.compute_pivot_matrix(
                context, objects, settings.use_cursor_pivot
            )

            requested_name = self.asset_name or (
                source_collection.name if source_collection else objects[0].name
            )
            asset_io.purge_unused_linked_asset_collections(asset_dir, requested_name)

            # The replacement instance goes where the originals lived.
            if source_collection is not None:
                instance_parent = asset_io.first_parent_collection(
                    context.scene, source_collection
                )
                # Free up the collection name for the asset before uniquifying.
                asset_io.rename_to_backup(source_collection)
            else:
                active = context.view_layer.objects.active
                reference = active if active in objects else objects[0]
                instance_parent = (
                    reference.users_collection[0]
                    if reference.users_collection
                    else context.scene.collection
                )

            if self.replace_existing:
                asset_name = asset_io.sanitize_name(requested_name)
                filepath = asset_io.asset_filepath(asset_dir, asset_name)
            else:
                asset_name, filepath = asset_io.unique_asset_identity(
                    asset_dir,
                    requested_name,
                )

            export_collection, created_objects, created_data, extra_dependencies = (
                asset_io.create_export_collection(asset_name, objects, pivot_matrix)
            )

            try:
                preview_png = asset_io.render_preview_png(export_collection)
                asset_io.write_asset_file(filepath, export_collection)
            finally:
                asset_io.cleanup_export_data(
                    export_collection,
                    created_objects,
                    created_data,
                )

            prefs = asset_io.addon_preferences()
            asset_io.queue_asset_postprocess(
                filepath,
                asset_name,
                png_path=preview_png,
                pack_textures=bool(getattr(prefs, "pack_textures", False)),
            )

            linked_collection = asset_io.link_collection_from_asset(filepath, asset_name)
            if source_collection is not None:
                asset_io.unlink_conflicting_linked_asset_collections(
                    instance_parent,
                    asset_dir,
                    requested_name,
                    keep_collection=linked_collection,
                )

            # Hand the clean name over to the instance if one of the source
            # objects holds it (it goes to the backup anyway).
            name_holder = bpy.data.objects.get(asset_name)
            if name_holder is not None and name_holder in objects:
                name_holder.name = f"{asset_name}_src"

            instance = asset_io.create_collection_instance(
                context,
                linked_collection,
                asset_name,
                pivot_matrix,
                instance_parent,
            )
            alignment = asset_io.align_collection_instance_to_snapshot(
                context,
                instance,
                objects,
                source_world_matrices,
            )

            if source_collection is not None:
                asset_io.move_collection_to_backup(context, source_collection)
            else:
                asset_io.move_originals_to_backup(context, objects, asset_name)

            context.view_layer.objects.active = instance
            instance.select_set(True)
            refresh_asset_library_items(context)
            asset_io.refresh_asset_browsers(context)

        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        message = (
            f"Created collection asset: {asset_name} "
            f"({os.path.basename(filepath)})"
        )
        if extra_dependencies:
            message += (
                f" — included {len(extra_dependencies)} referenced helper "
                f"object(s): {', '.join(extra_dependencies[:4])}"
            )
            if len(extra_dependencies) > 4:
                message += ", ..."
        self.report({"INFO"}, message)
        return {"FINISHED"}

    def _gather_source(self, context):
        if self.source == "COLLECTION":
            collection = self._resolve_source_collection(context)
            objects = list(collection.all_objects)
            if not objects:
                raise ValueError(f"Collection '{collection.name}' has no objects.")
            return objects, collection

        objects = list(context.selected_objects)
        if not objects:
            raise ValueError("Select at least one object to collectionize.")
        return objects, None

    def _resolve_source_collection(self, context):
        active = context.view_layer.objects.active
        if active is not None and active.select_get():
            for collection in active.users_collection:
                if (
                    collection != context.scene.collection
                    and asset_io.is_user_facing_collection(collection)
                ):
                    return collection

        layer_collection = context.view_layer.active_layer_collection
        if layer_collection is not None:
            collection = layer_collection.collection
            if (
                collection != context.scene.collection
                and asset_io.is_user_facing_collection(collection)
            ):
                return collection

        raise ValueError(
            "Select an object that lives inside a collection, "
            "or make a collection active in the Outliner."
        )


class AM_OT_refresh_asset_library(bpy.types.Operator):
    bl_idname = "asset_master.refresh_asset_library"
    bl_label = "Refresh Asset Library"
    bl_description = "Scan the configured asset library folder"
    bl_options = {"REGISTER"}

    def execute(self, context):
        count = refresh_asset_library_items(context)
        self.report({"INFO"}, f"Found {count} asset file(s).")
        return {"FINISHED"}


class AM_OT_open_asset_library_folder(bpy.types.Operator):
    bl_idname = "asset_master.open_asset_library_folder"
    bl_label = "Open Library Folder"
    bl_description = "Open the configured asset library folder"

    def execute(self, context):
        directory = asset_io.asset_library_dir_from_settings(context)
        if not directory or not os.path.isdir(directory):
            self.report({"ERROR"}, "Asset library folder does not exist.")
            return {"CANCELLED"}

        bpy.ops.wm.path_open(filepath=directory)
        return {"FINISHED"}


class AM_OT_remove_asset_file(bpy.types.Operator):
    bl_idname = "asset_master.remove_asset_file"
    bl_label = "Remove Asset File"
    bl_description = "Delete the selected asset .blend file from the asset library"
    bl_options = {"REGISTER"}

    asset_name: bpy.props.StringProperty(options={"SKIP_SAVE"})
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})

    def invoke(self, context, event):
        item = active_asset_library_item(context)
        if item is None:
            self.report({"ERROR"}, "Select an asset file first.")
            return {"CANCELLED"}

        self.asset_name = item.name
        self.filepath = item.filepath
        return context.window_manager.invoke_props_dialog(self, width=520)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Delete this asset file from disk?", icon="ERROR")
        layout.label(text=self.asset_name or os.path.basename(self.filepath))
        layout.label(text="Existing placed linked instances may need manual cleanup.")

    def execute(self, context):
        directory = asset_io.asset_library_dir_from_settings(context)
        if not directory:
            self.report({"ERROR"}, "Asset library folder is not configured.")
            return {"CANCELLED"}

        try:
            deleted = asset_io.delete_asset_file(self.filepath, directory)
            count = refresh_asset_library_items(context)
            asset_io.refresh_asset_browsers(context)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            f"Deleted {len(deleted)} file(s). {count} asset file(s) remain.",
        )
        return {"FINISHED"}


class AM_OT_disconnect_asset_library(bpy.types.Operator):
    bl_idname = "asset_master.disconnect_asset_library"
    bl_label = "Disconnect Asset Library"
    bl_description = "Remove the configured folder from Blender's asset libraries"
    bl_options = {"REGISTER"}

    directory: bpy.props.StringProperty(subtype="DIR_PATH", options={"SKIP_SAVE"})

    def invoke(self, context, event):
        self.directory = asset_io.asset_library_dir_from_settings(context) or ""
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Disconnect this asset library from Blender?", icon="QUESTION")
        layout.label(text=self.directory)
        layout.label(text="Files on disk will be kept.")

    def execute(self, context):
        if not self.directory:
            self.report({"ERROR"}, "Asset library folder is not configured.")
            return {"CANCELLED"}

        try:
            removed = asset_io.disconnect_asset_library(self.directory)
            asset_io.refresh_asset_browsers(context)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        if removed:
            self.report({"INFO"}, "Asset library disconnected.")
        else:
            self.report({"INFO"}, "Asset library was not registered.")
        return {"FINISHED"}


class AM_OT_delete_asset_library(bpy.types.Operator):
    bl_idname = "asset_master.delete_asset_library"
    bl_label = "Delete Asset Library"
    bl_description = "Disconnect and delete the configured asset library folder"
    bl_options = {"REGISTER"}

    directory: bpy.props.StringProperty(subtype="DIR_PATH", options={"SKIP_SAVE"})

    def invoke(self, context, event):
        self.directory = asset_io.asset_library_dir_from_settings(context) or ""
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Delete the whole asset library folder?", icon="ERROR")
        layout.label(text=self.directory)
        layout.label(text="This removes all asset files in that folder from disk.")

    def execute(self, context):
        if not self.directory:
            self.report({"ERROR"}, "Asset library folder is not configured.")
            return {"CANCELLED"}

        try:
            asset_io.disconnect_asset_library(self.directory)
            asset_io.delete_asset_library_directory(self.directory)
            context.scene.am_collectionize.asset_library_items.clear()
            context.scene.am_collectionize.active_asset_library_item_index = 0
            asset_io.refresh_asset_browsers(context)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report({"INFO"}, "Asset library disconnected and deleted.")
        return {"FINISHED"}
