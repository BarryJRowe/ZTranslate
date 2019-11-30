from PIL import Image, ImageFont, ImageDraw
import os
import datetime
import time
from ztrans_common.image_util import color_hex_to_byte

FONT_DATA = {
    "FONT": "",#"RobotoCondensed-Bold.ttf"
    "FONTS": [],#[ImageFont.truetype("./fonts/"+FONT, x+8) for x in range(32)]
    "FONTS_WH": list()
}

def load_font(font_name, font_object=None):
    global FONT_DATA
    if font_object is None:
        font_object = FONT_DATA
        
    font_object["font"] = font_name
    font_object["fonts"] = [ImageFont.truetype("./fonts/"+font_name, x+8) for x in range(32)]
    font_object["fonts_wh"] = list()
    fill_fonts_wh(font_object)


def fill_fonts_wh(font_object=None):
    global FONT_DATA
    if font_object is None:
        font_object = FONT_DATA

    test = Image.new('RGBA', (100, 100))
    test = test.convert("RGBA")
    draw = ImageDraw.Draw(test)

    largest_char_w_size = 0
    avg_w = 0
    largest_char_h_size = 0
    avg_h = 0

    for i in range(len(font_object['fonts'])):
        t = 0
        avg_w = 0
        avg_h = 0
        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz?!.,;'\"":
            t+=1
            size_x, size_y = draw.textsize(char, font=font_object['fonts'][i])
            avg_w += size_x
            avg_h += size_y

            if size_x > largest_char_w_size:
                largest_char_w_size = size_x
            if size_y > largest_char_h_size:
                largest_char_h_size = size_y
        avg_w = int(avg_w/t)
        avg_h = int(avg_h/t)

        font_object['fonts_wh'].append([avg_w, largest_char_h_size])

    draw = ImageDraw.Draw(test)


def wrap_text(text, font, draw, w):
    words = text.split(" ")
    outline = ""
    outtext = ""
    for word in words:
        size = draw.textsize(outline+" "+word, font=font)
        if size[0] < w:
            if outline:
                outline+=" "+word
            else:
                outline+=word
        else:
            outtext+=outline+"\n"
            outline = word
    if outtext and outtext[-1] == "\n":
        outtext+=outline
    else:
        outtext+=" "+outline
    return outtext

def get_approximate_font(text, w, h, font_object=None):
    global FONT_DATA
    if font_object is None:
        font_object = FONT_DATA

    best = 0
    for i in range(32):
        curr_x = 0
        curr_y = font_object['fonts_wh'][i][1]
        for word in text.split():
            curr_x+=len(word)*font_object['fonts_wh'][i][0]
            if curr_x > w:
                curr_x = len(word)*font_object['fonts_wh'][i][0]
                curr_y+=font_object['fonts_wh'][i][1]
        if curr_y > h:
            break
        best = i
    return best

def get_text_wh(text, font, draw, mw):
    height = font.getsize("A")[1]
    h = len(text.strip().split("\n"))*(height+1)
    w = 0
    for line in text.strip().split("\n"):
        cw = draw.textsize(line, font=font)
        if cw > w and cw <= mw:
            w = cw
    return w,h



def drawTextBox(draw, text, x,y, w, h, font=None, font_size=None,
                font_color=None, confid=1, exact_font=None,
                font_object=None, bg_color=None):
    global FONT_DATA
    if font_object is None:
        font_object = FONT_DATA

    if h < 18:
        h = 18
    font_color_byte = (255,255,255,255)
    if font_color:
        font_color_byte = color_hex_to_byte(font_color)
    if not bg_color:
        bg_color = (0,0,0,255)
    print "UUUUUUUUUUUUU"
    print bg_color
    #c = int(confid*255)
    draw.rectangle([x-2,y, x+w+2, y+h], fill=bg_color, outline=font_color_byte)

    approx_font = get_approximate_font(text, w, h, font_object=font_object)
    succ = wrap_text(text, font_object['fonts'][8], draw, w)
    succ_f = font_object['fonts'][8]
    for i in range(32):
        if exact_font is not None:
            i = exact_font

        if i < approx_font and exact_font:
            continue
        outtext = wrap_text(text, font_object['fonts'][i], draw, w)
        tw, th = get_text_wh(outtext, font_object['fonts'][i], draw, w)

        if th <= h and exact_font is None:
            succ = outtext
            succ_f = font_object['fonts'][i]
        else:
            break
    outtext = succ
    if font_size:
        succ_f = font_object['fonts'][font_size]
    if outtext and outtext[0] == "\n":
        outtext = outtext[1:]
        succ_f = font_object['fonts'][0]

    draw.multiline_text((x,y), outtext, font_color_byte, font=succ_f, spacing=1)
    return draw

