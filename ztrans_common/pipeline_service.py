import colorsys
import copy
import time
from fuzzywuzzy import fuzz
from PIL import Image, ImageEnhance, ImageChops, ImageDraw, ImageStat
from bson.objectid import ObjectId
from ztrans_common import ocr_tools
from ztrans_common.text_draw import drawTextBox
from ztrans_common.image_util import load_image, fix_bounding_box,\
                                     image_to_string, chop_to_box,\
                                     color_hex_to_byte,\
                                     get_color_counts,\
                                     get_color_counts_simple,\
                                     intersect_area,\
                                     get_bounding_box_area,\
                                     convert_to_absolute_box, \
                                     reduce_to_colors,\
                                     reduce_to_multi_color, segfill,\
                                     get_best_text_color, tint_image,\
                                     expand_horizontal, expand_vertical,\
                                     draw_solid_box, color_byte_to_hex
from ztrans_common.algos.moving_text_algorithm import MovingTextAlgorithm
from ztrans_common.algos.diff_block_algorithm import DiffBlockAlgorithm
from ztrans_common.algos.east_text_algorithm import EASTTextAlgorithm
from ztrans_common.text_tools import levenshtein, levenshtein_shortcircuit,\
                                     substitute_text, \
                                     levenshtein_shortcircuit_dist

HMAX = 16

def f_ord1(text):
    return sum((ord(c)*12345701)%255 for c in text)

def f_ord2(text):
    return sum((ord(c)*12359911)%255 for c in text)

def f_ord3(text):
    vals = list()
    for i,c in enumerate(text):
        val = ord(c)*(i%16)+ord(c)
        val = (val*123588163)%(255*16)
        vals.append(val)
    print vals
    return sum(vals)

def get_miss(miss_array, text):
    l = len(text)
    miss_var = miss_array[0]
    #print miss_array, 'cccccc', len(text)
    for i, val in enumerate(miss_array):
        if val <= l:
            miss_var = i+1
    return miss_var
        

class OCRPipeline:
    @classmethod
    def process_pipeline(cls, pipeline, image, metadata, short_list, 
                         target_lang=None, user_id=None, game_id=None,
                         index_name=None, package=None, debug=None):
        org_image = image.copy()
        data_in = [{"image": image, "meta": metadata,
                    "short_list": short_list}]
        
        t_time = time.time()
        for stage in pipeline:
            new_data_in = list()
            for data in data_in:
                new_data = cls.process_stage(stage, data, user_id=user_id,
                                             game_id=game_id, index_name=index_name,
                                             package=package)
                if new_data:
                    new_data_in.extend(new_data)
            data_in = new_data_in
            
        #add in the textboxes over this now...
        if target_lang != None:
            return cls.do_block_post_processing(org_image, data_in, 
                                                target_lang, package)
        else:
            #this is the same as the above, but here to emphasize the 
            #difference that target_lang=None does
            return cls.do_block_post_processing(org_image, data_in, None, 
                                                package)

    @classmethod
    def do_block_post_processing(cls, org_image, data, target_lang, package):
        #might have to do more resolution on what happens when there are
        #multiple matches on a block of text
        org_org_image = org_image.copy()
        draw = ImageDraw.Draw(org_image)
        new_data = list()
        
        box_non_overlap = list()
        for entry in data:
            #go through and select the best matches for boxes that are overlapping..."
            if "l_dist" in entry and entry.get("match"):
                bb = entry['block']['bounding_box']
                area = intersect_area(bb,bb)
                for k in box_non_overlap:
                    if k.get('match'):
                        bb2 = k['block']['bounding_box']
                        area2 = intersect_area(bb2,bb2)
                        if intersect_area(bb,bb2) > 0.75*min(area,area2):
                            #these boxes are overlapping, so get rid of one of them.
                            break
                else:
                    box_non_overlap.append(entry)
                    continue
                #so entry and k are overlapping... figure out which one to take
                #based on their levenshtein distances
                if entry['l_dist'] < k['l_dist']:
                    #k (old one) is worse, so make it a non-match and append the new one
                    #to box_non_overlap
                    k['match'] = False
                    box_non_overlap.append(entry)
                else:
                    #the new one (entry) is worse, so mark it as a non-match and leave it
                    entry['match'] = False

        for entry in data:
            if entry.get("match") == True:
                if target_lang != None and entry['block']['source_text'] and\
                        entry['block']['translation'].get(target_lang):
                    tinge = None
                    if entry.get("meta", {}).get("text_colors"):
                        text_colors = entry['meta']['text_colors']
                        tc_block = org_org_image.crop([entry['block']['bounding_box']['x1'],
                                                   entry['block']['bounding_box']['y1'],
                                                   entry['block']['bounding_box']['x2'],
                                                   entry['block']['bounding_box']['y2']])
                       
                        tinge = get_best_text_color(tc_block, text_colors, threshold=32)
                        if tinge == "FFFFFF":
                            tinge = None
                    if target_lang.lower() in [x.lower() for x in entry['block'].get("drawn_text", {})]:
                        offset = [entry['block']['bounding_box']['x1'],
                                  entry['block']['bounding_box']['y1'],
                                 ]
                        for t in entry['block']['drawn_text']:
                            if t.lower() == target_lang.lower():
                                i_img = entry['block']['drawn_text'][t]

                        i_img = load_image(i_img)
                        if tinge:
                            i_img = tint_image(i_img, tinge)

                        org_image.paste(i_img, offset)
                    else:
                        tb = entry['block']['bounding_box']
                        HMAX=16

                        font_name = block.get("font","RobotoCondensed-Bold.ttf")
                        font_size = None
                        font_color = None  
                        bg_color = None  

                        special_json = entry['block'].get('special_json', {})
                        for i, atrb in enumerate(special_json.get("box_attributes", [])):
                            if i == int(entry['block']['block_id'].split("_")[1]):
                                font_size = atrb.get("font size")
                                font_color = atrb.get("font color")
                                bg_color = atrb.get("bg color")

                        if tinge:
                            font_color = tinge
                        if bg_color:
                            bg_color = color_hex_to_byte(bg_color)
                        else:
                            bg_color = (0,0,0,255)
                        image = Image.new("RGBA", (tb['x2']-tb['x1'],
                                          max(tb['y2']-tb['y1'], HMAX+1)),bg_color)
                        draw = ImageDraw.Draw(image)
                     
                        #this is to work around upper-case keys for languages
                        #when this is phased out, it'll just be lower-cased
                        #all the time.
                        target_lang = target_lang.lower()
                        for key in entry['block']['translation']:
                            if key.lower() == target_lang:
                                if entry['block']['translation'][key]:
                                    translation = entry['block']['translation'][key]

                        text_source = ""
                        for e in entry['meta']['index']:
                            for v in e['values']:
                                text_source+=v['text_source']   
                   
                        sub_chars = entry['meta']['subs']['sub_chars']
                        sub_placeholder = entry['meta']['subs']['sub_placeholder']
                        
                        output_text = substitute_text(translation, text_source, sub_placeholder, sub_chars)
                        draw = drawTextBox(draw, 
                                           output_text,
                                           2,0,image.width-5, 
                                           max(image.height-2, HMAX),
                                           font_name, 
                                           font_size=font_size,
                                           font_color=font_color,
                                           font_object=package.font_object,
                                           bg_color=bg_color)
                        org_image.paste(image, [tb['x1'], tb['y1']])   
        #org_image.show()
        return org_image, data

    @classmethod
    def process_stage(cls, stage, data, user_id=None, game_id=None, 
                      index_name=None, package=None):
        print stage
        output = list()
        options = stage.get('options', {})
        if stage['action'] == "resize":
            out = PipelineResize.resize(data, options)
            output.extend(out)
        elif stage['action'] == "crop":
            out = PipelineCrop.crop(data, options)
            output.extend(out)
        elif stage['action'] == "cropFilter":
            out = PipelineCrop.crop_filter(data, options)
            output.extend(out)
        elif stage['action'] == "textFilter":
            out = PipelineTextFilter.text_filter(data, options)
            output.extend(out)
        elif stage['action'] == "reduceToColors":
            out = PipelineReduceToColors.reduce_colors(data, options)
            output.extend(out)
        elif stage['action'] == "reduceToMultiColor":
            out = PipelineReduceToColors.reduce_to_multi_color(data, options)
            output.extend(out)
        elif stage['action'] == "segFill":
            out = PipelineColorFill.seg_fill(data, options)
            output.extend(out)
        elif stage['action'] == "indexHSV":
            out = PipelineIndexHSV.index_hsv(data, options)
            output.extend(out)
        elif stage['action'] == "indexPixelCount":
            out = PipelineIndexPixelCount.index_pixel_count(data, options)
            output.extend(out)
        elif stage['action'] == "sharpen": 
            out = PipelineSharpen.sharpen(data, options)
            output.extend(out)
        elif stage['action'] == "findShortlistByIndex":
            out = PipelineFindByIndex.find_by_index(data, options,
                                                    index_name, package=package)
            output.extend(out)
        elif stage['action'] == "expandShortlist":
            short_list = data['short_list']
            out = list()
            
            for doc in short_list:
                short_block = doc['block']
                short_index = doc['index']
                out.append({"image": data['image'].copy(), 
                            "meta": copy.deepcopy(data['meta']),
                            "block": short_block,
                            "index": short_index
                           })
            output.extend(out)
        elif stage['action'] == "diffImage":
            out = PipelineDiffImage.diff_image(data, options)
            output.extend(out)
        elif stage['action'] == "fuzzyDiffImage":
            out = PipelineFuzzyDiffImage.fuzzy_diff_image(data, options)
            output.extend(out)
        elif stage['action'] == "matchFilters":
            out = PipelineMatchFilter.match_filters(data, options)
            output.extend(out)
        elif stage['action'] == "diffTextLines":
            out = PipelineDiffTextLines.diff_text_lines(data, options)
            output.extend(out)
        elif stage['action'] == "diffTextDetect":
            out = PipelineDiffTextDetect.diff_text_detect(data, options)
            output.extend(out)
        elif stage['action'] == "getTextBlocks":
            out = PipelineGetTextBlocks.get_text_blocks(data, options)
            output.extend(out)
        elif stage['action'] == "indexOCR":
            out = PipelineIndexOCR.ocr_index(data, options)
            output.extend(out)
        elif stage['action'] == "indexTextDetect":
            out = PipelineTextDetect.text_detect_index(data, options)
            output.extend(out)
        elif stage['action'] == "expandColorHorizontal":
            out = PipelineExpandColor.expand_horizontal(data, options)
            ouput.extend(out)
        elif stage['action'] == "expandColorVertical":
            out = PipelineExpandColor.expand_vertical(data, options)
            ouput.extend(out)
        elif stage['action'] == "expandColor":
            out = PipelineExpandColor.expand_color(data, options)
            ouput.extend(out)
        elif stage['action'] == "rectangle":
            out = PipelineRectangle.rectangle(data, options)
            ouput.extend(out)
        elif stage['action'] == "createIndex":
            out = PipelineCreateIndex.create_index(data, options, 
                                                   user_id=user_id,
                                                   game_id=game_id,
                                                   index_name=index_name,
                                                   package=package)
            output.extend(out)

        return output


class PipelineAction:
    @classmethod
    def resolve_var(cls, name, data):
        if isinstance(name, basestring) and name.startswith("$"):
            names = name.partition("$")[2].split(".")
            s_data = data
            try:
                for seg in names:
                    data = data[seg]
            except:
                data = s_data['meta']
                for seg in names:
                    data = data[seg]
            return data 
        else:
            return name


##### IMAGE MODIFIERS ################

class PipelineResize(PipelineAction):
    @classmethod
    def resize(cls, data, ops):
        new_image = data['image'].resize([cls.resolve_var(ops['width'], data),
                                          cls.resolve_var(ops['height'], data)])
        return [{"image": new_image, "meta": data['meta']}]


class PipelineCrop(PipelineAction):
    @classmethod
    def crop(cls, data, ops):
        x1,y1,x2,y2 = [cls.resolve_var(ops[c],data) for c in\
                           ['x1', 'y1', 'x2', 'y2']]
        crop_type = cls.resolve_var(ops.get("type", "diff"), data)
        new_image = data['image'].crop([x1, y1, x2, y2])
        data['image'] = new_image
        return [data]
        #data['meta']['bounding_box'] = {"x1": x1, "x2": x2, "y1": y1, "y2": y2}

    @classmethod
    def crop_filter(cls, data, ops):

        x1,y1,x2,y2 = [cls.resolve_var(ops[c],data) for c in\
                           ['x1', 'y1', 'x2', 'y2']]
        crop_type = cls.resolve_var(ops.get("type", "diff"), data)
        new_image = data['image'].crop([x1, y1, x2, y2])
        #data['meta']['bounding_box'] = {"x1": x1, "x2": x2, "y1": y1, "y2": y2}

        if "filters" not in data['meta']:
            data['meta']['filters'] = list()
        if new_image.size[0] > 0 and new_image.size[1] > 0:
            data['meta']['filters'].append({"box": {"x1": x1, "x2": x2,
                                                    "y1": y1, "y2": y2},
                                            "type": crop_type,
                                            "image": new_image})
        else:
            return []
        return [data]


class PipelineTextFilter(PipelineAction):
    @classmethod
    def text_filter(cls, data, ops):
        #we're creating a text filter now... so find the appropriate filter stuff
        # match up the blocks x,y,w,h to the index lines [...]
        res_blocks = list()
        bb = data['meta']['block']['bounding_box']


        subs = data['meta']['subs']
        common_errors = data['meta']['common_errors']
        common_errors_subs = common_errors+[x+"=" for x in subs.get("sub_chars", [])]

        bb_org_text = data['meta']['block']['source_text']
        bb_modified_text = ocr_fix_text(bb_org_text, common_errors_subs)
        bb_modified_text = bb_modified_text.replace(" ", "")

        for entry in data['meta']['index']:
            ib = entry['data']['box']
            ib = {"x1": ib[0], "y1": ib[1], "x2": ib[2], "y2": ib[3]}

            ib = fix_bounding_box(data['meta']['original_image'], ib)
    
            if intersect_area(bb,ib) > get_bounding_box_area(bb)/2 >4 or\
               intersect_area(bb,ib) > get_bounding_box_area(ib)/2 >4:
                #this block matches
                res_blocks.append(entry)
        if len(res_blocks) > 0:
            if "filters" not in data['meta']:
                data['meta']['filters'] = list()
            data['meta']['filters'].append({"type": "text", 
                                            "lines": [x['val_s'] for x in res_blocks],
                                            "full_text": bb_modified_text,
                                            "org_text": bb_org_text})
            #miss
            #common error 
            #subs
        return [data]





class PipelineSharpen(PipelineAction):
    @classmethod
    def sharpen(cls, data, ops):
        enhancer = ImageEnhance.Sharpness(data['image'])
        new_image = enhancer.enhance(cls.resolve_var(ops['sharpness'], data))
        return [{"image": new_image, "meta": data['meta']}]

class PipelineReduceToColors(PipelineAction):
    @classmethod
    def reduce_colors(cls, data, ops):
        threshold = cls.resolve_var(ops['threshold'], data)
        colors = cls.resolve_var(ops['colors'], data)
        img = reduce_to_colors(data['image'].convert("P", 
                                                     palette=Image.ADAPTIVE), 
                                                     colors, threshold)
        return [{"image": img, "meta": data['meta']}]

    @classmethod
    def reduce_to_multi_color(cls, data, ops):
        image = data['image']
        image=image.convert("P", palette=Image.ADAPTIVE)
        threshold = cls.resolve_var(ops['threshold'], data)
        base_color = cls.resolve_var(ops['base'], data)
        colors = cls.resolve_var(ops['colors'], data)
        threshold = 32  
        reduce_to_multi_color(image, base_color,
                              colors,
                              threshold=threshold)
        return [{"image": image, "meta": data['meta']}]

class PipelineColorFill(PipelineAction):
    @classmethod
    def seg_fill(cls, data, ops):
        image = data['image']
       
        base_color = cls.resolve_var(ops['base'], data)
        colors = cls.resolve_var(ops['colors'], data)  
        image = segfill(image, "FF0000", "FFFFFF")
        
        return [{"image": image, "meta": data['meta']}]


######## INDEXERS #################

class PipelineIndexHSV(PipelineAction):
    @classmethod
    def index_hsv(cls, data, ops):
        tolerance = cls.resolve_var(ops.get('tolerenace', 0.5), data)
        if "x1" in ops:
            x1,y1,x2,y2 = [cls.resolve_var(ops[c], data) for c in\
                                                       ['x1','y1', 'x2', 'y2']]
            res = data['image'].crop([x1,y1,x2,x2])
        else:
            res = data['image']

        res = res.resize((1,1), Image.ANTIALIAS).convert("RGB")
        r,g,b = res.getpixel((0,0))
        h,s,v = colorsys.rgb_to_hsv(float(r)/255, float(g)/255, float(b)/255)
        if 'index' not in data['meta']:
            data['meta']['index'] = list()
        existing_docs = dict()

        curr_number = 1
        for entry in data['meta']['index']:
            if entry['type'] == 'h':
                if entry['num'] >= curr_number:
                    curr_number = entry['num']+1

        for ch, v in zip('hsv', (h,s,v)):
            index_block = {
                "type": ch,
                "num": curr_number,
                "val_s": None,
                "val_i": None,
                "val_f": v,
                "tol": tolerance
            }
            data['meta']['index'].append(index_block)
        return [data]

class PipelineIndexPixelCount(PipelineAction):
    @classmethod
    def index_pixel_count(cls, data, ops):
        tolerance = cls.resolve_var(ops['tolerenace'], data)     
        pixel_count = data['meta']['pixel_count']

        if 'index' not in data['meta']:
            data['meta']['index'] = list()
        existing_docs = dict()

        curr_number = 1
        for entry in data['meta']['index']:
            if entry['type'] == 'pc':
                if entry['num'] >= curr_number:
                    curr_number = entry['num']+1

        index_block = {
            "type": "pc",
            "num": curr_number,
            "val_s": None,
            "val_i": pixel_count,
            "val_f": None,
            "tol": tolerance
        }
        data['meta']['index'].append(index_block)
        return [data]


def ocr_fix_text(text, fixer):
    for fix in fixer:
        p = fix.partition("=")
        text = text.replace(p[0], p[2])
    return text

class PipelineIndexOCR(PipelineAction):
    @classmethod
    def ocr_fix_text(cls, text, fixer):
        for fix in fixer:
            p = fix.partition("=")
            text = text.replace(p[0], p[2])
        return text


    @classmethod
    def ocr_index(cls, data, ops):
        t = time.time()
        miss = cls.resolve_var(ops.get("miss", [1,2]), data)
        min_pixels = cls.resolve_var(ops.get("min_pixels", 1), data)
        common_errors = cls.resolve_var(ops.get("common_errors", []), data)
        subs = cls.resolve_var(ops.get("subs", {}), data)
        common_errors_subs = common_errors+[x+"=" for x in subs.get("sub_chars", [])]
        tolerance = cls.resolve_var(ops.get("tolerance", 32), data)

        typ = cls.resolve_var(ops.get("ocr_type", "boxes"), data)      
        if typ == "boxes":
            boxes = ocr_tools.tess_helper(data['image'], cls.resolve_var(ops['lang'], data),
                                          cls.resolve_var(ops.get('mode'), data),
                                          min_pixels)
        else:
            boxes = ocr_tools.tess_helper_data(data['image'], cls.resolve_var(ops['lang'], data),
                                               cls.resolve_var(ops.get('mode'), data),
                                               min_pixels)

        text_colors = cls.resolve_var(ops.get("text_colors", []), data)

        if 'index' not in data['meta']:
            data['meta']['index'] = list()
        existing_docs = dict()

        curr_number = 1
        for entry in data['meta']['index']:
            if entry['type'] == 'ocr':
                if entry['num'] >= curr_number:
                    curr_number = entry['num']+1

        docs = [{"text": ocr_fix_text(t[0], common_errors_subs),
                "text_source": t[0],
                "box": t[1]} for t in boxes]
        """
                entry = {
                    'val_s': None, 
                    'type': 'td_east_hu_0', 
                    'data': {
                        'box': [191.7125, 84.009375, 241.596875, 100.321875], 
                        'image': <PIL.Image.Image image mode=P size=50x16 at 0x7FEEB43D4690>, 
                        'pc': 62, 
                        'colors': {
                            (20, 20, 20, 255): 'text', 
                            (86, 86, 86, 255): 'bg'}, 
                        'hsv': [0.0, 0.0, 0.12941176470588237], 
                        'type': 'best'}, 
                    'num': 1, 
                    'val_f': 2.0010317177959713, 
                    'tol': 0.01, 
                    'val_i': None} 
        """
        ##Right now, turning the words into lines is happening at the ocr level of things.
        ##...Maybe it should be happening at the create_index level, in order to intersect
        ##the lines with the current bounding box...
        for ii, entry in enumerate(docs):
            text_value = entry['text']
            if text_value:
                data_doc = {"box": entry['box'], "image": data['image'].crop(entry['box']),
                        "text": entry['text'], "type": "line", "sub_num": ii}
                sub_id = "ocr_"+str(curr_number)+"_"+str(ii)
           
                index_block = {
                    "type": "ocr",
                    "num": curr_number,
                    "val_s": text_value,
                    "val_i": None,
                    "val_f": None,
                    "sub_id": sub_id,
                    "data": data_doc,
                    "tol": tolerance
                }
                data['meta']['index'].append(index_block)

        new_data = copy.deepcopy(data)
        data = new_data
        data['meta']['containing'] = True
        data['meta']['miss'] = miss
        data['meta']['common_errors'] = common_errors
        data['meta']['subs'] = subs
        data['meta']['text_colors'] = text_colors
        return [data]


class PipelineTextDetect(PipelineAction):
    @classmethod
    def text_detect_index(cls, data, ops):
        method = cls.resolve_var(ops.get("method", "east"), data)
        min_conf = cls.resolve_var(ops.get("min_confidence", 0.5), data)
        width = cls.resolve_var(ops.get("width", 320), data)
        height = cls.resolve_var(ops.get("height", 320), data)
        padding = cls.resolve_var(ops.get("padding", 0.25), data)
        threshold = cls.resolve_var(ops.get("threshold", 32), data)
        tolerance = cls.resolve_var(ops.get("tolerance", 0.01), data)
        get_colors = cls.resolve_var(ops.get("get_text_colors", True), data)
        image = data['image']

        output = list()
        if method == "east":
            t = time.time()
            res = EASTTextAlgorithm.find_text(image, min_conf, width, height,
                                              padding, threshold=threshold,
                                              get_text_colors=get_colors)
            print time.time()-t
            output.extend(res)
 
        if 'index' not in data['meta']:
            data['meta']['index'] = list()
        existing_docs = dict()

        curr_number = 1
        for entry in data['meta']['index']:
            if entry['type'] == 'td_east_hu_0':
                if entry['num'] >= curr_number:
                    curr_number = entry['num']+1

        num_mini_blocks = 0
        for d in res:
            if d['type'] == 'best':
                num_mini_blocks+=1

        for d in res:
            colors = dict()
            for k in d['colors']:
                new_k = color_byte_to_hex(k[:3])
                colors[new_k] = d['colors'][k]
            d['colors'] = colors

            docs = {
                    "hsv": d['hsv'],
                    "pc": d['pc'],
                    "colors": d['colors'],
                    "image": d['crop'],
                    "box": d['box'],
                    "type": d['type']
                   }
            sub_id = d['type']+"_"+str(d['num'])
            for i in range(7):
                index_block = {
                    "type": "td_east_hu_"+str(i),
                    "num": d['num'],
                    "val_s": None,
                    "val_i": None,
                    "val_f": d['hu'][i],
                    "data": docs,
                    "tol": tolerance,
                    "num_max": num_mini_blocks,
                    "sub_id": sub_id
                }
                data['meta']['index'].append(index_block)       
        return [data]
        

########## INDEX FUNCTION ################

class PipelineFindByIndex(PipelineAction):
    @classmethod
    def find_by_index(cls, data, ops, index_name, package):
        #old function
        t_ = time.time()
        if 'indexes' in ops:
            indexes = list()
            for entry in ops['indexes']:
                for ind in data['meta']['index']:
                    if ind['name'] == entry:
                        indexes.append(ind)
                        break
                else:
                    print "Index not found: "+entry
        else:
            indexes = data['meta'].get('index', [])
        count = 0
        db_query = {"user_id": user_id, "game_id": game_id, "type": index_name}
        
        for index in indexes:
            if index['type'] == 'hsv':
                tol = index['tolerance']
                for c in 'hsv':
                    ik = "index."+str(count)+".value"
                    db_query[ik] = {"$gte": index['values'][c]-tol, 
                                    "$lte": index['values'][c]+tol}
                    count+=1
            elif index['type'] == 'pixel_count':
                tol = index['tolerance']
                ik = "index."+str(count)+".value"
                db_query[ik] = {"$gte": index['values']['pixel_count']/tol,
                                "$lte": index['values']['pixel_count']*tol}
            elif index['type'] == "text_detect":
                tol = index.get('tolerance', 0.01)

                if not '$and' in db_query:
                    db_query['$and'] = list()
                db_query['$and'].append({"$or": []})

                for iv_value in index['values']:
                    db_query['$and'][-1]['$or'].append(dict())
                   
                    for i in range(3):
                        ik = "index."+str(count+i)+".value"
                        db_query['$and'][-1]['$or'][-1][ik] = {
                                        "$gte": iv_value['hu'][i]-tol,
                                        "$lte": iv_value['hu'][i]+tol
                                       }
                if not db_query['$and'][-1]['$or']:
                    db_query['$and'].pop()
                if not db_query['$and']:
                    del db_query['$and']
                count+=3
            elif index['type'] == 'ocr':
                l = list()
                index_key1 = "index."+str(count)+".value"
                #index_key2 = "index."+str(count)+".ord1"
                #index_key3 = "index."+str(count)+".ord2"
                if not '$and' in db_query:
                    db_query['$and'] = list()
                db_query['$and'].append({"$or": []})

                start_count =  count

                for iv_entry in index['values']:
                    db_query['$and'][-1]['$or'].append(dict())
               
                    ord1 = f_ord1(iv_entry['text'].encode("utf-8"))
                    ord2 = f_ord2(iv_entry['text'].encode("utf-8"))
                    miss = get_miss(data['meta'].get("miss", [1,2]), iv_entry['text'].encode("utf-8"))
    
                    index_key1 = "index."+str(start_count)+".value"
                    db_query['$and'][-1]['$or'][-1][index_key1] = {
                                                 "$gte": ord1-255*miss,
                                                 "$lte": ord1+255*miss}
                  

                    index_key2 = "index."+str(start_count+1)+".value"
                    db_query['$and'][-1]['$or'][-1][index_key2] = {
                                                 "$gte": ord2-255*miss,
                                                 "$lte": ord2+255*miss}

                if not db_query['$and'][-1]['$or']:
                    db_query['$and'].pop()
                if not db_query['$and']:
                    del db_query['$and']
                count+=2
       
        short_list = [x for x in package.find_by_query(db_query)]
        if not data.get("short_list"):
            data['short_list'] = list()
        data['short_list'].extend(short_list)
        if db_query['type'] == 'deu_ocr':
            print [time.time()-t_]
        return [data]

    @classmethod
    def find_by_index(cls, data, ops, index_type, package):
        new_values = list()
        for doc in data['meta']['index']:
            if 'data' in doc:
                del doc['data']
            new_values.append(doc)
        results = package.search_index(index_type, new_values)
        short_list = results
        if not data.get("short_list"):
            data['short_list'] = list()
        data['short_list'].extend(short_list)
        return [data]
        


########### CREATE INDEX ###################

class PipelineCreateIndex(PipelineAction):
    @classmethod
    def create_index(cls, data, options, user_id=None, game_id=None,
                          index_name=None, package=None):
        #if this data has a bounding box, check to see if the bounding
        #box is "close enough" to the index bounding box.
        print "CREATE INDEX"
        
        indexes = list()
        if 'block' in data['meta']:
            block = data['meta']['block']
            filters = data['meta'].get("filters",[])
            bb = block['bounding_box']
            bb = fix_bounding_box(data['meta']['original_image'], 
                                  bb)

            for entry in data['meta']['index']:
                #if the index has a bounding box associated to it
                #for example, from text detection, or OCR, then
                #require that it is inside this block's image.
                if 'data' in entry and 'box' in entry['data']:
                    ib = [int(x) for x in entry['data']['box']]
                    ib = {"x1": ib[0], "y1": ib[1],
                          "x2": ib[2], "y2": ib[3]}
                    ib = fix_bounding_box(data['meta']['original_image'],
                                          ib)
                    entry['sub_type'] = entry['data']['type']
    
                    if intersect_area(bb,ib) > get_bounding_box_area(ib)/2 >4 or\
                       intersect_area(bb,ib) > get_bounding_box_area(bb)/2 >4:
                        #this block matches
                        indexes.append(entry)
                else:
                    #otherwise, there is no box, so this is like an HSV index
                    #which indexes based on screen properties and not a sub box
                    #found inside the text.

                    indexes.append(entry)
            if indexes or filters:
                block['drawn_text'] = dict()
                font_name = "RobotoCondensed-Bold.ttf"
                font_size = block.get("font size")
                font_color = block.get("font color")
                bg_color = block.get("bg color")
                if bg_color:
                    bg_color = color_hex_to_byte(bg_color)
                else:
                    bg_color = (0,0,0,255)

                for lang in block['translation']:
                    size = (bb['x2']-bb['x1'], max(bb['y2']-bb['y1'], HMAX+1))

                    image = Image.new("RGBA", size, bg_color)
                    if size[0] > 5:
                        draw = ImageDraw.Draw(image)
                        draw = drawTextBox(draw, 
                                           block['translation'][lang],
                                           2,0,image.width-5, 
                                           max(image.height-2, HMAX),
                                           font_name, 
                                           font_size=font_size,
                                           font_color=font_color,
                                           font_object=package.font_object,
                                           bg_color=bg_color)
                        block['drawn_text'][lang] = image_to_string(image)
                                       
                #we now have a list of matching index entries, so add them to the index:
                package.save_index_data(index_name, indexes, filters, block)
        return [data]

###### FILTER STUFF NOW #############

class PipelineMatchFilter(PipelineAction):
    @classmethod
    def match_filters(cls, data, ops):
        output = list()
        if not data.get("block"):
            return []
        for f in data['block']['filters']:
            if f['type'] == "diff":
                res = PipelineFilterImageDiff.diff_image(data, f, ops)
            elif f['type'] == 'text':
                res = PipelineFilterTextDiff.diff_text(data, f, ops)
            else:
                res = list()
            if not res:
                break
        else:
            #this image passed all the filters:
            data['match'] = True
            return [data]
        return []

class PipelineFilterImageDiff(PipelineAction):
    @classmethod
    def diff_image(cls, data, f, ops):
        test_image = data['image']
        test_image = test_image.crop([f['box']['x1'], f['box']['y1'],
                                      f['box']['x2'], f['box']['y2']])

        index_image = load_image(f['image'])
        im = ImageChops.difference(test_image, index_image).convert("RGBA")               
        pix = ImageStat.Stat(im).mean
        threshold = f.get("threshold", 16.0)
        the_sum = (pix[0]**2+pix[1]**2+pix[2]**2)/(threshold**2)

        if the_sum < 1.0 and pix[3] < 128:
            return True
        return False


class PipelineFilterTextDiff(PipelineAction):
    @classmethod
    def diff_text(cls, data, f, ops):
        output = list()
        index_lines = ["".join(x['val_s'].split(" ")) for x in data['meta']['index']]
        inside_compare = "".join(f.get("lines"))
        compare_length = 0
        line_matches = 0
        miss = 2#compute this from inside_compare and miss variable     
        for line in index_lines:
            threshold = (float(len(line)-miss)/len(line))*100
            if threshold < 50:
                treshold = 50
            match_per = fuzz.partial_ratio(inside_compare, line)
            if match_per > threshold:
                #match!
                compare_length+=len(line)
                line_matches+=1
                continue
            else:
                pass
        else:
            if compare_length > len(inside_compare)-miss*line_matches:
                #got a match for all lines:
                output.append(data)
        return output
        ########################
   
        """
        subs = data['meta']['subs']
        common_errors = data['meta']['common_errors']
        common_errors_subs = common_errors+[x+"=" for x in subs.get("sub_chars", [])]

        bb_org_text = data['meta']['block']['source_text']
        bb_modified_text = ocr_fix_text(bb_org_text, common_errors_subs)
        bb_modified_text = bb_modified_text.replace(" ", "")

        for entry in data['meta']['index']:
            ib = entry['data']['box']
            ib = {"x1": ib[0], "y1": ib[1], "x2": ib[2], "y2": ib[3]}

            ib = fix_bounding_box(data['meta']['original_image'], ib)

            if intersect_area(bb,ib) > get_bounding_box_area(bb)/2 >4 or\
               intersect_area(bb,ib) > get_bounding_box_area(ib)/2 >4:
                #this block matches
                res_blocks.append(entry)
        if len(res_blocks) > 0:
            if "filters" not in data['meta']:
                data['meta']['filters'] = list()
            data['meta']['filters'].append({"type": "text",
                                            "lines": [x['val_s'] for x in res_blocks],
                                            "full_text": bb_modified_text,
                                            "org_text": bb_org_text})
        """

############ IMAGE TESTERS (OLD) #################

class PipelineDiffImage(PipelineAction):
    @classmethod
    def diff_image(cls, data, ops):
        test_image = data['image'].convert("RGBA")
        #index_image = load_image(data['block']['index_image'])
        index_image = load_image(cls.resolve_var(ops['image'], data))
        
        if data['block'].get("text_colors"):
            pass#figure this out in a bit....

        im = ImageChops.difference(test_image, index_image).convert("RGBA")
        pix = ImageStat.Stat(im).mean
        threshold = f.get("threshold", 16.0)

        the_sum = (pix[0]**2+pix[1]**2+pix[2]**2)/(threshold**2)

        output = data.copy()
        if the_sum < 1.0 and pix[3] < 128:
            output['match'] = True
            output['l_dist'] = the_sum
        else:
            output['match'] = False
        return [output]

class PipelineGetTextBlocks(PipelineAction):
    @classmethod
    def get_text_blocks(cls, data, ops):
        image_data = data['image']
        text_colors = cls.resolve_var(ops["colors"], data)
        threshold = cls.resolve_var(ops["threshold"], data)
        scale_factor = cls.resolve_var(ops.get("scale_factor"), data)
        kwargs = dict()
        if scale_factor:
            kwargs['scale_factor'] = scale_factor

        boxes = MovingTextAlgorithm.get_text_blocks(image_data, text_colors,
                                                    threshold, **kwargs)
        name = cls.resolve_var(ops.get("name", ""), data)
        #boxes = [[image, {"bounding_box": bounding_box,
        #                  "pixel_count": pixel_count}], ...]

        output = list()
        for image, box in boxes:
            if box['pixel_count'] > threshold:
                d = copy.deepcopy(data)
                d['image'] = image

                if not 'index' in d['meta']:
                    d['meta']['index'] = list()

                i_entry = {
                            'bounding_box': box['bounding_box'],
                            'pixel_count': box['pixel_count'],
                            'text_colors': text_colors,
                            'threshold': threshold,
                            'type': "mov"
                          }
                if name:
                    i_entry['name'] = name
                else:
                    i_entry['name'] = "__"+str(len(d['meta']['index']))
                d['meta']['index'].append(i_entry)
                d['meta']['bounding_box'] = box['bounding_box']
                d['meta']['text_colors'] = text_colors
                d['meta']['threshold'] = threshold
                d['meta']['pixel_count'] = box['pixel_count']
                d['meta']['dont_crop'] = True
                output.append(d)
        return output
 
class PipelineFuzzyDiffImage(PipelineAction):
    @classmethod
    def fuzzy_diff_image(cls, data, ops):
        test_image = data['image']
        index_image = load_image(cls.resolve_var(ops['image'], data))
        threshold = cls.resolve_var(ops.get("threshold",16), data)
        the_sum = MovingTextAlgorithm.chop_difference(index_image, test_image,
                                                  (255,255,255,255), threshold)
        if the_sum >= 1.0 and index_image.height < test_image.height:
            the_sum = MovingTextAlgorithm.chop_difference(index_image, 
                                          test_image.crop((0,0, test_image.width,
                                                                index_image.height)),
                                          (255,255,255,255), threshold)

        if the_sum >= 1.0 and index_image.height < test_image.height:
            the_sum = MovingTextAlgorithm.chop_difference(index_image,
                                          test_image.crop((0, test_image.height-index_image.height,
                                                           test_image.width, test_image.height)),
                                          (255,255,255,255), threshold)
        output = data
        if the_sum < 1.0:
            #is a match!
            output['match'] = True
            output['l_dist'] = the_sum
        else:
            output['match'] = False
        return [output]


class PipelineDiffTextLines(PipelineAction):
    @classmethod
    def diff_text_lines(cls, data, ops):
        #compare data['block'] (shortlist) to
        #        data['meta']['index']
        #        data['block']['index_ocr_text'] = full ocr text to compare for the block
        output = data.copy()
        f_boxes = list()
        common_errors = data['meta']['common_errors']
        sub_chars = [x+"=" for x in data['meta'].get("subs", {}).get("sub_chars", [])]
        sub_placeholder = data['meta'].get("subs", {}).get("sub_placeholder")

        f_dists = list()
        for entry in data['block']['index_ocr_text']:
            text = entry['text']
            found = False
            for check in data['meta']['index']:
                for val in check['values']:
                    miss = data['meta'].get("miss", [1,2])
                    miss = get_miss(miss, text)

                    subs = data['meta'].get("subs", {}).get("sub_chars", [])
                    match, dist = is_string_similar(val['text'], 
                                         ocr_fix_text(text, common_errors+subs),
                                         miss=miss)
                    if match:
                        f_boxes.append(val['box'])
                        f_dists.append(dist)
                        found = True
                        print ['t', dist, text]
                        break
                if found:
                    break

            if found == False:
                output['match'] = False
                break
        else:
            box = [min([b[0] for b in f_boxes]), min([b[1] for b in f_boxes]),
                   max([b[2] for b in f_boxes]), max([b[3] for b in f_boxes])]
             
            data['block']['bounding_box'] = {"x1": box[0], "y1": box[1],
                                             "x2": box[2], "y2": box[3]}
            output['match'] = True
            output['l_dist'] = sum(f_dists)
        return [output]




class PipelineDiffTextDetect(PipelineAction):
    @classmethod
    def diff_text_detect(cls, data, ops):
        output = data.copy()
        output['match'] = True
        return [output]

        f_boxes = list()
        common_errors = data['meta']['common_errors']
        sub_chars = [x+"=" for x in data['meta'].get("subs", {}).get("sub_chars", [])]
        sub_placeholder = data['meta'].get("subs", {}).get("sub_placeholder")

        f_dists = list()
        for entry in data['block']['index_ocr_text']:
            text = entry['text']
            found = False
            for check in data['meta']['index']:
                for val in check['values']:
                    miss = data['meta'].get("miss", [1,2])
                    miss = get_miss(miss, text)

                    subs = data['meta'].get("subs", {}).get("sub_chars", [])
                    match, dist = is_string_similar(val['text'], 
                                         ocr_fix_text(text, common_errors+subs),
                                         miss=miss)
                    if match:
                        f_boxes.append(val['box'])
                        f_dists.append(dist)
                        found = True
                        print ['t', dist, text]
                        break
                if found:
                    break

            if found == False:
                output['match'] = False
                break
        else:
            box = [min([b[0] for b in f_boxes]), min([b[1] for b in f_boxes]),
                   max([b[2] for b in f_boxes]), max([b[3] for b in f_boxes])]
             
            data['block']['bounding_box'] = {"x1": box[0], "y1": box[1],
                                             "x2": box[2], "y2": box[3]}
            output['match'] = True
            output['l_dist'] = sum(f_dists)
        return [output]





class PipelineExpandColor(PipelineAction):
    @classmethod
    def expand_horizontal(cls, data, ops):
        image = data['image']
        base_color = cls.resolve_var(ops['base'], data)
        target_color = cls.resolve_var(ops['target'], data) 
        if not target_color:
            target_color = "FFFFFF"
        image = expand_horizontal(image, base_color, target_color)
        return [{"image": image, "meta": data['meta']}]

    @classmethod
    def expand_vertical(cls, data, ops):
        image = data['image']
        base_color = cls.resolve_var(ops['base'], data)
        target_color = cls.resolve_var(ops['target'], data) 
        if not target_color:
            target_color = "FFFFFF"
        image = expand_vertical(image, base_color, target_color)
        return [{"image": image, "meta": data['meta']}]

    @classmethod
    def expand_color(cls, data, ops):
        image = data['image']
        base_color = cls.resolve_var(ops['base'], data)
        target_color = cls.resolve_var(ops['target'], data) 
        if not target_color:
            target_color = "FFFFFF"
        image = expand_horizontal(image, base_color, target_color)
        image = expand_vertical(image, base_color, target_color)
        return [{"image": image, "meta": data['meta']}]


class PipelineRectangle(PipelineAction):
    @classmethod
    def rectangle(cls, data, options):
        boundary_box = cls.resolve_var(ops['bounding_box'], data)
        color = cls.resolve_var(ops['color'], data)
        image = draw_solid_box(image, color, boundary_box)
        return [{"image": image, "meta": data['meta']}]


##################################

###############################

def is_string_similar_inside(str1, str2):
    #is string 2 inside str1?
    vals1 = dict()
    vals2 = dict()
    for k in str1.lower().replace(" ", ""):
        vals1[k] = vals1.get(k,0)+1
    for k in str2.lower().replace(" ", ""):
        vals2[k] = vals2.get(k,0)+1

    succ_count = 0
    fail_count = 0
    for key in vals2.keys():
        if vals2.get(key,0) <= vals1.get(key,0):
            succ_count +=1
        else:
            fail_count +=1
    if succ_count >= fail_count or (fail_count < 2 and len(str2) > 1):
        return True
    return False 

def is_string_similar_inside2(str1, str2):
    str1 = str1.lower().replace(" ", "")
    str2 = str2.lower().replace(" ", "")
    if is_string_similar_inside(str1, str2):
        for text in str2.split("\n"):
            for stext in str1.split("\n"):
                if levenshtein(text, stext, miss=miss):
                    break
            else:
                #no texts matched, so this part of str2 is not in str1
                #so these strings don't match
                break
            #this text did have a match, so continue for now.
        else:
            #all matches, so return True
            return True
    return False

def is_string_similar(str1, str2, miss=2, subs=[]):
    #return levenshtein_shortcircuit(str1, str2, miss)
    str1 = str1.lower().replace(" ", "")
    str2 = str2.lower().replace(" ", "")
    for char in subs:
        str1 = str1.replace(char, "")
        str2 = str2.replace(char, "")
    match, dist = levenshtein_shortcircuit_dist(str1, str2, miss)
    return match, dist
   
def is_string_simple_similar(str1,str2, miss):
    if abs(len(str1)-len(str2)) > miss:
        return False
    return True

    s1 = dict()
    s2 = dict()
    for c in str1:
        s1[c] = s1.get(c,0)+1
    for c in str2:
        s2[c] = s2.get(c,0)+1

    diss = 0
    for c in s1:
        diss+=abs(s1[c]-s2.get(c,0))
    for c in s2:
        diss+=abs(s2[c]-s1.get(c,0))
    if diss < miss*4:
        return True
    return False

def main():
    import pymongo
    db = pymongo.Connection("localhost", 27017).ztrans
    user_id = db.ocr_images.find_one({"game_id": ObjectId("5b67a518f28a772314c422af")})['user_id']

    q = {"user_id": {"$ne": user_id}}
    t = db.ocr_images.find(q).count()
    cursor = db.ocr_images.find(q)
    
    l = list()
    r = None
    for i, doc in enumerate(cursor):
        image_data = doc.get("image_data")
        image = load_image(image_data)
        
        data = {"image": image, "meta": {}}
        opts = dict()
        res = PipelineTextDetect.text_detect_index(data, opts)
        import pdb
        pdb.set_trace()
        if not r:
            r = res[0]
        l.append(res)
        print [i, t]
        if i > 10:
            break
        
    time.sleep(1)
    for k in range(10):
      t = time.time()
      c = 0
      for i, cd in enumerate(l):
        for d in cd:
            s = 0
            import pdb
            pdb.set_trace()
            for j in range(7):
                s+=abs(r['hu'][j]-d['hu'][j])
            if s < 0.01:
                c+=1
      print [c, k, time.time()-t]
      import pdb
      pdb.set_trace()

if __name__=='__main__':
    main()
