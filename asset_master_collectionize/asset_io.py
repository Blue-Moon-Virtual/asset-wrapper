import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import bpy
from bpy.app.handlers import persistent
from mathutils import Matrix, Vector


BACKUP_ROOT_NAME = "AM_Collectionize_Backups"
ASSET_DIR_NAME = "asset_library"
ASSET_FILE_SUFFIX = ".asset.blend"

# Object types whose bound_box is meaningless; use their origin for pivot math.
_POINT_LIKE_TYPES = {"EMPTY", "LIGHT", "CAMERA", "SPEAKER", "LIGHT_PROBE"}


def sanitize_name(name):
    cleaned = re.sub(r"[^\w .-]+", "_", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or "CollectionAsset"


def default_asset_library_dir():
    if not bpy.data.filepath:
        return None
    return os.path.normpath(bpy.path.abspath("//" + ASSET_DIR_NAME))


def asset_library_dir_from_settings(context):
    settings = context.scene.am_collectionize
    configured = settings.target_asset_library_dir.strip()

    if configured:
        return os.path.abspath(bpy.path.abspath(configured))

    return default_asset_library_dir()


def resolve_asset_library_dir(context, create=True):
    directory = asset_library_dir_from_settings(context)
    if directory is None:
        raise ValueError(
            "Save the .blend file first (the asset library lives next to it), "
            "or set a Target Asset Library folder."
        )

    if create:
        os.makedirs(directory, exist_ok=True)

    if not os.path.isdir(directory):
        raise ValueError(f"Target Asset Library is not a folder: {directory}")

    ensure_asset_library_registered(directory)
    return directory


def ensure_asset_library_registered(directory):
    libraries = bpy.context.preferences.filepaths.asset_libraries
    wanted = _normalized_path(directory)
    library_name = project_asset_library_name()

    for library in libraries:
        if _normalized_path(bpy.path.abspath(library.path)) == wanted:
            library.name = library_name
            _configure_asset_library(library)
            return library

    library = libraries.new(name=library_name, directory=directory)
    _configure_asset_library(library)
    return library


def find_registered_asset_library(directory):
    wanted = _normalized_path(directory)

    for library in bpy.context.preferences.filepaths.asset_libraries:
        if _normalized_path(bpy.path.abspath(library.path)) == wanted:
            return library

    return None


def disconnect_asset_library(directory):
    libraries = bpy.context.preferences.filepaths.asset_libraries
    library = find_registered_asset_library(directory)

    if library is None:
        return False

    libraries.remove(library)
    _save_user_preferences()
    return True


def scan_asset_library_files(directory):
    if not directory or not os.path.isdir(directory):
        return []

    files = []
    for entry in os.scandir(directory):
        if not entry.is_file() or not entry.name.lower().endswith(".blend"):
            continue

        filename = entry.name
        display_name = (
            filename[: -len(ASSET_FILE_SUFFIX)]
            if filename.endswith(ASSET_FILE_SUFFIX)
            else os.path.splitext(filename)[0]
        )
        stat = entry.stat()
        files.append(
            {
                "name": display_name,
                "filename": filename,
                "filepath": entry.path,
                "size": stat.st_size,
                "size_text": _format_file_size(stat.st_size),
            }
        )

    files.sort(key=lambda item: item["name"].lower())
    return files


def delete_asset_file(filepath, library_dir):
    filepath = os.path.abspath(bpy.path.abspath(filepath))
    library_dir = os.path.abspath(bpy.path.abspath(library_dir))

    _ensure_inside_directory(filepath, library_dir)

    if not os.path.isfile(filepath) or not filepath.lower().endswith(".blend"):
        raise ValueError(f"Asset file was not found: {filepath}")

    deleted = []
    basename = os.path.basename(filepath)

    for entry in os.scandir(library_dir):
        if not entry.is_file():
            continue
        if entry.name == basename or (
            entry.name.startswith(basename)
            and entry.name[len(basename) :].isdigit()
        ):
            _ensure_inside_directory(entry.path, library_dir)
            os.remove(entry.path)
            deleted.append(entry.path)

    return deleted


def delete_asset_library_directory(directory):
    directory = os.path.abspath(bpy.path.abspath(directory))
    _ensure_safe_library_directory(directory)

    if os.path.isdir(directory):
        shutil.rmtree(directory)


def _save_user_preferences():
    try:
        bpy.ops.wm.save_userpref()
    except Exception as exc:
        print(f"Asset Master: could not save user preferences: {exc}")


def _clear_asset_mark(data_block):
    if data_block is not None and getattr(data_block, "asset_data", None):
        data_block.asset_clear()


def project_asset_library_name():
    if bpy.data.filepath:
        project_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
    else:
        project_name = "Untitled"

    prefs = addon_preferences()
    prefix = getattr(prefs, "library_name_prefix", "") if prefs else ""
    return f"{prefix}{sanitize_name(project_name)} Assets"


@persistent
def autodetect_project_library_handler(_filepath=None):
    autodetect_project_library()


def autodetect_project_library():
    directory = default_asset_library_dir()
    if directory and os.path.isdir(directory):
        try:
            ensure_asset_library_registered(directory)
        except Exception as exc:
            print(f"Asset Master: could not register project asset library: {exc}")


def unique_asset_identity(directory, requested_name):
    base = sanitize_name(requested_name)
    index = 0

    while True:
        suffix = "" if index == 0 else f"_{index:03d}"
        asset_name = f"{base}{suffix}"
        filepath = os.path.join(directory, f"{asset_name}{ASSET_FILE_SUFFIX}")

        if not os.path.exists(filepath) and not _local_collection_exists(asset_name):
            return asset_name, filepath

        index += 1


def asset_filepath(directory, asset_name):
    return os.path.join(directory, f"{sanitize_name(asset_name)}{ASSET_FILE_SUFFIX}")


def compute_pivot_matrix(context, objects, use_cursor):
    if use_cursor:
        return Matrix.Translation(context.scene.cursor.location.copy())

    points = []
    for obj in objects:
        points.extend(_object_bound_points(obj))

    if not points:
        return Matrix.Identity(4)

    min_x = min(p.x for p in points)
    max_x = max(p.x for p in points)
    min_y = min(p.y for p in points)
    max_y = max(p.y for p in points)
    min_z = min(p.z for p in points)

    # Bounding-box bottom center: the natural "stands on the floor" pivot.
    pivot = Vector(((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, min_z))
    return Matrix.Translation(pivot)


def _object_bound_points(obj, matrix=None, depth=0):
    matrix = obj.matrix_world if matrix is None else matrix

    # Collection instances have no own geometry; expand into the instanced
    # collection so pivots and thumbnails frame what is actually visible.
    if (
        obj.instance_type == "COLLECTION"
        and obj.instance_collection is not None
        and depth < 4
    ):
        collection = obj.instance_collection
        offset = Matrix.Translation(-Vector(collection.instance_offset))
        points = []
        for inner in collection.all_objects:
            points.extend(
                _object_bound_points(
                    inner,
                    matrix @ offset @ inner.matrix_world,
                    depth + 1,
                )
            )
        if points:
            return points

    if obj.type in _POINT_LIKE_TYPES:
        return [matrix.translation.copy()]

    return [matrix @ Vector(corner) for corner in obj.bound_box]


def create_export_collection(asset_name, source_objects, pivot_matrix):
    source_objects = list(dict.fromkeys(source_objects))

    # Objects referenced by modifiers, constraints, or curve settings must
    # travel with the asset and be rebased with it, otherwise deformers
    # (Curve, Mirror, Boolean, Lattice, Armature, hooks, ...) evaluate
    # against targets that stayed at their old world positions and the
    # instanced result looks completely broken.
    dependencies = _gather_external_dependencies(source_objects)
    export_objects = source_objects + dependencies

    export_collection = bpy.data.collections.new(asset_name)
    export_collection.instance_offset = (0.0, 0.0, 0.0)

    pivot_inverse = pivot_matrix.inverted()
    source_world_matrices = {obj: obj.matrix_world.copy() for obj in export_objects}
    copies = {}
    material_copies = {}
    created_data = []

    for original in export_objects:
        copied = original.copy()

        if original.data is not None:
            copied.data = original.data.copy()
            _clear_asset_mark(copied.data)
            created_data.append(copied.data)

            if hasattr(copied.data, "materials"):
                for index, material in enumerate(copied.data.materials):
                    if material is None:
                        continue
                    if material not in material_copies:
                        material_copy = material.copy()
                        _clear_asset_mark(material_copy)
                        material_copies[material] = material_copy
                        created_data.append(material_copy)
                    copied.data.materials[index] = material_copies[material]

        _clear_asset_mark(copied)
        export_collection.objects.link(copied)
        copies[original] = copied

    _remap_object_references(copies)

    setup_scene = bpy.context.scene
    setup_scene.collection.children.link(export_collection)
    try:
        # Preserve internal hierarchy, then explicitly restore each copy to the
        # rebased world matrix. Some imported assets carry matrix_parent_inverse
        # values that otherwise rotate/offset children after their parent is copied.
        for original, copied in copies.items():
            copied.parent = copies.get(original.parent)
            copied.matrix_parent_inverse = Matrix.Identity(4)

        bpy.context.view_layer.update()

        # Parents must receive their rebased matrix before their children:
        # a child's matrix_world assignment is computed against the parent's
        # current world matrix.
        for original, copied in sorted(
            copies.items(), key=lambda pair: _hierarchy_depth(pair[0])
        ):
            copied.matrix_world = pivot_inverse @ source_world_matrices[original]

        bpy.context.view_layer.update()
    finally:
        setup_scene.collection.children.unlink(export_collection)

    export_collection.asset_mark()
    if export_collection.asset_data:
        export_collection.asset_data.description = "Generated by Asset Master Collectionize"

    return (
        export_collection,
        list(copies.values()),
        created_data,
        [dep.name for dep in dependencies],
    )


def _gather_external_dependencies(source_objects):
    included = set(source_objects)
    queue = list(source_objects)
    dependencies = []

    while queue:
        obj = queue.pop()
        for dep in _iter_object_dependencies(obj):
            if dep is None or dep in included:
                continue
            included.add(dep)
            dependencies.append(dep)
            queue.append(dep)

    return dependencies


def _iter_object_dependencies(obj):
    for modifier in getattr(obj, "modifiers", ()):
        yield from _iter_pointer_objects(modifier)
        if modifier.type == "NODES":
            yield from _iter_id_property_objects(modifier)

    for modifier in getattr(obj, "grease_pencil_modifiers", ()):
        yield from _iter_pointer_objects(modifier)

    for constraint in obj.constraints:
        yield from _iter_pointer_objects(constraint)
        if constraint.type == "ARMATURE":
            for target in constraint.targets:
                yield target.target

    data = obj.data
    if data is not None:
        for attr in ("bevel_object", "taper_object"):
            yield getattr(data, attr, None)


def _iter_pointer_objects(struct):
    for prop in struct.bl_rna.properties:
        if prop.type != "POINTER":
            continue
        value = getattr(struct, prop.identifier, None)
        if isinstance(value, bpy.types.Object):
            yield value


def _iter_id_property_objects(struct):
    for key in struct.keys():
        try:
            value = struct[key]
        except Exception:
            continue
        if isinstance(value, bpy.types.Object):
            yield value


def _remap_object_references(copies):
    for original, copied in copies.items():
        for modifier in getattr(copied, "modifiers", ()):
            _remap_pointer_objects(modifier, copies)
            if modifier.type == "NODES":
                _remap_id_property_objects(modifier, copies)

        for modifier in getattr(copied, "grease_pencil_modifiers", ()):
            _remap_pointer_objects(modifier, copies)

        for constraint in copied.constraints:
            _remap_pointer_objects(constraint, copies)
            if constraint.type == "ARMATURE":
                for target in constraint.targets:
                    if target.target in copies:
                        target.target = copies[target.target]

        data = copied.data
        if data is not None:
            for attr in ("bevel_object", "taper_object"):
                value = getattr(data, attr, None)
                if value is not None and value in copies:
                    setattr(data, attr, copies[value])


def _remap_pointer_objects(struct, mapping):
    for prop in struct.bl_rna.properties:
        if prop.type != "POINTER" or prop.is_readonly:
            continue
        value = getattr(struct, prop.identifier, None)
        if isinstance(value, bpy.types.Object) and value in mapping:
            setattr(struct, prop.identifier, mapping[value])


def _remap_id_property_objects(struct, mapping):
    for key in struct.keys():
        try:
            value = struct[key]
        except Exception:
            continue
        if isinstance(value, bpy.types.Object) and value in mapping:
            struct[key] = mapping[value]


def _hierarchy_depth(obj):
    depth = 0
    parent = obj.parent
    while parent is not None and depth < 64:
        depth += 1
        parent = parent.parent
    return depth


def addon_preferences():
    addon = bpy.context.preferences.addons.get(__package__)
    return getattr(addon, "preferences", None)


def preview_size_from_preferences():
    prefs = addon_preferences()
    try:
        return int(prefs.preview_size)
    except (AttributeError, TypeError, ValueError):
        return 256


def render_preview_png(collection, size=None):
    # Deliberately NOT bpy.ops.ed.lib_id_generate_preview: that renders on a
    # background job thread and crashes Blender when the collection is removed
    # before the job finishes. This renders synchronously instead and returns
    # the path of the rendered PNG (or None on failure).
    if size is None:
        size = preview_size_from_preferences()

    try:
        return _render_collection_preview(collection, size)
    except Exception as exc:
        print(f"Asset Master: preview generation failed: {exc}")
        return None


def queue_asset_postprocess(
    filepath,
    collection_name,
    png_path=None,
    size=None,
    pack_textures=False,
):
    # bpy.data.libraries.write does not store ID previews, so a headless
    # Blender opens the asset file, loads the rendered PNG into the
    # collection preview, optionally packs external textures, and saves.
    # No rendering happens there.
    if not png_path and not pack_textures:
        return

    binary_path = bpy.app.binary_path
    if not binary_path or not os.path.exists(binary_path):
        return

    if size is None:
        size = preview_size_from_preferences()

    script = f"""
import bpy, os

filepath = {filepath!r}
png_path = {png_path!r}
collection_name = {collection_name!r}
size = {size!r}
pack_textures = {pack_textures!r}

bpy.ops.wm.open_mainfile(filepath=filepath, load_ui=False)
collection = bpy.data.collections.get(collection_name)
if collection is not None:
    if png_path and os.path.exists(png_path):
        image = bpy.data.images.load(png_path)
        pixels = list(image.pixels)
        bpy.data.images.remove(image)

        preview = collection.preview_ensure()
        preview.image_size = (size, size)
        preview.image_pixels_float = pixels
        preview.is_image_custom = True
        preview.icon_size = (size, size)
        preview.icon_pixels_float = pixels
        preview.is_icon_custom = True

    if pack_textures:
        try:
            bpy.ops.file.pack_all()
        except Exception as exc:
            print(f"Asset Master: packing textures failed: {{exc}}")

    bpy.ops.wm.save_mainfile(filepath=filepath, compress=True)

for path in (png_path, __file__):
    if not path:
        continue
    try:
        os.remove(path)
    except OSError:
        pass
"""

    try:
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            suffix="_am_preview_inject.py",
            encoding="utf-8",
            delete=False,
        )
        with handle:
            handle.write(script)

        subprocess.Popen(
            [binary_path, "--background", "--factory-startup", "--python", handle.name],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        print(f"Asset Master: preview injection skipped: {exc}", file=sys.stderr)


def _render_collection_preview(collection, size):
    points = []
    for obj in collection.all_objects:
        points.extend(_object_bound_points(obj))

    if not points:
        return None

    center = sum(points, Vector()) / len(points)
    radius = max((point - center).length for point in points) or 1.0

    scene = bpy.data.scenes.new("AM_Preview_Temp")
    camera_data = bpy.data.cameras.new("AM_Preview_Cam")
    camera = bpy.data.objects.new("AM_Preview_Cam", camera_data)
    fd, render_path = tempfile.mkstemp(suffix="_am_preview.png")
    os.close(fd)

    # Keep viewport-hidden helpers (deform curves, lattices, rig empties)
    # out of the thumbnail without changing the asset's render behavior.
    render_flag_restore = []
    for obj in collection.all_objects:
        if obj.hide_viewport and not obj.hide_render:
            render_flag_restore.append(obj)
            obj.hide_render = True

    try:
        scene.collection.children.link(collection)
        scene.collection.objects.link(camera)
        scene.camera = camera

        direction = Vector((1.0, -1.0, 0.8)).normalized()
        distance = radius / math.tan(camera_data.angle * 0.5) + radius
        camera.location = center + direction * distance
        camera.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
        camera_data.clip_start = max(distance * 0.01, 0.001)
        camera_data.clip_end = distance + radius * 4.0

        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "TEXTURE"
        scene.render.resolution_x = size
        scene.render.resolution_y = size
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = True
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.filepath = render_path
        scene.view_settings.view_transform = "Standard"

        bpy.ops.render.render(write_still=True, scene=scene.name)
        return render_path
    except Exception:
        try:
            os.remove(render_path)
        except OSError:
            pass
        raise
    finally:
        for obj in render_flag_restore:
            obj.hide_render = False
        bpy.data.scenes.remove(scene)
        if camera.name in bpy.data.objects:
            bpy.data.objects.remove(camera)
        if camera_data.name in bpy.data.cameras:
            bpy.data.cameras.remove(camera_data)


def write_asset_file(filepath, export_collection, attempts=5):
    # A queued post-process (preview/pack) may still hold the file for a
    # moment when an asset is re-exported quickly; retry briefly.
    for attempt in range(attempts):
        try:
            bpy.data.libraries.write(
                filepath,
                {export_collection},
                path_remap="RELATIVE_ALL",
                fake_user=True,
                compress=True,
            )
            return
        except (OSError, RuntimeError):
            if attempt == attempts - 1:
                raise
            time.sleep(0.4)


def link_collection_from_asset(filepath, collection_name):
    existing = find_linked_collection_from_asset(filepath, collection_name)
    if existing is not None:
        library = existing.library
        library.reload()
        reloaded = find_linked_collection_from_asset(filepath, collection_name)
        if reloaded is not None:
            return reloaded

    with bpy.data.libraries.load(filepath, link=True, relative=True) as (data_src, data_dst):
        if collection_name not in data_src.collections:
            raise ValueError(f"Collection was not found in asset file: {collection_name}")
        data_dst.collections = [collection_name]

    linked_collection = data_dst.collections[0]
    if linked_collection is None:
        raise ValueError(f"Failed to link collection from asset file: {collection_name}")

    return linked_collection


def find_linked_collection_from_asset(filepath, collection_name):
    wanted_path = _normalized_path(bpy.path.abspath(filepath))

    for collection in bpy.data.collections:
        if collection.name != collection_name or collection.library is None:
            continue
        library_path = _normalized_path(bpy.path.abspath(collection.library.filepath))
        if library_path == wanted_path:
            return collection

    return None


def create_collection_instance(context, linked_collection, instance_name, pivot_matrix, parent_collection=None):
    instance = bpy.data.objects.new(instance_name, None)
    instance.empty_display_type = "PLAIN_AXES"
    instance.empty_display_size = 0.001
    instance.instance_type = "COLLECTION"
    instance.instance_collection = linked_collection

    target_collection = parent_collection or context.collection or context.scene.collection
    target_collection.objects.link(instance)
    instance.matrix_world = pivot_matrix
    context.view_layer.update()
    return instance


def align_collection_instance_to_snapshot(
    context,
    instance,
    source_objects,
    source_world_matrices,
    tolerance=1e-5,
):
    linked_collection = instance.instance_collection
    if linked_collection is None:
        return {"corrected": False, "max_delta": 0.0, "reason": "no collection"}

    linked_objects = list(linked_collection.all_objects)
    if not linked_objects or not source_objects:
        return {"corrected": False, "max_delta": 0.0, "reason": "empty collection"}

    if len(linked_objects) != len(source_objects):
        return {
            "corrected": False,
            "max_delta": 0.0,
            "reason": "object count mismatch",
        }

    before = _instance_matrix_deltas(
        context,
        instance,
        linked_objects,
        source_world_matrices,
    )

    if before["missing"] or before["max_delta"] <= tolerance:
        return {
            "corrected": False,
            "max_delta": before["max_delta"],
            "reason": "already aligned" if not before["missing"] else "missing evaluated objects",
        }

    correction = None
    for linked_object, expected_matrix in zip(linked_objects, source_world_matrices):
        actual_matrix = before["matrices"].get(linked_object.name)
        if actual_matrix is None:
            continue
        correction = expected_matrix @ actual_matrix.inverted_safe()
        break

    if correction is None:
        return {
            "corrected": False,
            "max_delta": before["max_delta"],
            "reason": "no correction anchor",
        }

    instance.matrix_world = correction @ instance.matrix_world
    context.view_layer.update()

    after = _instance_matrix_deltas(
        context,
        instance,
        linked_objects,
        source_world_matrices,
    )

    return {
        "corrected": True,
        "max_delta": after["max_delta"],
        "reason": "corrected",
    }


def unlink_conflicting_linked_asset_collections(
    parent_collection,
    asset_dir,
    base_name,
    keep_collection=None,
):
    if parent_collection is None or not asset_dir or not base_name:
        return []

    asset_dir = os.path.abspath(bpy.path.abspath(asset_dir))
    base_name = sanitize_name(base_name)
    conflicts = []

    for child in tuple(parent_collection.children):
        if child.library is None:
            continue
        if not _is_name_or_numbered_variant(child.name, base_name):
            continue

        library_path = os.path.abspath(bpy.path.abspath(child.library.filepath))
        if not _is_asset_library_file(library_path, asset_dir):
            continue

        parent_collection.children.unlink(child)
        conflicts.append(child.name)

        if child != keep_collection and child.users == 0:
            bpy.data.collections.remove(child)

    return conflicts


def purge_unused_linked_asset_collections(asset_dir, base_name=None):
    if not asset_dir:
        return []

    asset_dir = os.path.abspath(bpy.path.abspath(asset_dir))
    base_name = sanitize_name(base_name) if base_name else None
    purged = []

    for collection in tuple(bpy.data.collections):
        if collection.library is None or collection.users != 0:
            continue
        if base_name and not _is_name_or_numbered_variant(collection.name, base_name):
            continue

        library_path = os.path.abspath(bpy.path.abspath(collection.library.filepath))
        if not _is_asset_library_file(library_path, asset_dir):
            continue

        purged.append(collection.name)
        bpy.data.collections.remove(collection)

    return purged


def is_user_facing_collection(collection):
    if collection.library is not None:
        return False
    if collection.name == BACKUP_ROOT_NAME:
        return False

    backup_root = bpy.data.collections.get(BACKUP_ROOT_NAME)
    if backup_root is not None and _collection_contains(backup_root, collection):
        return False

    return True


def first_parent_collection(scene, target):
    if target.name in scene.collection.children:
        return scene.collection

    for collection in bpy.data.collections:
        if collection.library is None and target.name in collection.children:
            return collection

    return scene.collection


def rename_to_backup(collection):
    collection.name = f"{collection.name}_backup"


def move_collection_to_backup(context, source_collection):
    root = _ensure_backup_root(context.scene)

    for obj in source_collection.all_objects:
        obj.select_set(False)

    for parent in _collection_parents(source_collection):
        if parent != root:
            parent.children.unlink(source_collection)

    if source_collection.name not in root.children:
        root.children.link(source_collection)

    source_collection.hide_viewport = True
    source_collection.hide_render = True
    return source_collection


def move_originals_to_backup(context, selected_objects, asset_name):
    root = _ensure_backup_root(context.scene)

    backup = bpy.data.collections.new(f"{asset_name}_backup")
    root.children.link(backup)

    world_matrices = {obj: obj.matrix_world.copy() for obj in selected_objects}

    for obj in selected_objects:
        backup.objects.link(obj)
        for collection in tuple(obj.users_collection):
            if collection != backup:
                collection.objects.unlink(obj)
        obj.matrix_world = world_matrices[obj]
        obj.select_set(False)

    backup.hide_viewport = True
    backup.hide_render = True
    return backup


def refresh_asset_browsers(context):
    try:
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.ui_type == "ASSETS":
                    with context.temp_override(window=window, area=area):
                        bpy.ops.asset.library_refresh()
    except Exception as exc:
        print(f"Asset Master: asset browser refresh skipped: {exc}")


def cleanup_export_data(export_collection, created_objects, created_data):
    if export_collection.name in bpy.data.collections:
        bpy.data.collections.remove(export_collection)

    for obj in created_objects:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj)

    for data in created_data:
        if data.users == 0:
            _remove_id_data(data)


def _ensure_backup_root(scene):
    root = bpy.data.collections.get(BACKUP_ROOT_NAME)

    if root is None:
        root = bpy.data.collections.new(BACKUP_ROOT_NAME)
        scene.collection.children.link(root)
    elif not _collection_contains(scene.collection, root):
        scene.collection.children.link(root)

    root.hide_viewport = True
    root.hide_render = True
    return root


def _collection_parents(target):
    parents = []
    candidates = [scene.collection for scene in bpy.data.scenes]
    candidates.extend(c for c in bpy.data.collections if c.library is None)

    for candidate in candidates:
        if any(child == target for child in candidate.children):
            parents.append(candidate)

    return parents


def _local_collection_exists(name):
    collection = bpy.data.collections.get(name)
    return collection is not None and collection.library is None


def _configure_asset_library(library):
    if hasattr(library, "import_method"):
        library.import_method = "LINK"
    if hasattr(library, "use_relative_path"):
        library.use_relative_path = True


def _normalized_path(path):
    return os.path.normcase(os.path.abspath(path))


def _ensure_inside_directory(filepath, directory):
    filepath = os.path.abspath(filepath)
    directory = os.path.abspath(directory)

    try:
        common = os.path.commonpath([filepath, directory])
    except ValueError as exc:
        raise ValueError(f"Path is outside the asset library: {filepath}") from exc

    if _normalized_path(common) != _normalized_path(directory):
        raise ValueError(f"Path is outside the asset library: {filepath}")


def _ensure_safe_library_directory(directory):
    directory = os.path.abspath(directory)
    parent = os.path.dirname(directory)

    if not directory or directory == parent:
        raise ValueError("Refusing to delete a filesystem root.")

    home = os.path.expanduser("~")
    unsafe = {
        _normalized_path(os.getcwd()),
        _normalized_path(home),
        _normalized_path(os.path.dirname(home)),
    }

    if _normalized_path(directory) in unsafe:
        raise ValueError(f"Refusing to delete unsafe folder: {directory}")


def _is_name_or_numbered_variant(name, base_name):
    if name == base_name:
        return True

    prefix = f"{base_name}_"
    return name.startswith(prefix) and name[len(prefix) :].isdigit()


def _is_asset_library_file(filepath, asset_dir):
    try:
        _ensure_inside_directory(filepath, asset_dir)
    except ValueError:
        return False

    filename = os.path.basename(filepath).lower()
    return filename.endswith(ASSET_FILE_SUFFIX)


def _instance_matrix_deltas(context, instance, linked_objects, expected_matrices):
    context.view_layer.update()

    depsgraph = context.evaluated_depsgraph_get()
    instance_matrices = {}

    for object_instance in depsgraph.object_instances:
        if not object_instance.is_instance:
            continue

        parent = getattr(object_instance, "parent", None)
        if parent is None or parent.original != instance:
            continue

        obj = object_instance.object
        original = obj.original if obj and obj.original else obj
        if original is not None:
            instance_matrices[original.name] = object_instance.matrix_world.copy()

    max_delta = 0.0
    missing = 0

    for linked_object, expected_matrix in zip(linked_objects, expected_matrices):
        actual_matrix = instance_matrices.get(linked_object.name)
        if actual_matrix is None:
            missing += 1
            continue

        delta = max(
            abs(actual_matrix[row][column] - expected_matrix[row][column])
            for row in range(4)
            for column in range(4)
        )
        max_delta = max(max_delta, delta)

    return {
        "matrices": instance_matrices,
        "max_delta": max_delta,
        "missing": missing,
    }


def _format_file_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024.0


def _collection_contains(parent_collection, target):
    if parent_collection == target:
        return True

    for child in parent_collection.children:
        if _collection_contains(child, target):
            return True

    return False


def _remove_id_data(data):
    collection_name = {
        "ARMATURE": "armatures",
        "CAMERA": "cameras",
        "CURVE": "curves",
        "GREASEPENCIL": "grease_pencils",
        "LATTICE": "lattices",
        "LIGHT": "lights",
        "MATERIAL": "materials",
        "MESH": "meshes",
        "META": "metaballs",
        "POINTCLOUD": "pointclouds",
        "SPEAKER": "speakers",
        "CURVES": "hair_curves",
        "VOLUME": "volumes",
    }.get(data.id_type)

    if collection_name is None:
        return

    collection = getattr(bpy.data, collection_name, None)
    if collection is not None and data.name in collection:
        collection.remove(data)
