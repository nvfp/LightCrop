import os


SOFTWARE_DIR_PTH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOFTWARE_NAME = os.path.basename(SOFTWARE_DIR_PTH)
SOFTWARE_VER = 'dev-0.2.0'

TMP_DIR_PTH = os.path.join(SOFTWARE_DIR_PTH, 'tmp')
SETTINGS_FILE_PTH = os.path.join(SOFTWARE_DIR_PTH, 'main', 'settings.txt')

PROXY_FILE_PTH = os.path.join(TMP_DIR_PTH, f'proxy-{SOFTWARE_NAME}-v{SOFTWARE_VER}.jpg')

ALLOWED_EXTENSIONS = (
    '.jpg',
    '.jpeg',
    '.png',
    '.bmp',
    '.tiff',
    '.webp',
    '.svg',
    '.ico',
    '.heic',
)