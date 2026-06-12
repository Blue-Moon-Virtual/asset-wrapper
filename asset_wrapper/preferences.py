import bpy

from . import addon_updater_ops


@addon_updater_ops.make_annotations
class AssetWrapperPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    library_name_prefix = bpy.props.StringProperty(
        name="Library Name Prefix",
        description=(
            "Prefix for auto-registered project asset libraries, "
            "e.g. 'BM - ' turns 'MyProject Assets' into 'BM - MyProject Assets'"
        ),
        default="",
    )

    preview_size = bpy.props.EnumProperty(
        name="Thumbnail Size",
        description="Resolution of the rendered asset thumbnails",
        items=(
            ("128", "128 px", "Small and fast"),
            ("256", "256 px", "Default, crisp in the Asset Browser"),
            ("512", "512 px", "Large, slightly slower to generate"),
        ),
        default="256",
    )

    pack_textures = bpy.props.BoolProperty(
        name="Pack Textures into Asset Files",
        description=(
            "Embed external image textures inside each asset .blend so assets "
            "keep working on other machines and synced drives. Increases "
            "asset file size"
        ),
        default=True,
    )

    # --- Properties required by the CGCookie addon updater ---
    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )
    updater_interval_months = bpy.props.IntProperty(
        name="Months",
        description="Number of months between checking for updates",
        default=0,
        min=0,
    )
    updater_interval_days = bpy.props.IntProperty(
        name="Days",
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31,
    )
    updater_interval_hours = bpy.props.IntProperty(
        name="Hours",
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23,
    )
    updater_interval_minutes = bpy.props.IntProperty(
        name="Minutes",
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59,
    )

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(self, "library_name_prefix")
        col.prop(self, "preview_size")
        col.prop(self, "pack_textures")

        layout.separator()
        # Updater settings box (check now, auto-check, intervals, install).
        addon_updater_ops.update_settings_ui(self, context)

        layout.separator()
        footer = layout.box().row()
        footer.label(text="Asset Wrapper", icon="OUTLINER_OB_GROUP_INSTANCE")
        links = footer.row(align=True)
        links.alignment = "RIGHT"
        links.operator(
            "wm.url_open", text="Blue Moon Virtual", icon="URL"
        ).url = "https://www.bm-3d.de"
        links.operator(
            "wm.url_open", text="Report an Issue", icon="HELP"
        ).url = "https://github.com/Blue-Moon-Virtual/asset-wrapper/issues"
