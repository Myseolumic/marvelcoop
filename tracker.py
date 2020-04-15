from marvelmind import MarvelmindHedge
from time import sleep
import numpy as np
import sys
import threading as th
from tkinter import *
import tkinter.filedialog as FileDialog
from PIL import ImageTk


# whole app requires: pyserial, crcmod, matplotlib, Pillow, numpy
class SampleApp(Tk):
    def __init__(self):
        Tk.__init__(self)
        self._frame = None
        self.geometry("1280x720")
        self.title("Coopi tracker")
        # self.commThread = CommThread()
        # self.commThread.setDaemon(True)
        self.switch_frame(ReplayFrame)

    def switch_frame(self, frame_class):
        print("switched window")
        new_frame = frame_class(self)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.pack()

        if frame_class == ReplayFrame:
            self._frame.canvas_widget.menubar(self)


class BeaconPath(object):
    def __init__(self, id, mat):
        self.start_point = (mat[0][0], mat[0][1])
        self.id = id
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


# feeds info into TrackingFrame
class CommThread(th.Thread):

    def __init__(self):
        th.Thread.__init__(self)
        hedge = MarvelmindHedge(tty="\\.\COM4", adr=None, debug=False)  # create MarvelmindHedge thread
        hedge.start()  # start thread
        with open("C:/Users/karl3/Desktop/test_save_active_2.txt", "w", encoding="utf-8") as log:
            while True:
                try:
                    sleep(1)
                    coords = hedge.position()
                    # currentpoint = (coords[1], coords[2])
                    if self.valid_coords(coords):
                        log.write(str(coords) + "\n")

                except KeyboardInterrupt:
                    hedge.stop()  # stop and close serial port
                    sys.exit()

    @staticmethod
    def valid_coords(coords):
        if coords[0] == 0 and coords[1] == 0 and coords[2] == 0 and coords[3] == 0:
            return False
        return True


class ReplayFrame(Frame):

    def __init__(self, root):
        # Init objects
        Frame.__init__(self, root)
        self.canvas_widget = CanvasWidget(self, 0, 1)
        self.file = FileDialog.askopenfile(parent=root, mode='r', title='Choose a file')
        self.bg_image = ImageTk.PhotoImage(file='test_image.png')
        self.beacons_active = {}
        self.beacon_paths = {}

        # parse raw data into an id-based dictionary
        beacons = {}
        prev_parts = None
        for line in self.file.readlines():
            parts = line.strip().replace(' ', '')[1:-1].split(',')

            for i in range(len(parts[1:-1])):
                parts[i + 1] = float(parts[i + 1])
            parts[-1] = int(parts[-1])
            if parts == prev_parts:
                continue

            if parts[0] not in beacons.keys():
                beacons[parts[0]] = []

            beacons[parts[0]].append(parts[1:])
            prev_parts = parts[:]
        self.file.close()

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
        self.scale = Scale(self, from_=self.start_time, to=self.end_time, orient=HORIZONTAL, command=self.update_canvas) \
            .grid(row=1, column=0, columnspan=3, sticky=W)

        # Setup Checkboxes for enabling beacons
        j = 0
        self.beacons_container = Frame(self, borderwidth=1)
        for beacon in self.beacon_paths:
            self.beacons_active[beacon] = IntVar()
            Checkbutton(self.beacons_container, text="Beacon " + beacon, variable=self.beacons_active[beacon]).grid(
                row=j, sticky=W)
            j += 1
        self.beacons_container.grid(row=0, column=0, sticky=W)

        # Setup map image container
        self.map_container = Frame(self, borderwidth=1)
        self.map_container.grid(row=1, column=0, sticky=W)

    def update_canvas(self, scale_value):
        self.canvas_widget.canvas.delete("all")
        self.canvas_widget.canvas.create_image(400, 300, image=self.bg_image)
        # self.canvas_widget.canvas.create_line(0, 0, 800, 600, fill="black")
        self.canvas_widget.draw_origin()
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


class TrackingFrame(Frame):

    def __init__(self, root):
        Frame.__init__(self, root)
        self.root = root
        self.canvas = CanvasWidget(self)
        CanvasControls(self, self.canvas)
        self.menubar(root)

    def menubar(self, root):
        menu = Menu(root)
        root.config(menu=menu)

        editMenu = Menu(menu)
        editMenu.add_command(label="Place origin beacon", command=self.canvas.place_beacon)
        editMenu.add_command(label="Add room plan", command=self.place_beacon)
        menu.add_cascade(label="Edit", menu=editMenu)

        menu.add_command(label="Replays", command=lambda: self.root.switch_frame(ReplayFrame))

    def place_beacon(self):
        print("placed.")


class CanvasWidget:

    def __init__(self, root, row=0, column=0):
        self.canvas = Canvas(root, width=800, height=600, bg="blue")
        self.canvas.grid(row=row, column=column, columnspan=3, rowspan=3, sticky='nsew')
        self.beacon = self.canvas.create_rectangle(0, 0, 20, 20, fill="blue")
        self.beacon = self.canvas.create_rectangle(0, 0, 20, 20, fill="red")
        self.canvas.bind('<Button-1>', self.handle_mouse_click)
        #self.canvas.bind('<MouseWheel>', self.handle_mouse_wheel)
        self.canvas.bind('<B1-Motion>', self.pan_canvas)
        self.canvas.bind('<ButtonRelease-1>', self.end_pan)
        self.cs_x = 0
        self.cs_y = 0
        self.zoom = 30

        self.PLACING_BEACON = False
        self.PLACING_IMAGE = False
        self.PANNING = False

    def handle_mouse_wheel(self, event):
        """ Zoom with mouse wheel """
        x = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
        y = self.canvas.canvasy(event.y)

        scale = 1.0
        if event.delta == -120:  # scroll down
            print("scrolling down")
        if event.delta == 120:  # scroll up, bigger
            print("scrolling up")

        #self.canvas.scale('all', x, y, scale, scale)  # rescale all objects

    def handle_mouse_click(self, event):
        print(self.PLACING_BEACON)
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
        self.PLACING_IMAGE = True

    def draw_origin(self):
        self.canvas.create_oval(self.cs_x - 5, self.cs_y - 5, self.cs_x + 5, self.cs_y + 5, fill="yellow")

    def draw_lines(self, start, vectors):
        x1 = self.cs_x + float(start[0])
        y1 = self.cs_y + float(start[1])
        for vector in vectors:
            vector = np.multiply(vector, self.zoom)
            x2 = x1 + float(vector[0])
            y2 = y1 - float(vector[1])
            self.canvas.create_line(x1, y1, x2, y2, fill="red", width=2)
            x1 = x2
            y1 = y2

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
        menu.add_cascade(label="Canvas...", menu=editMenu)

        menu.add_command(label="Replays", command=lambda: self.root.switch_frame(ReplayFrame))


class CanvasControls:

    def __init__(self, root, canvas_widget):
        self.canvasWidget = canvas_widget
        Label(root, text="Zoom").grid(row=2)
        self.zoom_entry = Entry(root)
        self.zoom_entry.bind("<Return>", self.update_zoom)
        self.zoom_entry.grid(row=2, column=1)

    def update_zoom(self, event):
        self.canvasWidget.zoom = int(self.zoom_entry.get())


def valid_coords(coords):
    if coords[0] == 0 and coords[1] == 0 and coords[2] == 0 and coords[3] == 0:
        return False
    return True


def main(window):
    hedge = MarvelmindHedge(tty="\\.\COM4", adr=None, debug=False)  # create MarvelmindHedge thread
    hedge.start()  # start thread
    with open("C:/Users/karl3/Desktop/test_save_active_2.txt", "w", encoding="utf-8") as log:
        while True:
            try:
                coords = hedge.position()
                if type(window._frame) == TrackingFrame:
                    window._frame.canvas.update_beacon(coords[1], coords[2])
                if valid_coords(coords):
                    log.write(str(coords) + "\n")
                    print(coords)
                window.update()

            except KeyboardInterrupt:
                hedge.stop()  # stop and close serial port
                sys.exit()


#main(SampleApp())

SampleApp().mainloop()
