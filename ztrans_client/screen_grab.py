import os
from PIL import Image
import time
import datetime

if os.name == 'nt':
    try:
        import win32gui
        import win32ui
        from ctypes import windll
    except:
        pass
elif os.name == "posix":
    pass


mock_int = 0
mock_grab = [
["default_images/default.png",'de'],
["default_images/japanese2.jpg",'ja'],
["default_images/japanese3.jpg",'ja'],
["default_images/japanese4.jpg",'ja'],
["default_images/japanese5.jpg",'ja'],
["default_images/japanese6.jpg",'ja'],
["default_images/japanese7.jpg",'ja'],
["default_images/japanese8.jpg",'ja'],
["default_images/muscle_psp.jpg",'ja'],
["default_images/napple_tale.jpg",'ja']
]


class ImageGrabber:
    @classmethod
    def grab_image(cls,*args, **kwargs):
        if os.name == "nt":
            grabbed_image = cls.grab_image_windows(*args,  **kwargs)
        else:
            grabbed_image = cls.grab_image_linux(*args,  **kwargs)
        return grabbed_image

    @classmethod
    def grab_image_linux(cls):
        t_time = time.time()
        os.system("import -window \"$(xdotool getwindowfocus )\" grab.bmp")
        image = Image.open("grab.bmp")
        print time.time()-t_time
        return image

    @classmethod
    def grab_image_mocked(cls):
        #this is just a mocked grabber.
        global mock_int
        mock_int+=1
        if mock_int >= len(mock_grab):
            mock_int = 0
        image_filename = mock_grab[mock_int][0]
        return image_filename

    @classmethod
    def grab_image_windows(cls):
        #print "grabbing images in windows..."
        #hwnd = win32gui.FindWindow(None, 'Calculator')
        hwnd = win32gui.GetForegroundWindow()
        # Change the line below depending on whether you want the whole window
        # or just the client area. 
        try:
            left, top, right, bot = win32gui.GetClientRect(hwnd)
            #left, top, right, bot = win32gui.GetWindowRect(hwnd)
            w = right - left
            h = bot - top

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

            saveDC.SelectObject(saveBitMap)

            # Change the line below depending on whether you want the whole window
            # or just the client area. 
            result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 1)
            #result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)

            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)

            im = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1)

            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

            if result == 1:
                #PrintWindow Succeeded
                try:
                    im.save("grab.bmp")
                except:
                    pass
                return im
            return im
        except:
            return None



