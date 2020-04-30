import os
import time
import tkinter.filedialog as filedialog
import schedule
import threading
import exporter as exp
from tkinter import *

import numpy as np
from PIL import Image, ImageTk

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


class BeaconPath(object):
    def __init__(self, id, mat):
        self.start_point = (mat[0][0], mat[0][1])
        self.id = id
        self.color = "red"
        self.points = mat[:]

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

        # generate BeaconPaths
        for key in beacons:
            self.beacon_paths[key] = BeaconPath(key, beacons[key])

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
        datetext = "Date (start):" + self.start_date
        Label(self.scale_container, text=datetext).grid(row=0, column=0, sticky=W)
        self.scale = Scale(self.scale_container, from_=self.start_time, length=400, to=self.end_time, orient=HORIZONTAL, command=self.update_canvas)
        self.scale_container.grid(row=4, column=1, columnspan=3, sticky=W)
        self.scale.grid(row=0, column=1, sticky=W)

        # Setup Checkboxes for enabling beacons
        j = 0
        self.beacons_container = Frame(self, borderwidth=1)
        for beacon in self.beacon_paths:
            self.beacons_active[beacon] = IntVar()
            Checkbutton(self.beacons_container, text="Hedgehog " + beacon, variable=self.beacons_active[beacon]).grid(
                row=j, sticky=W)
            j += 1
        self.beacons_container.grid(row=0, column=0, sticky=W)

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
                    point_count = i+1
                    break
                if i+1 == self.beacon_paths[b_name].vectors.shape[0] - 1:
                    point_count = i

            vectors = self.beacon_paths[b_name].vectors[:point_count]
            self.canvas_widget.draw_lines(self.beacon_paths[b_name].start_point, vectors)

    def onclose(self):
        self.destroy()


class CanvasControls(Frame):

    def __init__(self, root, canvas_widget):
        Frame.__init__(self, root)
        self.canvas_widget = canvas_widget
        Label(self, text="Origin rotation:").grid(row=0, columnspan=4)
        self.b_n = Button(self, text="N", command=lambda: self.buttonpress("N"), disabledforeground="red", state="disabled")
        self.b_n.grid(row=1, column=0)
        self.b_s = Button(self, text="S", command=lambda: self.buttonpress("S"), disabledforeground="red")
        self.b_s.grid(row=1, column=1)
        self.b_e = Button(self, text="E", command=lambda: self.buttonpress("E"), disabledforeground="red", state="disabled")
        self.b_e.grid(row=1, column=2)
        self.b_w = Button(self, text="W", command=lambda: self.buttonpress("W"), disabledforeground="red")
        self.b_w.grid(row=1, column=3)

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


class CanvasWidget:

    def __init__(self, root, row=0, column=0, img=None):
        self.root = root
        self.canvas_container = Frame(root)
        self.canvas_container.grid(row=row, column=column, columnspan=3, rowspan=3, sticky='nsew')
        self.canvas = Canvas(self.canvas_container, width=800, height=600, bg="#8c8c8c")
        self.canvas.grid(row=0, column=0, columnspan=3, rowspan=3, sticky='nsew')

        # reference points for scaling
        self.zero = self.canvas.create_text(0, 0, anchor='nw', text='0')
        self.cs_x = 0
        self.cs_y = 0
        self.origin_id = self.canvas.create_oval(self.cs_x - 5, self.cs_y - 5, self.cs_x + 5, self.cs_y + 5, fill="yellow")

        self.PLACING_BEACON = False
        self.PANNING = False
        self.origin_rotation = ["N", "E"]
        self.zoom = 10

        if img is None:
            self.floor_plan = ImageTk.PhotoImage(file='test_image.png')
            self.floor_plan_image = Image.open('test_image.png')
        else:
            self.floor_plan_image = Image.open(img)
            self.floor_plan = ImageTk.PhotoImage(self.floor_plan_image)

        self.floor_plan_scale = 1.0
        self.draw_floor_plan()

        self.canvas.bind('<Button-1>', self.handle_mouse_click)
        self.canvas.bind('<MouseWheel>', self.handle_mouse_wheel)
        self.canvas.bind('<B1-Motion>', self.pan_canvas)
        self.canvas.bind('<ButtonRelease-1>', self.end_pan)

        self.clear_ids = []

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

    def handle_mouse_wheel(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        scale = 1.0
        if event.delta == -120: # scroll down
            scale *= 0.8
            self.floor_plan_scale *= 0.8
        if event.delta == 120: # scroll up
            scale /= 0.8
            self.floor_plan_scale /= 0.8

        self.canvas.scale('all', x, y, scale, scale)
        self.new_rescale_image()
        self.update_origin()

    def handle_mouse_click(self, event):
        if self.PLACING_BEACON:
            self.place_beacon(event)
            self.PLACING_BEACON = False
        else:
            self.canvas.scan_mark(event.x, event.y)
            self.PANNING = True

    def pan_canvas(self, event):
        if self.PANNING:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self.canvas.scan_mark(event.x, event.y)

    def end_pan(self, event):
        if self.PANNING:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self.PANNING = False

    def place_beacon(self, event):
        self.cs_x = self.canvas.canvasx(event.x)
        self.cs_y = self.canvas.canvasy(event.y)
        self.draw_origin()

    def add_beacon(self):
        self.PLACING_BEACON = True

    def add_floor_plan(self):
        img_file = filedialog.askopenfilename(initialdir="./", title='Choose a file', filetypes=(("image files", "*.jpg;*.png"), ("all files", "*.*")))
        if img_file and os.path.exists(img_file) and os.path.isfile(img_file):
            self.floor_plan = ImageTk.PhotoImage(file=img_file)
            self.floor_plan_image = Image.open(img_file)
            self.floor_plan_scale = 1.0
            self.refresh()

    def rescale_image(self, x, y):
        self.floor_plan_scale = self.scale
        size = (int(self.floor_plan_image.width * self.scale), int(self.floor_plan_image.height * self.scale))
        self.floor_plan = ImageTk.PhotoImage(self.floor_plan_image.resize(size))
        # ((coord - offset) * scale + offset)
        self.floor_plan_x = (self.floor_plan_x - x) * self.scale + x
        self.floor_plan_y = (self.floor_plan_y - y) * self.scale + y
        self.draw_floor_plan()

    def new_rescale_image(self):
        width, height = self.floor_plan_image.size
        new_size = int(self.floor_plan_scale * width), int(self.floor_plan_scale * height)
        self.floor_plan = ImageTk.PhotoImage(self.floor_plan_image.resize(new_size))
        self.draw_floor_plan()

    def draw_floor_plan(self):
        img_id = self.canvas.create_image(self.get_zero_reference(), image=self.floor_plan)
        self.canvas.lower(img_id)

    def draw_origin(self):
        self.canvas.coords(self.origin_id, self.cs_x - 5, self.cs_y - 5, self.cs_x + 5, self.cs_y + 5)

    def update_origin(self):
        arr = self.canvas.coords(self.origin_id)
        self.cs_x = arr[0]
        self.cs_y = arr[1]

    def draw_lines(self, start, vectors):
        r = 3
        x1 = self.cs_x + float(start[0])
        y1 = self.cs_y + float(start[1])
        i = self.canvas.create_oval(x1 - r, y1 - r, x1 + r, y1 + r, fill="red")
        self.clear_ids.append(i)
        for vector in vectors:
            vector = np.multiply(vector, self.zoom * self.floor_plan_scale)
            x2 = self.calc_x(x1, vector[0])
            y2 = self.calc_y(y1, vector[1])
            i = self.canvas.create_line(x1, y1, x2, y2, fill="red", width=2)
            j = self.canvas.create_oval(x2-r, y2-r, x2+r, y2+r, fill="red")
            self.clear_ids.append(i)
            self.clear_ids.append(j)
            x1 = x2
            y1 = y2

    def draw_hedgehog(self, x, y, color="red"):
        r = 5
        self.canvas.create_rectangle(x-r, y-r, x+r, y+r, fill=color)

    def calc_x(self, x, val):
        if self.origin_rotation[1] == "E":
            return x + float(val)
        return x - float(val)

    def calc_y(self, y, val):
        if self.origin_rotation[0] == "N":
            return y - float(val)
        return y + float(val)

    def update_beacon(self, x, y):
        # 0-location: top-left
        x_loc = self.cs_x + x * self.zoom
        y_loc = self.cs_y + y * self.zoom
        self.canvas.coords(self.beacon, x_loc, y_loc, x_loc + 20, y_loc + 20)

    def menubar(self, root):
        menu = Menu(root)
        root.config(menu=menu)

        editMenu = Menu(menu)
        editMenu.add_command(label="Place origin beacon", command=self.add_beacon)
        editMenu.add_command(label="Add room plan", command=self.add_floor_plan)
        menu.add_cascade(label="Edit", menu=editMenu)

        menu.add_command(label="Replays", command=lambda: self.root.switch_frame(ReplayFrame))


class TrackingFrame(Frame):

    def __init__(self, root):
        Frame.__init__(self, root)
        self.root = root
        self.canvas = CanvasWidget(self)
        self.hedge = MarvelmindHedge(tty="\\.\COM4", adr=None, debug=False)  # create MarvelmindHedge thread
        self.start_comms()

    @staticmethod
    def valid_coords(coords):
        if coords[0] == 0 and coords[1] == 0 and coords[2] == 0 and coords[3] == 0:
            return False
        return True

    def start_comms(self, i=1):
        self.hedge.start()  # start marvelmind thread
        schedule.every(1).second.do(self.communicate)
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
            # log.write(str(coords) + "\n")
            self.canvas.draw_hedgehog(coords[1], coords[2], "orange")
            print(coords)
        else:
            print("Modem not connected!")

    def onclose(self):
        self.hedge.stop()
        self.destroy()


MainApp().mainloop()
