from PIL import Image
import base64
import time
import io
import sys
import os
import shlex
import subprocess
from ztrans_common.image_util import get_color_counts_simple

if os.name == "nt":
    import pyocr_util
else:
    import pytesseract


lang_to_tesseract_lang = {
    "deu": "deu",
    "eng": "eng"
}


def setup_pytesseract(lang="eng"):
    if lang is None:
        lang = "eng"

    if os.name == "nt": 
        pyocr_util.load_tesseract_dll(lang=lang)
    else:
        #linux here
        pytesseract.pytesseract.tesseract_cmd = r'tesseract'


def tess_helper(image, lang=None, mode=None,min_pixels=1):
    if os.name == "nt":
        return tess_helper_windows(image, lang, mode, min_pixels)
    else:
        return tess_helper_linux(image, lang, mode, min_pixels)

def tess_helper_data(image, lang=None, mode=None,min_pixels=1):
    if os.name == "nt":
        return tess_helper_data_windows(image, lang, mode, min_pixels)
    else:
        return tess_helper_data_linux(image, lang, mode, min_pixels)

def tess_helper_windows(image, lang=None, mode=None,min_pixels=1):
    setup_pytesseract(lang)

    if mode is None:
        mode = 6

    t_ = time.time()
    pc = get_color_counts_simple(image, ["FFFFFF"], 2)

    if min_pixels and pc < min_pixels:
        return list()
    x = pyocr_util.image_to_boxes(image, lang=lang, mode=mode)
    print ['ocr time', time.time()-t_]

    found_chars = list()
    for word_box in x:     
        word = word_box.content
        box = word_box.position

        l = len(word)
        w = box[1][0] - box[0][0]
            
        for i, char in enumerate(word):
            found_chars.append([char, [box[0][0]+((i)*w)/l, box[0][1], 
                                       box[0][0]+((i+1)*w)/l, box[1][1]]])
    
    data = list()
    curr_pos = None
    curr_box = None
    found_lines = list()
    curr_line = ""
    char_h = 0
    char_w = 0
    if found_chars:
        for entry in found_chars:
            char = entry[0]
            coords = entry[1]

            this_char_h = coords[3]-coords[1]
            this_char_w = coords[2]-coords[0]
            char_h = max(char_h, this_char_h)
            char_w = max(char_w, this_char_w)

            if curr_pos is None:
                curr_pos = coords
                curr_box = coords
                curr_line = char
            else:
                if coords[0] > last_x-char_w and\
                   curr_box[0]-char_w/2 < coords[0] < curr_box[2] + (char_w)*3 and\
                   curr_box[0]-char_w/2 < coords[2] < curr_box[2] + (char_w)*4 and\
                   curr_box[1]-char_h < coords[1] < curr_box[3] + (char_h) and\
                   curr_box[1]-char_h < coords[3] < curr_box[3]+char_h:
                    #another character to add:
                    if curr_box[0] > coords[0]:
                        curr_box[0]  = coords[0]
                    if curr_box[1] > coords[1]:
                        curr_box[1]  = coords[1]
                    if curr_box[2] < coords[2]:
                        curr_box[2]  = coords[2]
                    if curr_box[3] < coords[3]:
                        curr_box[3]  = coords[3]

                    curr_pos = coords
                    curr_line+=char
                else:
                    found_lines.append([curr_line, curr_box])
                    curr_pos = coords
                    curr_box = coords
                    curr_line = char
                    char_h = 0
                    char_w = 0
            last_x = coords[0]
        if curr_line:
            found_lines.append([curr_line, curr_box])
    #for c in found_lines:
    #    print c
    return found_lines
    


def tess_helper_data_windows(image, lang=None, mode=None,min_pixels=1):
    setup_pytesseract(lang)

    if mode is None:
        mode = 6

    t_ = time.time()
    pc = get_color_counts_simple(image, ["FFFFFF"], 2)

    if min_pixels and pc < min_pixels:
        return list()
    x = pyocr_util.image_to_data(image, lang=lang, mode=mode)

    return get_word_boxes(x)


def tess_helper_linux(image, lang=None, mode=None, min_pixels=1):
    import pytesseract
    setup_pytesseract()

    pc = get_color_counts_simple(image, ["FFFFFF"], 2)

    if min_pixels and pc < min_pixels:
        return list()

    config_arg = ""
    if mode is not None:
        #config_arg += " --oem 0 --psm "+str(mode)
        config_arg += " --psm "+str(mode)


    if not config_arg:
        config_arg = ""

    for i in range(2):
        try:
            if lang:
                lang = lang_to_tesseract_lang[lang]
                x = pytesseract.image_to_boxes(image, lang=lang, config=config_arg)
            else:
                x = pytesseract.image_to_boxes(image, config=config_arg)
            
            break
        except Exception as e:
            if type(e) == KeyboardInterrupt:
                raise

            if i == 1:
                raise
            print 'tttttttttttttttttttttttt'
            setup_pytesseract()


    h = image.height
    data = list()
    curr_pos = None
    curr_box = None
    found_lines = list()
    curr_line = ""
    char_h = 0
    char_w = 0
    last_x = None
    if x.strip():
        for line in x.split("\n"):
            split = line.split(" ")
            char = split[0]
            coords = [int(i) for i in split[1:5]]

            coords = [coords[0], coords[3], coords[2], coords[1]]
            coords[1] = h-coords[1]
            coords[3] = h-coords[3]

            this_char_h = coords[3]-coords[1]
            this_char_w = coords[2]-coords[0]
            char_h = max(char_h, this_char_h)
            char_w = max(char_w, this_char_w)

            if curr_pos is None:
                curr_pos = coords
                curr_box = coords
                curr_line = char
            else:
                if coords[0] > last_x-char_w and\
                   curr_box[0]-char_w/2 < coords[0] < curr_box[2] + (char_w)*3 and\
                   curr_box[0]-char_w/2 < coords[2] < curr_box[2] + (char_w)*4 and\
                   curr_box[1]-char_h < coords[1] < curr_box[3] + (char_h) and\
                   curr_box[1]-char_h < coords[3] < curr_box[3]+char_h:
                    #another character to add:
                    if curr_box[0] > coords[0]:
                        curr_box[0]  = coords[0]
                    if curr_box[1] > coords[1]:
                        curr_box[1]  = coords[1]
                    if curr_box[2] < coords[2]:
                        curr_box[2]  = coords[2]
                    if curr_box[3] < coords[3]:
                        curr_box[3]  = coords[3]

                    curr_pos = coords
                    curr_line+=char
                else:
                    found_lines.append([curr_line, curr_box])
                    curr_pos = coords
                    curr_box = coords
                    curr_line = char
                    char_h = 0
                    char_w = 0
            last_x = coords[0]

        if curr_line:
            found_lines.append([curr_line, curr_box])
    for l in found_lines:
        print l
    return found_lines




def tess_helper_data_linux(image, lang=None, mode=None, min_pixels=1):
    import pytesseract
    setup_pytesseract()

    pc = get_color_counts_simple(image, ["FFFFFF"], 2)

    if min_pixels and pc < min_pixels:
        return list()

    config_arg = ""
    if mode is not None:
        config_arg += " --oem 0 --psm "+str(mode)

    if not config_arg:
        config_arg = ""

    for i in range(2):
        try:
            if lang:
                lang = lang_to_tesseract_lang[lang]
                x = pytesseract.image_to_data(image, lang=lang, config=config_arg)
            else:
                x = pytesseract.image_to_data(image, config=config_arg)
            break
        except Exception as e:
            if type(e) == KeyboardInterrupt:
                raise

            if i == 1:
                raise
            print 'tttttttttttttttttttttttt'
            setup_pytesseract()
    return get_word_boxes(x)

def get_word_boxes(x):
    boxes = list()

    for i, line in enumerate(x.split("\n")):
        level, page_num, block_num, par_num, line_num, word_num,\
        left, top, width, height, conf, text = line.split("\t")
        x = int(x)
        y = int(y)
        w = int(width)
        h = int(height)
        curr_box = [x, y, w,h]
        curr_word = text
        if curr_word.strip():
            boxes.append([curr_word, curr_box])

    new_lines = list()
    seen = dict()
    for i, box1 in enumerate(boxes):
        if i not in seen:
            new_lines.append(box1)
            seen[i] = 1
            h = int(box1[1][2])
            
            nbox = sorted(boxes[i+1:], key=lambda x: int(x[1][0]))
            for j, box2 in nbox:
                if box2[1][0] < box1[1][0]+box1[1][2]+h*2 and\
                        abs(box2[1][1] - box1[1][1]) < h/2 and\
                        j not in seen:
                    seen[j] = 1
                    new_lines[-1][0]+=" "+box2[0]
                    new_lines[-1][1] = _merge_boxes(box1[1], box2[1])
    return boxes

def _merge_boxes(box1, box2):
    #convert to int
    box1 = [int(x) for x in box1]
    box2 = [int(x) for x in box2]
    #convert to absolute coordinates
    box1[2]+=box1[1][0]
    box1[3]+=box1[1][1]
    box2[2]+=box2[1][0]
    box2[3]+=box2[1][1]
    #merge boxes
    rbox = [min(box1[0], box2[0]), min(box1[1], box2[1]),
            max(box1[2], box2[2]), max(box1[3], box2[3])]
    #convert back to relative coordinates
    rbox[2]-=rbox[0]
    rbox[3]-=rbox[1]
    #convert back to str
    rbox = [str(x) for x in rbox]
    return rbox



def tess_helper_server(image, lang=None, mode=None):
    setup_pytesseract()

    config_arg = ""
    if mode is not None:
        config_arg += " --oem 0 --psm "+str(mode)

    if not config_arg:
        config_arg = ""

    if lang:
        lang = lang_to_tesseract_lang[lang]
        x = pytesseract.image_to_boxes(image, lang=lang, config=config_arg)
    else:
        x = pytesseract.image_to_boxes(image, config=config_arg)
    h = image.height
    data = list()
    curr_pos = None
    curr_box = None
    found_lines = list()
    curr_line = ""
    char_h = 0
    char_w = 0
    last_x = None
    if x.strip():
        for line in x.split("\n"):
            split = line.split(" ")
            char = split[0]
            coords = [int(i) for i in split[1:5]]
            coords = [coords[0], coords[3], coords[2], coords[1]]
            coords[1] = h-coords[1]
            coords[3] = h-coords[3]

            this_char_h = coords[3]-coords[1]
            this_char_w = coords[2]-coords[0]
            char_h = max(char_h, this_char_h)
            char_w = max(char_w, this_char_w)
            if curr_pos is None:
                curr_pos = coords
                curr_box = coords
                curr_line = char
            else:  
                
                if coords[0] > last_x-char_w and\
                   curr_box[0]-char_w/2 < coords[0] < curr_box[2] + (char_w)*3 and\
                   curr_box[0]-char_w/2 < coords[2] < curr_box[2] + (char_w)*4 and\
                   curr_box[1]-char_h < coords[1] < curr_box[3] + (char_h) and\
                   curr_box[1]-char_h < coords[3] < curr_box[3]+char_h:
                    #another character to add:
                    if curr_box[0] > coords[0]:
                        curr_box[0]  = coords[0]
                    if curr_box[1] > coords[1]:
                        curr_box[1]  = coords[1]
                    if curr_box[2] < coords[2]:
                        curr_box[2]  = coords[2]
                    if curr_box[3] < coords[3]:
                        curr_box[3]  = coords[3]

                    curr_pos = coords
                    curr_line+=char
                else:
                    found_lines.append([curr_line, curr_box])
                    curr_pos = coords
                    curr_box = coords
                    curr_line = char
                    char_h = 0 
                    char_w = 0
            last_x = coords[0]

        if curr_line:
            found_lines.append([curr_line, curr_box])
    return found_lines

def main():
    image= Image.open("a.png")
    tess_helper(image, lang="deu", mode=6, min_pixels=2)

if __name__=='__main__':
    main()
