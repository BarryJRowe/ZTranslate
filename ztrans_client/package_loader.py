import zipfile
import StringIO
import json
import base64
import time
import copy
from bson import json_util

class PackageObject:
    def __init__(self, filename=None, file_or_string=None):
      try:        
        #on windows, zipfile only seems to work for filename inputs and not file objects
        if filename:
            the_package_file = filename
        else:
            pass
        self.the_package_zip = zipfile.ZipFile(the_package_file, "r")
        self.info = json.loads(self.the_package_zip.read("info.json"))
        self.zip_name_list = self.the_package_zip.namelist()
        self.indexes = list()
        self.index_data = dict()
        self.metas = dict()
        self.index_data_types = dict()

        self.index_is_disabled = dict()

        for index in self.info.get("meta", {}).get("special_json", {}).get("indexes", []):
            self.indexes.append(index)
            self.index_data_types[index['name']] = index['index_data_types']

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
      except:
        import traceback
        traceback.print_exc()
        raise

    
    def is_index_disabled(self, name):
        return self.index_is_disabled.get(name, False)

    def disable_index(self, name):
        self.index_is_disabled[name] = True

    def enable_index(self, name):
        self.index_is_disabled[name] = False

    def get_game_indexes(self):
        #import pdb
        #pdb.set_trace()
        return self.indexes

    def set_variable(self, variable, value):
        self.variables[variable] = value

    def get_variable(self, variable):
        return self.variables.get(variable, "")
    
    def load_pipeline_index(self, index_type, index_name, full_name):  
        index_split = base64.b32decode(index_name.rpartition(".")[0]).split("_")
        index_vars = list()

        for i, entry in enumerate(index_split):
            #do modifications here like changing to int, float, unicode decoding, etc.
            the_type = self.index_data_types[index_type][i]
            
            if the_type == "string":
                index_vars.append(entry.decode("utf-8"))
            elif the_type == "int":
                index_vars.append(int(entry))
            elif the_type == "float":
                index_vars.append(float(entry))
            else:
                index_vars.append(entry)                

        if not index_type in self.index_data:
            self.index_data[index_type] = dict()

        curr_var = self.index_data[index_type]
        for entry in index_split[:-1]:
            if not entry in curr_var:
                curr_var[entry] = dict()
            curr_var = curr_var[entry]
        
        curr_var[index_split[-1]] = self.load_index_data_by_name(full_name)

    def load_index_data_by_name(self, full_name):
        data = self.the_package_zip.read(full_name)
        data = [json.loads(x, object_hook=json_util.object_hook) for x in data.split("\n")]
        return data

    def load_meta(self, name, full_name):
        self.metas[name] = self.load_index_data_by_name(full_name)
    
    def get_meta_data(self, name):
        return self.metas.get(name, {})

    def close(self):
        for algo in self.indexes.keys():
            for tup in self.indexes[algo].keys():
                for pc in self.indexes[algo][tup].keys():
                    del self.indexes[algo][tup][pc][:]
                    del self.indexes[algo][tup][pc]
                self.indexes[algo][tup]
            del self.indexes[algo]
    
    def find_by_query(self, db_query):
        def recur_checker(i, index):
            output = list()
            if i < len(checker):
                for key in index:
                    if checker[i][2] == None:
                        output.extend(recur_checker(i+1, index[key]))
                    elif checker[i][3] in ['int', 'float']:
                        caster = float

                        for sub_key in checker[i][2]:
                            if sub_key == "$lte" and caster(key) > checker[i][2][sub_key]:
                                break
                            elif sub_key == "$gte" and caster(key) < checker[i][2][sub_key]:
                                break
                        else:
                            output.extend(recur_checker(i+1, index[key]))
            else:
                output.extend(index)
            return output
        
        if '$and' in db_query:
            all_results = list()
            seen = dict()
            seen_current = dict()

            for i, x in enumerate(db_query['$and']):
                qu = copy.deepcopy(x)
                qu['type'] = db_query['type']
                for key in db_query:
                    if key.startswith("index."):
                        qu[key] = db_query[key]

                seen_current = dict()

                for res in self.find_by_query(qu):
                   if i==0 or res['_id'] in seen:
                       seen_current[res['_id']] = res
                seen = seen_current
            for key in seen:
                all_results.append(seen[key])
            print len(all_results)
            return all_results
        elif "$or" in db_query:
            all_results = list()
            seen = dict()

            for i, x in enumerate(db_query['$or']):
                qu = copy.deepcopy(x)
                qu['type'] = db_query['type']
                for key in db_query:
                    if key.startswith("index."):
                        qu[key] = db_query[key]

                for res in self.find_by_query(qu):
                   if res['_id'] not in seen:
                       seen[res['_id']] = res
                       all_results.append(res)
            return all_results

        results = list()
        index_type = db_query['type']
        checker = list()
        for key in db_query:
            if key.startswith("index."):
                value = db_query[key]
                checker.append([int(key.split(".")[1]), key, value])

        for i, k in enumerate(self.index_data_types[index_type]):
            if not "index."+str(i)+".value" in db_query:
                checker.append([i, "index."+str(i)+".value", None])

        checker.sort(key=lambda x: x[0])
        for i, entry in enumerate(checker):
            if i < len(self.index_data_types[index_type]):
                entry.append(self.index_data_types[index_type][i])

        if self.index_data.get(index_type,[]): 
            results = recur_checker(0, self.index_data[index_type])
            results.sort(key=lambda x: x.get("priority",0), reverse=True)
        else:
            results = list()
        return results
    
    #rewrite this function
    def find_data_by_values(self, algo, hsv, pc):
        output = list()
        for tup in self.indexes[algo]:
            if (tup == 'none' and hsv == None) or self.hsv_match(tup, hsv):
               for i_pc in self.indexes[algo][tup]:
                   if (i_pc == 'none' and pc == 'none') or (i_pc/2 < pc < i_pc*2)\
                           or (pc < 100):# and i_pc < 800):
                       output.extend(self.indexes[algo][tup][i_pc])
        return output


        
def main():
    package = PackageObject(filename="DieHolenWeltSaga0.01.ztp")
    t_time = time.time()
    results = package.find_data_by_values("diff", (0.3, 0.06, 0.32), None)
    print [time.time()-t_time]
    import pdb
    pdb.set_trace()

if __name__=="__main__":
    main()
