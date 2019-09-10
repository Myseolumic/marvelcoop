from marvelmind import MarvelmindHedge
from time import sleep
import sys
from tkinter import *
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

#whole app requires: pyserial, crcmod, matplotlib

class TopMenu:

    def __init__(self, root):
        menu = Menu(root)
        root.config(menu=menu)

        editMenu = Menu(menu)
        editMenu.add_command(label="Place Beacon", command=self.place_beacon)
        editMenu.add_command(label="Add room plan", command=self.place_beacon)
        menu.add_cascade(label="Edit", menu=editMenu)

        menu.add_command(label="Review", command=self.place_beacon())


    def place_beacon(self):
        print("placed.")

class BigCanvas:

    def __init__(self, root):
        self.canvas = Canvas(root, width=200, height=200)
        self.canvas.grid(row=2, column=0, columnspan=3, sticky='nsew')
        self.beacon = self.canvas.create_rectangle(0,0,20,20)

    def update_beacon(self, x, y):
        self.canvas.coords(self.beacon, x, y)


def main(window, canvas):
    hedge = MarvelmindHedge(tty="\\.\COM4", adr=None, debug=False)  # create MarvelmindHedge thread
    hedge.start()  # start thread
    while True:
        try:
            sleep(1)
            hedge.print_position()
            if (hedge.distancesUpdated):
                hedge.print_distances()

            print(hedge.position())
            coords = hedge.position()
            canvas.update_beacon(coords[1], coords[2])
            window.update()

        except KeyboardInterrupt:
            hedge.stop()  # stop and close serial port
            sys.exit()


x = list()
y = list()
for i in range(1,6):
    x.append(i)
    y.append(i*2)

window = Tk()
window.geometry("300x300")
window.title("Coopi tracker")

TopMenu(window)
canvas = BigCanvas(window)

main(window, canvas)