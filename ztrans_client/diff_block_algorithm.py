from PIL import Image, ImageEnhance, ImageChops, ImageDraw, ImageStat
from bson.objectid import ObjectId
import io
import base64
import time
from util import load_image, get_color_counts, reduce_to_colors, color_hex_to_byte,\
                  image_to_string, fix_bounding_box, general_index

class DiffBlockAlgorithm:
    @classmethod
    def prep_image(cls, image_data, sharp=4.0):###################
        img = load_image(image_data)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(sharp)
        img = img.convert("P", palette=Image.ADAPTIVE, colors=256)
        p = img.getpalette()
        return {"image": img, "palette": p}

    @classmethod
    def get_text_block(cls, img, p, block, text_colors=None):################
        bb = block['bounding_box']
        if 'x' in bb:
            x = bb['x']
            y = bb['y']
            w = bb['w']
            h = bb['h']
            img = img.crop([x,y,x+w,y+h])
        else:
            x1 = bb['x1']
            y1 = bb['y1']
            x2 = bb['x2']
            y2 = bb['y2']
            img = img.crop([x1,y1,x2,y2])

        tcs = list()

        if not text_colors:
            text_colors = block.get('text_colors')
        if not text_colors:
            text_colors = ["190506"]

        #img = reduce_to_colors(img, tcs, 
        #                       threshold=block.get("pixel_threshold", 16))
        return img


    @classmethod
    def get_image_diff(cls, test_image, index_image, tb, block, threshold):############
        if test_image.width <=0 or test_image.height<=0:
            return 256
        
        im = ImageChops.difference(test_image, index_image).convert("RGBA")
        if block.get("text_colors"):
            im_reduced = reduce_to_colors(im.convert("P", palette=Image.ADAPTIVE),                              
                                          block.get('text_colors', ["FFFFFF"]),
                                          16.0).convert("RGB")

        pix_r = ImageStat.Stat(im_reduced).mean
        threshold2 = 16.0
        #if pix_r[0]**2+pix_r[1]**2+pix_r[2]**2 > threshold2:        
        #    return 256

        if im.width <=0 or im.height<=0:
            return 256
        pix = ImageStat.Stat(im).mean
       
        rr = pix[0]**2
        gg = pix[1]**2
        bb = pix[2]**2
        threshold = 16.0
        the_sum = (rr+gg+bb)/(threshold**2)
      
        if the_sum < 1.0 and pix[3] < 128:
            return the_sum/4
        return 256

    @classmethod
    def find_matches(cls, image_data, package):#####################
        if type(image_data) == Image.Image:
            image_data_string = image_to_string(image_data)
        else:
            image_data_string = image_data
            image_data = load_image(image_data)

        hsv = general_index(image_data_string)
        threshold = 32
    
        blocks = list()
        original_image = image_data
        draw = ImageDraw.Draw(original_image)

        prep = cls.prep_image(image_data_string, sharp=4.0)
      
        white_pixel_count = get_color_counts(image_data.convert("P", palette=Image.ADAPTIVE),
                                             ["FFFFFF"], 16.0)
        index = {"h": hsv[0], "s": hsv[1], "v": hsv[2], "pc": white_pixel_count}
       
        s_time = time.time()

        short_list = cls.find_blocks_by_index(index, package)
        short_list.extend(cls.find_blocks_by_index({}, package))
 
        for entry in short_list:
            test_image = load_image(entry['index_image'])
            tb = entry['bounding_box']

            block = entry
            crop = cls.get_text_block(prep['image'], prep['palette'], 
                                      block, text_colors=None).convert("RGBA")

            tb2 = {"x1": 0, "y1": 0, "x2": crop.width, "y2": crop.height}
            threshold = 16

            res = cls.get_image_diff(crop, test_image, tb2, entry, threshold)
            
            if res < 1.0:
                #this is a match
                blocks.append(entry)
                draw.rectangle([tb['x1'], tb['y1'], tb['x2'], tb['y2']],
                               fill=(0,0,0,0))
                prep = cls.prep_image(image_to_string(original_image), 
                                      sharp=4.0)
        return {"blocks": blocks, "image": image_to_string(original_image)}
   
    @classmethod
    def find_blocks_by_index(cls, index, package):
        pixel_factor = 0.75
        
        hsv = list()
        for c in 'hsv':
            if c in index:
                hsv.append(index[c])
        if not hsv:
            hsv = None
        else:
            hsv = tuple(hsv)

        if 'pixel_count' in index:
            pc = index['pixel_count']
        else:
            pc = None
        short_list = package.find_data_by_values("diff", hsv, pc)
        return short_list

