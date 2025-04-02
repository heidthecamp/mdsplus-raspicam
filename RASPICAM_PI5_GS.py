
import MDSplus
import threading
import traceback

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
            'path': ':GAIN', # adjust the preprocessed gain
            'type': 'numeric',
            'options': ('no_write_shot',),
        },
        {
            'path': ':SEG_MODE',
            'type': 'text',
            'value': 'timestamped',
            'options': ('no_write_shot',),
        },
        {
            'path': ':FRAMES',
            'type': 'signal',
            'options': ('no_write_model',),
        },
        {
            'path': ':TIMESTAMPS',
            'type': 'numeric',
            'options': ('no_write_model',),
        },
        {
            'path': ':SEG_LENGTH',
            'type': 'numeric',
            'options': ('no_write_shot')
        },
        {
            'path': ':MAX_SEGMENTS',
            'type': 'numeric',
            'options': ('no_write_shot')
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
        {
            'path': ":SEG_EVENT",
            'type': 'text',
            'value': 'RASPICAM_SEGMENT',
            'options': ('no_write_shot',),
        },
        {
            'path': ':RUNNING',
            'type': 'any',
            'options': ('no_write_model'),
        },
    ]

    class StreamWriter(threading.Thread):
        def __init__(self, reader):
            threading.Thread.__init__(self, name="RASPICAM_PI5_GS.StreamWriter")
            self.tree_name = reader.device.tree.name
            self.tree_shot = reader.device.tree.shot
            self.node_path = reader.device.path
            self.buffer_queue = reader.buffer_queue

        def run(self):
            import queue
            import numpy

            try:
                self.tree = MDSplus.Tree(self.tree_name, self.tree_shot)
                self.device = self.tree.getNode(self.node_path)

                event_name = str(self.device.SEG_EVENT.data())

                seg_mode = str(self.device.SEG_MODE.data())

                fps = float(self.device.FPS.data())
                delta_time = 1.0 / fps

                segment_length = self.device.SEG_LENGTH.data()

                if seg_mode.lower() == 'timestamped':
                    self.device.TIMESTAMPS.record = MDSplus.DIM_OF(self.device.FRAMES)

                frames = []
                timestamps = []
                segment_index = 0
                while True:
                    try:
                        buffer = self.buffer_queue.get(block=True, timeout=1)
                    except queue.Empty:
                        continue

                    # A buffer of None signals the end to streaming
                    if buffer is not None:
                        frames.append(buffer[0])
                        timestamps.append(buffer[1])

                    if len(frames) >= segment_length or buffer is None:

                        if seg_mode.lower() == 'timestamped':
                            self.device.FRAMES.makeTimestampedSegment(numpy.array(timestamps), numpy.array(frames))

                        else:
                            begin = segment_index * segment_length * delta_time
                            end = begin + ((len(frames) - 1) * delta_time)
                            dim = MDSplus.Range(begin, end, delta_time)
                            
                            self.device.FRAMES.makeSegment(begin, end, dim, numpy.array(frames))
                            self.device.TIMESTAMPS.makeSegment(begin, end, dim, numpy.array(timestamps))

                        frames = []
                        timestamps = []
                        segment_index += 1

                        MDSplus.Event(event_name)
                    
                    if buffer is None:
                        break

            except Exception as e:
                self.exception = e
                traceback.print_exc()

    class StreamReader(threading.Thread):
        def __init__(self, device):
            threading.Thread.__init__(self, name="RASPICAM_PI5_GS.StreamReader")
            self.tree_name = device.tree.name
            self.tree_shot = device.tree.shot
            self.node_path = device.path
        
        def run(self):
            import queue
            from picamera2 import Picamera2, Preview

            try:
                self.tree = MDSplus.Tree(self.tree_name, self.tree_shot)
                self.device = self.tree.getNode(self.node_path)

                picam2 = Picamera2()

                self.buffer_queue = queue.Queue()

                height = int(self.device.HEIGHT.data())
                width = int(self.device.WIDTH.data())

                fps = float(self.device.FPS.data())
                exposure = int(self.device.EXPOSURE.data())
                gain = float(self.device.GAIN.data())

                max_frames = int(self.device.MAX_SEGMENTS.data() * self.device.SEG_LENGTH.data())

                # Configure Camera Setup
                camera_config = picam2.create_preview_configuration({
                    "format": "BGR888", # This gives us the results backwards as RGB888
                    "size": (width, height),
                })
                picam2.configure(camera_config)
                picam2.set_controls({
                    'FrameRate': fps,
                    "ExposureTime": exposure,
                    "AnalogueGain": gain,
                })

                # print("camera_configuration:")
                # print(picam2.camera_configuration())

                # Start Camera
                picam2.start_preview(Preview.NULL)
                picam2.start()

                self.writer = self.device.StreamWriter(self)
                self.writer.setDaemon(True)
                self.writer.start()
                
                frame_index = 0
                while self.device.RUNNING.on and frame_index < max_frames:
                    
                    try:
                        (frame,), metadata = picam2.capture_buffers()
                    except Exception as e:
                        self.exception = e
                        traceback.print_exc()
                        break

                    self.buffer_queue.put((
                        frame.reshape((height, width, 3)),
                        metadata['SensorTimestamp']
                    ))

                    frame_index += 1

                self.buffer_queue.put(None)
                self.device.RUNNING.on = False

            except Exception as e:
                self.exception = e
                traceback.print_exc()
            
            finally:
                picam2.stop()

    def init(self):

        self.RUNNING.on = True

        thread = self.StreamReader(self)
        thread.start()

    INIT = init

    def stop(self):
        self.RUNNING.on = False
    STOP = stop

    def average_fps(self):
        timestamps = self.TIMESTAMPS.data()

        duration = (timestamps[-1] - timestamps[0]) / 1e9
        avg_fps = 1 / (duration / len(timestamps))
    

        print(f"Target FPS: {self.FPS.data()}")
        print(f"Average FPS: {avg_fps}")

    AVERAGE_FPS = average_fps