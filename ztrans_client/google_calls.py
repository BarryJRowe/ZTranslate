import base64
import json
import httplib
import pprint
import re
import HTMLParser

def encode_image(img_file):
    image_content = open(img_file).read()
    return base64.b64encode(image_content)

def manual_ocr(img_file, source_lang=None):
    data = encode_image(img_file)
    doc = {"requests": [
            {"image": {"content": data},
             "features": [
               {"type": "DOCUMENT_TEXT_DETECTION"}
             ]            
            }
           ]
          }

    if source_lang:
        doc['requests'][0]['imageContext'] = {"languageHints": [source_lang]}
    body = json.dumps(doc)
    url = "https://vision.googleapis.com/v1p1beta1/images:annotate?key="
    uri = "/v1p1beta1/images:annotate?key="

    conn = httplib.HTTPSConnection("vision.googleapis.com", 443)
    conn.request("POST", uri, body)
    rep = conn.getresponse()
    output = json.loads(rep.read())
    return output['responses'][0]['fullTextAnnotation']
    
def manual_google_translate(strings, target_lang):
    conn = httplib.HTTPSConnection("translation.googleapis.com", 443)
    uri = "/language/translate/v2?key="
    uri+= ""
    body = '{\n'
    for string in strings:
        body += "'q': "+json.dumps(string)+",\n"
    body += "'target': '"+target_lang+"'\n"
    body +='}'

    conn.request("POST", uri, body)
    rep = conn.getresponse()
    output = json.loads(rep.read())
    #import pdb
    #pdb.set_trace()
    for x in output['data']['translations']:
        x['translatedText'] = HTMLParser.HTMLParser().unescape(x['translatedText'])
    #&quot
    return output



def main():
    path = "./default.png"
    path = "./japanese2.jpg"
    #path = "./jp_example.png"
    #detect_document(path)
    data = manual_ocr(path)
    #pprint.pprint(data['responses'][0]['fullTextAnnotation'])
    manual_google_translate([u'DEBI\n\u017fzobiilica?\nliicaid. Sibirmen\n\xc8RAKAT .\n'])
    #import pdb
    #pdb.set_trace()

if __name__=="__main__":
    main()

