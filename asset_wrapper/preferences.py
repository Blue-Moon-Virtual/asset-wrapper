import bpy

from . import updater


class AssetWrapperPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    library_name_prefix: bpy.props.StringProperty(
        name="Library Name Prefix",
        description=(
            "Prefix for auto-registered project asset libraries, "
            "e.g. 'BM - ' turns 'MyProject Assets' into 'BM - MyProject Assets'"
        ),
        default="",
    )

    preview_size: bpy.props.EnumProperty(
        name="Thumbnail Size",
        description="Resolution of the rendered asset thumbnails",
        items=(
            ("128", "128 px", "Small and fast"),
            ("256", "256 px", "Default, crisp in the Asset Browser"),
            ("512", "512 px", "Large, slightly slower to generate"),
        ),
        default="256",
    )

    pack_textures: bpy.props.BoolProperty(
        name="Pack Textures into Asset Files",
        description=(
            "Embed external image textures inside each asset .blend so assets "
            "keep working on other machines and synced drives. Increases "
            "asset file size"
        ),
        default=True,
    )

    update_repository: bpy.props.StringProperty(
        name="Repository",
        description="GitHub repository to check for updates, as owner/name",
        default="bluemoonvirtual/asset-wrapper",
    )

    check_on_startup: bpy.props.BoolProperty(
        name="Check for Updates on Startup",
        description="Quietly check for a newer release when Blender starts",
        default=False,
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
        updater.draw(layout, self)

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
        ).url = "https://github.com/bluemoonvirtual/asset-wrapper/issues"
