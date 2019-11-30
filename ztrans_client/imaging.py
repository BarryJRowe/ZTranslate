from PIL import Image, ImageFont, ImageDraw
import os
import datetime
import time
from ztrans_common.image_util import color_hex_to_byte
from ztrans_common.text_draw import drawTextBox

class ImageModder:
    @classmethod
    def write(cls, image_object, ocr_data, target_lang="en"):
        t_time = time.time()
        img = image_object.convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        font_name = "RobotoCondensed-Bold.ttf"
        if "ocr_results" in ocr_data:
            ocr_data = ocr_data['ocr_results']
        for block in ocr_data['blocks']:
            print "================"
            for key in block['bounding_box']:
                if not type(block['bounding_box'][key]) == int:
                    block['bounding_box'][key] = int(block['bounding_box'][key])
            draw = drawTextBox(draw, block['translation'][target_lang], 
                              block['bounding_box']['x']+2,
                              block['bounding_box']['y'],
                              block['bounding_box']['w']-2,
                              block['bounding_box']['h'],
                              font_name)
        return img

######### Now time for the stuff relati+ng to the user stored images...

IMAGES_DIRECTORY = "screenshots"

if os.name == "nt":
    dir_sep = "\\"
else:
    dir_sep = "/"

class ImageSaver:
    @classmethod
    def save_image(cls, image_object, image_source=None):
        #create directory
        try:
            os.mkdir(IMAGES_DIRECTORY)
        except:
            pass

        if image_source is not None:
            new_loc = image_source.split(".")
            new_loc[-2] = new_loc[-2]+"_t"
            new_loc = ".".join(new_loc)
        else:
            dt = datetime.datetime.now()
            extension = ".png"
            create_parts = [dt.year, dt.month, dt.day,
                            dt.hour, dt.minute, dt.second,
                            0, extension]
            dir_set = set(os.listdir(IMAGES_DIRECTORY))
            while cls.list_to_filename(create_parts) in dir_set:
                create_parts[-2]+=1
            create_filename = cls.list_to_filename(create_parts)
            new_loc = os.path.join(IMAGES_DIRECTORY, create_filename)
        image_object.save(new_loc)
        return new_loc

    @classmethod
    def list_to_filename(cls, list_obj):
        rval = [str(x) for x in list_obj]
        return "-".join(rval[0:6])+rval[6]+rval[7]

    @classmethod
    def copy(cls, org, new):
        new_file = open(new, "w")
        old_data = open(org).read()
        new_file.write(old_data)



class ImageItterator:
    @classmethod
    def next(cls, baseline=None, image_type=None):
        filename = cls._next_prev(baseline, image_type, pre_next="next")
        if filename:
            return os.path.join(IMAGES_DIRECTORY, filename)
        return None 

    @classmethod
    def prev(cls, baseline=None, image_type=None):
        filename = cls._next_prev(baseline, image_type, pre_next="prev")   
        if filename:
            return os.path.join(IMAGES_DIRECTORY, filename)
        return None

    @classmethod
    def date_order_convert(cls, date):
        orders = list()
        data = date.split("-")
        try:
            orders.append(int(data[0]))#year
            orders.append(int(data[1]))#month
            orders.append(int(data[2]))#day
            orders.append(int(data[3]))#hour
            orders.append(int(data[4]))#minute
            if "_" in data[5]:
                orders.append(int(data[5].partition("_")[0]))#seconds
                orders.append("_t.png")
            else:
                orders.append(int(data[5].partition(".")[0]))#seconds
                orders.append(".png")             
        except:
            print date, len(orders)
            while len(orders) < 6:
                orders.append(0)
            if "_" in date:
                orders.append("_t.png")
            else:
                orders.append(".png")
        
        return tuple(orders)

    @classmethod
    def _next_prev(cls, baseline=None, image_type=None, pre_next="prev"):
        try:
            file_list = os.listdir(IMAGES_DIRECTORY)
        except:
            return None
        if baseline and dir_sep in baseline:
            baseline = baseline.split(dir_sep)[-1]        

        file_list = sorted(file_list, key=lambda x: cls.date_order_convert(x))
        if pre_next == "prev":
            itterator = file_list[::-1]
        else:
            itterator = file_list[::]
    
        min_date = ""
        max_date = cls.date_order_convert("200000-12-12-12-12-12.png")
        if pre_next == "next" and baseline != None:
            min_date = cls.date_order_convert(baseline)
        if pre_next == "prev" and baseline != None:
            max_date = cls.date_order_convert(baseline)
        #just get the latest image
        for filename in itterator:
            if baseline:
                if min_date >= cls.date_order_convert(filename) or max_date <= cls.date_order_convert(filename):
                    continue
            if not filename.endswith(".png"):
                continue
            stripped = filename.replace("_t.png", "").replace(".png", "")
            if not stripped.replace("-", "").isdigit():
                continue
            if filename.endswith("_t.png"):
                if image_type != "screenshot":
                    return filename
                continue
            elif image_type != "translate":
                return filename
        return None
    
