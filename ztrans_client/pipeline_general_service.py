import time
from PIL import Image
from ztrans_common.pipeline_service import OCRPipeline
from ztrans_common.file_package import FilePackageDirectDAO

class PipelineGeneralService:
    @classmethod
    def run_ocr_pipeline(cls, image, package, target_lang):
        #get pipelines..
        indexes = package.get_game_indexes()
        the_image = image

        out_data = list()
        t = time.time()
        for index in indexes:
            metadata = dict()
            shortlist = list()
            index_name = index['name']
            if package.is_index_disabled(index_name):
                continue

            s = time.time()
            out, data = OCRPipeline.process_pipeline(index['ocr'],
                                                     the_image, metadata, shortlist,
                                                     target_lang=target_lang,
                                                     package=package,
                                                     index_name=index_name)
            print [index_name, time.time()-s]
            the_image=out
            out_data.extend(data)
        print ['f-time', time.time()-t] 
        return the_image, out_data



def main():
    user_id = ""
    game_id = ""
    font = "./fonts/Roboto-Bold.ttf"

    package = FilePackageDirectDAO(user_id, game_id, font, "/home/barry/Downloads/bbb.ztp")
    image1 = Image.open("/home/barry/Downloads/silber_test1.png")
    image2 = Image.open("/home/barry/Downloads/silber_test2.png")

    out, data = PipelineGeneralService.run_ocr_pipeline(image1, package, "en")
    import pdb
    pdb.set_trace()
    out, data = PipelineGeneralService.run_ocr_pipeline(image2, package, "en")
    import pdb
    pdb.set_trace()
   

if __name__=='__main__':
    main()
