import time
import imaging
import screen_grab
import Tkinter as tk
import os
import threading
import functools

from multiprocessing import Pipe
import Queue

# if this is run as a program (versus being imported),
# create a root window and an instance of our example,
# then start the event loop

##new version here:
pipe_read, pipe_write = Pipe(duplex=False)
read_queue = Queue.Queue()

def quit_pipe():
    pipe_write.send('quit')

g_exiting = False

def hook_loop(root,pipe_read):
    while True:
        msg = pipe_read.recv()
        if msg == 'quit':
            print "exiting pipe"
            try:
                hm.quit = True
            except:
                pass
            break
        root.event_generate("<<pyHookKeyDown>>", when='tail')

def keypressed(pipe, queue, event):
     print [event.ScanCode, event.Ascii]
     try:
         queue.put((event.ScanCode, chr(event.Ascii)))
     except:
         queue.put((event.ScanCode, int(event.Ascii)))

     pipe.send(1)
     return True

def linux_read(key):
    filey = "/tmp/ztranslate_keygrab_"+key
    try:
        s = open(filey).read()
    except:
        s = ""
    return s


key_to_scan_code = {
 "capt": 41,
 "prev": 2,
 "next": 3
}

key_to_default = {
 "capt": 96,
 "prev": 49,
 "next": 50
}

class LinuxHookEvent:
    def __init__(self, key):
        self.ScanCode = key_to_scan_code[key]
        self.Ascii = key_to_default[key]

class LinuxHookManager(threading.Thread):
    def __init__(self, function, pipe_write, read_queue, **kwargs):
        super(LinuxHookManager, self).__init__(**kwargs)
        self.function = function
        self.pipe_write = pipe_write
        self.read_queue = read_queue
        self.keys = dict()
        self.keys['capt'] = linux_read("capt")
        self.keys['prev'] = linux_read("prev")
        self.keys['next'] = linux_read("next")
        self.quit = False

    def run(self):
        while self.quit == False:
            time.sleep(0.01)
            for key in self.keys:
                val = linux_read(key)
                if val != self.keys[key]:
                    self.keys[key] = val
                    event = LinuxHookEvent(key)
                    self.function(self.pipe_write, self.read_queue, event)
        #print "linux loop quitting."

if os.name == "nt":
    try:
        import pythoncom, pyHook

        hm = pyHook.HookManager()
        hm.HookKeyboard()
        hm.KeyDown = functools.partial(keypressed, pipe_write, read_queue)
    except:
        pass
elif os.name == "posix":
    #run a thread,
    # it reads the key input file(s) every x ms
    # if input exists and is new, then run keypressed with pipe_write and read_queue)
    # --should be good?
    hm = LinuxHookManager(keypressed, pipe_write, read_queue)
    hm.start()
    pass






class QueueExecutor(object):
    def __init__(self):
        self.queue = list()
        self.kill = False

    def add_func(self, function):
        self.queue.append(function)

    def kill_queue(self):
        self.kill = True

    def loop(self):
        while(self.kill == False):
            if self.queue:
                try:
                    self.queue[0]()
                except:
                    import traceback
                    traceback.print_exc()
                self.queue = self.queue[1:]
            else:
                time.sleep(0.1)
        print "queue executor killed"

queue_executor = QueueExecutor()


def grab_input_stop():
    try:
        quit_pipe()
    except:
        pass

    try:
        queue_exectuor.kill_queue()
    except:
        pass

    try:
        hm.quit = True
    except:
        pass

