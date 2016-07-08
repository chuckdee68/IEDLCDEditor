# Infinity ErgoDox LCD Editor, by LuX
# The program will insert image and color data into pre-compiled *.dfu.bin files
#
# More info: https://geekhack.org/index.php?topic=82904.0
#       AND: https://input.club/forums/topic/ied-lcd-editor-v0-9-gui-editor-to-modify-the-lcd
#
# Code distributed "as is", use at your own risk


from tkinter import*
from PIL import Image, ImageTk

import ctypes

import serial
from time import sleep

# ============== GLOBALS ==============

IDERR = 0
IDOK = 1
IDCANCEL = 2
IDABORT = 3
IDRETRY = 4
IDIGNORE = 5
IDYES = 6
IDNO = 7
IDTRYAGAIN = 10
IDCONTINUE = 11

in_image = [None] * 8
image_data = [[] for y in range(8)]

# ============== GLOBALS ==============


class Graphics:
    root = None

    display_frame = [None for y in range(8)]
    display_photo = [None for y in range(8)]

    color_slide = [[None for x in range(3)] for y in range(8)]
    color_value = [[None for x in range(3)] for y in range(8)]

    color_int = [[None for x in range(3)] for y in range(8)]

    color_box = [None for y in range(8)]

    img_buttons = [[None for x in range(3)] for y in range(8)]
    gui_buttons = [None for y in range(5)]

    ser = None

    # ================================= INIT ================================ #

    def __init__(self):
        self.root = Tk()
        self.root.title("IED LCD Editor 0.9 - By LuX")
        self.root.resizable(0, 0)

        # =================================== Load images to black-white format
        for n in range(0, 8):
            try:
                in_image[n] = Image.open("F{0}.bmp".format(n)).convert("1")
            except:
                msgBox("Error loading image 'F{0}.bmp'\nThe app will now close".format(n), "File not found", 0)
                exit(1)

            if not in_image[n].width == 128 - 96 * min(1, n) or not in_image[n].height == 32:
                msgBox("Image 'F{0}.bmp' is of wrong size\nShould be:  {1} x 32\nImage is:  {2} x {3}\nThe app will now close".format(n, 128 - 96 * min(1, n), in_image[n].width, in_image[n].height), "Wrong size", 0)
                exit(1)

        # =========================== Transform images into LCD acceptable data
        image_data[0] = [0] * 4 * 128
        for i in range(1, 8):
            image_data[i] = [0] * 4 * 32

        for i in range(0, 8):
            imgwidth = in_image[i].width
            for p in range(0, 4):
                for y in range(0, 8):
                    for x in range(0, imgwidth):
                        if in_image[i].getpixel((x, (3-p)*8 + 7-y)) == 0:
                            image_data[i][p*imgwidth + x] |= (1 << y)

        # =================================================================== #
        # =================================================================== #
        # =================================================================== #

        # ======================================== Look for the keyboard serial
        com_number = 0
        com_ports = []

        # ======================================== Find all available COM ports
        while com_number < 100:
            try:
                self.ser = serial.Serial("COM{0}".format(com_number), 115200, timeout=0.5)
                self.ser.close()
            except:
                pass
            else:
                com_ports.append(com_number)

            if com_number == 99 and len(com_ports) == 0:
                msret = msgBox("No COM ports found!\nCheck that your Infinity Ergodox is plugged in\nDo you want to retry?", "No keyboard found", 5)
                if msret == IDRETRY:
                    com_number = -1
                elif msret == IDNO:
                    exit(1)

            com_number += 1

        # ======================================== Select which COM port to use
        if len(com_ports) > 1:
            com_selection = 0
            while com_selection < len(com_ports):
                msret = msgBox("Multiple COM ports found:{0}\nPress 'Yes' to select {1}\nPress 'NO' for next\nPress 'Cancel' to quit".format(com_ports, com_ports[com_selection]), "Multiple COM ports", 3)
                if msret == IDYES:
                    self.ser = serial.Serial("COM{0}".format(com_ports[com_selection]), 115200, timeout=0.5)
                    com_selection = len(com_ports)
                elif msret == IDNO:
                    com_selection += 1
                    if com_selection == len(com_ports):
                        com_selection = 0
                elif msret == IDCANCEL:
                    exit(1)
        self.ser.close()

        # =================================================================== #
        # =================================================================== #
        # =================================================================== #

        # ================================================ Make tkinter widgets

        # Load and make color scales
        colors = []
        try:
            with open("colors.txt") as f:
                line_num = 0
                for line in f:
                    line_num += 1
                    try:
                        colors.append(max(0, min(int(line), 100)))
                    except:
                        msgBox("Invalid color in 'colors.txt': '{0}', at line: {1}\nThe app will now close".format(line.rstrip(), line_num), "Invalid color", 0)
                        exit(1)
        except:
            msgBox("Error loading 'colors.txt'!\nThe app will now close", "File not found", 0)
            exit(1)

        if len(colors) < 24:
            msgBox("Invalid amount of colors in 'colors.txt'\nMake sure there are 24 lines of numbers in the file\nThe app will now close", "Invalid file", 0)
            exit(1)

        for i in range(0, 8):
            for c in range(0, 3):
                colorr = "red"
                if c == 1: colorr = "green"
                elif c == 2: colorr = "blue"

                self.color_value[i][c] = IntVar()
                self.color_slide[i][c] = Scale(self.root, bg=colorr, from_=0, to=100, variable=self.color_value[i][c], orient=HORIZONTAL,
                                               showvalue=0, width=12, length=200, sliderlength=20, command=self.updatecolor)
                self.color_slide[i][c].set(int(colors[i*3+c]))
                self.color_slide[i][c].place(x=40, y=20+i*80+c*20)

                self.color_int[i][c] = Label(self.root, text="0%")
                self.color_int[i][c].place(x=5, y=19+i*80+c*20)

            self.color_box[i] = Label(self.root, text="", width=1, padx=71, height=1, pady=19, bg="#FFFFFF")
            self.color_box[i].place(x=260, y=22+i*80)

        for i in range(0, 8):
            temp_img = Image.new("1", (128, 32), "white")
            temp_img.paste(in_image[i], (0, 0))
            self.display_photo[i] = ImageTk.PhotoImage(temp_img)

            self.display_frame[i] = Label(self.root, image=self.display_photo[i], padx=0, pady=0)
            self.display_frame[i].place(x=270, y=32+i*80)

        for i in range(0, 8):
            self.img_buttons[i][0] = Button(self.root, text="Preview", bg="#AAAAAA", font=("arial", 8), width=14, pady=-2, command=lambda ind=i: self.previewimage(ind))
            self.img_buttons[i][0].place(x=430, y=15+i*80)
            self.img_buttons[i][1] = Button(self.root, text="Reload Image", bg="#999999", font=("arial", 8), width=14, pady=-2, command=lambda ind=i: self.reloadimage(ind))
            self.img_buttons[i][1].place(x=430, y=38+i*80)
            self.img_buttons[i][2] = Button(self.root, text="Reload Color", bg="#888888", font=("arial", 8), width=14, pady=-2, command=lambda ind=i: self.reloadcolor(ind))
            self.img_buttons[i][2].place(x=430, y=61+i*80)

        self.gui_buttons[0] = Button(self.root, text="Default colors", bg="#9999AA", width=20, pady=-2, command=self.defaultall)
        self.gui_buttons[0].place(x=10, y=665)
        self.gui_buttons[1] = Button(self.root, text="Reload all", bg="#99AA99", width=20, pady=-2, command=self.reloadall)
        self.gui_buttons[1].place(x=195, y=665)
        self.gui_buttons[2] = Button(self.root, text="Exit", bg="#AA9999", width=20, pady=-2, command=self.root.destroy)
        self.gui_buttons[2].place(x=380, y=665)
        self.gui_buttons[3] = Button(self.root, text="Save LEFT.dfu.bin", bg="#44FF44", width=20, pady=-2, command=lambda left=True: self.savetofile(left))
        self.gui_buttons[3].place(x=100, y=700)
        self.gui_buttons[4] = Button(self.root, text="Save RIGHT.dfu.bin", bg="#44FF44", width=20, pady=-2, command=lambda left=False: self.savetofile(left))
        self.gui_buttons[4].place(x=300, y=700)


        self.root.geometry("540x735")
        self.root.mainloop()

# =========================================================================== #

    def updatecolor(self, a):
        for i in range(0, 8):
            col_r = int(pow(self.color_value[i][0].get(), 1/4) * 80.638)
            col_g = int(pow(self.color_value[i][1].get(), 1/4) * 80.638)
            col_b = int(pow(self.color_value[i][2].get(), 1/4) * 80.638)
            self.color_box[i].config(bg=('#%02x%02x%02x' % (col_r, col_g, col_b)))

            self.color_int[i][0].config(text="{0}%".format(self.color_value[i][0].get()))
            self.color_int[i][1].config(text="{0}%".format(self.color_value[i][1].get()))
            self.color_int[i][2].config(text="{0}%".format(self.color_value[i][2].get()))

# =========================================================================== #

    def previewimage(self, i):
        try:
            self.ser.open()

            # Change color
            command = "lcdColor " + str(int(655.35 * self.color_value[i][0].get())) + " " + str(int(655.35 * self.color_value[i][1].get())) + " " + str(int(655.35 * self.color_value[i][2].get())) + " \r"
            self.ser.write(command.encode())
            sleep(0.05)

            # Change image
            width = 128
            if i > 0: width = 32

            for segment in range(8):
                for y in range(0,4):
                    command = "lcdDisp " + hex(y) + " " + hex(segment * 16) + " "
                    for x in range(segment*16, segment*16+16):
                        if x < width:
                            command += hex(image_data[i][y*width + x]) + " "
                        else:
                            command += hex(0) + " "
                    command += "\r"
                    self.ser.write(command.encode())
                    sleep(0.03)
            self.ser.close()

        except:
            msret = msgBox("Error while previewing an image!\nThe app will now close\nDo you want to save colors?", "Error", 4)
            if msret == IDYES:
                with open("colors.txt", 'w') as cfile:
                    for i in range(0, 8):
                        cfile.write(str(self.color_value[i][0].get()) + "\n")
                        cfile.write(str(self.color_value[i][1].get()) + "\n")
                        cfile.write(str(self.color_value[i][2].get()) + "\n")
                cfile.close()
                exit(0)

            elif msret == IDNO:
                exit(0)


# =========================================================================== #

    def reloadimage(self, i):
        # ========================================== Reload the image from file
        try:
            in_image[i] = Image.open("F{0}.bmp".format(i)).convert("1")
        except:
            self.root.destroy()

        # =============================================== Clear previous buffer
        for n in range(0, len(image_data[i])):
            image_data[i][n] = 0

        # ======================================= Transform new image to buffer
        imgwidth = in_image[i].width
        for p in range(0, 4):
            for y in range(0, 8):
                for x in range(0, imgwidth):
                    if in_image[i].getpixel((x, (3-p)*8 + 7-y)) == 0:
                        image_data[i][p*imgwidth + x] |= (1 << y)

        # ============================================ Re-present the GUI image
        temp_img = Image.new("1", (128, 32), "white")
        temp_img.paste(in_image[i], (0, 0))
        self.display_photo[i] = ImageTk.PhotoImage(temp_img)
        self.display_frame[i].config(image=self.display_photo[i])

# =========================================================================== #

    def reloadcolor(self, i):
        with open("colors.txt") as f:
            colors = f.readlines()
        if len(colors) != 24: exit(32)

        self.color_slide[i][0].set(int(colors[i*3]))
        self.color_slide[i][1].set(int(colors[i*3+1]))
        self.color_slide[i][2].set(int(colors[i*3+2]))

# =========================================================================== #

    def defaultall(self):
        # ====================================================== default images
        # TODO: set images... meh

        # ======================================== default colors (approximate)
        self.color_slide[0][0].set(int(6))
        self.color_slide[0][1].set(int(6))
        self.color_slide[0][2].set(int(6))

        self.color_slide[1][0].set(int(65))
        self.color_slide[1][1].set(int(15))
        self.color_slide[1][2].set(int(12))

        self.color_slide[2][0].set(int(30))
        self.color_slide[2][1].set(int(55))
        self.color_slide[2][2].set(int(20))

        self.color_slide[3][0].set(int(0))
        self.color_slide[3][1].set(int(50))
        self.color_slide[3][2].set(int(70))

        self.color_slide[4][0].set(int(96))
        self.color_slide[4][1].set(int(64))
        self.color_slide[4][2].set(int(28))

        self.color_slide[5][0].set(int(72))
        self.color_slide[5][1].set(int(36))
        self.color_slide[5][2].set(int(52))

        self.color_slide[6][0].set(int(74))
        self.color_slide[6][1].set(int(71))
        self.color_slide[6][2].set(int(18))

        self.color_slide[7][0].set(int(1))
        self.color_slide[7][1].set(int(50))
        self.color_slide[7][2].set(int(34))

# =========================================================================== #

    def reloadall(self):
        for i in range(0, 8):
            self.reloadimage(i)
            self.reloadcolor(i)

# =========================================================================== #

    def savetofile(self, left_side):

        # Save color values
        with open("colors.txt", 'w') as cfile:
            for i in range(0, 8):
                cfile.write(str(self.color_value[i][0].get()) + "\n")
                cfile.write(str(self.color_value[i][1].get()) + "\n")
                cfile.write(str(self.color_value[i][2].get()) + "\n")
        cfile.close()

        # Save data
        filen = "left_kiibohd.dfu.bin"
        if not left_side: filen = "right_kiibohd.dfu.bin"

        try:
            with open(filen, 'rb') as infile, open("custom_"+filen[3:], 'wb') as outfile:
                search = True

                functionsSaved = False
                colorsSaved = False
                defaultSaved = False

                sstr = b"12345678901234567890"
                while search:
                    byte = infile.read(1)
                    sstr = (sstr + byte)[1:]
                    if not byte == b'':
                        if not functionsSaved and sstr == bytes([0xFC, 0xFC, 0xFC, 0xFC , 0xFC , 0xFC , 0xFC , 0xFC , 0xFC , 0xFC , 0xFC , 0xFF , 0xFF , 0xFF , 0xFF , 0xFF , 0xFF , 0x00 , 0x00 , 0x00]):
                            functionsSaved = True

                            outfile.write(bytes(2))
                            outfile.write((''.join(chr(i) for i in image_data[1])).encode('latin-1'))
                            outfile.write((''.join(chr(i) for i in image_data[2])).encode('latin-1'))
                            outfile.write((''.join(chr(i) for i in image_data[3])).encode('latin-1'))
                            outfile.write((''.join(chr(i) for i in image_data[4])).encode('latin-1'))
                            outfile.write((''.join(chr(i) for i in image_data[5])).encode('latin-1'))
                            outfile.write((''.join(chr(i) for i in image_data[6])).encode('latin-1'))
                            outfile.write((''.join(chr(i) for i in image_data[7])).encode('latin-1'))
                            infile.read(897)

                        elif not colorsSaved and sstr == bytes([0xFC, 0xFC, 0xFC, 0xFC, 0xFC, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x39, 0xB9, 0xEA, 0xAA, 0x8D, 0x8D]):
                            colorsSaved = True

                            outfile.write(bytes([0x8D]))
                            for col in range(1, 8):
                                for chan in range(0, 3):
                                    colval = int(655.35 * self.color_value[col][chan].get())
                                    lo, hi = divmod(colval, 1 << 8)
                                    outfile.write(chr(hi).encode('latin-1'))
                                    outfile.write(chr(lo).encode('latin-1'))
                            infile.read(42)

                        elif not defaultSaved and sstr == b"Defaults to control.":
                            defaultSaved = True

                            outfile.write(b"." + bytes(1))
                            outfile.write((''.join(chr(i) for i in image_data[0])).encode('latin-1'))
                            infile.read(513)
                        else:
                            outfile.write(byte)
                    else:
                        search = False

                if not (functionsSaved and colorsSaved and defaultSaved):
                    msgBox("An error may have occurred while saving '{0}'!\nRemake the .dfu.bin files from the online configurator and try again".format("custom_"+filen[3:]), "Error while saving", 0)
                else:
                    msgBox("'{0}' Saved successfully!".format("custom_"+filen[3:]), "File saved", 0)

            infile.close()
            outfile.close()

        except:
            msgBox("Error while saving file!\nColors have been saved".format(filen), "File not found", 0)


def msgBox(text, caption, utype):
    result = ctypes.windll.user32.MessageBoxW(0, text, caption, utype)
    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    return result


# =========================================================================== #


gfx = Graphics()
