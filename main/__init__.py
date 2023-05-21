import os
import subprocess as sp
import sys
import tkinter as tk
from PIL import ImageTk, Image

from carbon.gui.button.v2 import Button
from carbon.gui.label import Label
from carbon.gui.slider import Slider
from carbon.keycrate import KeyCrate
from carbon.path import open_file
from carbon.utils import printer

from main.constants import SOFTWARE_NAME, SOFTWARE_VER, TMP_DIR_PTH, SETTINGS_FILE_PTH, PROXY_FILE_PTH
from main.core import core


def deleting_intermediate_files():
    """from previous run. execute at first just in case there's an error from previous run that leave intermediate files"""
    if os.path.isfile(PROXY_FILE_PTH):
        printer(f'INFO: Deleting {repr(PROXY_FILE_PTH)}...')
        os.remove(PROXY_FILE_PTH)
deleting_intermediate_files()


## "tmp" folder should be clean, used for storing intermediate files
## during runtime and to prevent unintended file deletions.
if not (
    (len(os.listdir(TMP_DIR_PTH)) == 1)
    and
    (os.listdir(TMP_DIR_PTH)[0] == '.gitkeep')
):
    ## this shouldn't be raised unless bug occurs
    raise AssertionError(f'Directory {repr(TMP_DIR_PTH)} is not clean.')


## open settings
if len(sys.argv) != 1:
    if sys.argv[1] == 'settings':
        open_file(SETTINGS_FILE_PTH)
        printer(f'INFO: settings file opened')
    else:
        printer(f'ERROR: Maybe you meant to run `python {SOFTWARE_NAME} settings` instead?')
    sys.exit(1)


## parsing the settings
try:
    settings = KeyCrate(
        SETTINGS_FILE_PTH, key_is_var=True, eval_value=True,
        only_keys=['ffmpeg', 'open_dir', 'save_dir']
    )
except (SyntaxError, ValueError, AssertionError) as err:
    printer(f'ERROR: Run `python {SOFTWARE_NAME} settings` to fix this error: {err}')
    sys.exit(1)


## <checking ffmpeg>
FFMPEG = settings.ffmpeg

if FFMPEG != 'ffmpeg':
    if not (os.path.isfile(FFMPEG) and os.path.splitext(FFMPEG.lower())[1] == '.exe'):
        settings.open()
        printer(f'ERROR: FFmpeg not recognized or not an .exe file (reconfigure in settings file): {repr(FFMPEG)}')
        sys.exit(1)

try:
    sp.run([FFMPEG, '-version'], stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    printer(f'INFO: ffmpeg is valid and usable.')
except FileNotFoundError:
    settings.open()
    printer(f'ERROR: ffmpeg not found or not a recognized command (reconfigure in settings file): {repr(FFMPEG)}')
    sys.exit(1)
## </checking ffmpeg>


## <validating open/save dir>
OPEN_DIR_PTH = settings.open_dir
if OPEN_DIR_PTH != '/':
    if not os.path.isdir(OPEN_DIR_PTH):
        printer(f'WARNING: the default open-folder is not a dir: {repr(OPEN_DIR_PTH)}')
        OPEN_DIR_PTH = '/'

SAVE_DIR_PTH = settings.save_dir
if SAVE_DIR_PTH != '/':
    if not os.path.isdir(SAVE_DIR_PTH):
        printer(f'WARNING: the default save-folder is not a dir: {repr(SAVE_DIR_PTH)}')
        SAVE_DIR_PTH = '/'
## </validating open/save dir>


root = tk.Tk()
root.title(f'{SOFTWARE_NAME}-v{SOFTWARE_VER}')
root.attributes('-fullscreen', True)

mon_width = root.winfo_screenwidth()
mon_height = root.winfo_screenheight()

page = tk.Canvas(width=mon_width, height=mon_height, bg='#111', highlightthickness=0, borderwidth=0)
page.place(x=0, y=0)


Button.set_page(page)
Slider.set_page(page)

Slider.set_page_focus([None])  # not using page-focus mechanism


def prepare():  # using a function to preserve variable names and avoid conflicts
    """will return the variable that is going to be used"""
    
    r = 0.28  # to adjust the tools page width
    page.create_rectangle(
        mon_width*r, -1,  # -1 instead of 0 to remove the top border
        mon_width, mon_height,
        fill='#070707', outline='#555'
    )
    
    padx = 0.05
    pady = 0.05

    w = (1 - padx*2)*(mon_width - mon_width*r)
    h = (1 - pady*2)*mon_height
    x = mon_width*r + ((mon_width - mon_width*r) - w)*0.5  # 0.5 to make it centered
    y = (mon_height - h)*0.5
    
    ## uncomment to show the image bounding box
    # page.create_rectangle(x, y, x+w, y+h, outline='#f00')

    return w, h, x, y

PROXY_BOX_W, PROXY_BOX_H, PROXY_BOX_X, PROXY_BOX_Y = prepare()


TOLERANCE = 5  # crop TL and DR tolerance radius


class Rt:  # runtime

    input_pth = None

    proxy_photo = None  # to prevent the image from being collected by the Python garbage collector


    ## 0: no rotation
    ## 1: 90 CCW
    ## 2: 180 deg
    ## 3: 90 CW
    rotate = 0


    do_crop = False
    crop_tl_x = None
    crop_tl_y = None
    crop_dr_x = None
    crop_dr_y = None
    crop_offset_x = None
    crop_offset_y = None
    crop_mode = None
    crop_proxy_w = None
    crop_proxy_h = None
    crop_proxy_x = None
    crop_proxy_y = None
    crop_real_w = None
    crop_real_h = None
    crop_w = None
    crop_h = None
    crop_x = None
    crop_y = None


    ## change these values to change the default value of the sliders.
    ## these values are the default by FFmpeg.
    contrast = 1
    brightness = 0
    saturation = 1
    gamma = 1
    gamma_r = 1
    gamma_g = 1
    gamma_b = 1
    vignette = 0
    colortemperature = 6500
    avgblur = 1  # 1 is the minimum value, based on ffmpeg error message

    ## the gate
    do_contrast = False
    do_brightness = False
    do_saturation = False
    do_gamma = False
    do_gamma_r = False
    do_gamma_g = False
    do_gamma_b = False
    do_vignette = False
    do_colortemperature = False
    do_avgblur = False

    ## 1: highest quality
    ## 31: lowest quality
    ## src: https://trac.ffmpeg.org/wiki/Encode/MPEG-4#:~:text=You%20can%20select%20a%20video,the%20lowest%20quality%2Fsmallest%20filesize.
    q_v = 1

def redraw_crop_grid():

    color = '#888'
    color_ctr = '#555'

    page.delete('crop_grid')

    ## because the center line darker, it must below the lighter
    y = Rt.crop_tl_y + (Rt.crop_dr_y-Rt.crop_tl_y)/2
    page.create_line(Rt.crop_tl_x, y, Rt.crop_dr_x, y, fill=color_ctr, tags='crop_grid')

    x = Rt.crop_tl_x + (Rt.crop_dr_x-Rt.crop_tl_x)/2
    page.create_line(x, Rt.crop_tl_y, x, Rt.crop_dr_y, fill=color_ctr, tags='crop_grid')

    page.create_rectangle(
        Rt.crop_tl_x, Rt.crop_tl_y, Rt.crop_dr_x, Rt.crop_dr_y,
        outline=color, tags='crop_grid'
    )
    page.create_oval(
        Rt.crop_tl_x-TOLERANCE, Rt.crop_tl_y-TOLERANCE,
        Rt.crop_tl_x+TOLERANCE, Rt.crop_tl_y+TOLERANCE,
        fill='#000', outline=color, tags='crop_grid'
    )
    page.create_oval(
        Rt.crop_dr_x-TOLERANCE, Rt.crop_dr_y-TOLERANCE,
        Rt.crop_dr_x+TOLERANCE, Rt.crop_dr_y+TOLERANCE,
        fill='#000', outline=color, tags='crop_grid'
    )

    y = Rt.crop_tl_y + (Rt.crop_dr_y-Rt.crop_tl_y)*(1/3)
    page.create_line(Rt.crop_tl_x, y, Rt.crop_dr_x, y, fill=color, tags='crop_grid')
    y = Rt.crop_tl_y + (Rt.crop_dr_y-Rt.crop_tl_y)*(2/3)
    page.create_line(Rt.crop_tl_x, y, Rt.crop_dr_x, y, fill=color, tags='crop_grid')

    x = Rt.crop_tl_x + (Rt.crop_dr_x-Rt.crop_tl_x)*(1/3)
    page.create_line(x, Rt.crop_tl_y, x, Rt.crop_dr_y, fill=color, tags='crop_grid')
    x = Rt.crop_tl_x + (Rt.crop_dr_x-Rt.crop_tl_x)*(2/3)
    page.create_line(x, Rt.crop_tl_y, x, Rt.crop_dr_y, fill=color, tags='crop_grid')



Label('software_title', 3, 3, f'{SOFTWARE_NAME}-v{SOFTWARE_VER}', 'Verdana 10', fg='#333')
core(
    page,
    Rt, FFMPEG, OPEN_DIR_PTH,
    PROXY_BOX_W, PROXY_BOX_H, PROXY_BOX_X, PROXY_BOX_Y,
    redraw_crop_grid
)

def left_mouse_press(e):
    Button.press_listener()
    Slider.press_listener()

    if Rt.do_crop:
        x, y = e.x, e.y
        if (abs(x-Rt.crop_tl_x) < TOLERANCE) and (abs(y-Rt.crop_tl_y) < TOLERANCE):  # resize using TL corner
            Rt.crop_mode = 'TL'
        elif (abs(x-Rt.crop_dr_x) < TOLERANCE) and (abs(y-Rt.crop_dr_y) < TOLERANCE):  # resize using DR corner
            Rt.crop_mode = 'DR'
        elif (Rt.crop_tl_x < x < Rt.crop_dr_x) and (Rt.crop_tl_y < y < Rt.crop_dr_y):  # to move the crop grid
            Rt.crop_mode = 'move'
            Rt.crop_offset_x = x - Rt.crop_tl_x
            Rt.crop_offset_y = y - Rt.crop_tl_y

root.bind('<ButtonPress-1>', left_mouse_press)

def left_mouse_hold(e):
    Slider.hold_listener()

    if Rt.do_crop:
        if Rt.crop_mode is not None:
            x, y = e.x, e.y

            ## minimum size for the crop grid
            min_w = 20
            min_h = 20

            if Rt.crop_mode == 'TL':
                ## these logics ensure the rectangle "crop" can't go beyond the image size and must has min area
                if (x < Rt.crop_dr_x - min_w) and (x >= Rt.crop_proxy_x):
                    Rt.crop_tl_x = x
                if (y < Rt.crop_dr_y - min_h) and (y >= Rt.crop_proxy_y):
                    Rt.crop_tl_y = y
            
            elif Rt.crop_mode == 'DR':
                if (x > Rt.crop_tl_x + min_w) and (x <= (Rt.crop_proxy_x + Rt.crop_proxy_w)):
                    Rt.crop_dr_x = x
                if (y > Rt.crop_tl_y + min_h) and (y <= (Rt.crop_proxy_y + Rt.crop_proxy_h)):
                    Rt.crop_dr_y = y
            
            elif Rt.crop_mode == 'move':
                new_tl_x = x - Rt.crop_offset_x
                new_tl_y = y - Rt.crop_offset_y
                new_dr_x = new_tl_x + (Rt.crop_dr_x - Rt.crop_tl_x)
                new_dr_y = new_tl_y + (Rt.crop_dr_y - Rt.crop_tl_y)
                if (new_tl_x >= Rt.crop_proxy_x) and (new_dr_x <= (Rt.crop_proxy_x + Rt.crop_proxy_w)):
                    Rt.crop_tl_x = new_tl_x
                    Rt.crop_dr_x = new_dr_x
                if (new_tl_y >= Rt.crop_proxy_y) and (new_dr_y <= (Rt.crop_proxy_y + Rt.crop_proxy_h)):
                    Rt.crop_tl_y = new_tl_y
                    Rt.crop_dr_y = new_dr_y

            redraw_crop_grid()
root.bind('<B1-Motion>', left_mouse_hold)

def left_mouse_release(e):
    Button.release_listener()
    Slider.release_listener()

    if Rt.do_crop:
        Rt.crop_mode = None
        Rt.crop_w = round( (Rt.crop_dr_x-Rt.crop_tl_x)*(Rt.crop_real_w/Rt.crop_proxy_w) )
        Rt.crop_h = round( (Rt.crop_dr_y-Rt.crop_tl_y)*(Rt.crop_real_h/Rt.crop_proxy_h) )
        Rt.crop_x = round( (Rt.crop_tl_x-Rt.crop_proxy_x)*(Rt.crop_real_w/Rt.crop_proxy_w) )
        Rt.crop_y = round( (Rt.crop_tl_y-Rt.crop_proxy_y)*(Rt.crop_real_h/Rt.crop_proxy_h) )
root.bind('<ButtonRelease-1>', left_mouse_release)

def background_fast():
    Button.hover_listener()
    Slider.hover_listener()
    root.after(50, background_fast)


def exit(e):
    printer('INFO: Exiting..')
    root.destroy()
root.bind('<Escape>', exit)


def main():
    background_fast()
    root.mainloop()