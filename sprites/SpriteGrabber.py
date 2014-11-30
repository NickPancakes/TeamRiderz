from __future__ import print_function
from PIL import ImageGrab, Image
import logging
import os
from collections import namedtuple, OrderedDict
import win32gui
from time import sleep

def dhash(image, hash_size=64):
    # Grayscale and shrink the image.
    image = image.convert('L').resize(
        (hash_size + 1, hash_size),
        Image.ANTIALIAS,
    )

    differences = []
    for row in xrange(hash_size):
        for col in xrange(hash_size):
            pixel_left = image.getpixel((col, row))
            pixel_right = image.getpixel((col + 1, row))

            differences.append(pixel_left > pixel_right)

    hash_num = 0
    for value in differences:
        hash_num *= 2
        if value:
            hash_num += 1

    return hash_num

def dedupe_images(capture_path, dedupe_path):
    print("First Pass Dedupe")
    img_paths = []
    for f in os.listdir(capture_path):
        if f.endswith('.png'):
            img_paths.append(capture_path + '\\' + f)
    hashes = {}
    for img_path in img_paths:
        try:
            image = Image.open(img_path)
            img_hash = dhash(image)
            if img_hash not in hashes:
                hashes[img_hash] = []
            hashes[img_hash].append(img_path)
        except IOError as e:
            logging.warning(e.message)
            continue
    print("Second Pass Dedupe")
    img_paths = []
    for root, dirs, files in os.walk(dedupe_path):
        for name in files:
            if name.endswith('.png'):
                img_paths.append(os.path.join(root, name))
    for img_path in img_paths:
        try:
            image = Image.open(img_path)
            img_hash = dhash(image)
            if img_hash in hashes:
                hashes.pop(img_hash, None)
        except IOError as e:
            logging.warning(e.message)
            continue
    print("Dupes Removed, Saving Unique Frames")
    i = 0
    for img in hashes:
        src_path = hashes[img][0]
        dest_path = capture_path + "\\frame" + str(i).zfill(4) + ".png"
        os.rename(src_path, dest_path)
        i = i + 1

    print("Removing Temporary Frames")
    for f in os.listdir(capture_path):
        if 'sgtemp' in f:
            os.remove(capture_path + '\\' + f)

def capture_frames(capture_directory):
    toplist, winlist = [], []
    def enum_cb(hwnd, results):
        winlist.append((hwnd, win32gui.GetWindowText(hwnd)))
    win32gui.EnumWindows(enum_cb, toplist)

    oam_window = [(hwnd, title) for hwnd, title in winlist if 'OAM' in title]
    oam_window = oam_window[0]
    hwnd = oam_window[0]
    win32gui.SetForegroundWindow(hwnd)
    bbox = win32gui.GetWindowRect(hwnd)
    spritebox = (bbox[0]+137, bbox[1]+40, bbox[0]+201, bbox[1]+104)
    sleep(0.05)
    frames = []
    i = 0
    while i < 5000:
        if win32gui.GetForegroundWindow() == hwnd:
            img = ImageGrab.grab(spritebox)
            img.save(capture_directory + "\\sgtemp" + str(i).zfill(4) + ".png")
        else:
            break
        i = i + 1

def stripbg(capture_path):
    img_paths = []
    for f in os.listdir(capture_path):
        if f.endswith('.png'):
            img_paths.append(capture_path + '\\' + f)
    for img_path in img_paths:
        try:
            img = Image.open(img_path)
            img = img.convert("RGBA")
            pixdata = img.load()
            for y in xrange(img.size[1]):
                for x in xrange(img.size[0]):
                    if pixdata[x, y] == (248, 0, 248, 255):
                        pixdata[x, y] = (0, 0, 0, 0)
            img.save(img_path)
        except IOError as e:
            logging.warning(e.message)
            continue

if __name__ == '__main__':
    capture_directory = os.getcwd() + "\\capture"
    if not os.path.exists(capture_directory):
        os.makedirs(capture_directory)
    print("Capturing 5000 Frames, unfocus the window to stop early.")
    capture_frames(capture_directory)
    print("Frames Captured")
    print("Stripping Backgrounds")
    stripbg(capture_directory)
    print("Deduping")
    dedupe_directory = os.getcwd() + "\\complete"
    if not os.path.exists(dedupe_directory):
        os.makedirs(dedupe_directory)
    dedupe_images(capture_directory, dedupe_directory)
    print("Complete")
