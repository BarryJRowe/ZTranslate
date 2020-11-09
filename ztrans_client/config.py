import json

version_string = "1.03"
server_host = "barry-mac"#"172.20.10.3"
server_port = 8888
user_api_key = ""
default_target = "en"

local_server_enabled = False
local_server_host = "localhost"
local_server_port = 4404
local_server_ocr_key = ""
local_server_translation_key = ""
local_server_api_key_type = "google"

keycode_capture = 41
keycode_prev = 2
keycode_next = 3

ascii_capture = '`'
ascii_prev = '1'
ascii_next = '2'

capture_mode = "fast"

user_langs = ["En", "De", "Fr", "Es", "Ja"]
user_font = "RobotoCondensed-Bold.ttf"

ocr_output = ["image"]


def load_init():
    global server_host
    global server_port
    global user_api_key
    global default_target
    global local_server_enabled
    global local_server_host
    global local_server_port
    global local_server_ocr_key
    global local_server_translation_key
    global local_server_api_key_type

    global keycode_capture
    global keycode_prev
    global keycode_next

    global capture_mode

    global ascii_capture# = 246
    global ascii_prev# = 49
    global ascii_next# = 50


    global user_langs
    global user_font

    global ocr_output

    try:
        config_file = json.loads(open("./config.json").read())
    except Exception as e:
        print "Invalid config file specification:"
        print e.message
        return False

    if "server_host" in config_file:
        server_host = config_file['server_host']    
    if "server_port" in config_file:
        server_port = config_file['server_port']    
    if "user_api_key" in config_file:
        user_api_key = config_file['user_api_key']    
    if "default_target" in config_file:
        default_target = config_file['default_target']    

    if "local_server_enabled" in config_file:
        local_server_enabled = config_file['local_server_enabled']
    if "local_server_host" in config_file:
        local_server_host = config_file['local_server_host']
    if "local_server_port" in config_file:
        local_server_port = config_file['local_server_port']

    if "local_server_ocr_key" in config_file:
        local_server_ocr_key = config_file['local_server_ocr_key']
    if "local_server_translation_key" in config_file:
        local_server_translation_key = config_file['local_server_translation_key']
    if "local_server_api_key_type" in config_file:
        local_server_api_key_type = config_file['local_server_api_key_type']

    if "keycode_capture" in config_file:
        keycode_capture = config_file['keycode_capture']
    if "keycode_prev" in config_file:
        keycode_prev = config_file['keycode_prev']
    if "keycode_next" in config_file:
        keycode_next = config_file['keycode_next']

    if "ascii_capture" in config_file:
        ascii_capture = config_file['ascii_capture']
    if "ascii_prev" in config_file:
        ascii_prev = config_file['ascii_prev']
    if "ascii_next" in config_file:
        ascii_next = config_file['ascii_next']

    if "user_langs" in config_file:
        user_langs = config_file['user_langs']
    if "user_font" in config_file:
        user_font = config_file['user_font']

    if "ocr_output" in config_file:
        ocr_output = config_file['ocr_output']

    if "capture_mode" in config_file:
        capture_mode = config_file['capture_mode']

    print "config loaded"
    print "===================="
    #print user_api_key
    return True

def set_config(key, value):
    global ascii_capture
    global ascii_prev
    global ascii_next
    global capture_mode
    if key == "ascii_capture":
        ascii_capture = value
    elif key == "ascii_prev":
        ascii_prev = value
    elif key == "ascii_next":
        ascii_next = value
    elif key == "capture_mode":
        capture_mode = value
    write_init()

def write_init():
    obj = {"server_host": server_host,
           "server_port": server_port,
           "user_api_key": user_api_key,
           "default_target": default_target,
           "local_server_enabled": local_server_enabled,
           "local_server_host": local_server_host,
           "local_server_port": local_server_port,
           "local_server_ocr_key": local_server_ocr_key,
           "local_server_translation_key": local_server_translation_key,
           "local_server_api_key_type": local_server_api_key_type,
           "keycode_capture": keycode_capture,
           "keycode_prev": keycode_prev,
           "keycode_next": keycode_next,
           "user_langs": user_langs,
           "user_font": user_font,
           "capture_mode": capture_mode,
           "ascii_capture": ascii_capture,
           "ascii_prev": ascii_prev,
           "ascii_next": ascii_next
    }
    config_file = open("./config.json", "w")
    config_file.write(json.dumps(obj, indent=4))

