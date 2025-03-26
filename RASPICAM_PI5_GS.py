
import MDSplus

class RASPICAM_PI5_GS(MDSplus.Device):
    
    parts = [
        {
            'path': ':COMMENT',
            'type': 'text',
        },
        {
            'path': ':ID', # which camera is being addressed
            'type': 'text',
            'options': ('no_write_shot',),
        },
        {
            'path': ':WIDTH', # pixel measurements for width
            'type': 'numeric',
            'options': ('no_write_shot',),
        },
        {
            'path': ':HEIGHT', # pixel measurments for height
            'type': 'numeric',
            'options': ('no_write_shot',),
        },
        {
            'path': ':FPS', # frame rate
            'type': 'numeric',
            'options': ('no_write_shot',),
        },
        {
            'path': ':EXPOSURE', # duration of exposure
            'type': 'numeric',
            'options': ('no_write_shot',),
        },
        {
            'path': ':ANALOG_GAIN', # adjust the preprocessed gain
            'type': 'text',
            'options': ('no_write_shot',),
        },
        {
            'path': ':FRAMES',
            'type': 'signal',
            'options': ('no_write_model',),
        },
        {
            'path': ":INIT_ACTION",
            'type': 'action',
            'valueExpr': "Action(Dispatch('SERVER','INIT',50,None),Method(None,'INIT',head))",
            'options': ('no_write_shot',),
        },
        {
            'path': ":STOP_ACTION",
            'type': 'action',
            'valueExpr': "Action(Dispatch('SERVER','STORE',50,None),Method(None,'STOP',head))",
            'options': ('no_write_shot',),
        },
    ]


    def init(self):
        print('Initializing')
        # fps = float(self.FPS.data())
    INIT = init


    def stop(self):
        print('Stopping')
        # fps = float(self.FPS.data())
    STOP = stop