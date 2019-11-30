import json
import google_calls

class OCRClient:
    @classmethod
    def call_ocr(cls, image_filename, source_lang=None, target_lang='en'):
        data = google_calls.manual_ocr(image_filename, source_lang)
        data = cls.process_output(data)
        data = cls.translate_output(data, target_lang)
        #data = cls.mocked_call(image_filename)
        return data

    @classmethod
    def mocked_call_api(cls, image_filename):
        #currently mocked out instead of done correctly
        data = json.loads(open("./mocks/mock.json").read())
        return data

    @classmethod
    def mocked_call(cls, image_filename):
        data = cls.mocked_call_api(image_filename)
        return cls.process_output(data)

    @classmethod
    def process_output(cls, data):
        results = {"blocks": []}
        for page in data.get("pages", []):
            for block in page.get("blocks", []):
                this_block = {"source_text": [], "language": "", "translation": "", 
                              "bounding_box": {"x": 0, "y": 0, "w": 0, "h": 0}, 
                              "confidence": block.get("confidence")}
                bb = block.get("boundingBox", {}).get("vertices", [])
                this_block['bounding_box']['x'] = bb[0]['x']
                this_block['bounding_box']['y'] = bb[0]['y']
                this_block['bounding_box']['w'] = bb[2]['x'] - bb[0]['x']
                this_block['bounding_box']['h'] = bb[2]['y'] - bb[0]['y']
                
                for paragraph in block.get("paragraphs", []):
                    for word in paragraph.get("words", []):
                        for symbol in word.get("symbols", []):
                            if (symbol['text'] == "." and this_block['source_text']\
                                                      and this_block['source_text'][-1] == " "):
                                this_block['source_text'][-1] = "."
                            else:
                                this_block['source_text'].append(symbol['text'])
                        this_block['source_text'].append(" ")
                    this_block['source_text'].append("\n")
                this_block['source_text'] = "".join(this_block['source_text']).replace("\n", " ").strip()
                results['blocks'].append(this_block)
        return results
    
    @classmethod
    def translate_output(cls, data, target_lang):
        translates = google_calls.manual_google_translate([x['source_text'] for x in data['blocks']], target_lang)
        for i, block in enumerate(data['blocks']):
            block['translation'] = translates['data']['translations'][i]['translatedText']
            block['language'] = translates['data']['translations'][i]['detectedSourceLanguage']

        return data

def main():
    OCRClient.mocked_call("hw_16.png")
   
if __name__=="__main__":
    main()

