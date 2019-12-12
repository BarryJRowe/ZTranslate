import zipfile
import json
import base64

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
        self.zipfile = zipfile.ZipFile(filename, "r")
        self.info = json.loads(self.zipfile.read("info.json"))
        self.zip_name_list = self.zipfile.namelist()

        self.indexes = list()
        self.index_data = dict()     
        self.metas = dict()

        self.index_is_disabled = dict()

        for index in self.info.get("meta", {}).get("special_json", {}).get("indexes", []):
            self.indexes.append(index)
            #self.index_data_types[index['name']] = index['index_data_types']

        #load index data
        for name in self.zip_name_list:
            split = name.split("/")
            if split[0] == "algorithms":
                if len(split) > 2 and split[2]:
                    index_name = split[1]
                    self.load_pipeline_index(split[1], split[2], name)
                elif split[0] == "tessdata":
                    data = self.the_package_zip.read(name)
                    ff = open("./tessdata/"+split[1], "w")
                    ff.write(data)
                    ff.close()

        self.variables = dict()
 
    def is_index_disabled(self, index_name):
        return self.index_is_disabled.get(index_name, False)

    def disable_index(self, name):
        self.index_is_disabled[name] = True

    def enable_index(self, name):
        self.index_is_disabled[name] = False

    def get_game_indexes(self): 
        return self.indexes

    def set_variable(self, variable, value):
        self.variables[variable] = value

    def get_variable(self, variable):
        return self.variables.get(variable, "")

    def load_pipeline_index(self, index_type, index_name, full_name):
        index_split = base64.b32decode(index_name.rpartition(".")[0]).split("_")
        index_vars = list()
        pass
        ### this should load the index data into the index cache

        #raise NotImplemented

    def load_index_data_by_name(self, full_name):
        pass

    def get_meta_data(self, name):
        return self.metas.get(name, {})

    def load_meta(self, name, full_name):
        self.metas[name] = self.load_index_data_by_name(full_name)
 
    def close(self):
        #clear index data in indexes.
        pass

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
                print block_id
                seen_blocks[block_id] = self._fetch_from_file(
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
        par = block_id.partition("_")
        block = par[0]
        try:
            num = int(par[2])
        except:
            num = None
        fname = "algorithms/"+index_type+"/"+data_type+"_"+block
        if num == None:
            data = self.zipfile.read(fname).split("\n")
            return [json.loads(x) for x in data]
        else:
            data = self.zipfile.read(fname).split("\n")[num]
            return json.loads(data)
 

class FilePackageDirectDAO(FilePackageInterface):
    def __init__(self, user_id, game_id, font, filename, *args, **kwargs):
        super(FilePackageDirectDAO, self).__init__(user_id, game_id, font,
                                                   filename,
                                                   *args, **kwargs)

    def _match_sub_query(self, doc_sub, query_sub):
        if query_sub['type'] == doc_sub['type'] and\
                query_sub['num'] == doc_sub['num']:
            for key in ['val_f', 'val_i']:
                if query_sub.get(key):
                    if doc_sub.get(key) is None:
                        return False
                    if abs(doc_sub[key]-query_sub[key]) > query_sub['tol']:
                        return False
            if query_sub.get("val_s") != None:
                pass
            #otherwise it's a match
            return True
        return False
             
    def _search_zip(self, index_type, query, sort):
        #itterate through zip and return valid documents
        output = list()

        #first, limit files to the index_types
        for filename in self.zipfile.namelist():
            if filename == 'info.json':
                continue
            if filename.startswith("algorithms/"+index_type):
                #should be a cached read, or a simpler index based on the
                # index spec
                parr = filename.split("/")
                tn = parr[2].partition("_")[0]
                for entry in self.zipfile.read(filename).split("\n"):
                    if tn != "bid":
                        continue
                    doc = json.loads(entry)
                    for query_sub in query:
                        for doc_sub in doc['indexes']:    
                            if self._match_sub_query(doc_sub, query_sub):
                                break
                        else:
                            #no breaks, so no matches for this query_sub
                            break
                    else:
                        #no breaks inside, so query_sub had a match!
                        out_doc = {"_id": doc['_id'],
                                   "_source": doc['indexes']}
                        output.append(out_doc)
        return output
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
