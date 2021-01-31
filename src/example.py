from tkinter import *
import os

COLORS = ['black', 'red', 'yellow', 'azure4', 'orange', 'maroon', 'pink', 'lime green', 'dark violet', 'green']

root = Tk()
numx = 12
numy = 9
sizex = 1000 / numx
sizey = 500 / numy
array = [0] * (numx * numy)

frame = Frame(root, width=1000, height=500)

frame.pack()
myCanvas = Canvas(frame, bg='white', width=1000, height=500)


def output():
    x = "test"
    print("outputing to file " + x + ".infile and " + x + ".ps")

    f = open(x + ".infile", 'w')
    print(numx, numy)
    f.write(str(numx) + " " + str(numy) + "\n")

    blocks = []
    for i in range(0, len(array)):
        if array[i] == -1:
            blocks.append([i - numx * (i / numx), i / numx])

    print(len(blocks))
    f.write(str(len(blocks)) + "\n")
    for el in blocks:
        print(el[0], el[1])
        f.write(str(el[0]) + " " + str(el[1]) + "\n")

    wires = []
    for j in range(1, 9):
        wire = []
        for i in range(0, len(array)):
            if array[i] == j:
                wire.append([i - numx * (i / numx), i / numx])

        if len(wire) > 0:
            wires.append(wire)

    print(len(wires))
    f.write(str(len(wires)) + "\n")

    for el in wires:
        outwire = [len(el)]
        for i in el:
            outwire.append(i[0])
            outwire.append(i[1])
        for i in outwire:
            f.write(str(i) + " ")
            print(i, end=' ')
        print()
        f.write("\n")

    f.close()

    myCanvas.postscript(file=x + ".ps")


def keyx(event):
    if int(event.char) == 0:
        print("Zero")
    else:
        cv = event.widget
        xloc = int(event.x / sizex)
        yloc = int(event.y / sizey)
        print("Clicked at", xloc, yloc)
        array[yloc * numx + xloc] = int(event.char)
        cv.create_rectangle(sizex * xloc, sizey * yloc, sizex * (xloc + 1), sizey * (yloc + 1),
                            fill=COLORS[int(event.char)])
        cv.create_text(sizex * (xloc + 0.5), sizey * (yloc + 0.5), text=int(event.char))


def callback(event):
    cv = event.widget
    xloc = int(event.x / sizex)
    yloc = int(event.y / sizey)
    print("Clicked at", xloc, yloc)
    array[yloc * numx + xloc] = -1
    cv.create_rectangle(sizex * xloc, sizey * yloc, sizex * (xloc + 1), sizey * (yloc + 1), fill="blue")


myCanvas.focus_set()
myCanvas.bind("<Key>", keyx)
myCanvas.bind("<Button-1>", callback)

myCanvas.pack()

for x in range(0, numx):
    for y in range(0, numy):
        myCanvas.create_rectangle(sizex * x, sizey * y, sizex * (x + 1), sizey * (y + 1), fill="white")

root.mainloop()
