import omni.ui as ui

class ButtonSelectionWindow:
    def __init__(self,window_name,buttons,width=200, height=70,button_width=30,button_height=30):
        self.buttons = buttons
        self.window_name= window_name
        self.width=width
        self.height= height
        self.button_width= button_width
        self.button_height= button_height
        self.window_object = None
    
    def set_up_window(self):

        self.window_object = ui.Window(self.window_name, width=self.width, height=self.height)
        with self.window_object.frame:
            with ui.HStack():

                for k,v in self.buttons.items():
                    ui.Button(k, width=self.button_width, height=self.button_height, clicked_fn= v)
    
    def on_shutdown(self):
        self.window_object = None
        
               
class InitialWindow:
    def __init__(self, window_name, buttons,width=250, height=150):
        self.buttons = buttons
        self.window_name= window_name
        self.width=width
        self.height= height
        self.window_object = None
    
    def set_up_window(self):
        combobox = []
        self.window_object = ui.Window(self.window_name, width=self.width, height=self.height)
        with self.window_object.frame:
            with ui.VStack():
                for k, v in self.buttons.items():
                    with ui.HStack():
                        ui.Label(k)
                        if v[0]:
                            with ui.HStack():
                                c = ui.ComboBox(0, width = ui.Percent(50))
                                combobox.append(c)
                                ui.Button(v[1], clicked_fn=v[2])
                        else:
                             ui.Button(v[1], clicked_fn=v[2])
        return combobox

class SliderWrapper:
    def __init__(self, labels, slider_min=0, slider_max=2,style = {"font_size": 7}, enabled = False):
        self.labels = labels
        self.slider_min = slider_min
        self.slider_max = slider_max
        self.style = style
        self.enabled = enabled
        self.ui_labels = []
    
    def set_up_slider(self):
        self.slider = ui.IntSlider(min=self.slider_min, max=self.slider_max, style = self.style, enabled = self.enabled)
        self.prev_ind = self.slider.model.get_value_as_int()
        self.slider.set_mouse_released_fn(lambda x, y, a, b, : self.slider_helper(x, y, a, b))
        with ui.HStack():
            self.ui_labels.append(ui.Label(self.labels[0], alignment = ui.Alignment.CENTER_TOP, style = {"color":0xFF000000} ))
            for a in range(1, len(self.labels)):
                self.ui_labels.append(ui.Label(self.labels[a], alignment = ui.Alignment.CENTER_TOP))
            
    # def slider_helper(self, x, y, a, b):
    #     index = self.slider.model.get_value_as_int()
    #     black=0xFFDDDDDD
    #     white=0xFF000000
    #     for i in range(len(self.ui_labels)):
    #         if index == i:



