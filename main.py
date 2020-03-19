from threading import Thread
from web_server import WebServer

from PIL import ImageGrab, Image
import cv2
import numpy as np
import time
import copy
import os
import pyautogui as pg
import threading
import win32ui
import win32gui
import pickle

class Bot():
    # ------------- Settings -------------
    margin_c_b = 2
    bobber_threshold = 0.85

    bbox_bobber = None
    bobber_template = None

    item_list = {
                "Total": 0,
                "Failed": 0,
                "Successful": 0,
                }

    screenshot_im = None

    hand_cursor_im = None
    fishing_cursor_im = None

    time_start = None

    running = False
    is_fishing = False
    reset = None

    limit = {"item": None,
             "count": None,
             "time": None
             }

    # ------------- Config Part -------------
    # Is Bot ready to start
    @property
    def is_ready(self):
        if self.bbox_bobber is None or \
        self.bobber_template is None or \
        self.hand_cursor_im is None or \
        self.fishing_cursor_im is None:
            return False
        return True

    # Returns properties
    @property
    def config_properties(self):
        return {"margin_c_b": self.margin_c_b,
                "bobber_threshold": self.bobber_threshold,}

    # Changes bot config
    def change_config(self, request):
        margin_c_b = request["config[margin_c_b]"]
        bobber_threshold = request["config[bobber_threshold]"]
        self.margin_c_b = int(margin_c_b) if margin_c_b != "" else self.margin_c_b
        self.bobber_threshold = float(bobber_threshold) if bobber_threshold != "" else self.margin_c_b

    def debug(self):
        #print(self.item_list)
        name = self.get_current_item()
        print(name)

    # Saves config
    def save(self):
        if self.is_ready:
            data = [self.bbox_bobber, self.bobber_template,
                    self.bobber_threshold, self.hand_cursor_im,
                    self.fishing_cursor_im, self.margin_c_b]
        f = open("save.pickle", "wb")
        pickle.dump(data, f)
        f.close()

    # Loads saved config
    def load(self):
        data = []
        f = open("save.pickle", "rb")
        data = pickle.load(f)
        f.close()
        self.bbox_bobber, self.bobber_template, \
        self.bobber_threshold, self.hand_cursor_im, \
        self.fishing_cursor_im, self.margin_c_b = data

    # Sets limit
    def set_limit(self, item, count, time):
        self.limit["item"] = item if item != "" else None
        self.limit["count"] = int(count) if count != "" else None
        self.limit["time"] = int(float(time) * 60 * 60) if time != "" else None

    # ------------- Statistics Part -------------
    # Returns bot running time (minutes)
    def running_minutes(self):
        if self.time_start is None:
            return 0
        minutes = (time.time() - self.time_start) / 60
        return minutes

    # ------------- Vision Part -------------
    # Returns position and match
    def match_template(self, im, template):
        res = cv2.matchTemplate(im, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return max_loc, max_val

    # Returns absolute position of bobber
    def detect_bobber(self, last_usage=False):
        im = self.take_screenshot(last_usage)
        cropped = self.crop_image_by_bbox(im, self.bbox_bobber)
        # Template matching
        loc, val = self.match_template(cropped, self.bobber_template)
        if val < self.bobber_threshold:
            return False
        loc = (loc[0] + self.bbox_bobber[0][0],
            loc[1] + self.bbox_bobber[0][1])
        return loc

    # Selects ROI for bobber detection
    def bobber_roi(self):
        self.bbox_bobber = self.select_bbox(self.take_screenshot(True), 1)

    # Selects n bboxes on image
    def select_bbox(self, im, num):
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        bboxes = []
        im_copy = copy.deepcopy(im)
        im = copy.deepcopy(im)
        # Callback function for OpenCV imshow window
        def select_callback(event, x, y, *args):
            if len(bboxes) >= num * 2:
                return
            if event == cv2.EVENT_LBUTTONDOWN:
                bboxes.append((x, y))
            elif event == cv2.EVENT_LBUTTONUP:
                bboxes.append((x, y))
                cv2.rectangle(im, bboxes[-2], bboxes[-1], colors[len(bboxes) % len(colors)], 3)
                cv2.imshow("im", im)
        while True:
            cv2.imshow("im", im)
            cv2.setMouseCallback("im", select_callback)
            key = cv2.waitKey()
            if chr(key) == "r":
                bboxes = []
                im = copy.deepcopy(im_copy)
                cv2.imshow("im", im)
            elif chr(key) == "s":
                if len(bboxes) == num * 2:
                    break
        cv2.destroyAllWindows()
        return bboxes

    # Takes or returns screenshot
    def take_screenshot(self, last_usage=False):
        if self.screenshot_im is not None and not last_usage:
            return self.screenshot_im
        im = ImageGrab.grab()
        im = np.array(im)
        im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
        if not last_usage:
            self.screenshot_im = im
        elif last_usage:
            self.screenshot_im = None
        return im

    # Returns cropped image by bbox
    def crop_image_by_bbox(self, im, bbox):
        x1 = bbox[0][0]
        y1 = bbox[0][1]
        x2 = bbox[1][0]
        y2 = bbox[1][1]
        cropped = im[y1:y2, x1:x2]
        return cropped

    # Creates bobber template for template matching
    def select_bobber_template(self):
        if self.bbox_bobber is None:
            return False
        im = self.take_screenshot(True)
        cropped = self.crop_image_by_bbox(im, self.bbox_bobber)

        bbox = self.select_bbox(cropped, 1)
        template = self.crop_image_by_bbox(cropped, bbox)

        self.bobber_template = template

    # Returns current cursor bitmap
    def get_current_cursor(self):
        try:
            # Get Display Context
            hwin = win32gui.GetDesktopWindow()
            hwindc = win32gui.GetWindowDC(hwin)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()
            # Create Bitmap
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, 32, 32)
            # Draw icon on Bitmap
            memdc.SelectObject(bmp)
            c = win32gui.GetCursorInfo()[1]
            memdc.DrawIcon( (0,0), c )
            # Convert Bitmap to numpy array(Image)
            signedIntsArray = bmp.GetBitmapBits(True)
            im = Image.frombuffer("RGB", (32, 32), signedIntsArray)
            #img = np.fromstring(signedIntsArray, dtype='uint8')
            #img.shape = (32,32,4)
            im = np.array(im)
            im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
            # Release handlers
            srcdc.DeleteDC()
            memdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)
            win32gui.DeleteObject(bmp.GetHandle())
            return im
        except Exception as e:
            #print("Win32Api Error:", e)
            #exc_type, exc_obj, exc_tb = os.sys.exc_info()
            #print(exc_type, exc_tb.tb_lineno)
            return self.hand_cursor_im

    # Creates hand cursor bitmap
    def create_hand_cursor(self):
        im = self.get_current_cursor()
        self.hand_cursor_im = im

    # Creates fishing cursor bitmap
    def create_fishing_cursor(self):
        im = self.get_current_cursor()
        self.fishing_cursor_im = im

    # ------------- I/O Part -------------

    # Shutdowns PC
    def shutdown(self):
        os.system("shutdown /s /f /t 0")

    # Returns zipped 3000 points for mouse movement
    def human_movement(self, pt1, pt2, num):
        dx = abs(pt1[0] - pt2[0])
        dy = abs(pt1[1] - pt2[1])

        x = np.linspace(pt1[0], pt2[0], num).astype(np.float32)
        y = np.linspace(pt1[1], pt2[1], num).astype(np.float32)

        r = np.random.uniform(-100, 100, num-1)
        if dx > dy:
            y[:-1] += r
            pol = np.polyfit(x, y, 4)
            y = np.polyval(pol, x)
        else:
            x[:-1] += r
            pol = np.polyfit(y, x, 4)
            x = np.polyval(pol, y)
        return zip(x, y)

    # Starts BOT
    def start_init(self):
        assert self.is_ready is True
        self.running = True
        self.is_fishing = False
        self.time_start = time.time()
        return True

    # Stops BOT
    def stop_init(self):
        self.running = False
        self.is_fishing = False
        if self.reset is not None:
            self.reset.cancel()
            self.reset = None

    # Casts fishing
    def cast_fishing(self):
        mloc = pg.position()
        movement = self.human_movement(mloc, (159, 926), 300)
        for x, y in movement:
            pg.moveTo(x, y, 0, pause=0.1e-14 + np.random.random() * 0.9e-13)
        pg.press("enter")
        pg.typewrite(list("/cast Fishing"), 0.02 + np.random.random() * 0.06)
        pg.press("enter")
        time.sleep(0.8)

    # Resets fishing
    def detach_fishing(self):
        if self.reset is not None:
            self.reset.cancel()
            self.reset = None
        self.is_fishing = False

    # Moves the cursor N pixels below the no label spot
    def move_to_no_label_spot(self, speed, last_usage=False):
        time.sleep(0.05)
        if (self.get_current_cursor() == self.hand_cursor_im).all():
            self.detach_fishing()
            time.sleep(1.2)
            return
        while (self.get_current_cursor() == self.fishing_cursor_im).all() and self.is_fishing:
            pg.moveRel(round(np.random.random() * 2) - 1, speed, duration=0.1e-9, pause=0.8e-2, _pause=True)
        if self.margin_c_b != 0:
            pg.moveRel(None, self.margin_c_b, duration=0.1e-9)
        time.sleep(0.5)

    # Alt-TAB
    def alt_tab(self):
        pg.keyDown("alt")
        pg.press("tab")
        pg.keyUp("alt")

    # Hits Enter key
    def hit_enter(self):
        pg.press("enter")

    # Returns screenshot with bobber bbox and cursor circle
    def stream_live(self, last_usage=False):
        if self.is_ready:
            im = self.take_screenshot()
            loc = self.detect_bobber(last_usage)
            if loc is not False:
                im = cv2.rectangle(im, loc, (loc[0] + self.bobber_template.shape[1], loc[1] + self.bobber_template.shape[0]), (0, 0, 255), 3)
        else:
            im = self.take_screenshot(last_usage)
        mloc = pg.position()
        im = cv2.circle(im, mloc, 5, (0, 0, 255), 5)
        return im

    # Checks limits set by user and shuts down computer when over limit
    def check_limits(self):
        # Item count limit
        if self.limit["item"] is not None and self.limit["count"] is not None:
            if(self.item_list[self.limit["item"]]) >= self.limit["count"]:
                #pg.keyDown("alt")
                #pg.press("tab")
                #pg.keyUp("alt")
                #time.sleep(1)
                self.running = False
                os.system("shutdown /s /f /t 0")
                return True

        elif self.limit["time"] is not None: # Time limit
            if time.time() >= self.time_start + self.limit["time"]:
                #pg.keyDown("alt")
                #pg.press("tab")
                #pg.keyUp("alt")
                #time.sleep(1)
                self.running = False
                os.system("shutdown /s /f /t 0")
                return True
        return False

    def fishing_failed(self):
        self.item_list["Total"] += 1
        self.item_list["Failed"] += 1
        self.detach_fishing()

def main():
    bot = Bot()
    webbserver = WebServer(bot)
    webbserver.run()

    time.sleep(3)
    print("BOT started")

    while True:
        # If not running do nothing
        if not bot.running:
            continue

        # Check limits set by user
        ret = bot.check_limits()
        if ret:
            continue

        # If bot is not fishing cast fishing and start restart timer
        if not bot.is_fishing:
            if bot.reset is not None:
                bot.reset.cancel()
            bot.reset = threading.Timer(25, bot.fishing_failed)
            bot.reset.start()
            bot.cast_fishing()
            time.sleep(0.25)
            bot.is_fishing = True

        # Take screenshot and detect bobber location
        try:
            im = bot.take_screenshot()
            loc = bot.detect_bobber(True)
        except Exception as e:
            print("Screen Capture Error", e)


        # If bobber was detected
        if loc is not False:
            # Get mouse position + bobber centroid
            try:
                mloc = pg.position()
                loc = (loc[0] + int(bot.bobber_template.shape[1] / 2),
                        loc[1] + int(bot.bobber_template.shape[0] / 2))
                # Generate human-like movement and move mouse along the path
                movement = bot.human_movement(mloc, loc, 300)
                for x, y in movement:
                    pg.moveTo(x, y, 0, pause=0.1e-14 + np.random.random() * 0.9e-13)
                # When mouse reached the bobber move the cursor under bobber
                bot.move_to_no_label_spot(1, True)
            except Exception as e:
                print("Mouse Movement Error", e)

            # Waiting for fish
            while bot.is_fishing:
                # Fish?
                try:
                    if (bot.get_current_cursor() == bot.fishing_cursor_im).all():
                        # Detach reset timer and variables needed for fishing
                        bot.detach_fishing()
                        # Move cursor to bobber's position and click
                        time.sleep(np.random.random() * 0.8 + 0.5)
                        pg.moveRel(None, int(bot.bobber_template.shape[0] / 2) * -0.9, duration=0.1e-1 + np.random.random() * 0.5)
                        pg.click()
                        # Log item
                        bot.item_list["Total"] += 1
                        bot.item_list["Successful"] += 1
                        time.sleep(1.8)
                except Exception as e:
                    print("Fish Detection Error", e)


main()
