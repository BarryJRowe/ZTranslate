import imaging
import screen_grab
import ocr_api
import server_client
import config

mock_int = 0

class CallScreenshots:
    @classmethod
    def call_screenshot(cls, image_object, source_lang=None,
                             target_lang='en', fast=None, free=None):
        #return cls.call_screenshot_api_mock(source_lang, target_lang)
        return cls.call_screenshot_api(image_object, source_lang, 
                                       target_lang, fast, free)

    @classmethod
    def call_screenshot_api(cls, image_object=None, source_lang=None,
                                 target_lang='en', fast=None, free=None):
        print 'ooooooooooooooooo'
        print [source_lang, target_lang]
        if image_object == None:
            image_object = screen_grab.ImageGrabber.grab_image()
        #save image to user storage
        print ['grabbed']
        stored_filename = imaging.ImageSaver.save_image(image_object)
        print ['saved']
        result = server_client.ServerClient.call_server(image_object, 
                                                        source_lang, 
                                                        target_lang,
                                                        fast, free,
                                                        out=config.ocr_output)
        quota = result.get("quota", 0)
        print ['called']
        if "image" in config.ocr_output:
            output_image = imaging.ImageModder.write(image_object, result, 
                                                     target_lang)
        if "sound" in config.ocr_output and "sound" in result:
            output_sound = sound.SoundPlayer.play(result['sound'])

        print ['wrote']
        imaging.ImageSaver.save_image(output_image, stored_filename)
        print ['saved again']
        return output_image, quota

    @classmethod
    def call_screenshot_api_mock(cls, source_lang=None, target_lang='en'):
        #-first, get the screen image of the focused image
        #-second, send image to server for OCR and translation
        #-third, replace 

        image_filename = screen_grab.ImageGrabber.grab_image()
        ocr_results = ocr_api.OCRClient.call_ocr(image_filename, 
                                                 source_lang, 
                                                 target_lang)
        output_filename = imaging.ImageModder.write(image_filename, ocr_results)
        return output_filename   
    
    @classmethod
    def call_screenshot_package():
        pass
        

