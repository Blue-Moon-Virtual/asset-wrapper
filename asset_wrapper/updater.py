"""Lightweight, self-contained update system.

Checks the GitHub Releases of the configured repository, compares the latest
tag against this add-on's bl_info version, and offers a one-click download +
install from the add-on preferences (BlenderKit-style).

Design notes:
- Network access happens on a worker thread so the UI never blocks.
- The worker only mutates a plain module-level dict (safe off the main
  thread). All ``bpy`` access — redrawing, installing — stays on the main
  thread, driven by a polling timer.
- A release must attach the built add-on ``.zip`` (see build_release.py).
  The source "zipball" is intentionally not used: it nests the code in a
  repo-named folder and will not install cleanly.
"""

import json
import os
import ssl
import sys
import tempfile
import threading
import urllib.request

import bpy

ADDON_PACKAGE = __package__  # "asset_wrapper"
_USER_AGENT = "AssetWrapper-Updater"
_REQUEST_TIMEOUT = 15

# Shared state, read by the preferences draw code, written by the worker.
state = {
    "checking": False,
    "checked": False,
    "update_available": False,
    "latest_version": "",
    "download_url": "",
    "error": "",
}

_poll_registered = False


# --------------------------------------------------------------------- helpers
def current_version_tuple():
    module = sys.modules.get(ADDON_PACKAGE)
    version = getattr(module, "bl_info", {}).get("version", (0, 0, 0))
    return tuple(int(part) for part in version)


def current_version_text():
    return ".".join(str(part) for part in current_version_tuple())


def _parse_version(text):
    digits = []
    current = ""
    for char in str(text):
        if char.isdigit():
            current += char
        elif current:
            digits.append(int(current))
            current = ""
    if current:
        digits.append(int(current))
    return tuple(digits) if digits else (0,)


def _addon_preferences():
    addon = bpy.context.preferences.addons.get(ADDON_PACKAGE)
    return getattr(addon, "preferences", None)


def _repository():
    prefs = _addon_preferences()
    repo = (getattr(prefs, "update_repository", "") or "").strip()
    return repo.rstrip("/")


# ----------------------------------------------------------------- redraw timer
def _redraw_preferences():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "PREFERENCES":
                area.tag_redraw()


def _poll():
    _redraw_preferences()
    if state["checking"]:
        return 0.4
    global _poll_registered
    _poll_registered = False
    return None


def _start_poll():
    global _poll_registered
    if not _poll_registered:
        _poll_registered = True
        bpy.app.timers.register(_poll)


# --------------------------------------------------------------------- checking
def _check_worker(repo, current):
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "application/vnd.github+json",
            },
        )
        context = ssl.create_default_context()
        with urllib.request.urlopen(
            request, timeout=_REQUEST_TIMEOUT, context=context
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))

        tag = payload.get("tag_name") or payload.get("name") or ""
        latest = _parse_version(tag)

        download_url = ""
        for asset in payload.get("assets", []):
            name = (asset.get("name") or "").lower()
            if name.endswith(".zip"):
                download_url = asset.get("browser_download_url", "")
                break

        state["latest_version"] = tag.lstrip("vV ") or ".".join(map(str, latest))
        state["download_url"] = download_url
        state["update_available"] = latest > current
        state["error"] = "" if (download_url or not (latest > current)) else (
            "Update found but the release has no installable .zip asset."
        )
    except Exception as exc:  # noqa: BLE001 - surface any network/parse error
        state["error"] = str(exc)
        state["update_available"] = False
    finally:
        state["checking"] = False
        state["checked"] = True


def check_for_updates():
    repo = _repository()
    if not repo:
        state["error"] = "Set a repository (owner/name) in the field below."
        state["checked"] = True
        return False

    if state["checking"]:
        return True

    state["checking"] = True
    state["error"] = ""
    state["update_available"] = False
    state["latest_version"] = ""
    state["download_url"] = ""

    thread = threading.Thread(
        target=_check_worker,
        args=(repo, current_version_tuple()),
        daemon=True,
    )
    thread.start()
    _start_poll()
    return True


# --------------------------------------------------------------------- install
def _download(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    with urllib.request.urlopen(
        request, timeout=_REQUEST_TIMEOUT * 4, context=context
    ) as response, open(destination, "wb") as handle:
        handle.write(response.read())


# --------------------------------------------------------------------- startup
def _startup_check():
    prefs = _addon_preferences()
    if prefs is not None and getattr(prefs, "check_on_startup", False):
        check_for_updates()
    return None


def on_register():
    bpy.app.timers.register(_startup_check, first_interval=3.0)


def on_unregister():
    for timer in (_poll, _startup_check):
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)


# ------------------------------------------------------------------- operators
class AW_OT_check_for_updates(bpy.types.Operator):
    bl_idname = "asset_wrapper.check_for_updates"
    bl_label = "Check for Updates"
    bl_description = "Check the configured repository for a newer release"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        if not check_for_updates():
            self.report({"WARNING"}, state["error"] or "Could not start update check.")
            return {"CANCELLED"}
        return {"FINISHED"}


class AW_OT_install_update(bpy.types.Operator):
    bl_idname = "asset_wrapper.install_update"
    bl_label = "Install Update"
    bl_description = "Download and install the latest release, then restart Blender"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        url = state.get("download_url")
        if not url:
            self.report({"ERROR"}, "No downloadable release found. Check again first.")
            return {"CANCELLED"}

        context.window.cursor_set("WAIT")
        try:
            fd, zip_path = tempfile.mkstemp(suffix="_asset_wrapper_update.zip")
            os.close(fd)
            _download(url, zip_path)

            bpy.ops.preferences.addon_install(filepath=zip_path, overwrite=True)
            bpy.ops.preferences.addon_enable(module=ADDON_PACKAGE)
            bpy.ops.wm.save_userpref()
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Update failed: {exc}")
            return {"CANCELLED"}
        finally:
            context.window.cursor_set("DEFAULT")
            try:
                os.remove(zip_path)
            except OSError:
                pass

        state["update_available"] = False
        self.report(
            {"INFO"},
            "Update installed. Restart Blender to finish.",
        )
        return {"FINISHED"}


# ------------------------------------------------------------------------- draw
def draw(layout, prefs):
    box = layout.box()
    header = box.row(align=True)
    header.label(text="Updates", icon="FILE_REFRESH")
    header.label(text=f"Installed: {current_version_text()}")

    body = box.column()

    if state["checking"]:
        body.label(text="Checking for updates…", icon="SORTTIME")
    elif state["update_available"]:
        row = body.row()
        row.alert = True
        row.label(
            text=f"Update available: {state['latest_version']}",
            icon="IMPORT",
        )
        install = body.row()
        install.scale_y = 1.3
        install.operator("asset_wrapper.install_update", icon="IMPORT")
    elif state["error"]:
        body.label(text=state["error"], icon="ERROR")
    elif state["checked"]:
        body.label(text="You are up to date.", icon="CHECKMARK")

    actions = body.row(align=True)
    actions.enabled = not state["checking"]
    actions.operator("asset_wrapper.check_for_updates", icon="FILE_REFRESH")

    settings = box.column(align=True)
    settings.use_property_split = True
    settings.use_property_decorate = False
    settings.prop(prefs, "update_repository")
    settings.prop(prefs, "check_on_startup")
