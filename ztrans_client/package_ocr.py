import time
import json
from PIL import Image, ImageDraw

from diff_block_algorithm import DiffBlockAlgorithm
from moving_text_algorithm import MovingTextAlgorithm
from util import load_image
from pipeline_general_service import PipelineGeneralService
import imaging


running_textboxes = list()    


class PackageOCR:
    @classmethod
    def call_ocr(cls, image_data, target_lang, package):
        t_time = time.time()
        blocks = list()
        if isinstance(image_data, basestring):
            image_object = load_image(image_data)
        else:
            image_object = image_data.copy()

        image_obj, data = PipelineGeneralService.run_ocr_pipeline(image_object, 
                                                                  package, 
                                                                  target_lang)
        for entry in data:
            if entry.get("match"):
                if 'special_json' in entry['block']:
                    MetaJson.parse_commands(entry['block']['special_json'],
                                            entry['block'], 
                                            package)
        return image_obj

class MetaJson:
    @classmethod
    def parse_commands(cls, special_json, block, package):
        if "box_meta" in special_json and type(special_json['box_meta']) == list:
            the_block = int(block.get("block_id").split("_")[1])

            if len(special_json['box_meta']) > the_block:
                if "meta_commands" in special_json['box_meta'][the_block]:
                    commands = special_json['box_meta'][the_block]['meta_commands']
                    req = special_json['box_meta'][the_block]['meta_req']
                    if cls.check_requirement(req, package):
                        for command in commands:
                            cls.run_command(command, package)
    @classmethod
    def check_requirement(cls, req, package):
        for cond in req:
            if type(cond) == dict:
                for key in cond:
                    if key == "equal_variable":
                       for subkey in cond[key]:
                           if package.get_variable(subkey) != cond[key][subkey]:
                               return False
                    elif key == "is_index_disabled":
                        return package.get_index_disabled(cond)
                    elif key == "textboxes_length":
                       for subkey in cond[key]:
                           if subkey == "not_equal": 
                               if len(running_textboxes) == cond[key][subkey]:
                                   return False
                           elif subkey == "equal": 
                               if len(running_textboxes) != cond[key][subkey]:
                                   return False

        return True

    @classmethod
    def run_command(cls, command, package):
        if type(command) != dict:
            return
        for key in command:
            cls.run_command2(key, command[key], package)
        pass

    @classmethod
    def run_command2(cls, command_name, command_data, package):
        if command_name == "set_variable":
            if type(command_data) == dict:
                for variable in command_data:
                    package.set_variable(variable, command_data[variable])
        elif command_name == "disable_index":
            package.disable_index(command_data)
        elif command_name == "enable_index":
            package.enable_index(command_data)
        elif command_name == "textbox":
            if type(command_data) == dict:
                print "------------"
                print package.variables
                print len(running_textboxes)
                TextBox.add_textbox(command_data)
        elif command_name == "unset_textboxes":
            if type(command_data) == dict:
                TextBox.remove_textboxes(command_data)

                
class TextBox:
    @classmethod
    def add_textbox(cls, textbox):
        global running_textboxes
        start = textbox.get("delay", 0)+time.time()
        end = textbox.get("duration", 1)+start
        running_textboxes.append({"start": start, "end": end,
                                  "bounding_box": textbox.get("bounding_box"),
                                  "text": textbox.get("text")
                                 })
    @classmethod
    def remove_textboxes(cls, textbox):
        if running_textboxes:
            global running_textboxes
            running_textboxes = list()

    @classmethod
    def check_requirement(cls, req, package):
        return MetaJson.check_requirement(req, package)

    @classmethod
    def process_textboxes(cls, image, target_lang, package):
        global running_textboxes
        new_textboxes = list()
        draw = ImageDraw.Draw(image)
        c_time = time.time()
        #print "================="
        #print running_textboxes
        for textbox in running_textboxes:
            if textbox['start'] <= c_time <= textbox['end']:
                bb = textbox['bounding_box']
                #print textbox
                imaging.drawTextBox(draw, textbox['text'].get(target_lang), 
                                    bb[0],bb[1], bb[2], bb[3], 
                                    font=None, confid=1, exact_font=textbox.get("font_size", 8))
            req = textbox.get("req", list())
            if time.time() <= textbox['end'] and cls.check_requirement(req, package):
                new_textboxes.append(textbox)
        running_textboxes = new_textboxes
        return image
