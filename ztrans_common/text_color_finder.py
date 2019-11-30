from PIL import Image, ImageDraw
from ztrans_common.image_util import load_image, reduce_to_multi_color,\
                                     color_byte_to_hex, color_hex_to_byte,\
                                     color_dist, intersect_area
from ztrans_common.opencv_engine import TextFeatureFinder, HuMoments
import pymongo
import time
from bson.objectid import ObjectId

class TextColorFinder:
    @classmethod
    def _near_intersect(cls, bb1, bb2):
        bh1 = (bb1[3]-bb1[1])/2
        bx1 = {"x1": bb1[0], "y1": bb1[1]-bh1,
                "x2": bb1[2], "y2": bb1[3]+bh1}
        bh2 = (bb2[3]-bb2[1])/2
        bx2 = {"x1": bb2[0], "y1": bb2[1]-bh2,
               "x2": bb2[2], "y2": bb2[3]+bh2}
        if intersect_area(bx1, bx2) > 0:
            return True
        return False

    @classmethod
    def find_text_colors(cls, image, threshold=32):
        #find east feature boxes
        #  -find variances for each box
        #  -extend boxes horizontally, and somewhat vertically.
        #  -join together relevent boxes that are "close enough" together.
        colors = TextVarianceFinder.extract_var_text(image)

        #Get the brightest/darkest two colors
        largest = None
        smallest = None
        l_sum = None
        s_sum = None
        for x in colors:
            cb = color_hex_to_byte(x)
            d = sum(x**2 for x in cb)
            if largest is None:
                largest = cb
                smallest = cb
                s_sum = d
                l_sum = d
            elif d > l_sum:
                largest = cb
                l_sum = d
            elif d < s_sum:
                smallest = cb
                s_sum = d
        if smallest is None:
            return {}
        smallest_t = colors[color_byte_to_hex(smallest)]['total']
        largest_t = colors[color_byte_to_hex(largest)]['total']

        largest_type = "text"
        smallest_type = "bg"
        if largest_t > smallest_t:
            largest_type = "bg"
            smallest_type = "text"
          
        likely_text_colors = {largest: [colors[color_byte_to_hex(largest)]['total'], {largest_type:1}], 
                              smallest:[colors[color_byte_to_hex(smallest)]['total'], {smallest_type: 1}]}
        return likely_text_colors      


class TextVarianceFinder:
    @classmethod
    def extract_var_text(cls, image, threshold=32):
        image = image.convert("P", palette=Image.ADAPTIVE, colors=64)

        colors_tolerance = list()   
        colors_single = list()   
        colors_total = dict()
        for tup in image.getcolors():
            colors_total[tup[1]] = tup[0]

        p = image.getpalette()[:3*128]

        it = iter(p)
        p_sing = zip(it,it,it)
                
        var_single = dict()
        var_tolerance = dict()

        for i, h in enumerate(range(image.height)):
            colors_single.append(dict())
            #colors_tolerance.append(dict())

            c = image.crop((0,h, image.width, h+1))
            cl = c.getcolors()
            temp_ = dict()
            for tup in cl:
                temp_[tup[1]] = tup[0]
     
            for tup in cl:
                colors_single[-1][tup[1]] = tup[0]

            for tup in cl:
                this_color = tup[1]
                if i > 1:
                    d = abs(colors_single[i-2].get(tup[1], 0)-colors_single[i-1].get(tup[1],0))
                    if d > 2:
                        if not tup[1] in var_single:  # is the color
                            var_single[tup[1]] = {"n": 0, "s": 0, "s2": 0}
                        var_single[tup[1]]['n']+=1
                        var_single[tup[1]]['s']+= d
                        var_single[tup[1]]['s2']+= d*d
            
        #variances calc
        for var in [var_single]:#, var_tolerance]:
            for p_c in var:
                s = var[p_c]['s']
                s2 = var[p_c]['s2']
                n = var[p_c]['n']
                var[p_c]['var'] = s2/n - s*s/(n**2)
        s_list = sorted(var_single.keys(), key=lambda x: var_single[x]['var'], reverse=True)[:20]
        out_list = list()

        for i, p_c in enumerate(s_list):
            p = p_sing[p_c]
            if i == 0:
                out_list.append([p, p_c])
            else:
                for s,s_c in out_list:
                    if (s[0]-p[0])**2 +(s[1]-p[1])**2 + (s[2]-p[2])**2 < (2*threshold)**2:
                        break
                else:
                    out_list.append([p, p_c])
                    if len(out_list) > 4:
                        break

        output = dict()
        for p, p_c in out_list:
            colorh = color_byte_to_hex((p[0],p[1],p[2]))
            output[colorh] = {"total": colors_total[p_c],
                              "variance": var_single[p_c]['var']}         
        return output














































def simple_show(image, color,threshold=32):
    color_hex = color_byte_to_hex(color)
    im = reduce_to_colors(image.copy(), [color_hex], threshold=threshold)
    im.show()


class TextDetectorAlgo:
    @classmethod
    def detect_text(cls, image, method, options=None):
        if options is None:
            options = dict()

        if method.lower() == "east":
            east = options.get("east", "data/frozen_east_text_detection.pb")
            min_conf = options.get("min_confidence", 0.5)
            width = options.get("width", 320)
            height = options.get("height", 320)
            padding = options.get("padding", 0.0)
            padding = 0.25
            out = TextFeatureFinder.find_features(image, east=east,
                                                  min_confidence=min_conf,
                                                  width=width, height=height,
                                                  padding=padding)
        return out   




class TextFinderAlgo:
    @classmethod
    def text_color_finder(cls, image, threshold=32):
        #algo:
        # -convert to 256 color, or less (128)
        # -SUBCASE #1: solid pixel text.
        #   -go through image horizontally and r ecord color counts per line,
        #    and what colors, and return the single color variance, maybe multi
        #    color variance.  
        #   -Get candiates for text color and surrounding color if any.
        # -SUBCASE #2: drawn, smooth text, with near-solid surrounding colors.
        #   -use opencv east text extractor to get possible boxes.

        #factor out function to compute
        #-use east
        #out_image = TextVarianceFinder.extract_var_text(image)
        out_image = TextEastFinder.extract_east_text(image)
 

class TextEastFinder:
    @classmethod
    def _near_intersect(cls, bb1, bb2):
        bh1 = (bb1[3]-bb1[1])/2
        bx1 = {"x1": bb1[0], "y1": bb1[1]-bh1,
                "x2": bb1[2], "y2": bb1[3]+bh1}
        bh2 = (bb2[3]-bb2[1])/2
        bx2 = {"x1": bb2[0], "y1": bb2[1]-bh2,
               "x2": bb2[2], "y2": bb2[3]+bh2}
        if intersect_area(bx1, bx2) > 0:
            return True
        return False

    @classmethod
    def extract_east_text(cls, image, threshold=32):
        #find east feature boxes
        #  -find variances for each box
        #  -extend boxes horizontally, and somewhat vertically.
        #  -join together relevent boxes that are "close enough" together.
        #as a final step, use ocr on the likely text color
        #  -(example: top management)
        boxes = TextFeatureFinder.find_features(image, padding=0.25)
        new_boxes = list()
        for b in boxes:
            curr_box = b
            i = TextVarianceFinder.extract_var_text(image.crop(b))

            x1,y1,x2,y2 = b
            old_b = x1,y1,x2,y2
            for sign in [(-1,0),(0,1)]:
                while True:
                    w = (y2-y1)*2
                    b2 = [x1+sign[0]*w, y1, x2+sign[1]*w, y2]
                    if b2[0] < 0:
                         b2[0] = 0
                    if b2[2] > image.width-1:
                         b2[2] = image.width-1
                    b2 = tuple(b2)
                    if sign == (-1,0):
                        b3 = (b2[0], b2[1], old_b[0], b2[3])
                    else:
                        b3 = (old_b[2], b2[1], b2[2], b2[3])

                    j = TextVarianceFinder.extract_var_text(image.crop(b3))
                    
                    c = 0
                    c22 = 0
                    for color in i:
                        if color in j:
                            c+=1
                        else:
                            for c2 in j:
                                if color_dist(color_hex_to_byte(color), 
                                              color_hex_to_byte(c2)) < 32**2:
                                    c22+=1
                                    break
                    if (c > 0 or c22+c > 1) and b2!=(x1,y1,x2,y2):
                        x1,y1,x2,y2 = b2
                    else:
                        break
                    old_b = b2
            curr_box = (x1,y1,x2,y2)
            new_boxes.append({"bounding_box": (int(x1),int(y1),
                                               int(x2),int(y2)), 
                              "color": i})
        for b in new_boxes:
            largest = None
            smallest = None
            for x in b['color']:
                cb = color_hex_to_byte(x)
                print x, b['color'][x]
                if largest is None:
                    largest = cb
                    smallest = cb
                elif cb > largest:
                    largest = cb
                elif cb < smallest:
                    smallest = cb
            smallest_t = b['color'][color_byte_to_hex(smallest)]['total']
            largest_t = b['color'][color_byte_to_hex(largest)]['total']

            largest_type = "text"
            smallest_type = "bg"
            if largest_t > smallest_t:
                largest_type = "bg"
                smallest_type = "text"
            
            b['likely_text_colors'] = {largest: [b['color'][color_byte_to_hex(largest)]['total'], {largest_type:1}], 
                                       smallest:[b['color'][color_byte_to_hex(smallest)]['total'], {smallest_type: 1}]}

        boxes = new_boxes

        #now merge boxes together...
        new_boxes = list()
        for i, b1 in enumerate(boxes):
            if 'merged' in b1:
                continue
            for j, b2 in enumerate(boxes):
                bb1 = b1['bounding_box']
                bb2 = b2['bounding_box']
                if j > i and cls._near_intersect(bb1,bb2):
                    merged_colors = b1['color']
                    for key in b2['color']:
                        if key not in merged_colors:
                             merged_colors[key] = b2['color'][key]
                        else:
                             merged_colors[key]['total'] += b2['color'][key]['total']
                             merged_colors[key]['variance']+=b2['color'][key]['variance']
                    
                    for ltc2 in b2['likely_text_colors']:
                        if ltc2 not in b1['likely_text_colors']:
                            b1['likely_text_colors'][ltc2] = b2['likely_text_colors'][ltc2]
                        else:
                            b1['likely_text_colors'][ltc2][0]+=b2['likely_text_colors'][ltc2][0]
                            for key in b2['likely_text_colors'][ltc2][1]:
                                b1['likely_text_colors'][ltc2][1][key] = b1['likely_text_colors'][ltc2][1].get(key, 0)+b2['likely_text_colors'][ltc2][1][key]

                        
                    b1 = {"bounding_box": (min(bb1[0], bb2[0]),
                                           min(bb1[1], bb2[1]),
                                           max(bb1[2], bb2[2]),
                                           max(bb1[3], bb2[3])),
                          "likely_text_colors": b1['likely_text_colors'],
                          "color": merged_colors}
                    b2['merged'] = True
            new_boxes.append(b1)        
                    
        for b in new_boxes:
            d = b['likely_text_colors']
            new_d = dict()
            for c in d:
                for t in new_d:
                    if color_dist(c,t) < 32**2:
                        new_d[t][2].append(c)
                        new_d[t][0]+=d[c][0]
                        for key in d[c][1]:
                            new_d[t][1][key] = new_d[t][1].get(key,0)+d[c][1][key]
                        break
                else:
                    new_d[c] = d[c]
                    new_d[c].append([c])
            new_d2 = dict()
            for key in new_d:
                a = [0,0,0,0]
                n = 0
                for c in new_d[key][2]:
                    n+=1
                    a[0]+=c[0]
                    a[1]+=c[1]
                    a[2]+=c[2]
                    a[3]+=c[3]
                a = (a[0]/n, a[1]/n, a[2]/n, a[3]/n)
                new_d2[a] = new_d[key][:2]
            b['likely_text_colors'] = new_d2
        color_map = list()
        for b in new_boxes:
            for color in b['likely_text_colors']:
                if b['likely_text_colors'][color][1].get("text"):
                    color_map.append([color_byte_to_hex(color), None])
                else:
                    color_map.append([color_byte_to_hex(color), "000000"])
        print color_map
        image = image.convert("P", palette=Image.ADAPTIVE)
        image = reduce_to_multi_color(image, "000000", color_map, 48)
        boxes = new_boxes
        if False or True:
            image2 = image.convert("RGBA")
            draw = ImageDraw.Draw(image2)
            for b in boxes:
                box = b['bounding_box']
                draw.rectangle([(box[0], box[1]),
                                (box[2], box[3])],
                               outline=(255,0,0,255))
            image2.show()
        print 'TTTTTTTTTTTTT'
        for b in boxes:
            print "______________"
            for key in b:
                print key
                print b[key]
        
  
        


class TextVarianceFinder:
    @classmethod
    def extract_var_text(cls, image, threshold=32):
        image = image.convert("P", palette=Image.ADAPTIVE, colors=64)

        colors_tolerance = list()   
        colors_single = list()   
        colors_total = dict()
        for tup in image.getcolors():
            colors_total[tup[1]] = tup[0]

        p = image.getpalette()[:3*128]

        it = iter(p)
        p_sing = zip(it,it,it)
                
        var_single = dict()
        var_tolerance = dict()

        """
        near_colors = dict()
        for i, c1 in enumerate(p_sing):
            for j, c2 in enumerate(p_sing):
                if (c1[0]-c2[0])**2+(c1[1]-c2[1])**2+(c1[2]-c2[2])**2 < threshold**2:
                    if not i in near_colors:
                        near_colors[i] = list()
                    near_colors[i].append(j)
        """
        for i, h in enumerate(range(image.height)):
            colors_single.append(dict())
            #colors_tolerance.append(dict())

            c = image.crop((0,h, image.width, h+1))
            cl = c.getcolors()
            temp_ = dict()
            for tup in cl:
                temp_[tup[1]] = tup[0]
     
            for tup in cl:
                #colors_tolerance[-1][tup[1]] = 0
                colors_single[-1][tup[1]] = tup[0]

                #for near in near_colors[tup[1]]:
                #     colors_tolerance[-1][tup[1]] += temp_.get(near,0)

            for tup in cl:
                this_color = tup[1]
                #nears = near_colors[tup[1]]
                
                if i > 1:
                    """
                    d = abs(colors_tolerance[i-2].get(tup[1], 0)-colors_tolerance[i-1].get(tup[1],0))
                    if d > 20:
                        if not tup[1] in var_tolerance:  # is the color
                            var_tolerance[tup[1]] = {"n": 0, "s": 0, "s2": 0}
                        var_tolerance[tup[1]]['n']+=1
                        var_tolerance[tup[1]]['s']+= d
                        var_tolerance[tup[1]]['s2']+= d*d
                    """
                    d = abs(colors_single[i-2].get(tup[1], 0)-colors_single[i-1].get(tup[1],0))
                    if d > 2:
                        if not tup[1] in var_single:  # is the color
                            var_single[tup[1]] = {"n": 0, "s": 0, "s2": 0}
                        var_single[tup[1]]['n']+=1
                        var_single[tup[1]]['s']+= d
                        var_single[tup[1]]['s2']+= d*d
            
        #variances calc
        for var in [var_single]:#, var_tolerance]:
            for p_c in var:
                s = var[p_c]['s']
                s2 = var[p_c]['s2']
                n = var[p_c]['n']
                var[p_c]['var'] = s2/n - s*s/(n**2)
        """
        print "____________________"
        s_list = sorted(var_tolerance.keys(), key=lambda x: var_tolerance[x]['var'], reverse=True)[:20]
        for p_c in s_list:
            if var_tolerance[p_c]['var'] > var_tolerance[s_list[0]]['var']/4 or True:
                print p[3*p_c], p[3*p_c+1], p[3*p_c+2], "--", colors_total[p_c], "--", var_tolerance[p_c]['var']
        """
        #print "==="
        s_list = sorted(var_single.keys(), key=lambda x: var_single[x]['var'], reverse=True)[:20]
        out_list = list()

        for i, p_c in enumerate(s_list):
            p = p_sing[p_c]
            if i == 0:
                out_list.append([p, p_c])
            else:
                for s,s_c in out_list:
                    if (s[0]-p[0])**2 +(s[1]-p[1])**2 + (s[2]-p[2])**2 < (2*threshold)**2:
                        break
                else:
                    out_list.append([p, p_c])
                    if len(out_list) > 4:
                        break

        output = dict()
        for p, p_c in out_list:
            colorh = color_byte_to_hex((p[0],p[1],p[2]))
            output[colorh] = {"total": colors_total[p_c],
                              "variance": var_single[p_c]['var']}

            #print p[0], p[1], p[2], "--", colors_total[p_c], "--", var_single[p_c]['var']
            
            #im = reduce_to_multi_color(image.copy(), "000000", 
            #                          [[color_byte_to_hex(p_sing[p_c]), 
            #                            "FFFFFF"]],
            #                          threshold)
        return output

def main():
    db = pymongo.Connection("localhost", 27017).ztrans
    for i, doc in enumerate(db.ocr_images.find({"game_id": ObjectId("5bd49ba9f28a770da63c74d4")})):
        image_data = doc.get("image_data")
        image = load_image(image_data)
        image.save("images_test_"+str(i)+".png")
        #image.show()
        TextFinderAlgo.text_color_finder(image,32)

def main2():
    for i in range(18):
        if i < 1:
            continue
        image = Image.open("images_test_"+str(i)+".png")
        #image.show()
        t_time = time.time()
        TextFinderAlgo.text_color_finder(image,32)
        print time.time()-t_time
        import pdb
        pdb.set_trace()


def main3():
    db = pymongo.Connection("localhost", 27017).ztrans
    user_id = db.ocr_images.find_one({"game_id": ObjectId("5b67a518f28a772314c422af")})['user_id']
 
    q = {"user_id": {"$ne": user_id}}
    t = db.ocr_images.find(q).count()
    cursor = db.ocr_images.find(q)

    for i, doc in enumerate(cursor):
        image_data = doc.get("image_data")
        image = load_image(image_data)
        user_id = doc.get("user_id", "")

        #image.save("output/images_test_"+str(user_id)+"_"+str(i)+".png")
        #image.show()
        #b = TextFinderAlgo.text_color_finder(image,32)

        t_time = time.time()
        _id = doc['_id']
        text, image_out = TextDetectorAlgo.detect_text(image, method="east")
        image_out.save("output/images_test_"+str(user_id)+"_"+str(_id)+".png")
        print [i, t, time.time()-t_time]
    print [t/(time.time()-t_time)]

def main4():
    db = pymongo.Connection("localhost", 27017).ztrans
    image1 = db.ocr_images.find_one({"_id": ObjectId("5d205ebf8ac3d962e9364bf2")})['image_data']
    image2 = db.ocr_images.find_one({"_id": ObjectId("5d205f188ac3d962e9364bf6")})['image_data']
    image1 = load_image(image1)
    image2 = load_image(image2)

    text1, image_out1 = TextDetectorAlgo.detect_text(image1, method="east")
    text2, image_out2 = TextDetectorAlgo.detect_text(image2, method="east")

    boxes1 = list()
    boxes2 = list()

    for crop in text1:
        boxes1.append(image1.crop(crop))

    for crop in text2:
        boxes2.append(image2.crop(crop))

    for i, b in enumerate(boxes1):
        d = [x[0] for x in HuMoments.calculate_hu_moments(b)]
        print [i, d]
    for i, b in enumerate(boxes2):
        d = [x[0] for x in HuMoments.calculate_hu_moments(b)]
        print [i, d]
    print "++++++++++++++++++++++++++++++++++++"
    for i,b1 in enumerate(boxes1):
        for j,b2 in enumerate(boxes2):
            d = HuMoments.match_shapes(b1,b2)
            if sum(1 if x < 0.02 else 0 for x in d) >= 2:
                print [i,j,d]
            #print [i,j, HuMoments.match_shapes(b1, b2)]
    image_out1.show()
    image_out2.show()

    import pdb
    pdb.set_trace()
    return



    

if __name__=="__main__":
    main5()

