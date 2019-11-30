"""
  TODO...
"""
from ztrans_common.opencv_engine import TextFeatureFinder,\
                                        HuMoments
from ztrans_common.text_color_finder import TextColorFinder
from ztrans_common.image_util import color_byte_to_hex,\
                                     reduce_to_multi_color
import colorsys
from PIL import Image
import time

class EASTTextAlgorithm:
    @classmethod
    def find_text(cls, image, min_conf, width, height, padding,
                       threshold=32, get_text_colors=False):
        east = "data/frozen_east_text_detection.pb"
        out, img = TextFeatureFinder.find_features(image, east=east, 
                                                   min_confidence=min_conf,
                                                   width=width, height=height,
                                                   padding=padding)
        t = time.time()
        out, img = TextFeatureFinder.find_features(image, east=east, 
                                                   min_confidence=min_conf,
                                                   width=width, height=height,
                                                   padding=padding)
        #format:
        # out = [{"box": [x1,y1,x2,y2], "type": <large|small|best>, "num": i}]
        # new entries to add:
        # -crop: the cropped image to this box
        # -hu: the hu moments of this cropped image
        # -hsv: the hsv index of this image

        for entry in out:
            entry['crop'] = image.crop(entry['box'])
            res = entry['crop'].resize((1,1), Image.ANTIALIAS).convert("RGB")
            r,g,b = res.getpixel((0,0))
            h,s,v = colorsys.rgb_to_hsv(float(r)/255, float(g)/255, float(b)/255)
            entry['hsv'] = [h,s,v]
            
        num_lookup = dict()
        if get_text_colors:
            for entry in out:
                if entry['type'] == "best":
                    text_colors = TextColorFinder.find_text_colors(entry['crop'],
                                                                   threshold=32)
                    num_lookup[entry['num']] = text_colors
            for entry in out:
                tc = num_lookup[entry['num']]
                #now... reduce image to the estimated text colors.
                bg_color = None
                fg_color = None
                entry['colors'] = dict()
                for c in tc:
                    v = tc[c]
                    if v[1].get("bg"):
                        bg_color = color_byte_to_hex(c)
                        entry['colors'][c] = "bg"
                    elif v[1].get("text"):
                        fg_color = color_byte_to_hex(c)
                        entry['colors'][c] = "text"
                entry['crop'] = entry['crop'].convert("P", palette=Image.ADAPTIVE)
                if bg_color and fg_color:
                    bg = "000000"
                    mapping = [[bg_color, "000000"], [fg_color, "FFFFFF"]]
                    entry['crop'] = reduce_to_multi_color(entry['crop'], bg=bg_color,
                                                          colors_map=mapping,
                                                          threshold=threshold)
                    for p in entry['crop'].convert("RGB").getcolors():
                        if p[1] == (255,255,255):
                            entry['pc'] = p[0]
        for entry in out:
            if get_text_colors:
                entry['hu'] = HuMoments.calculate_hu_moments(entry['crop'], binarized=False)
            else:
                entry['hu'] = HuMoments.calculate_hu_moments(entry['crop'], binarized=True)
        print [5,time.time()-t]
        return out
        
                
