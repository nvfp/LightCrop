import datetime
import math
import os
import subprocess as sp
import tkinter as tk
from PIL import ImageTk, Image
from tkinter import filedialog

from carbon.gui.button.v2 import Button
from carbon.gui.slider import Slider
from carbon.utils import printer

from main.constants import ALLOWED_EXTENSIONS, PROXY_FILE_PTH


def render(
    ffmpeg,
    input_pth,
    output_pth,

    rotate,

    do_crop,
    crop_w,
    crop_h,
    crop_x,
    crop_y,

    do_contrast,
    do_brightness,
    do_saturation,
    do_gamma,
    do_gamma_r,
    do_gamma_g,
    do_gamma_b,
    do_vignette,
    do_colortemperature,
    do_avgblur,

    contrast,
    brightness,
    saturation,
    gamma,
    gamma_r,
    gamma_g,
    gamma_b,
    vignette,
    colortemperature,
    avgblur,

    q_v
):

    filters = []

    if rotate == 1:  # 90 CCW
        filters.append('transpose=2')
    elif rotate == 2:  # 180 deg
        filters.append('transpose=1,transpose=1')
    elif rotate == 3:  # 90 CW
        filters.append('transpose=1')

    if do_crop:
        filters.append(f'crop={crop_w}:{crop_h}:{crop_x}:{crop_y}')

    if do_contrast or do_brightness or do_saturation or do_gamma or do_gamma_r or do_gamma_g or do_gamma_b:
        eqs = []
        if do_contrast:
            eqs.append(f'contrast={contrast}')
        if do_brightness:
            eqs.append(f'brightness={brightness}')
        if do_saturation:
            eqs.append(f'saturation={saturation}')
        if do_gamma:
            eqs.append(f'gamma={gamma}')
        if do_gamma_r:
            eqs.append(f'gamma_r={gamma_r}')
        if do_gamma_g:
            eqs.append(f'gamma_g={gamma_g}')
        if do_gamma_b:
            eqs.append(f'gamma_b={gamma_b}')
        filters.append('eq=' + ':'.join(eqs))

    if do_vignette:
        if vignette >= 0:
            filters.append(f'vignette=a={math.pi*vignette/180}:mode=backward')
        else:
            filters.append(f'vignette=a={-math.pi*vignette/180}:mode=forward')
    
    if do_colortemperature:
        filters.append(f'colortemperature=temperature={colortemperature}')
    
    if do_avgblur:
        filters.append(f'avgblur={avgblur}')


    if filters == []:
        filters_cmd = []
    else:
        filters_cmd = ['-vf', ','.join(filters),]

    cmd = [
        ffmpeg, '-v', 'error',
        '-i', input_pth,
        *filters_cmd,
        '-q:v', str(q_v),
        '-y',  # overwrite
        output_pth
    ]
    printer(f'INFO: Rendering {repr(output_pth)}...')
    sp.call(cmd)


def reshow_proxy_photo(SETTINGS_FFMPEG, page: tk.Canvas, Rt, PROXY_BOX_W, PROXY_BOX_H, PROXY_BOX_X, PROXY_BOX_Y):

    render(
        SETTINGS_FFMPEG,
        Rt.input_pth,
        PROXY_FILE_PTH,

        Rt.rotate,

        False,
        Rt.crop_w,
        Rt.crop_h,
        Rt.crop_x,
        Rt.crop_y,

        Rt.do_contrast,
        Rt.do_brightness,
        Rt.do_saturation,
        Rt.do_gamma,
        Rt.do_gamma_r,
        Rt.do_gamma_g,
        Rt.do_gamma_b,
        Rt.do_vignette,
        Rt.do_colortemperature,
        Rt.do_avgblur,

        Rt.contrast,
        Rt.brightness,
        Rt.saturation,
        Rt.gamma,
        Rt.gamma_r,
        Rt.gamma_g,
        Rt.gamma_b,
        Rt.vignette,
        Rt.colortemperature,
        Rt.avgblur,

        Rt.q_v
    )
    
    img = Image.open(PROXY_FILE_PTH)
    w = img.width
    h = img.height
    r = w/h

    if r > (PROXY_BOX_W/PROXY_BOX_H):  # landscape
        W = round(PROXY_BOX_W)
        H = round(W/r)
        X = PROXY_BOX_X
        Y = PROXY_BOX_Y + (PROXY_BOX_H - H)/2
    else:  # portrait
        H = round(PROXY_BOX_H)
        W = round(H*r)
        X = PROXY_BOX_X + (PROXY_BOX_W - W)/2
        Y = PROXY_BOX_Y

    ## rescale
    img = img.resize((W, H))
    Rt.proxy_photo = ImageTk.PhotoImage(img)  # to prevent the image from being collected by the Python garbage collector

    page.delete('proxy_photo')
    page.create_image(X, Y, image=Rt.proxy_photo, anchor='nw', tags='proxy_photo')
    page.create_rectangle(X-1, Y-1, X+W, Y+H, outline='#555', tags='proxy_photo')  # border

    ## cropping needs
    Rt.crop_tl_x = X
    Rt.crop_tl_y = Y
    Rt.crop_dr_x = X + W
    Rt.crop_dr_y = Y + H
    Rt.crop_proxy_w = W
    Rt.crop_proxy_h = H
    Rt.crop_proxy_x = X
    Rt.crop_proxy_y = Y
    Rt.crop_real_w = w
    Rt.crop_real_h = h


def core(
    page: tk.Canvas,
    Rt, SETTINGS_FFMPEG, SETTINGS_OPEN_DIR_PTH, SETTINGS_SAVE_DIR_PTH,
    PROXY_BOX_W, PROXY_BOX_H, PROXY_BOX_X, PROXY_BOX_Y,
    redraw_crop_grid
):

    def rotate_left():
        Rt.rotate = (Rt.rotate + 1) % 4
        reshow_proxy_photo(SETTINGS_FFMPEG, page, Rt, PROXY_BOX_W, PROXY_BOX_H, PROXY_BOX_X, PROXY_BOX_Y)
    
    def rotate_right():
        Rt.rotate = (Rt.rotate - 1) % 4
        reshow_proxy_photo(SETTINGS_FFMPEG, page, Rt, PROXY_BOX_W, PROXY_BOX_H, PROXY_BOX_X, PROXY_BOX_Y)

    Button(
        x=50, y=55,
        fn=rotate_left, label='Rotate (Left)', id='rotate_ccw', width=85, locked=True, tags='tools'
    )
    Button(
        x=Button.get_bounding_box_by_id('rotate_ccw')[2]+15,
        y=Button.get_bounding_box_by_id('rotate_ccw')[1],
        fn=rotate_right, label='Rotate (Right)', id='rotate_cw', width=85, locked=True, tags='tools'
    )


    def crop_toggle():

        Rt.do_crop = not Rt.do_crop

        if Rt.do_crop:
            Button.set_label_by_id('crop', 'Crop (ON)')
            # Button.set_lock_by_tag('crop_ratio', False)
            redraw_crop_grid()
        else:
            Button.set_label_by_id('crop', 'Crop (OFF)')
            # Button.set_lock_by_tag('crop_ratio', True)
            page.delete('crop_grid')

    Button(
        x=50,
        y=Button.get_bounding_box_by_id('rotate_cw')[3]+25,
        fn=crop_toggle, label='Crop (OFF)', id='crop', width=70, locked=True, tags='tools'
    )
    Button(
        x=Button.get_bounding_box_by_id('crop')[2]+10,
        y=Button.get_bounding_box_by_id('crop')[1],
        fn=None, label='1:1', id='crop1:1', width=30, locked=True, tags='crop_ratio'
    )
    Button(
        x=Button.get_bounding_box_by_id('crop1:1')[2]+5,
        y=Button.get_bounding_box_by_id('crop')[1],
        fn=None, label='16:9', id='crop16:9', width=30, locked=True, tags='crop_ratio'
    )
    Button(
        x=Button.get_bounding_box_by_id('crop16:9')[2]+5,
        y=Button.get_bounding_box_by_id('crop')[1],
        fn=None, label='9:16', id='crop9:16', width=30, locked=True, tags='crop_ratio'
    )
    Button(
        x=Button.get_bounding_box_by_id('crop9:16')[2]+5,
        y=Button.get_bounding_box_by_id('crop')[1],
        fn=None, label='2:1', id='crop2:1', width=30, locked=True, tags='crop_ratio'
    )
    Button(
        x=Button.get_bounding_box_by_id('crop2:1')[2]+5,
        y=Button.get_bounding_box_by_id('crop')[1],
        fn=None, label='1:2', id='crop1:2', width=30, locked=True, tags='crop_ratio'
    )


    X = 20
    Y = Button.get_bounding_box_by_id('crop')[3] + 65
    GAP = 45
    GAP2 = 120  # gap between gate and slider

    def update_filter_gate(filter_name):
        
        filter_gate = 'do_' + filter_name
        setattr(Rt, filter_gate, not getattr(Rt, filter_gate))  # flipping the value
        
        if getattr(Rt, filter_gate):
            Button.set_label_by_id(filter_gate, 'Used')
            Slider.set_lock_by_id(filter_name, False)
        else:
            Button.set_label_by_id(filter_gate, 'OFF')
            Slider.set_lock_by_id(filter_name, True)
        
        reshow_proxy_photo(SETTINGS_FFMPEG, page, Rt, PROXY_BOX_W, PROXY_BOX_H, PROXY_BOX_X, PROXY_BOX_Y)

    def update_filter_value(filter_name):
        new_value = Slider.get_value_by_id(filter_name)
        setattr(Rt, filter_name, new_value)

        reshow_proxy_photo(SETTINGS_FFMPEG, page, Rt, PROXY_BOX_W, PROXY_BOX_H, PROXY_BOX_X, PROXY_BOX_Y)

    BTN_W = 40  # gate buttons width
    
    Button(x=X, y=Y+GAP*0, fn=lambda: update_filter_gate('contrast'), label='OFF', id='do_contrast', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='contrast',
        min=-5, max=5, step=0.01, init=Rt.contrast,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*0,
        fn=lambda: update_filter_value('contrast'),
        label='Contrast',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True
    )
    Button(x=X, y=Y+GAP*1, fn=lambda: update_filter_gate('brightness'), label='OFF', id='do_brightness', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='brightness',
        min=-1, max=1, step=0.005, init=Rt.brightness,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*1,
        fn=lambda: update_filter_value('brightness'),
        label='Brightness',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True
    )
    Button(x=X, y=Y+GAP*2, fn=lambda: update_filter_gate('saturation'), label='OFF', id='do_saturation', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='saturation',
        min=0, max=3, step=0.01, init=Rt.saturation,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*2,
        fn=lambda: update_filter_value('saturation'),
        label='Saturation',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True
    )
    Button(x=X, y=Y+GAP*3, fn=lambda: update_filter_gate('gamma'), label='OFF', id='do_gamma', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='gamma',
        min=0.1, max=10, step=0.005, init=Rt.gamma,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*3,
        fn=lambda: update_filter_value('gamma'),
        label='Gamma',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True
    )
    Button(x=X, y=Y+GAP*4, fn=lambda: update_filter_gate('gamma_r'), label='OFF', id='do_gamma_r', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='gamma_r',
        min=0.1, max=10, step=0.005, init=Rt.gamma_r,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*4,
        fn=lambda: update_filter_value('gamma_r'),
        label='Gamma-R',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True
    )
    Button(x=X, y=Y+GAP*5, fn=lambda: update_filter_gate('gamma_g'), label='OFF', id='do_gamma_g', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='gamma_g',
        min=0.1, max=10, step=0.005, init=Rt.gamma_g,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*5,
        fn=lambda: update_filter_value('gamma_g'),
        label='Gamma-G',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True
    )
    Button(x=X, y=Y+GAP*6, fn=lambda: update_filter_gate('gamma_b'), label='OFF', id='do_gamma_b', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='gamma_b',
        min=0.1, max=10, step=0.005, init=Rt.gamma_b,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*6,
        fn=lambda: update_filter_value('gamma_b'),
        label='Gamma-B',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True
    )
    Button(x=X, y=Y+GAP*7, fn=lambda: update_filter_gate('vignette'), label='OFF', id='do_vignette', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='vignette',
        min=-90, max=90, step=1, init=Rt.vignette,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*7,
        fn=lambda: update_filter_value('vignette'),
        label='Vignette',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True
    )
    Button(x=X, y=Y+GAP*8, fn=lambda: update_filter_gate('colortemperature'), label='OFF', id='do_colortemperature', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='colortemperature',
        min=1000,
        # max=40000,  # is the maximum that ffmpeg allows
        max=20000,  # should be enough
        step=50, init=Rt.colortemperature,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*8,
        fn=lambda: update_filter_value('colortemperature'),
        label='White Balance',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, suffix=' K', locked=True
    )
    Button(x=X, y=Y+GAP*9, fn=lambda: update_filter_gate('avgblur'), label='OFF', id='do_avgblur', width=BTN_W, locked=True, anchor='w', tags='tools')
    Slider(
        id='avgblur',
        min=1,
        # max=1024,  # is the maximum that ffmpeg allows
        max=25,  # should be enough
        step=1, init=Rt.avgblur,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*9,
        fn=lambda: update_filter_value('avgblur'),
        label='Blur',  # average blur
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True
    )
    Slider(
        id='q_v',
        min=1, max=31, step=1, init=Rt.q_v,
        x=Button.get_bounding_box_by_id('do_contrast')[2]+GAP2, y=Y+GAP*10,
        fn=lambda: update_filter_value('q_v'),
        label='Quality (1: highest, 31: lowest)',
        label_y_shift=-20, yield_x_shift=40, yield_box_color='#000', yield_box_height=20, yield_box_width=55, show_yield_box=True, locked=True, tags='tools'
    )


    def open_new_image():

        pth = filedialog.askopenfilename(initialdir=SETTINGS_OPEN_DIR_PTH)
        if (not os.path.isfile(pth)) or (not pth.lower().endswith(ALLOWED_EXTENSIONS)):
            printer(f'WARNING: Invalid image: {repr(pth)}')
            return

        Rt.input_pth = pth

        Button.set_lock_by_tag('tools', False)
        Slider.set_lock_by_tag('tools', False)
        
        reshow_proxy_photo(SETTINGS_FFMPEG, page, Rt, PROXY_BOX_W, PROXY_BOX_H, PROXY_BOX_X, PROXY_BOX_Y)

    Button(
        x=50, y=Y+GAP*11+25,
        fn=open_new_image, label='Open', id='open'
    )

    def save_the_output():

        name, ext = os.path.splitext(os.path.basename(Rt.input_pth))
        date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        output_pth = filedialog.asksaveasfilename(
            initialfile=f'{name}_{date}{ext}',
            initialdir=SETTINGS_SAVE_DIR_PTH,
            filetypes=(
                ('JPEG', '*.jpg'),
                ('JPEG', '*.jpeg'),
                ('PNG', '*.png'),
                ('Bitmap', '*.bmp'),
                ('TIFF', '*.tiff'),
                ('WebP', '*.webp'),
                ('SVG', '*.svg'),
                ('ICO', '*.ico'),
                ('HEIC', '*.heic'),
            )
        )

        if os.path.exists(output_pth):
            printer(f'WARNING: Unable to render the output; the file already exists: {repr(output_pth)}')
            return
        
        render(
            SETTINGS_FFMPEG,
            Rt.input_pth,
            output_pth,

            Rt.rotate,

            Rt.do_crop,
            Rt.crop_w,
            Rt.crop_h,
            Rt.crop_x,
            Rt.crop_y,

            Rt.do_contrast,
            Rt.do_brightness,
            Rt.do_saturation,
            Rt.do_gamma,
            Rt.do_gamma_r,
            Rt.do_gamma_g,
            Rt.do_gamma_b,
            Rt.do_vignette,
            Rt.do_colortemperature,
            Rt.do_avgblur,

            Rt.contrast,
            Rt.brightness,
            Rt.saturation,
            Rt.gamma,
            Rt.gamma_r,
            Rt.gamma_g,
            Rt.gamma_b,
            Rt.vignette,
            Rt.colortemperature,
            Rt.avgblur,

            Rt.q_v
        )

        printer(f'INFO: Output is saved: {repr(output_pth)}')

    Button(
        x=Button.get_bounding_box_by_id('open')[2]+15,
        y=Button.get_bounding_box_by_id('open')[1],
        fn=save_the_output, anchor='nw', label='Save', locked=True, tags='tools'
    )