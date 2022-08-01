from carb import dictionary
from omni.kit.viewport.window.manipulator.context_menu import ClickGesture
import omni.ui as ui
import omni.ext
import os
from omni.kit.window.toolbar import SimpleToolButton
from .adobe import AdobeInterface

class ButtonSelectionWindow:
    def __init__(self,window_name,buttons,width=200, height=150,button_width=30,button_height=30):
        self.buttons = buttons
        self.window_name= window_name
        self.width=width
        self.height= height
        self.button_width= button_width
        self.button_height= button_height
        self.window_object = None
        self.sliders = None
    
    def set_up_window(self, plane):
        """
        NEed to first choose a projection, then the paint button is enabled
        """
        paint_buttons = []
        self.window_object = ui.Window(self.window_name, width=self.width, height=self.height)
        with self.window_object.frame:
            with ui.VStack():
                with ui.HStack():
                    for k,v in self.buttons.items():
                        ui.Button(k, width=self.button_width, height=self.button_height, clicked_fn= v)
                with ui.HStack():
                    paint_buttons.append(ui.Button("Export Image"))
        if plane is None:
            self.window_object.visible = False
        return paint_buttons

                
    def on_shutdown(self):
        self.window_object = None
        
               
class IconWindow:
    def __init__(self, window_name, buttons,width=800, height=600):
        """
        buttons:
        a dictionary of
        key: name of collapsable frame
        value: a list of tuples
        where teh tuples contains (whether only label,name of label, whether there is a combobox, text on the button, callback fn of the button)
        """
        self.buttons = buttons
        self.window_name= window_name
        self.width=width
        self.height= height
        self.window_object = None
    
    def set_up_window(self):
        combobox = []
        self.window_object = ui.Window(self.window_name, width=self.width, height=self.height, visible=False)
        with self.window_object.frame:
            with ui.VStack():
                for k, v in self.buttons.items():
                    with ui.CollapsableFrame(k):
                        with ui.VStack():
                            for values in v:
                                with ui.HStack():
                                    ui.Label(values[0])
                                    if values[1]:
                                        with ui.HStack():
                                            c = ui.ComboBox(0, width = ui.Percent(50))
                                            combobox.append(c)
                                            ui.Button(values[2], clicked_fn=values[3])
                                    else:
                                        ui.Button(values[2], clicked_fn=values[3])
        # self.window_object.visible = False
        return combobox


class SliderWrapper:
    def __init__(self, labels_list, style = {"font_size": 7}, enabled = False, visible = False, black=0xFFDDDDDD , white=0xFF000000 ):
        self.labels_list = labels_list
        self.slider_min = 0
        self.slider_max = len(labels_list)-1
        self.style = style
        self.enabled = enabled
        self.visible = visible
        self.ui_labels = []
        self.black=black
        self.white=white
        self.slider=None
    
    def set_up_slider(self):
        self.slider = ui.IntSlider(min=self.slider_min, max=self.slider_max, style = self.style, enabled = self.enabled, visible = self.visible)
        self.slider.set_style({"color":0x00FFFFFF})
        self.slider.set_mouse_released_fn(lambda x, y, a, b: self.slider_helper(x, y, a, b))

        with ui.HStack():
            self.ui_labels.append(ui.Label(self.labels_list[0][0], alignment = ui.Alignment.CENTER_TOP, style = {"color":0xFF000000}, visible = self.visible ))
            for a in range(1, len(self.labels_list)):
                self.ui_labels.append(ui.Label(self.labels_list[a][0], alignment = ui.Alignment.CENTER_TOP, visible = self.visible))
            
    def slider_helper(self, x, y, a, b):
        index = self.slider.model.get_value_as_int()
        for i in range(len(self.ui_labels)):
            if index == i:
                self.ui_labels[i].set_style({'color': self.white})
                self.labels_list[i][1]()
            else:
                self.ui_labels[i].set_style({'color' : self.black})
                if self.labels_list[i][2]:
                    self.labels_list[i][2]()

    def set_label_visibility(self, c):
        if self.slider:
            self.slider.visible = c
        for label in self.ui_labels:
            label.visible = c


class SideIconWrapper:
    def __init__(self, ext_path, folder_name="", icon_buttons=None):
        self.ext_path = ext_path
        self.icon_path = os.path.join(self.ext_path,folder_name)
        self.icon_buttons = icon_buttons
        self.icons = []
        self.pos = 800
        self.toolbar = omni.kit.window.toolbar.get_instance()

    def set_up_icons(self):
        self.icons = []
        for button in self.icon_buttons:
            self.icons.append(
                SimpleToolButton(name=button[0],
            tooltip=button[1],
            icon_path=f"{self.icon_path}/{button[2]}",
            icon_checked_path=f"{self.icon_path}/{button[3]}",
            hotkey=button[4],
            toggled_fn=button[5])
            )
        for icon in self.icons:
            self.toolbar.add_widget(icon, self.pos)
            self.pos+=100

    def shut_down_icons(self):
        for icon in self.icons:
            self.toolbar.remove_widget(icon)
            icon.clean()
            icon = None

