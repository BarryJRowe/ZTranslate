import time
from PIL import Image
from pipeline_service import OCRPipeline

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
    import package_loader
    package = package_loader.PackageObject("./packages/hw.1.01.ztp")
    image = Image.open("d.png")
    out,data = PipelineGeneralService.run_ocr_pipeline(image, package, "en")
    import pdb
    pdb.set_trace()
    

if __name__=='__main__':
    main()