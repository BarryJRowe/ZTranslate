from Tkinter import *
import ttk
import tkFileDialog
import tkMessageBox
 
from PIL import ImageTk, Image
import os
import os.path
import time
import io
import base64
import functools
from threading import Thread
 
import config
import imaging
import screen_translate
import screen_grab
import server_client
import package_loader
import package_ocr
import api_service
import key_input

from ztrans_common import text_draw

def donothing():
   filewin = Toplevel(root)
   button = Button(filewin, text="Do nothing button")
   button.pack()


DEFAULT_IMAGE_PATH = "default.png"

FONT = "RobotoCondensed-Bold.ttf"   

"""
---------------------------------------------------------
                        ZTranslate
File Options Help
[ --News from the server here.....!!!------------------- ]
Translation Mode: [Free/Paid]        Usage: [1235/10,000]
Source language: [DE/Auto]        Target Language: [En/Fr]
Screenshot Key:  ( ? )            Save screenshots: [X]
Loaded Package: [Package Name](load)(clear)
[<<<] [key]                                      [key] [>>>]
_________________________________________________________
|                                                       |
|                                                       |
|                                                       |
|                                                       |
_________________________________________________________

Weburl: {url link}
Words Statistics
Druck (de): Pressure, somethingelse (tech.), rank: 3451
...
...
...
---------------------------------------------------------
"""

APP_TITLE = "ZTranslate"

class MainWindow():
    def __init__(self):
        self.curr_image = imaging.ImageItterator.prev()
        self.root = Tk()
        self.set_window_basics()
        self.add_menu()
        self.add_top_ui()
        self.add_image_section()
        self.add_word_statistics()
        self.configure_weights()

        self.add_events()

    def set_window_basics(self):
        self.last_resize = time.time()
        self.should_resize = False
        self.root.title(APP_TITLE)
        self.root.geometry("645x545")#535
        self.w = 645
        self.h = 545
               
        self.temp_call = ""

        #self.root.geometry("1280x960")

        self.mainframe = ttk.Frame(self.root,  width=645, height=135)
        self.imageframe = ttk.Frame(self.root, width=645, height = 400)
        #self.mainframe = ttk.Frame(self.root,  width=1280, height=960)
 
        self.package_object = None

    def add_menu(self):
        self.menubar = Menu(self.root)
        self.filemenu = Menu(self.menubar, tearoff=0)
        #self.filemenu.add_command(label="New", command=donothing)
        self.filemenu.add_command(label="Load Package", command=self.load_package)
        self.filemenu.add_command(label="Close Package", command=self.close_package)
        self.filemenu.add_command(label="Package Info", command=self.package_info)
        #self.filemenu.add_command(label="Save", command=donothing)
        #self.filemenu.add_command(label="Save as...", command=donothing)

        self.filemenu.add_separator()

        self.filemenu.add_command(label="Exit", command=self.on_quit)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        #####################
        self.settingsmenu = Menu(self.menubar, tearoff=0)
        self.settingsmenu.add_command(label="Key Binds", command=self.key_binds)
        self.settingsmenu.add_command(label="API Key", command=self.api_key)

        self.menubar.add_cascade(label="Settings", menu=self.settingsmenu)
        ######################
        self.helpmenu = Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label="Help Index", command=donothing)
        self.helpmenu.add_command(label="About...", command=donothing)

        self.menubar.add_cascade(label="Help", menu=self.helpmenu)

        self.root.config(menu=self.menubar)        

    def add_top_ui(self):
        self.mainframe.grid(column=0, row=0)#, sticky=N+W+E+S)

        #Server Messages:
        self.top_ui_server_messages_var = StringVar()
        self.top_ui_server_messages_var.set("")#No news to report.")
        self.top_ui_server_messages = ttk.Label(self.mainframe, 
                        textvariable=self.top_ui_server_messages_var,
                        foreground = 'red', background='white')
        self.top_ui_server_messages.grid(row=0, column=0, columnspan=5, sticky="W")

        #Translation Mode
        self.top_ui_mode_var = StringVar()
        self.top_ui_mode_desc = ttk.Label(self.mainframe, text="Translate Mode:")
        self.top_ui_mode_desc.grid(column=0, row=1, sticky='W')

        self.top_ui_mode = ttk.Combobox(self.mainframe, width=8)
        self.top_ui_mode['values'] = ['Package', 'Free', 'Normal', 'Fast']
        self.top_ui_mode['state'] = 'readonly'
        self.top_ui_mode.set("Normal")
        self.top_ui_mode.grid(row=1, column=1, sticky='W')
        self.top_ui_mode.grid_configure(padx=10,pady=5)

        #Translation Quota
        self.top_ui_quota_text_var = StringVar()
        self.top_ui_quota_text_var.set("Quota: ???/???")
 
        self.top_ui_quota_text = ttk.Label(self.mainframe, 
                                           textvariable=self.top_ui_quota_text_var)
        self.top_ui_quota_text.grid(column=2, row=1, sticky='W')
 
        self.top_ui_quota_prog = ttk.Progressbar(self.mainframe,
                                                 orient=HORIZONTAL,
                                                 length=100,
                                                 mode='determinate')
        self.top_ui_quota_prog.grid(column=3, row=1, sticky='W')
        self.top_ui_quota_prog['value'] = 500
        self.top_ui_quota_prog['maximum'] = 1000

        #update the quota via a thread call...
        self.async_quota_call()


        #Package name
        self.top_ui_package_var = StringVar()
        self.top_ui_package_desc = ttk.Label(self.mainframe, text="  Package: ")
        self.top_ui_package_desc.grid(column=4, row=1, sticky='E')

        self.top_ui_package_name_var = StringVar()
        self.top_ui_package_name_var.set("(None)")
        self.top_ui_package_name_desc = ttk.Label(self.mainframe,  
                        textvariable=self.top_ui_package_name_var,
                        foreground = 'red', background='white')
        self.top_ui_package_name_desc.grid(column=5, row=1, sticky='W')

       
        #source language
        langs_possible = list()
        for lang in config.user_langs:
            langs_possible.append(lang.lower().title())

        self.top_ui_source_lang_desc = ttk.Label(self.mainframe, text="Source Language:")
        self.top_ui_source_lang_desc.grid(row=2, column=0, sticky="W")

        self.top_ui_source_lang = ttk.Combobox(self.mainframe, width=4)
        self.top_ui_source_lang['values'] = ["Auto"]+langs_possible
        self.top_ui_source_lang['state'] = 'readonly'
        self.top_ui_source_lang.set("Auto")
        self.top_ui_source_lang.grid(row=2, column=1, sticky='W')
        self.top_ui_source_lang.grid_configure(padx=10, pady=5)

        ###target language
        self.top_ui_target_lang_desc = ttk.Label(self.mainframe, text="Target Language:")
        self.top_ui_target_lang_desc.grid(row=2, column=2, sticky="W")

        self.top_ui_target_lang = ttk.Combobox(self.mainframe, width=4)
        self.top_ui_target_lang['values'] = langs_possible
        self.top_ui_target_lang['state'] = 'readonly'
        if config.default_target not in self.top_ui_target_lang['values']:
            self.top_ui_target_lang.set("En")
        else:
            self.top_ui_target_lang.set(config.default_target)
   
        self.top_ui_target_lang.grid(row=2, column=3, sticky='W')

        ###auto_translate
        self.top_ui_auto_package_desc = ttk.Label(self.mainframe, 
                                                  text="Auto Capture: ")
        self.top_ui_auto_package_desc.grid(row=2, column=4, sticky="W")
        self.top_ui_auto_package_var = IntVar()
        self.top_ui_auto_package = ttk.Checkbutton(self.mainframe, 
                                                   text="",
                                                   variable=self.top_ui_auto_package_var,
                                                   command=self.update_auto_capture_checkbox)
        self.top_ui_auto_package['state'] = 'disabled'
        self.top_ui_auto_package_desc['state'] = 'disabled'
        self.top_ui_auto_package.grid(row=2, column=5, sticky='W')

        #screenshot key
        self.top_ui_screenkey_desc = ttk.Label(self.mainframe, text="Screenshot Keys:")
        self.top_ui_screenkey_desc.grid(row=3, column=0, sticky="W")
        self.top_ui_screenkey_var = StringVar()
        self.top_ui_screenkey_entry = ttk.Entry(self.mainframe, width=3, textvariable=self.top_ui_screenkey_var)
        self.top_ui_screenkey_var.set("~")
        self.top_ui_screenkey_entry.grid(row=3, column=1, sticky='W')
        self.top_ui_screenkey_entry.grid_configure(padx=10, pady=5) 

        self.top_ui_screenkey_prev_var = StringVar()
        self.top_ui_screenkey_prev_entry = ttk.Entry(self.mainframe, width=3, textvariable=self.top_ui_screenkey_prev_var)
        self.top_ui_screenkey_prev_var.set("1")
        self.top_ui_screenkey_prev_entry.grid(row=3, column=2, sticky='W')
        self.top_ui_screenkey_prev_entry.grid_configure(padx=10, pady=5) 

        self.top_ui_screenkey_next_var = StringVar()
        self.top_ui_screenkey_next_entry = ttk.Entry(self.mainframe, width=3, textvariable=self.top_ui_screenkey_next_var)
        self.top_ui_screenkey_next_var.set("2")
        self.top_ui_screenkey_next_entry.grid(row=3, column=2, sticky='W')
        self.top_ui_screenkey_next_entry.grid_configure(padx=10, pady=5) 

        #keep screenshots (moved to menu options)
 
    def add_image_section(self):
        if self.curr_image == None:
            self.load_image(DEFAULT_IMAGE_PATH)
        else:
            self.load_image(self.curr_image)
        #self.img = PhotoImage(file=DEFAULT_IMAGE_PATH)
        #add left button
        self.image_ui_left = ttk.Button(self.imageframe, text="<<<", command=self.left_image)
        self.image_ui_left.grid(row=4, column=0, sticky=W)

        #add right button
        self.image_ui_right = ttk.Button(self.imageframe, text=">>>", command=self.right_image)
        self.image_ui_right.grid(row=4, column=4, sticky=E)
     
        #add zoom button -
        #self.image_ui_right = ttk.Button(self.imageframe, text="Zoom -", command=zoom_minus)
        #self.image_ui_right.grid(row=4, column=1, sticky=E)
        #add reset zoom 
        self.image_ui_right = ttk.Button(self.imageframe, text="Reset", command=self.zoom_reset)
        self.image_ui_right.grid(row=4, column=2, sticky=E+W)

        #add zoom button +
        #self.image_ui_right = ttk.Button(self.imageframe, text="Zoom +", command=zoom_plus)
        #self.image_ui_right.grid(row=4, column=3, sticky=W)

        #add image
        self.image_screenshot = ttk.Label(self.imageframe, image=self.img)
        self.image_screenshot.grid(row=5, column=0, columnspan=5, sticky=W)

    def load_image_object(self, image_object):
        self.img = image_object
        self.img_org = image_object.copy()

        w = self.w - 5
        h = self.h - 145

        if w < 640:
            w = 640
        if h < 400:
            h = 400
    
        self.img = self.img.resize((w,h), Image.ANTIALIAS)
        self.img = ImageTk.PhotoImage(self.img)
        try:
            self.image_screenshot.configure(image=self.img)
        except AttributeError:
            pass


    def load_image(self, image_name):
        print [image_name]
        the_image = Image.open(image_name)
        print [the_image]
        self.load_image_object(the_image)


    def configure_weights(self):
        #for rows in xrange(5):
        #    self.mainframe.rowconfigure(rows, weight=1)
        #self.mainframe.rowconfigure(4, weight=1)
        #self.mainframe.rowconfigure(5, weight=5)
        pass
        #for columns in xrange(4):
        #    self.mainframe.columnconfigure(columns, weight=1)

    def add_events(self):
        self.root.bind("<Configure>", self.resizing_window)
        self.root.bind("<<pyHookKeyDown>>", self.on_pyhook)
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)


    def resizing_window(self, event):       
        if event.width >= 645 and event.height >= 545:
            self.should_resize = True
            self.w = event.width
            self.h = event.height

    def poller(self):
        if self.should_resize:
            self.should_resize = False
            self.w = self.root.winfo_width()
            self.h = self.root.winfo_height()
            self.img_org.save("tmpy1.png")
            self.load_image("tmpy1.png")
            os.remove("tmpy1.png")
            self.last_resize = time.time()
        self.mainframe.after(100, self.poller)#call every 100 miliseconds

    def async_quota_call(self):
        #farm this out to a thread
        self.quota_thread = Thread(target=self.async_quota_call2)
        self.quota_thread.start()

    def async_quota_call2(self):
        quota = server_client.ServerClient.get_quota()
        if quota and quota.get("langs"):
            self.set_langs(quota['langs'])
        self.update_quota(quota)

    def set_langs(self, langs):
        config.user_langs = langs

        langs_possible = list()
        for lang in config.user_langs:
            langs_possible.append(lang.lower().title().strip())

        self.top_ui_source_lang['values'] = ["Auto"]+langs_possible
        self.top_ui_target_lang['values'] = ["Auto"]+langs_possible
        pass

    def run(self):
        t = Thread(target=key_input.hook_loop, args=(self.root, key_input.pipe_read))
        t.start()
      
        self.input_thread = Thread(target=key_input.queue_executor.loop)
        self.input_thread.start()
        
        api_service.start_api_server(self)

        self.grabbed_images = list()
        self.root.mainloop()
        config.write_init()

    def statuser(self):
        import time
        time.sleep(4)
        import pdb
        pdb.set_trace()

    def add_statistics(self):
        pass

    def add_word_statistics(self):
        pass

    def call_screenshoter(self):
        config.default_target = self.top_ui_target_lang.get()
        if self.top_ui_mode.get() in ['Normal', 'Free', 'Fast'] or self.temp_call == "active":
            image_object = screen_grab.ImageGrabber.grab_image()
            self.grabbed_images.append(image_object)        
            key_input.queue_executor.add_func(self.call_screenshoter_part2)
            if self.temp_call == "active":
                self.temp_call = "active_stage2"
            print 'func added', self.temp_call

        elif self.top_ui_mode.get() == 'Package' and self.temp_call != "active_stage2":
            image_object = screen_grab.ImageGrabber.grab_image()
            print ['-------------------------', self.temp_call]
            try:
                if image_object and self.root.focus_get() is None:
                    source_lang = self.top_ui_source_lang.get().lower()
                    target_lang = self.top_ui_target_lang.get().lower()
                    if source_lang.lower() == "auto":
                        source_lang = None
                    image_result = package_ocr.PackageOCR.call_ocr(image_object, 
                                                                   target_lang, 
                                                                   self.package_object)
                    #image_result is a temp image filename, with updated, translated text.
                    image_result = package_ocr.TextBox.process_textboxes(image_result,
                                                                         target_lang,
                                                                         self.package_object)
                    self.load_image_object(image_result)
            except KeyboardInterrupt as e:
                raise
            except:
                import traceback
                traceback.print_exc() 
            if self.package_object and self.top_ui_auto_package_var.get() == 1:
                self.root.after(25, self.call_screenshoter_safe)
        elif self.top_ui_mode.get() == 'Package' and self.temp_call == "active_stage2":
            self.temp_call = ""
            print "TTTTTT", self.temp_call
            if self.package_object and self.top_ui_auto_package_var.get() == 1:
                self.root.after(25, self.call_screenshoter)

    def call_screenshoter_safe(self):
        if self.temp_call != "active_stage2":
            self.call_screenshoter()

    def call_screenshoter_part2(self):
        if len(self.grabbed_images) > 0:
            image_object = self.grabbed_images.pop(0)

            source_lang = self.top_ui_source_lang.get().lower()
            target_lang = self.top_ui_target_lang.get().lower()
            if source_lang.lower() == "auto":
                source_lang = None
            if self.top_ui_mode.get() == "Fast":
                fast = True
            else:
                fast = False
            if self.top_ui_mode.get() == "Free":
                free = True
            else:
                free = False
            print [[fast, free]]
            image_result, quota = screen_translate.CallScreenshots.call_screenshot(image_object, 
                                                                                   source_lang, 
                                                                                   target_lang,
                                                                                   fast=fast,
                                                                                   free=free)
            if quota:
                self.update_quota(quota)

            #image_result is a temp image filename, with updated, translated text.
            self.load_image_object(image_result)
            self.curr_image = imaging.ImageItterator.prev()

    def update_quota(self, quota):
        if not quota:
            return
        qmax = int(quota['quota_max'])
        qcur = int(quota['quota'])
        self.top_ui_quota_text_var.set("Quota: "+str(qcur)+"/"+str(qmax))
        if isinstance(qmax, basestring) or isinstance(qcur, basestring):
            self.top_ui_quota_prog['value'] = 1000      
            self.top_ui_quota_prog['maximum'] = 1000
        else:
            self.top_ui_quota_prog['value'] = qcur        
            self.top_ui_quota_prog['maximum'] = qmax

    def zoom_reset(self):
        self.call_screenshoter()

    def left_image(self):
        img = imaging.ImageItterator.prev(self.curr_image)
        print [self.curr_image]
        if img:
            self.curr_image = img
            self.load_image(self.curr_image)

    def right_image(self):
        img = imaging.ImageItterator.next(self.curr_image)
        if img:
            self.curr_image = img
            self.load_image(self.curr_image)
        self.load_image(self.curr_image)

    def load_package(self):
        filename = tkFileDialog.askopenfilename(initialdir = "./packages", 
                                                title = "Select file",
                                                filetypes = (("ztranslate packages","*.ztp"),
                                                             ("all files","*.*")))
        if filename:
            if self.package_object != None:
                #close this package
                self.package_object.close()
            try:
                self.package_object = package_loader.PackageObject(filename) 
            except:
                tkMessageBox.showinfo("Error", "Package '"+filename+"' could not be loaded.  Is it in use by another program?") 
                self.top_ui_package_name_var = "(None)"
                self.top_ui_mode.set("Normal")
                return
            #change the mode to be in "Package" mode
            self.top_ui_mode.set("Package")
            self.top_ui_package_name_var.set(os.path.basename(filename))
            self.temp_call = ""

            self.top_ui_auto_package['state'] = 'normal'
            self.top_ui_auto_package_desc['state'] = 'normal'

            if self.package_object.info.get("auto_package") == "t":
                self.top_ui_auto_package_var.set(1)
                self.root.after(25, self.call_screenshoter)
            else:
                self.top_ui_auto_package_var.set(0)
            
        print [self.package_object, filename]  

    def update_auto_capture_checkbox(self):
        if self.top_ui_auto_package_var.get() == 1:
            self.root.after(25, self.call_screenshoter)
 
    def package_info(self):
        try:
            self.package_info_window.destroy()
        except:
            pass
        self.package_info_window = Toplevel(self.root)
        piw = self.package_info_window
        piw.wm_title("Package Info")

        if not self.package_object:
            game_name_l = ttk.Label(piw, text="No package loaded", justify="center").grid()
        else:
            #show package info
            info = self.package_object.info
            # - Game Name
            game_name_v = info.get("name", "")
            print info.keys()
            # - Author
            author_v = info.get("author", "")
            # - Version
            version_v = info.get("version", "")
            # - Description
            description_v = info.get("version", "")
            # - Source language

            # - Target language
            #screen_width = self.package_info_window.winfo_screenwidth()
            #screen_height = self.package_info_window.winfo_screenheight()
            game_name_l = ttk.Label(piw, text="Game Name:").grid(row=0, column=0, sticky="W")
            game_name = ttk.Label(piw, text=game_name_v).grid(row=0, column=1, columnspan=1, sticky="W")
            author_l = ttk.Label(piw, text="Author:").grid(row=1, column=0, sticky="W")
            author = ttk.Label(piw, text=author_v).grid(row=1, column=1, columnspan=1,sticky="W")
            version_l = ttk.Label(piw, text="Version:").grid(row=2, column=0, sticky="W")
            version = ttk.Label(piw, text=version_v).grid(row=2, column=1, columnspan=1,sticky="W")
            #source_l = ttk.Label(piw, text="Source Language:").grid(row=3, column=0, sticky="W")
            #source = ttk.Label(piw, text="(De)").grid(row=3, column=1, columnspan=1, sticky="W")
            #target_l = ttk.Label(piw, text="Target Language:").grid(row=4, column=0, sticky="W")
            #target = ttk.Label(piw, text="(En)").grid(row=4, column=1, columnspan=1,sticky="W")
            #spacker:
            ttk.Label(piw, text="").grid(row=5)

            desc_l = ttk.Label(piw, text="Description:").grid(row=6, column=0, sticky="W")
            desc = ttk.Label(piw, text=description_v, wraplength=320, justify="left").grid(
                    row=7, column=0, columnspan=2, sticky="W")
       
        x, y = self.root.winfo_x(), self.root.winfo_y()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        w2, h2 = 3*w/4, 3*h/4
        x2, y2 = x+w2/8, y+h2/8
 
        #w2, h2 = piw.winfo_width, piw.winfo_height()
        piw.geometry(str(w2)+"x"+str(h2)+"+"+str(x2)+"+"+str(y2))

    def close_package(self):
        self.top_ui_auto_package['state'] = 'disabled'
        self.top_ui_auto_package_desc['state'] = 'disabled'


        if self.package_object != None:
            #close this package
            self.package_object.close()
            self.top_ui_package_name_var.set("(None)")

    def key_binds(self):
        pass

    def api_key(self):
        pass

    def on_quit(self):
        self.root.destroy()
        key_input.quit_pipe()
        key_input.queue_executor.kill_queue() 
        api_service.kill_api_server()

    def on_pyhook(self, event):
        if not key_input.read_queue.empty():
            scancode, ascii = key_input.read_queue.get()
            ##print [scancode, ascii]
            if scancode == config.keycode_capture:#41
                print "Capture"
                if self.temp_call == "":
                    self.temp_call = "active"
                if self.package_object and self.top_ui_auto_package_var.get() == 1:
                    self.temp_call = ""
                self.call_screenshoter()
            elif scancode == config.keycode_prev:#2
                print "Prev"
                self.left_image()
            elif scancode == config.keycode_next:#3
                print "Next"
                self.right_image()
            
def zoom_minus():
    pass

def zoom_reset():
    pass

def zoom_plus():
    pass


def main():
    if config.load_init() is False:
        try:
            key_input.grab_input_stop()
        except:
            pass
        return
    text_draw.load_font(config.user_font)

    window = MainWindow()
    window.mainframe.pack(anchor=W)
    window.imageframe.pack(fill=BOTH, expand=YES)
    window.mainframe.after(100, window.poller)
    try:
        window.run()
    except:
        import traceback
        traceback.print_exc()

        try:
            key_input.grab_input_stop()
        except:
            traceback.print_exc()
            pass
        window.root.destroy()
        key_input.queue_executor.kill_queue()
        key_input.quit_pipe()
        api_service.kill_api_server()

  

if __name__=='__main__':
    main()   
