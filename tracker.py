from marvelmind import MarvelmindHedge
from time import sleep
import sys
from tkinter import *
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


def main():
    hedge = MarvelmindHedge(tty="\\.\COM4", adr=None, debug=False)  # create MarvelmindHedge thread
    hedge.start()  # start thread
    f = open("demofile2.txt", "a")
    while True:
        try:
            # print (hedge.position()) # get last position and print
            sleep(1)
            hedge.print_position()
            if (hedge.distancesUpdated):
                hedge.print_distances()

            print(hedge.position() )
            #print("Raw data:")
            #print("valuesUltrasoundPosition: " + str(hedge.valuesUltrasoundPosition))
            #print("valuesImuData: " + str(hedge.valuesImuData))
            #print("valuesImuRawData: " + str(hedge.valuesImuRawData))
            #print()
            #window.update()
            #f.write(hedge.position()+';'+hedge.distances())
        except KeyboardInterrupt:
            hedge.stop()  # stop and close serial port
            f.close()
            sys.exit()


x = list()
y = list()
for i in range(1,6):
    x.append(i)
    y.append(i*2)

#window = Tk()
#window.geometry("300x300")
#window.title("Coopi tracker")

main()

#figure = Figure(figsize=(4, 4), dpi=70)
#figure.suptitle('Location')

#a = figure.add_subplot(111)
#a.plot(x,y,marker='o')
#a.grid()

#canvas = FigureCanvasTkAgg(figure, master=window)
#canvas.draw()

#graph_widget = canvas.get_tk_widget()
#graph_widget.grid(row=0, column=0, columnspan=3, sticky='nsew')


