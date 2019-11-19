from marvelmind import MarvelmindHedge
from time import sleep
import sys
from tkinter import *
import tkinter.filedialog as FileDialog
from PIL import ImageTk


#whole app requires: pyserial, crcmod, matplotlib, Pillow
class SampleApp(Tk):
    def __init__(self):
        Tk.__init__(self)
        self._frame = None
        self.geometry("1280x720")
        self.title("Coopi tracker")
        self.switch_frame(TrackingFrame)

    def switch_frame(self, frame_class):
        print("switched window")
        new_frame = frame_class(self)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.pack()


class ReplayFrame(Frame):

    def __init__(self, root):
        Frame.__init__(self, root)
        self.canvas_widget = CanvasWidget(self, 0, 1)
        self.file = FileDialog.askopenfile(parent=root, mode='r', title='Choose a file')
        self.bg_image = ImageTk.PhotoImage(file='test_image.png')
        self.beacons = {}
        self.beacons_active = {}
        for line in self.file.readlines():
            parts = line.strip().replace(' ', '')[1:-1].split(',')
            if parts[0] not in self.beacons.keys():
                self.beacons[parts[0]] = []
            self.beacons[parts[0]].append(parts[1:])
        self.file.close()
        self.start_time = int(self.beacons.get("13")[0][4])
        self.end_time = int(self.beacons.get("13")[-1][4])
        self.scale = Scale(self, from_=self.start_time, to=self.end_time, orient=HORIZONTAL, command=self.update_canvas)\
            .grid(row=1, column=0, columnspan=3, sticky=W)

        j = 0
        self.beacons_container = Frame(self, borderwidth=1)
        for beacon in self.beacons.keys():
            self.beacons_active[beacon] = IntVar()
            Checkbutton(self.beacons_container, text="Beacon "+beacon, variable=self.beacons_active[beacon]).grid(row=j, sticky=W)
            j += 1
        self.beacons_container.grid(row=0, column=0, sticky=W)

    def update_canvas(self, scale_value):
        self.canvas_widget.canvas.delete("all")
        self.canvas_widget.canvas.create_image(400, 300, image=self.bg_image)
        self.canvas_widget.canvas.create_line(0, 0, 800, 600, fill="black")
        self.canvas_widget.draw_origin()
        for b_name in self.beacons_active:
            print(b_name, self.beacons_active[b_name].get())
            if self.beacons_active[b_name].get() == 0:
                continue
            for i in range(len(self.beacons[b_name])-1):
                if self.beacons[b_name][i+1][4] > scale_value:
                    break
                point1 = self.beacons[b_name][i]
                point2 = self.beacons[b_name][i+1]
                self.canvas_widget.draw_line(point1, point2)


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
        self.canvas.grid(row=row, column=column, columnspan=3, sticky='nsew')
        self.beacon = self.canvas.create_rectangle(0, 0, 20, 20, fill="blue")
        self.beacon = self.canvas.create_rectangle(0, 0, 20, 20, fill="red")
        self.canvas.bind('<Button-1>', self.place_beacon)
        self.cs_x = 0
        self.cs_y = 0
        self.zoom = 10

    def place_beacon(self, event):
        self.cs_x = event.x
        self.cs_y = event.y
        self.draw_origin()

    def draw_origin(self):
        self.canvas.create_oval(self.cs_x-5, self.cs_y-5, self.cs_x+5, self.cs_y+5, fill="yellow")

    def draw_line(self, point1, point2):
        x1 = self.cs_x + float(point1[0]) * self.zoom
        y1 = self.cs_y + float(point1[1]) * self.zoom
        x2 = self.cs_x + float(point2[0]) * self.zoom
        y2 = self.cs_y + float(point2[1]) * self.zoom
        self.canvas.create_line(x1, y1, x2, y2, fill="red", width=2)

    def update_beacon(self, x, y):
        #0-location: top-left
        x_loc = self.cs_x + x * self.zoom
        y_loc = self.cs_y + y * self.zoom
        self.canvas.coords(self.beacon, x_loc, y_loc, x_loc+20, y_loc+20)


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


main(SampleApp())
