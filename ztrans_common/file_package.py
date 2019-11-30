import zipfile
import json
#import whoosh.fields
#import whoosh.index

GLOBAL_FONTS_DICT = {}


def load_font(font_name):
    font_obj = ztrans_common.text_draw.load_font(font_name, GLOBAL_FONTS_DICT)
    return font_obj

class FilePackageInterface(object):
    def __init__(self, user_id, game_id, font, filename, *args, **kwargs):
        self.font_object = font
        self.user_id = user_id
        self.game_id = game_id
        self.filename = filename
        self.zipfile = zipfile.ZipFile(filename)
        self._info = json.loads(self.zipfile.read("info.json"))
 
    def is_index_disabled(self, index_name):
        return False

    def get_game_indexes(self):
        return [x for x in self._info['meta']['special_json']['indexes']]

    def get_game_font_object(self, user_id, game_id):
        font_obj = load_font(self._info.get("game_font", "RobotoCondensed-Bold.ttf"))
        return font_obj
    
    def search_index(self, index_type, query, sort=None):
        if sort is None:
            sort = "priority"

        results = self._search_zip(index_type, query, sort)
        seen_blocks = dict()
        output = list()

        for result in results:
            block_id = result['_id']

            if block_id not in seen_blocks:
                seen_blocks[block_id] = self.fetch_from_file(
                        index_type, block_id, "bid")

            output.append({"block": seen_blocks[block_id],
                           "index": result['_source']})

        return output

    def save_index_data(self, index_type, index_values, filters, block_data):
        pass

    def save_data_to_file(self, user_id, game_id):
        pass

    def clear_index_data(self, block_id):
        pass

    def _search_zip(self, index_type, query, sort):
        raise NotImplemented

    def _fetch_from_file(self, index_type, block_id, data_type):
        fname = "algorithms/"+index_type+"/"+data_type+"_"+block_id
        data = self.zipfile.read(name)
        return json.loads(data)
 


class FilePackageDirectDAO(FilePackageInterface):
    def __init__(self, user_id, game_id, font, filename, *args, **kwargs):
        super(FilePackageDirectDAO, self).__init__(user_id, game_id, font,
                                                   filename,
                                                   *args, **kwargs)

    def _search_zip(self, index_type, query, sort):
        #itterate through zip and return valid documents
        output = list()
        #first, limit files to the index_types
        for filename in self.zipfile.namelist():
            import pdb
            pdb.set_trace()


        """
        query = [value_doc1, value_doc2, ...]

        """


"""
class FilePackageWhooshDAO(FilePackageInterface):
    def __init__(self, *args, **kwargs):
        super(FilePackageWhooshDAO,self).__init__(*args, **kwargs)
        self._load_index()

    def _load_index(self):
        #loads the index data from the zipfile into woosh.
        schema = whoosh.fields.Schema(type=fields.ID, val_s=field.TEXT,
                                      val_f=fields.NUMERIC,
                                      val_i=fields.NUMERIC,
                                      num=fields.ID,
                                      sub_id=fields.ID,
                                      subdata_id=fields.ID,
                                      sub_type=fields.ID,
                                     )
        ix = whoosh.index.create_in("temp_dir", schema)
        with ix.writer() as w:
            with w.group():
                w.add_document(type="document")
                w.add_document(type="ocr", val_s="sss")
                #...
        for index_document in whatever:
            pass

    def _search_zip(self, index_tpe, query, sort):
        pass
"""

def main():
    package = FilePackageDirectDAO(user_id="", game_id="", font="", filename="/home/barry/Downloads/aaa.ztp")
    package._search_zip("diff_block", [{"":""}], True)

if __name__=="__main__":
    main()
