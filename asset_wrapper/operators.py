import os

import bpy

from . import asset_io


def refresh_library_items(context):
    settings = context.scene.asset_wrapper
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


def active_library_item(context):
    settings = context.scene.asset_wrapper
    index = settings.active_asset_library_item_index

    if index < 0 or index >= len(settings.asset_library_items):
        return None

    return settings.asset_library_items[index]


class AW_OT_wrap(bpy.types.Operator):
    bl_idname = "asset_wrapper.wrap"
    bl_label = "Wrap into Asset"
    bl_description = "Wrap objects into a linked collection asset stored in the project asset library"
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
        settings = context.scene.asset_wrapper
        layout.prop(self, "asset_name")
        if settings.project_tag.strip():
            tag = settings.project_tag.strip()
            layout.label(text=f"Saved as: {tag}_{self.asset_name}", icon="ASSET_MANAGER")
        layout.prop(self, "replace_existing")
        layout.prop(settings, "use_cursor_pivot")
        layout.prop(settings, "project_tag")

    def execute(self, context):
        try:
            objects, source_collection = self._gather_source(context)
            settings = context.scene.asset_wrapper
            context.view_layer.update()
            source_world_matrices = [obj.matrix_world.copy() for obj in objects]

            asset_dir = asset_io.resolve_asset_library_dir(context)
            pivot_matrix = asset_io.compute_pivot_matrix(
                context, objects, settings.use_cursor_pivot
            )

            requested_name = self.asset_name or (
                source_collection.name if source_collection else objects[0].name
            )
            # Prefix with the project tag so projects sharing one library folder
            # never collide on generic names (e.g. "BED" -> "Cozy_BED").
            requested_name, project_tag = asset_io.apply_project_tag(
                requested_name, settings.project_tag
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

            # File the asset under a per-project catalogue.
            if project_tag and export_collection.asset_data is not None:
                catalog_id = asset_io.ensure_catalog(asset_dir, project_tag)
                if catalog_id:
                    export_collection.asset_data.catalog_id = catalog_id

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
            asset_io.align_collection_instance_to_snapshot(
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
            refresh_library_items(context)
            asset_io.refresh_asset_browsers(context)

        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        message = f"Wrapped asset: {asset_name} ({os.path.basename(filepath)})"
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
            raise ValueError("Select at least one object to wrap.")
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


class AW_OT_refresh_library(bpy.types.Operator):
    bl_idname = "asset_wrapper.refresh_library"
    bl_label = "Refresh Library"
    bl_description = "Scan the configured asset library folder"
    bl_options = {"REGISTER"}

    def execute(self, context):
        count = refresh_library_items(context)
        self.report({"INFO"}, f"Found {count} asset file(s).")
        return {"FINISHED"}


class AW_OT_open_library_folder(bpy.types.Operator):
    bl_idname = "asset_wrapper.open_library_folder"
    bl_label = "Open Library Folder"
    bl_description = "Open the configured asset library folder in your file browser"

    def execute(self, context):
        directory = asset_io.asset_library_dir_from_settings(context)
        if not directory or not os.path.isdir(directory):
            self.report({"ERROR"}, "Asset library folder does not exist.")
            return {"CANCELLED"}

        bpy.ops.wm.path_open(filepath=directory)
        return {"FINISHED"}


class AW_OT_set_custom_folder(bpy.types.Operator):
    bl_idname = "asset_wrapper.set_custom_folder"
    bl_label = "Set Custom Folder"
    bl_description = (
        "Choose a custom asset library folder instead of the default "
        "'asset_library' folder next to the .blend file"
    )
    bl_options = {"REGISTER", "UNDO"}

    directory: bpy.props.StringProperty(subtype="DIR_PATH", options={"SKIP_SAVE"})

    def invoke(self, context, event):
        self.directory = context.scene.asset_wrapper.target_asset_library_dir
        return context.window_manager.invoke_props_dialog(self, width=520)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Custom asset library folder:")
        layout.prop(self, "directory", text="")
        layout.label(text="Leave empty to use the default folder next to the file.")

    def execute(self, context):
        context.scene.asset_wrapper.target_asset_library_dir = self.directory.strip()
        refresh_library_items(context)
        return {"FINISHED"}


class AW_OT_reset_folder(bpy.types.Operator):
    bl_idname = "asset_wrapper.reset_folder"
    bl_label = "Use Default Folder"
    bl_description = "Clear the custom folder and use the default 'asset_library' folder"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.scene.asset_wrapper.target_asset_library_dir = ""
        refresh_library_items(context)
        return {"FINISHED"}


class AW_OT_edit_asset(bpy.types.Operator):
    bl_idname = "asset_wrapper.edit_asset"
    bl_label = "Edit Asset"
    bl_description = (
        "Open the selected asset in a separate Blender window for editing. "
        "Saved changes apply to every project that links it after a reload"
    )
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.asset_wrapper.asset_library_items)

    def execute(self, context):
        item = active_library_item(context)
        if item is None:
            self.report({"ERROR"}, "Select an asset first.")
            return {"CANCELLED"}

        if not asset_io.launch_asset_editor(item.filepath):
            self.report({"ERROR"}, "Could not open the asset for editing.")
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            f"Opened '{item.name}' for editing. Save there, then Reload here.",
        )
        return {"FINISHED"}


class AW_OT_reload_libraries(bpy.types.Operator):
    bl_idname = "asset_wrapper.reload_libraries"
    bl_label = "Reload Asset Libraries"
    bl_description = (
        "Reload linked assets so edits made to the asset files appear in this project"
    )
    bl_options = {"REGISTER"}

    def execute(self, context):
        count = asset_io.reload_asset_libraries(context)
        asset_io.refresh_asset_browsers(context)
        self.report({"INFO"}, f"Reloaded {count} linked asset(s).")
        return {"FINISHED"}


class AW_OT_remove_asset_file(bpy.types.Operator):
    bl_idname = "asset_wrapper.remove_asset_file"
    bl_label = "Remove Asset File"
    bl_description = "Delete the selected asset .blend file from the asset library"
    bl_options = {"REGISTER"}

    asset_name: bpy.props.StringProperty(options={"SKIP_SAVE"})
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})

    def invoke(self, context, event):
        item = active_library_item(context)
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
            count = refresh_library_items(context)
            asset_io.refresh_asset_browsers(context)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            f"Deleted {len(deleted)} file(s). {count} asset file(s) remain.",
        )
        return {"FINISHED"}


class AW_OT_disconnect_library(bpy.types.Operator):
    bl_idname = "asset_wrapper.disconnect_library"
    bl_label = "Disconnect Library"
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


class AW_OT_delete_library(bpy.types.Operator):
    bl_idname = "asset_wrapper.delete_library"
    bl_label = "Delete Library Folder"
    bl_description = "Disconnect and delete the configured asset library folder from disk"
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
            context.scene.asset_wrapper.asset_library_items.clear()
            context.scene.asset_wrapper.active_asset_library_item_index = 0
            asset_io.refresh_asset_browsers(context)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report({"INFO"}, "Asset library disconnected and deleted.")
        return {"FINISHED"}


class AW_OT_rename_asset(bpy.types.Operator):
    bl_idname = "asset_wrapper.rename_asset"
    bl_label = "Rename Asset"
    bl_description = (
        "Rename the selected asset: its file, the collection inside it, and any "
        "linked instances placed in this scene"
    )
    bl_options = {"REGISTER"}

    new_name: bpy.props.StringProperty(name="New Name", default="")

    @classmethod
    def poll(cls, context):
        return bool(context.scene.asset_wrapper.asset_library_items)

    def invoke(self, context, event):
        item = active_library_item(context)
        if item is None:
            self.report({"ERROR"}, "Select an asset first.")
            return {"CANCELLED"}
        self.new_name = item.name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        item = active_library_item(context)
        layout = self.layout
        if item is not None:
            layout.label(text=f"Rename '{item.name}'", icon="OUTLINER_OB_GROUP_INSTANCE")
        layout.prop(self, "new_name")

    def execute(self, context):
        directory = asset_io.asset_library_dir_from_settings(context)
        if not directory:
            self.report({"ERROR"}, "Asset library folder is not configured.")
            return {"CANCELLED"}

        item = active_library_item(context)
        if item is None:
            self.report({"ERROR"}, "Select an asset first.")
            return {"CANCELLED"}

        old_name = item.name
        new_name = asset_io.sanitize_name(self.new_name)

        if new_name == old_name:
            self.report({"INFO"}, "Name unchanged.")
            return {"CANCELLED"}

        if asset_io.asset_file_exists(directory, new_name):
            self.report({"ERROR"}, f"An asset named '{new_name}' already exists.")
            return {"CANCELLED"}

        try:
            renamed, instances = asset_io.rename_asset(
                context, directory, old_name, new_name
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        if not renamed:
            self.report({"ERROR"}, f"Could not rename '{old_name}'.")
            return {"CANCELLED"}

        refresh_library_items(context)
        _select_asset_by_name(context, new_name)
        asset_io.refresh_asset_browsers(context)
        self.report(
            {"INFO"},
            f"Renamed '{old_name}' to '{new_name}' "
            f"({instances} scene instance(s) updated).",
        )
        return {"FINISHED"}


class AW_OT_batch_rename(bpy.types.Operator):
    bl_idname = "asset_wrapper.batch_rename"
    bl_label = "Batch Rename Assets"
    bl_description = "Rename every asset in the library by find & replace, prefix, or suffix"
    bl_options = {"REGISTER"}

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=(
            ("REPLACE", "Find & Replace", "Replace text within asset names"),
            ("PREFIX", "Add Prefix", "Add text to the start of every name"),
            ("SUFFIX", "Add Suffix", "Add text to the end of every name"),
        ),
        default="REPLACE",
    )
    find: bpy.props.StringProperty(name="Find", default="")
    replace: bpy.props.StringProperty(name="Replace", default="")
    affix: bpy.props.StringProperty(name="Text", default="")

    @classmethod
    def poll(cls, context):
        return bool(context.scene.asset_wrapper.asset_library_items)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "mode")
        if self.mode == "REPLACE":
            layout.prop(self, "find")
            layout.prop(self, "replace")
        else:
            layout.prop(self, "affix")

        renames = self._compute(context)
        box = layout.box()
        if not renames:
            box.label(text="No assets will change.", icon="INFO")
            return
        box.label(text=f"{len(renames)} asset(s) will change:", icon="FILE_REFRESH")
        for old_name, new_name in renames[:8]:
            box.label(text=f"{old_name}   →   {new_name}")
        if len(renames) > 8:
            box.label(text=f"…and {len(renames) - 8} more")

    def _new_name(self, old_name):
        if self.mode == "REPLACE":
            return old_name.replace(self.find, self.replace) if self.find else old_name
        if self.mode == "PREFIX":
            return f"{self.affix}{old_name}"
        if self.mode == "SUFFIX":
            return f"{old_name}{self.affix}"
        return old_name

    def _compute(self, context):
        settings = context.scene.asset_wrapper
        directory = asset_io.asset_library_dir_from_settings(context)
        if not directory:
            return []

        existing = {item.name for item in settings.asset_library_items}
        renames = []
        seen_new = set()

        for item in settings.asset_library_items:
            old_name = item.name
            new_name = asset_io.sanitize_name(self._new_name(old_name))
            if not new_name or new_name == old_name:
                continue
            # Skip names that would clash with another asset or another rename.
            if new_name in seen_new:
                continue
            if new_name in existing and new_name not in {o for o, _ in renames}:
                continue
            if asset_io.asset_file_exists(directory, new_name) and new_name not in {
                o for o, _ in renames
            }:
                continue
            seen_new.add(new_name)
            renames.append((old_name, new_name))

        return renames

    def execute(self, context):
        directory = asset_io.asset_library_dir_from_settings(context)
        if not directory:
            self.report({"ERROR"}, "Asset library folder is not configured.")
            return {"CANCELLED"}

        # Operate on the current contents of the folder, not a stale list.
        refresh_library_items(context)
        renames = self._compute(context)
        if not renames:
            self.report({"INFO"}, "No assets to rename.")
            return {"CANCELLED"}

        try:
            done, instances = asset_io.rename_assets(context, directory, renames)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        refresh_library_items(context)
        asset_io.refresh_asset_browsers(context)
        self.report(
            {"INFO"},
            f"Renamed {len(done)} asset(s), updated {instances} scene instance(s).",
        )
        return {"FINISHED"}


def _select_asset_by_name(context, name):
    settings = context.scene.asset_wrapper
    for index, item in enumerate(settings.asset_library_items):
        if item.name == name:
            settings.active_asset_library_item_index = index
            return
