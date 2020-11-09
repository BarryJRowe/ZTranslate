import colorsys
import copy
import time
from PIL import Image, ImageEnhance, ImageChops, ImageDraw, ImageStat

from bson.objectid import ObjectId
import imaging
from imaging import drawTextBox
import ocr_tools
from util import load_image, fix_bounding_box,\
          image_to_string, chop_to_box,\
          get_color_counts,\
          get_color_counts_simple,\
          intersect_area,\
          get_bounding_box_area,\
          convert_to_absolute_box, reduce_to_colors,\
          reduce_to_multi_color, segfill,\
          get_best_text_color, tint_image,\
          expand_horizontal, expand_vertical,\
          draw_solid_box
from moving_text_algorithm import MovingTextAlgorithm
from text_tools import levenshtein, levenshtein_shortcircuit,\
                       substitute_text,levenshtein_shortcircuit_dist


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
                         index_name=None, package=None):
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
            return cls.do_block_post_processing(org_image, data_in, target_lang)
        else:
            #this is the same as the above, but here to emphasize the 
            #difference that target_lang=None doesa
            return cls.do_block_post_processing(org_image, data_in, None)

    @classmethod
    def do_block_post_processing(cls, org_image, data, target_lang):
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
                        entry['block']['translation'][target_lang]:
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
                   
                    if target_lang in entry['block'].get("drawn_text", {}):
                        offset = [entry['block']['bounding_box']['x1'],
                                  entry['block']['bounding_box']['y1'],
                                 ]
                        i_img = entry['block']['drawn_text'][target_lang]
                        i_img = load_image(i_img)
                        if tinge:
                            i_img = tint_image(i_img, tinge)

                        org_image.paste(i_img, offset)
                    else:
                        tb = entry['block']['bounding_box']
                        HMAX=16

                        font_name = "RobotoCondensed-Bold.ttf"     
                        font_size = None
                        font_color = None  
                        special_json = entry['block'].get('special_json', {})
                        for i, atrb in enumerate(special_json.get("box_attributes", [])):
                            if i == int(entry['block']['block_id'].split("_")[1]):
                                font_size = atrb.get("font size")
                                font_color = atrb.get("font color")

                        if tinge:
                            font_color = tinge
                        image = Image.new("RGBA", (tb['x2']-tb['x1'],
                                          max(tb['y2']-tb['y1'], HMAX+1)))
                        draw = ImageDraw.Draw(image)
                     
                        translation = entry['block']['translation'][target_lang]
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
                                           font_color=font_color)
                        org_image.paste(image, [tb['x1'], tb['y1']])


                
        #org_image.show()
        return org_image, data

    @classmethod
    def process_stage(cls, stage, data, user_id=None, game_id=None, 
                      index_name=None, package=None):
        output = list()
        options = stage.get('options', {})
        if stage['action'] == "resize":
            out = PipelineResize.resize(data, options)
            output.extend(out)
        elif stage['action'] == "crop":
            out = PipelineCrop.crop(data, options)
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
            out = PipelineFindByIndex.find_by_index(data, options, user_id,
                                                    game_id, index_name, package=package)
            output.extend(out)
        elif stage['action'] == "expandShortlist":
            short_list = data['short_list']
            out = list()
            for short_block in short_list:
                out.append({"image": data['image'].copy(), 
                            "meta": copy.deepcopy(data['meta']),
                            "block": short_block
                           })
            output.extend(out)
        elif stage['action'] == "diffImage":
            out = PipelineDiffImage.diff_image(data, options)
            output.extend(out)
        elif stage['action'] == "fuzzyDiffImage":
            out = PipelineFuzzyDiffImage.fuzzy_diff_image(data, options)
            output.extend(out)
        elif stage['action'] == "diffTextLines":
            out = PipelineDiffTextLines.diff_text_lines(data, options)
            output.extend(out)
        elif stage['action'] == "getTextBlocks":
            out = PipelineGetTextBlocks.get_text_blocks(data, options)
            output.extend(out)
        elif stage['action'] == "indexOCR":
            out = PipelineIndexOCR.ocr_index(data, options)
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
                                                   index_name=index_name)
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
        
        new_image = data['image'].crop([x1, y1, x2, y2])
        if 'color' in ops:
            pass#TODO
        data['image'] = new_image
        data['meta']['bounding_box'] = {"x1": x1, "x2": x2, "y1": y1, "y2": y2}
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
        name = ops.get("name", "__"+str(len(data['meta']['index'])))
        data['meta']['index'].append({"type": "hsv", 
                                      "values": {"h": h, "s":s, "v": v},
                                      "name": name, 
                                      "tolerance": ops['tolerance']})
        return [data]

class PipelineIndexPixelCount(PipelineAction):
    @classmethod
    def index_pixel_count(cls, data, ops):
        #######TODO
        pixel_count = data['meta']['pixel_count']
        name = ops.get("name", "__"+str(len(data['meta']['index'])))
        data['meta']['index'].append({"type": "pixel_count", 
                                      "values": {"pixel_count": pixel_count},
                                      "name": name, 
                                      "tolerance": ops['tolerance']})
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

        boxes = ocr_tools.tess_helper(data['image'], cls.resolve_var(ops['lang'], data),
                                      cls.resolve_var(ops.get('mode'), data),
                                      min_pixels)
        print boxes
        print ['--', miss]
        text_colors = cls.resolve_var(ops.get("text_colors", []), data)

        if 'index' not in data['meta']:
            data['meta']['index'] = list()
        name = ops.get("name", "__"+str(len(data['meta']['index'])))
        output = list()

        new_data = copy.deepcopy(data)
        data = new_data
        data['meta']['containing'] = True
        data['meta']['miss'] = miss
        data['meta']['index'].append({"type": "ocr",
                                      "values": [{"text": ocr_fix_text(t[0],common_errors_subs),
                                                 "text_source": t[0],
                                                 "box": t[1]} for t in boxes],
                                      "name": name,
                                     })
        data['meta']['common_errors'] = common_errors
        data['meta']['subs'] = subs
        data['meta']['text_colors'] = text_colors

        return [data]

########## INDEX FUNCTION ################

class PipelineFindByIndex(PipelineAction):
    @classmethod
    def find_by_index(cls, data, ops, user_id, game_id, index_name, package):
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

        #indexes = [{"type": "hsv", "values": {"h": 0, "s": 0, "v": 0},
        #            "name": "__0", "tolerance": 0.05},
        #           {"type": "pixel_count", "values": {"count": 1150},
        #            "name": "__1", "tolerance": 3}]


############ IMAGE TESTERS #################

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
        threshold = ops.get("threshold", 16.0)

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
            #at this point we have a match, so modify the image and change
            #the output and stuff.
            #bb = data['block']['bounding_box']
            
            #box = [min([b[0] for b in f_boxes]), min([b[1] for b in f_boxes])]
            #box.append(box[0]+bb['x2']-bb['x1'])
            #box.append(box[1]+bb['y2']-bb['y1'])

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
        #image.show()
        image = expand_horizontal(image, base_color, target_color)
        return [{"image": image, "meta": data['meta']}]

    @classmethod
    def expand_vertical(cls, data, ops):
        image = data['image']
        base_color = cls.resolve_var(ops['base'], data)
        target_color = cls.resolve_var(ops['target'], data) 
        if not target_color:
            target_color = "FFFFFF"
        #image.show()
        image = expand_vertical(image, base_color, target_color)
        return [{"image": image, "meta": data['meta']}]

    @classmethod
    def expand_color(cls, data, ops):
        image = data['image']
        base_color = cls.resolve_var(ops['base'], data)
        target_color = cls.resolve_var(ops['target'], data) 
        if not target_color:
            target_color = "FFFFFF"
        #image.show()
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


