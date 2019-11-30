from ztrans_common.image_util import general_index, load_image,\
                                     fix_bounding_box, image_to_string,\
                                     chop_to_box
from PIL import Image, ImageDraw, ImageChops
from bson.objectid import ObjectId

class MovingTextAlgorithm:
    @classmethod
    def get_text_blocks(cls, image_data, text_colors=("FFFFFF",), 
                        threshold=16, scale_factor=10):
        output = list()
        img_org = load_image(image_data)
        img = img_org.convert("P", palette=Image.ADAPTIVE, colors=256)
        p = img.getpalette()

        if not text_colors:
            text_colors = ["FFFFFF"]

        tcs = list()
        if text_colors:
            for text_color in text_colors:
                tc = (int(text_color[0:2], 16),
                      int(text_color[2:4], 16),
                      int(text_color[4:6], 16))
                tcs.append(tc)

        new_palette = list()
        for i in range(256):
            r = p[3*i]
            g = p[3*i+1]
            b = p[3*i+2]
            vals = list()
            for tc in tcs:
                rr = r-tc[0]
                gg = g-tc[1]
                bb = b-tc[2]
                vals.append(rr**2+gg**2+bb**2)

            if min(vals) <= threshold**2:
                new_palette.extend([255,255,255])
            else:
                new_palette.extend([0,0,0])
        img.putpalette(new_palette)

        width = img.width
        height = img.height
        bw = width/scale_factor
        bh = height/scale_factor
        t=img.convert("RGBA").resize((bw,bh), resample=Image.BILINEAR)

        checked = [[0 for y in range(bh)] for x in range(bw)]
        for i in range(bw):
            for j in range(bh):
                if t.getpixel((i,j)) != (0,0,0,255) and checked[i][j] == 0:
                    s_pix = t.getpixel((i,j))[0]
                    min_x, min_y = i,j
                    max_x, max_y = i+1,j+1
                    if j > 0 and i< bw-1 and t.getpixel((i+1, j-1)) != (0,0,0,255):
                        #in the case of rounded corner, the above loop could
                        #miss the first pixel line
                        min_y = j-1
                    for k in range(i+1,bw):
                        if t.getpixel((k,j)) == (0,0,0,255) and\
                               (k >= bw-1 or t.getpixel((k+1, j)) == (0,0,0,255)):
                            max_x = min(bw, k+1)
                            break
                    for l in range(j+1, bh):
                        if t.getpixel((k-1,l)) == (0,0,0,255) and\
                               (l >= bh-1 or t.getpixel((k-1, l+1)) == (0,0,0,255)):
                            max_y = l+1
                            break
                    if max_y>j+1:
                        for k2 in range(max_x, bw):
                            if t.getpixel((k2,l)) != (0,0,0,255) or \
                                    (l>0 and t.getpixel((k2, l-1))):
                                max_x = k2+1
                                break

                    #box to check: min_x, min_y, max_x, max_y
                    x1,y1,x2,y2= min_x*scale_factor, min_y*scale_factor,\
                                 max_x*scale_factor, max_y*scale_factor
                    #x1,y1,x2,y2 = [0,0,100,100]
                    f=img.crop((x1,y1,x2,y2)).convert("RGBA")
                    #crop again by min_x and min_y of white values,
                    #              max_x, max_y of white values
                    f_width = f.width
                    f_height = f.height
                    min_width = 0
                    min_height = 0
                    max_width = 1
                    max_height = 1
                    for l in range(f_height):
                        for k in range(f_width):
                            if f.getpixel((k,l)) == (255,255,255,255):
                                min_height = l
                                break
                        else:
                            continue
                        break
                    for k in range(f_width):
                        for l in range(f_height):
                            if f.getpixel((k,l)) == (255,255,255,255):
                                min_width = k
                                break
                        else:
                            continue
                        break
                    for l in range(1,f_height):
                        for k in range(1,f_width):
                            if f.getpixel((f_width-k,f_height-l)) == (255,255,255,255):
                                max_height = f_height-l+1
                                break
                        else:
                            continue
                        break
                    for k in range(1,f_width):
                        for l in range(1,f_height):
                            if f.getpixel((f_width-k,f_height-l)) == (255,255,255,255):
                                max_width = f_width-k+1
                                break
                        else:
                            continue
                        break

                    g = f.crop((min_width,min_height, max_width, max_height))

                    bounding_box = {"x1": min_width+x1, "y1": min_height+y1,
                                    "x2": min_width+x1+g.width, "y2": min_height+y1+g.height}
                    pixel_count = 1
                    for c in g.getcolors():
                        if c[1] == (255,255,255,255):
                            pixel_count = c[0]
                    output.append([g, {"bounding_box": bounding_box, 
                                       "pixel_count": pixel_count}])

                    for k in range(min_x, max_x):
                        for l in range(min_y, max_y):
                            checked[k][l] = 1
        return output

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
        short_list = package.find_data_by_values("mov", hsv, pc)
        return short_list
 
    @classmethod
    def get_center(cls, image, color):
        n = 0
        avg_x = 0
        avg_y = 0
        threshold = 16.0
        for i, pixel in enumerate(image.getdata()):
            x = i%image.width
            y = int(i/image.width)
            if (pixel[0]-color[0])**2+(pixel[1]-color[1])**2+\
               (pixel[2]-color[2])**2 < threshold**2:
                avg_x += x
                avg_y += y
                n+=1
        if n == 0:
            return [image.width/2, image.height/2]
        return [avg_x/n, avg_y/n]

    @classmethod
    def chop_difference(cls, tb, mi, color, threshold):
        tb_c = cls.get_center(tb, color)
        mi_c = cls.get_center(mi, color)

        #find the required size of the new embedding image:
        tb_c_w = max(tb.width-tb_c[0], tb_c[0])*2
        tb_c_h = max(tb.height-tb_c[1], tb_c[1])*2

        mi_c_w = max(mi.width-mi_c[0], mi_c[0])*2
        mi_c_h = max(mi.height-mi_c[1], mi_c[1])*2

        new_w = max(tb_c_w, mi_c_w)+2
        new_h = max(tb_c_h, mi_c_h)+2

        min_sum = 1000000000000000
        offs = [[0,0], [1,0], [-1, 0], [0, -1], [0, 1], 
                [-1, -1], [-1, 1], [1, -1], [1,1]]
        #offs = [[0,0]]
        for off in offs:
            new_mi = Image.new("RGBA", (new_w, new_h), color=(0,0,0,255))
            new_tb = Image.new("RGBA", (new_w, new_h), color=(0,0,0,255))

            #center the original images into this image:
            mi_px = new_w/2 - mi_c[0]
            mi_py = new_h/2 - mi_c[1]
            new_mi.paste(mi, (mi_px+off[0], mi_py+off[1]))

            tb_px = new_w/2 - tb_c[0]
            tb_py = new_h/2 - tb_c[1]
            new_tb.paste(tb, (tb_px, tb_py))
            new_tb1 = new_tb.convert("RGB").resize((new_w/2, new_h/2), Image.BILINEAR)
            new_mi1 = new_mi.convert("RGB").resize((new_w/2, new_h/2), Image.BILINEAR)

            im = ImageChops.difference(new_tb1, new_mi1).convert("RGBA")

            pix = im.convert("RGB").resize((1,1), Image.BILINEAR)
            pix = pix.getpixel((0,0))
            #print pix
            rr = pix[0]**2
            gg = pix[1]**2
            bb = pix[2]**2
            the_sum = (rr+gg+bb)/(threshold**2)
            if the_sum < min_sum:
                min_sum = the_sum
        return min_sum
 
      
    @classmethod
    def test_image_text_via_index(cls, index, image_object):
        mi = image_object
        tb = load_image(index['index_image'])
        threshold = 16

        if mi.width <=0 or mi.height<=0:
            return False

        the_sum = cls.chop_difference(tb, mi, (255,255,255,255), threshold)
        if the_sum >= 1.0 and tb.height < mi.height:
            the_sum = cls.chop_difference(tb, mi.crop((0,0, tb.width, tb.height)),
                                          (255,255,255,255), threshold)
        if the_sum >= 1.0 and tb.height < mi.height:
            the_sum = cls.chop_difference(tb, mi.crop((0, mi.height-tb.height, tb.width, mi.height)),
                                          (255,255,255,255), threshold)

        if the_sum < 1.0:# and pix[3] > 128:
            return {"block_reference": index['_id'], "conf": 1.0-the_sum}
        return False


    @classmethod
    def find_matches(cls, image_data, package):
        hsv = general_index(image_data)
        threshold = 32
        text_colors = cls.get_index_text_colors(package)
        text_blocks = cls.get_text_blocks(image_data, text_colors, threshold)
        blocks = list()
        original_image = load_image(image_data)
        draw = ImageDraw.Draw(original_image)

        found_block_ids = dict()
        for text_image, text_data in text_blocks:
            index = {"h": hsv[0], "s": hsv[1], "v": hsv[2]}
            index['type'] = 'hsv_mov'
            index['pixel_count'] = text_data['pixel_count']
            short_list = cls.find_blocks_by_index(index, package)
            
            for index_entry in short_list:
                is_match = cls.test_image_text_via_index(index_entry, 
                                                         text_image)
                
                if is_match:
                    index_entry['bounding_box'] = text_data['bounding_box']
                    blocks.append(index_entry)
                    bb = text_data['bounding_box']
                    draw.rectangle([bb['x1'], bb['y1'], bb['x2'], bb['y2']],
                                   fill=(0,0,0,0))
                    break
        return {"blocks": blocks, "image": image_to_string(original_image)}
                
    @classmethod
    def get_index_text_colors(cls, package):
        doc = package.get_meta_data("moving_text_colors.json")[0]
        return doc['text_colors'].keys()


def main():
    image_mi = Image.open("test_mi.png")
    image_tb = Image.open("test_tb.png")
    MovingTextAlgorithm.chop_difference(image_tb, image_mi, (255,255,255,255), 16)

if __name__=="__main__":
    main()
