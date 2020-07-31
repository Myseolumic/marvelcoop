import os
import time
import math
import tkinter.filedialog as filedialog
import schedule
import threading
import random
import exporter as exp
from tkinter import *

import numpy as np
from PIL import Image, ImageTk, ImageDraw

from marvelmind import MarvelmindHedge


# whole app requires: pyserial, crcmod, matplotlib, Pillow, numpy
class MainApp(Tk):
    def __init__(self):
        Tk.__init__(self)
        self._frame = None
        self.title("Coopi tracker")
        self.switch_frame(ReplayFrame)
        self.protocol("WM_DELETE_WINDOW", self.app_close_callback)

    def switch_frame(self, frame_class):
        new_frame = frame_class(self)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.pack()

        if frame_class == ReplayFrame:
            self._frame.canvas_widget.menubar(self)

    def app_close_callback(self):
        self._frame.onclose()
        self.destroy()


class Heatmap(object):
    def __init__(self, image, root, start_point, zoom):
        self.image = image.copy().convert('RGBA')
        size = self.image.size
        matrix, edge_x, edge_y, start_point, map_max = root.generate_heatmap(60, 40, size[0], size[1], zoom, start_point)
        self.heat_overlay = Image.new('RGBA', self.image.size, (255, 255, 255, 0))
        self.draw = ImageDraw.Draw(self.heat_overlay)
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                val = int((matrix[i][j] / map_max) * 255)
                x1 = edge_x * j
                x2 = x1 + edge_x
                y1 = edge_y * i
                y2 = y1 + edge_y
                self.draw.rectangle([x1, y1, x2, y2], fill=(val, 255 - val, 255 - val, 128))

        self.comp_img = Image.alpha_composite(self.image, self.heat_overlay)
        self.save_heatmap()

    def save_heatmap(self):
        self.comp_img.save("vad helvete.png")


class BeaconPath(object):
    def __init__(self, id, mat):
        self.start_point = (mat[0][0], mat[0][1])
        self.id = id
        self.color = "red"
        self.points = mat[:]  # unique timestamps

        # Create temporary list to later use for building the numpy array
        temp_l = []
        for i in range(len(mat) - 1):
            vector_x = mat[i + 1][0] - mat[i][0]
            vector_y = mat[i + 1][1] - mat[i][1]
            temp_l.append([vector_x, vector_y, mat[i + 1][4]])
        self.vectors = np.asarray(temp_l)

    def captured_time(self):
        return self.points[0][4], self.points[-1][4]


class ReplayFrame(Frame):

    def __init__(self, root):
        # Init objects
        Frame.__init__(self, root)
        self.beacons_active = {}
        self.beacon_paths = {}

        zip_file = filedialog.askopenfilename(initialdir="./", title='Choose a file',
                                              filetypes=(("zip files", "*.zip"), ("all files", "*.*")))
        data = exp.import_file(zip_file)
        beacons = data["beacons"]
        self.canvas_widget = CanvasWidget(self, 0, 1, data["img"])

        self.start_date = data["date"]
        self.time = self.start_date.split(" ")[1].split(".")

        # generate BeaconPaths
        for key in beacons:
            self.beacon_paths[key] = BeaconPath(key, beacons[key])

        # Status box in the corner
        self.status_box = Frame(self)
        self.status_box.grid(row=0, column=0, sticky=W)  # adding a status box to corner of the screen
        self.status_text = StringVar()
        self.zoom_text = StringVar()
        self.status_label = Label(self.status_box, textvariable=self.status_text, fg="#228C22", bg="#a1a1a1", width=16,
                                  height=2)
        self.zoom_label = Label(self.status_box, textvariable=self.zoom_text, fg="black", bg="#a1a1a1", width=16,
                                height=2)
        self.status_label.grid(row=0, column=0, sticky="NSEW")
        self.zoom_label.grid(row=1, column=0, sticky="NSEW")
        self.zoom_text.set("Zoom: 1.0")
        self.status_text.set("IDLE")

        # Setup the scale
        self.start_time = 999999999
        self.end_time = 0
        for key in self.beacon_paths:
            start, end = self.beacon_paths[key].captured_time()
            if start < self.start_time:
                self.start_time = start
            if end > self.end_time:
                self.end_time = end
        self.scale_container = Frame(self, padx=100)
        self.scale_text = StringVar()
        self.scale_text.set("Current time:" + self.start_date)
        Label(self.scale_container, textvariable=self.scale_text).grid(row=0, column=0, sticky='ns',)
        self.scale = Scale(self.scale_container, from_=self.start_time, showvalue=0, length=400, to=self.end_time, orient=HORIZONTAL,
                           command=self.update_canvas)
        self.scale_container.grid(row=4, column=1, columnspan=3, sticky=W)
        self.scale.grid(row=0, column=1, sticky='ns')

        # Setup Checkboxes for enabling beacons
        j = 0
        self.beacons_container = Frame(self, borderwidth=1)
        for beacon in self.beacon_paths:
            self.beacons_active[beacon] = IntVar()
            Checkbutton(self.beacons_container, text="Hedgehog " + beacon, variable=self.beacons_active[beacon]).grid(
                row=j, sticky=W)
            j += 1
        self.beacons_container.grid(row=1, column=0, sticky=W)

        # Setup buttons for rotating the origin.
        self.controls_container = CanvasControls(self, self.canvas_widget)
        self.controls_container.grid(row=2, column=0, sticky=W)

        # First draw
        self.update_canvas()

    def update_canvas(self, scale_value=0):
        self.canvas_widget.clear()
        self.canvas_widget.draw_origin()
        scale_value = self.scale.get()
        for b_name in self.beacons_active:
            if self.beacons_active[b_name].get() == 0:  # check if beacon is set visible
                continue
            point_count = 0
            for i in range(self.beacon_paths[b_name].vectors.shape[0] - 1):
                time = self.beacon_paths[b_name].vectors[i][2]
                if time > int(scale_value):
                    point_count = i + 1
                    break
                if i + 1 == self.beacon_paths[b_name].vectors.shape[0] - 1:
                    point_count = i

            vectors = self.beacon_paths[b_name].vectors[:point_count]
            self.canvas_widget.draw_lines(self.beacon_paths[b_name].start_point, vectors)

        diff = scale_value - self.start_time + int(self.time[0])*60*60*1000 + int(self.time[1])*60*1000 + int(self.time[2])*1000
        seconds = math.floor((diff / 1000) % 60)
        minutes = math.floor((diff / (1000 * 60)) % 60)
        hours = math.floor((diff / (1000 * 60 * 60)) % 24)
        hours = "0" + str(hours) if (hours < 10) else hours
        minutes = "0" + str(minutes) if (minutes < 10) else minutes
        seconds = "0" + str(seconds) if (seconds < 10) else seconds
        text = self.start_date.split(" ")[0]+" "+str(hours)+"."+str(minutes)+"."+str(seconds)
        self.scale_text.set("Current time: " + text)

    def generate_heatmap(self, seg_x=10, seg_y=10, width=100, height=100, zoom=1, start_point=None):
        edge_x = width / seg_x
        edge_y = height / seg_y
        if start_point is None:
            start_point = [width / 2, height / 2]
        max = 1.0

        start_x = width / 2 + start_point[0]
        start_y = height / 2 + start_point[1]
        matrix = []
        for y in range(seg_y):
            matrix.append([])
            for x in range(seg_x):
                appended_val = 0.0
                seg_start_x = x * edge_x
                seg_start_y = y * edge_y
                for b in self.beacon_paths:
                    positions = self.beacon_paths[b].points
                    for p in positions:
                        p_x = start_x - p[0] * zoom
                        p_y = height - start_y + p[1] * zoom
                        if seg_start_x <= p_x <= seg_start_x + edge_x and seg_start_y <= p_y <= seg_start_y + edge_y:
                            appended_val += 1.0
                if appended_val > max:
                    max = appended_val
                matrix[y].append(appended_val)
        return [matrix, edge_x, edge_y, start_point, max]

    def onclose(self):
        self.destroy()


class CanvasControls(Frame):

    def __init__(self, root, canvas_widget):
        Frame.__init__(self, root)
        self.canvas_widget = canvas_widget
        Label(self, text="Origin rotation:").grid(row=0, columnspan=4)
        self.b_n = Button(self, text="N", command=lambda: self.buttonpress("N"), disabledforeground="red",
                          state="disabled")
        self.b_n.grid(row=1, column=0)
        self.b_s = Button(self, text="S", command=lambda: self.buttonpress("S"), disabledforeground="red")
        self.b_s.grid(row=1, column=1)
        self.b_e = Button(self, text="E", command=lambda: self.buttonpress("E"), disabledforeground="red",
                          state="disabled")
        self.b_e.grid(row=1, column=2)
        self.b_w = Button(self, text="W", command=lambda: self.buttonpress("W"), disabledforeground="red")
        self.b_w.grid(row=1, column=3)
        self.b_l = Button(self, text="L", command=lambda: self.buttonpress("L"), disabledforeground="red",
                          state="disabled")
        self.b_l.grid(row=2, column=1)
        self.b_r = Button(self, text="R", command=lambda: self.buttonpress("R"), disabledforeground="red")
        self.b_r.grid(row=2, column=2)

    def buttonpress(self, letter):
        self.canvas_widget.set_origin_rotation(letter)
        if letter == "N":
            self.b_n["state"] = DISABLED
            self.b_s["state"] = NORMAL
        elif letter == "S":
            self.b_s["state"] = DISABLED
            self.b_n["state"] = NORMAL
        elif letter == "E":
            self.b_e["state"] = DISABLED
            self.b_w["state"] = NORMAL
        elif letter == "W":
            self.b_w["state"] = DISABLED
            self.b_e["state"] = NORMAL
        elif letter == "L":
            self.b_l["state"] = DISABLED
            self.b_r["state"] = NORMAL
        elif letter == "R":
            self.b_r["state"] = DISABLED
            self.b_l["state"] = NORMAL


class CanvasWidget:

    def __init__(self, root, row=0, column=0, img=None, heatmapped=False):
        self.root = root
        self.canvas_container = Frame(root)
        self.canvas_container.grid(row=row, column=column, columnspan=3, rowspan=3, sticky='nsew')
        self.canvas = Canvas(self.canvas_container, width=800, height=600, bg="#8c8c8c")
        self.canvas.grid(row=0, column=0, columnspan=3, rowspan=3, sticky='nsew')
        self.heatmapper = None
        self.drawn_hedgehogs = {}

        # reference points for scaling
        self.zero = self.canvas.create_text(0, 0, anchor='center', text='0')
        self.cs_x = 0
        self.cs_y = 0
        self.origin_id = self.canvas.create_oval(self.cs_x - 5, self.cs_y - 5, self.cs_x + 5, self.cs_y + 5,
                                                 fill="yellow")
        # mouse-events related
        self.PLACING_BEACON = False
        self.PANNING = False
        self.CALIBRATING = False
        self.calibration_start = None
        self.calibration_line = None
        self.origin_rotation = ["N", "E", "L"]
        self.zoom = 10

        # parsing floor-plan
        if img is None:
            self.floor_plan = ImageTk.PhotoImage(file='test_image.png')
            self.floor_plan_image = Image.open('test_image.png')
        else:
            self.floor_plan_image = Image.open(img)
            self.floor_plan = ImageTk.PhotoImage(self.floor_plan_image)
        self.floor_plan_scale = 1.0
        self.draw_floor_plan()

        # bind mouse-events
        self.canvas.bind('<Button-1>', self.handle_mouse_click)
        self.canvas.bind('<MouseWheel>', self.handle_mouse_wheel)
        self.canvas.bind('<B1-Motion>', self.handle_mouse_move)
        self.canvas.bind('<ButtonRelease-1>', self.handle_mouse_raise)

        # cleared elements every re-draw
        self.clear_ids = []
        self.heatmap_img = None

    def refresh(self):
        self.root.update_canvas()

    def clear(self):
        for i in self.clear_ids:
            self.canvas.delete(i)
        self.clear_ids = []

    def get_zero_reference(self):
        return self.canvas.coords(self.zero)

    def set_origin_rotation(self, val):
        if val in ("N", "S"):
            self.origin_rotation[0] = val
        elif val in ("E", "W"):
            self.origin_rotation[1] = val
        elif val in ("L", "R"):
            self.origin_rotation[2] = val

    def handle_mouse_wheel(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        scale = 1.0
        if event.delta == -120:  # scroll down
            scale *= 0.8
            self.floor_plan_scale *= 0.8
        if event.delta == 120:  # scroll up
            scale /= 0.8
            self.floor_plan_scale /= 0.8

        self.root.zoom_text.set("Zoom: " + str(round(self.floor_plan_scale, 3)))
        self.canvas.scale('all', x, y, scale, scale)
        self.rescale_image()
        self.refresh()

    def handle_mouse_click(self, event):
        if self.PLACING_BEACON:
            self.root.status_text.set("IDLE")
            self.place_beacon(event)
            self.PLACING_BEACON = False

        elif self.CALIBRATING:
            if self.calibration_start is None:
                x = self.canvas.canvasx(event.x)
                y = self.canvas.canvasy(event.y)
                self.calibration_start = [x, y]

        else:
            self.canvas.scan_mark(event.x, event.y)
            self.PANNING = True

    def handle_mouse_move(self, event):
        if self.PANNING:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self.canvas.scan_mark(event.x, event.y)

        if self.CALIBRATING and self.calibration_start is not None:
            if self.calibration_line is not None:
                self.canvas.delete(self.calibration_line)
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            self.calibration_line = self.canvas.create_line(self.calibration_start[0], self.calibration_start[1], x, y,
                                                            width=3, fill="orange")

    def calibrate(self):
        self.CALIBRATING = True
        self.root.status_text.set("CALIBRATING...")

    def handle_mouse_raise(self, event):
        if self.PANNING:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self.PANNING = False

        if self.CALIBRATING:
            self.CALIBRATING = False
            self.root.status_text.set("IDLE")
            x1 = self.calibration_start[0]
            y1 = self.calibration_start[1]
            x2 = self.canvas.canvasx(event.x)
            y2 = self.canvas.canvasy(event.y)
            self.zoom = int(math.sqrt(math.pow((x2 - x1), 2) + math.pow((y2 - y1), 2)))
            self.canvas.delete(self.calibration_line)
            self.refresh()

    def paint_heatmap(self):
        self.clear()
        self.heatmapper = Heatmap(self.floor_plan_image, self.root, [self.cs_x, self.cs_y], self.zoom)
        print(self.heatmapper.comp_img)
        self.heatmap_img = ImageTk.PhotoImage(self.heatmapper.comp_img)
        mid = self.canvas.create_image(0, 0, image=self.heatmap_img)
        self.canvas.lift(mid)

    def place_beacon(self, event):
        self.cs_x = self.canvas.canvasx(event.x)
        self.cs_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.origin_id, self.cs_x - 5, self.cs_y - 5, self.cs_x + 5, self.cs_y + 5)

    def add_beacon(self):
        self.PLACING_BEACON = True
        self.root.status_text.set("PLACING ORIGIN")

    def add_floor_plan(self):
        img_file = filedialog.askopenfilename(initialdir="./", title='Choose a file',
                                              filetypes=(("image files", "*.jpg;*.png"), ("all files", "*.*")))
        if img_file and os.path.exists(img_file) and os.path.isfile(img_file):
            self.floor_plan = ImageTk.PhotoImage(file=img_file)
            self.floor_plan_image = Image.open(img_file)
            self.floor_plan_scale = 1.0
            self.refresh()

    def rescale_image(self):
        width, height = self.floor_plan_image.size
        new_size = int(self.floor_plan_scale * width), int(self.floor_plan_scale * height)
        self.floor_plan = ImageTk.PhotoImage(self.floor_plan_image.resize(new_size))
        if self.heatmapper is not None:
            self.heatmap_img = ImageTk.PhotoImage(self.heatmapper.comp_img.resize(new_size))
        self.draw_floor_plan()

    def draw_floor_plan(self):
        img_id = self.canvas.create_image(self.get_zero_reference(), image=self.floor_plan)
        if self.heatmapper is not None:
            hid = self.canvas.create_image(self.get_zero_reference(), image=self.heatmap_img)
            self.canvas.lift(hid)
        self.canvas.lower(img_id)

    def draw_origin(self):
        og = self.canvas.coords(self.origin_id)
        self.cs_x = (og[0] + og[2]) / 2
        self.cs_y = (og[1] + og[3]) / 2
        self.canvas.coords(self.origin_id, self.cs_x - 5, self.cs_y - 5, self.cs_x + 5, self.cs_y + 5)

    def draw_lines(self, start, vectors):
        r = 3
        x1 = self.cs_x + float(start[0])
        y1 = self.cs_y + float(start[1])
        i = self.canvas.create_oval(x1 - r, y1 - r, x1 + r, y1 + r, fill="red")
        self.clear_ids.append(i)
        for vector in vectors:
            vector = np.multiply(vector, self.zoom * self.floor_plan_scale)
            # x2 = self.calc_x(x1, vector[0])
            # y2 = self.calc_y(y1, vector[1])
            x2, y2 = self.calc_xy(x1, y1, vector)
            i = self.canvas.create_line(x1, y1, x2, y2, fill="red", width=2)
            j = self.canvas.create_oval(x2 - r, y2 - r, x2 + r, y2 + r, fill="red")
            self.clear_ids.append(i)
            self.clear_ids.append(j)
            x1 = x2
            y1 = y2

    def draw_hedgehog(self, arr):
        self.clear()
        r = 5
        id = arr[0]
        x = arr[1] * 10
        y = arr[2] * 10
        if id not in self.drawn_hedgehogs:
            rand = lambda: random.randint(0, 255)
            self.drawn_hedgehogs[id] = '#{:02x}{:02x}{:02x}'.format(rand(), rand(), rand())
        c_id = self.canvas.create_rectangle(x - r, y - r, x + r, y + r, fill=self.drawn_hedgehogs[id])
        self.clear_ids.append(c_id)

    def calc_xy(self, x, y, vector):
        pair = [0, 0]
        if self.origin_rotation[2] == "R":
            c = vector[0]
            vector[0] = vector[1]
            vector[1] = c


        if self.origin_rotation[1] == "E":
            pair[0] = x + float(vector[0])
        else:
            pair[0] = x - float(vector[0])
        if self.origin_rotation[0] == "N":
            pair[1] = y - float(vector[1])
        else:
            pair[1] = y + float(vector[1])

        return pair

    def menubar(self, root):
        menu = Menu(root)
        root.config(menu=menu)

        editMenu = Menu(menu)
        editMenu.add_command(label="Add room plan", command=self.add_floor_plan)
        editMenu.add_command(label="Place origin beacon", command=self.add_beacon)
        editMenu.add_command(label="Calibrate", command=self.calibrate)
        menu.add_cascade(label="Edit", menu=editMenu)

        menu.add_command(label="Generate heatmap", command=self.paint_heatmap)
        menu.add_command(label="LIVE TRACKING", command=lambda: self.root.switch_frame(TrackingFrame))


class TrackingFrame(Frame):

    def __init__(self, root):
        Frame.__init__(self, root)
        self.root = root
        self.canvas = CanvasWidget(self)
        self.controls_container = CanvasControls(self, self.canvas)
        self.controls_container.grid(row=2, column=0, sticky=W)
        self.hedge = MarvelmindHedge(tty="\\.\COM3", adr=None, debug=False)  # create MarvelmindHedge thread
        self.start_comms()
        self.ram_log = []

    @staticmethod
    def valid_coords(coords):
        if coords[0] == 0 and coords[1] == 0 and coords[2] == 0 and coords[3] == 0:
            return False
        return True

    def start_comms(self, i=1):
        self.hedge.start()  # start marvelmind thread
        schedule.every(1).seconds.do(self.communicate)
        cease = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease.is_set():
                    schedule.run_pending()
                    time.sleep(i)

        continuous_thread = ScheduleThread()
        continuous_thread.start()
        return cease

    def communicate(self):
        coords = self.hedge.position()
        if self.valid_coords(coords):
            self.parse_hedgehogs(list(self.hedge.valuesUltrasoundPosition))
        else:
            print("Modem not connected!")

    def parse_hedgehogs(self, raw_data):
        parsed_hedgehogs = []
        for arr in raw_data:
            id = arr[0]
            if id not in parsed_hedgehogs:
                parsed_hedgehogs.append(id)
                self.ram_log.append(arr)
                self.canvas.draw_hedgehog(arr)

    def onclose(self):
        self.hedge.stop()
        self.destroy()


MainApp().mainloop()
