import httplib
import json
import base64
import io
import config
import time
from PIL import Image

class ServerClient:
    @classmethod
    def call_server(cls, image_object, source_lang, target_lang,
                         fast, free, out=None):
        if fast:
            mode = "fast"
        elif free:
            mode = "free"
        else:
            mode = "normal"

        if out is None:
            out = ['image', 'sound']

        if mode == "fast":
            #speeds up upload by 4x, but inexact pixels
            image_object = image_object.convert("P", palette=Image.ADAPTIVE)
        else:
            #speeds up upload by %33 by removing alpha.
            image_object = image_object.convert("RGB")
        
        image_byte_array = io.BytesIO()
        image_object.save(image_byte_array, format='PNG')
        image_data = image_byte_array.getvalue()

        image_data = base64.b64encode(image_data)
        print ['size', len(image_data)]
        if fast:
            mode = "fast"
        elif free:
            mode = "free"
        else:
            mode = "normal"
         

        body = {
            "timestamp": "",
            "api_key": config.user_api_key,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "image": image_data,
            "mode": mode,
            "output": out
        }
        print '-------------------'
        print [fast, mode]
        print [[source_lang], [target_lang]]
        t_time = time.time()
        
        #conn = httplib.HTTPSConnection(server_host, server_port)
        try:
            conn = httplib.HTTPSConnection(config.server_host, config.server_port)
            conn.request("POST", "/ocr", json.dumps(body))
            rep = conn.getresponse()
            d = rep.read()
            output = json.loads(d)
            print ['Took: ', time.time()-t_time]

            return output
        except:
            import traceback
            traceback.print_exc()
            print [d, body]
            raise

    @classmethod
    def get_quota(cls):
        body = {
            "api_key": config.user_api_key,
        }
        print "CALLED QUOTA"
        #print body
        try:
            conn = httplib.HTTPSConnection(config.server_host, config.server_port)
            conn.request("POST", "/quota", json.dumps(body))
            rep = conn.getresponse()
            d = rep.read()
            output = json.loads(d)
            print output
            return output
        except:
            print "Quota call failed... invalid key?  Update config.json file."
            return dict()
        
