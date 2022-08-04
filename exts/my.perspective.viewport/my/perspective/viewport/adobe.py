"""
This credit goes to our beloved TA John Wolford
"""

from ctypes import alignment
import os
import asyncio
import numpy as np

from functools import partial
from typing import List, Tuple, Callable, Dict

import omni.ext
import omni.ui as ui
import omni.kit.viewport_legacy as vp
import omni.kit.capture.viewport
from omni.kit.window.filepicker import FilePickerDialog, dialog
from omni.kit.widget.filebrowser import FileBrowserItem
import carb.settings

from .cameras_model import CamerasModel

import subprocess
import glob

COLUMN_WIDTH_PIXELS = 150

DEFAULT_FILE_EXTENSION_TYPES = [
    (".png", "PNG Image Format"),
    (".jpg", "JPG Image Format")
]

# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class AdobeInterface():

    def _load_default_settings(self) -> dict:
        settings = carb.settings.get_settings()
        default_settings_path = settings.get_as_string("/exts/omni.pcg.adobeinterface/appSettings")

        default_settings = {}
        default_settings['directory'] = settings.get_as_string(f"{default_settings_path}/directory") or \
            carb.tokens.get_tokens_interface().resolve("${shared_documents}/adobeinterface")
        default_settings['file_extension'] = settings.get_as_string(f"{default_settings_path}/file_extension") or None
        return default_settings

    def _save_default_settings(default_settings: Dict):
        settings = carb.settings.get_settings()
        default_settings_path = settings.get_as_string("/exts/omni.pcg.adobeinterface/appSettings")
        settings.set_string(f"{default_settings_path}/directory", default_settings['directory'] or "")
        settings.set_string(f"{default_settings_path}/file_extension", default_settings['file_extension'] or "")

    def hide_window(self):
        """Hides and destroys the dialog window."""
        self.destroy_dialog()

    def click_apply(self):
        """Helper function to progammatically execute the apply callback.  Useful in unittests"""
        if self._dialog:
            self._dialog._widget._file_bar._on_apply()

    def click_cancel(self):
        """Helper function to progammatically execute the cancel callback.  Useful in unittests"""
        self._dialog._widget._file_bar._on_cancel()

    def destroy_dialog(self):
        if self._dialog:
            self._dialog.destroy()
        self._dialog = None

    def on_port(export_fn: Callable[[str, str, List[str]], None], dialog: FilePickerDialog, filename: str, dirname: str):
        AdobeInterface._save_default_settings({
            'directory': dirname,
            'file_postfix': dialog.get_file_postfix(),
            'file_extension': dialog.get_file_extension(),
        })

        selections = dialog.get_current_selections() or []
        dialog.hide()

        if export_fn:
            export_fn(filename, dirname, selections=selections, extension_str=dialog.get_file_extension())

    def export_handler(self, filename, dirname, selections, extension_str):
        if filename[-len(extension_str):] == extension_str:
            filename = filename[0:-len(extension_str)]

        self._expfilename = filename
        self._expfileextension = extension_str
        self._expdirname = dirname

        self.update_labels()

    def import_handler(self, filename, dirname, selections, extension_str):
        if filename[-len(extension_str):] == extension_str:
            filename = filename[0:-len(extension_str)]

        self._impfilename = filename
        self._impfileextension = extension_str
        self._impdirname = dirname

        self.update_labels()
        

    def on_exp_browse_clicked(self):
        default_settings = self._load_default_settings()
        filename = None
        directory = default_settings.get('directory')
        file_extension = default_settings.get('file_extension')

        self._dialog = FilePickerDialog(
            "Choose an Export Location",
            width=900,
            height=500,
            splitter_offset=260,
            enable_file_bar=True,
            enable_filename_input=True,
            enable_checkpoints=True,
            show_detail_view=False,
            show_only_collections=False,
            file_extension_options=DEFAULT_FILE_EXTENSION_TYPES,
            apply_button_label="Select",
            current_directory=directory,
            current_filename=filename,
            current_file_extension=file_extension,
        )

        self._dialog.set_click_apply_handler(partial(AdobeInterface.on_port, self.export_handler, self._dialog))

    def on_imp_browse_clicked(self):
        default_settings = self._load_default_settings()
        filename = None
        directory = default_settings.get('directory')
        file_extension = default_settings.get('file_extension')

        self._dialog = FilePickerDialog(
            "Choose an Import Location",
            width=900,
            height=500,
            splitter_offset=260,
            enable_file_bar=True,
            enable_filename_input=True,
            enable_checkpoints=True,
            show_detail_view=False,
            show_only_collections=False,
            file_extension_options=DEFAULT_FILE_EXTENSION_TYPES,
            apply_button_label="Select",
            current_directory=directory,
            current_filename=filename,
            current_file_extension=file_extension,
        )

        self._dialog.set_click_apply_handler(partial(AdobeInterface.on_port, self.import_handler, self._dialog))

    def on_exp_clear_clicked(self):
        self._expfilename = None
        self._expdirname = None
        self.update_labels()

    def on_imp_clear_clicked(self):
        self._impfilename = None
        self._impdirname = None
        self.update_labels()

    def update_labels(self):
        self._export_label.text = "Export Path: " + ((self._expdirname + self._expfilename)[0:8] + "..." if self._expfilename != None else "")
        self._import_label.text = "Import Path: " + ((self._impdirname + self._impfilename)[0:8] + "..." if self._impfilename != None else "")

    def save_view(self):
        print("Export Start")
        self.setup_dynamic_capture_options()
        print(self._expdirname)
        print(self._expfilename)
        print(self._expfileextension)
        self._capture_instance.start()
        print("Export End")

    def export_view(self):
        FNULL = open(os.devnull,'w')
        modImage=""
        
        list_of_files = glob.glob(f'{str(self._expdirname)}/*')
        latest_file = max(list_of_files, key=os.path.getctime)

        for char in range(0, len(latest_file)):
            if(latest_file[char] == '/'):
                modImage += r"\\"
            else:
                modImage += latest_file[char]
        # print(latest_file+"!!!!")
        # print(modImage+"!!!!mod")

        os.path.isfile(modImage)
        args = f"C:\\Program Files\\Adobe\\Adobe Photoshop 2022\\Photoshop.exe --open {modImage}"
        subprocess.call( args,stdout=FNULL,stderr=FNULL, shell=False)

    def import_image(self):
        print("Import")

    def setup_dynamic_capture_options(self):
        self._capture_instance.options.camera = self._camera_combo_model.get_current_camera()
        self._capture_instance.options.res_width = self._ui_res_width_input.model.get_value_as_int()
        self._capture_instance.options.res_height = self._ui_res_height_input.model.get_value_as_int()
        self._capture_instance.options.output_folder = self._expdirname
        self._capture_instance.options.file_name = self._expfilename
        self._capture_instance.options.file_type = self._expfileextension

    def setup_static_capture_options(self):
        # Capture Options
        
        self._capture_instance.options.movie_type = omni.kit.capture.viewport.CaptureMovieType.SEQUENCE

        # Render Options
        self._capture_instance.options.render_product = ""
        self._capture_instance.options.render_preset = omni.kit.capture.viewport.CaptureRenderPreset.RAY_TRACE
        self._capture_instance.options.debug_material_type = omni.kit.capture.viewport.CaptureDebugMaterialType.SHADED
        self._capture_instance.options.path_trace_spp = 1
        self._capture_instance.options.ptmb_subframes_per_frame = 1
        self._capture_instance.options.ptmb_fso = 0
        self._capture_instance.options.ptmb_fsc = 1
        self._capture_instance.options.real_time_settle_latency_frames = 0

        # Output Options
        self._capture_instance.options.capture_every_Nth_frames = -1
        self._capture_instance.options.overwrite_existing_frames = True
        self._capture_instance.options.save_alpha = False
        self._capture_instance.options.hdr_output = False

        print(type(self._capture_instance._viewport.get_viewport_window()),"HEREEEEE")
        
    def change_window_visibility(self, visible):
        self._window.visible = visible

    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def __init__(self):
        print("[omni.pcg.adobeinterface] Adobe Interface startup")

        viewport = vp.get_viewport_interface()
        self._viewport_window = viewport.get_viewport_window()
        print(type(self._viewport_window), "hiiiiiii")

        self._capture_instance = omni.kit.capture.viewport.CaptureExtension.get_instance()

        self._dialog  = None
        self._expfilename = None
        self._expfileextension = None
        self._expdirname = None
        self._impfilename = None
        self._impfileextension = None
        self._impdirname = None

        self._window = ui.Window("Adobe Omniverse Interface", width=500, height=200, visible = False)
        with self._window.frame:
            with ui.VStack():
                ui.Label("Export Settings", height = ui.Pixel(30), alignment=ui.Alignment.CENTER)
                with ui.HStack(height=ui.Pixel(30)):
                    self._export_label = ui.Label("Export Path: ", width=ui.Pixel(COLUMN_WIDTH_PIXELS))
                    ui.Button("Browse", clicked_fn=lambda: self.on_exp_browse_clicked())
                    ui.Button("Clear", clicked_fn=lambda: self.on_exp_clear_clicked())
                with ui.HStack(height=ui.Pixel(30)):
                    ui.Label("Camera:", width=ui.Pixel(COLUMN_WIDTH_PIXELS), alignment=ui.Alignment.LEFT_TOP)
                    self._camera_combo_model = CamerasModel()
                    self._ui_kit_combobox_camera_type = ui.ComboBox(self._camera_combo_model, alignment=ui.Alignment.CENTER_BOTTOM)
                with ui.HStack(height=ui.Pixel(15)):
                    ui.Label("Resolution: ", width=ui.Pixel(COLUMN_WIDTH_PIXELS))
                    with ui.HStack():
                        with ui.VStack(width=ui.Percent(50)):
                            ui.Label("Width", alignment=ui.Alignment.CENTER_BOTTOM)
                            self._ui_res_width_input = ui.IntField(alignment=ui.Alignment.CENTER_TOP, width=ui.Percent(90))
                            self._ui_res_width_input.model.set_value(1920)
                        with ui.VStack(width=ui.Percent(50)):
                            ui.Label("Height", alignment=ui.Alignment.CENTER_BOTTOM)
                            self._ui_res_height_input = ui.IntField(alignment=ui.Alignment.CENTER_TOP, width=ui.Percent(90))
                            self._ui_res_height_input.model.set_value(1080)
                ui.Spacer(height=ui.Pixel(25))
                ui.Button("Save", clicked_fn=lambda: self.save_view())
                ui.Button("Export to Photoshop", clicked_fn=lambda: self.export_view())
                ui.Spacer(height=ui.Pixel(25))
                ui.Label("Import Settings", height = ui.Pixel(30), alignment=ui.Alignment.CENTER)
                with ui.HStack(height=ui.Pixel(30)):
                    self._import_label = ui.Label("Import Path: ", width=ui.Pixel(COLUMN_WIDTH_PIXELS))
                    ui.Button("Browse", clicked_fn=lambda: self.on_imp_browse_clicked())
                    ui.Button("Clear", clicked_fn=lambda: self.on_imp_clear_clicked())
                
                ui.Spacer(height=ui.Pixel(25))
                ui.Button("Import", clicked_fn=lambda: self.import_image())

        self.setup_static_capture_options()


    def on_shutdown(self):
        print("[omni.pcg.adobeinterface] Adobe Interface shutdown")
