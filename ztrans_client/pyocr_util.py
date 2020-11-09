from PIL import Image

import os
import os.path

os.environ['TESSDATA_PREFIX'] = "bin"

import pyocr.libtesseract 
import pyocr
import ctypes
import time


################ hack to override pyocr ##################33
handle = None

def load_tesseract_dll(lang="eng"):
    global handle 
    if handle is None:
        handle = pyocr.libtesseract.tesseract_raw.init(lang=lang)

def release_tesseract_dll():
    pyocr.libtesseract.tesseract_raw.cleanup(handle)

def main():
    image = Image.open("bin\\tsg.tif")

    load_tesseract_dll()
    s=image_to_boxes(image, 'eng')


def image_to_boxes(image, lang=None, builder=None, mode=6):
    global handle

    if builder is None:
        builder = pyocr.builders.WordBoxBuilder(mode)
    if handle is None:
        load_tesseract_dll(lang)

    lvl_line = pyocr.libtesseract.tesseract_raw.PageIteratorLevel.TEXTLINE
    lvl_word = pyocr.libtesseract.tesseract_raw.PageIteratorLevel.WORD

    try:
        clang = lang if lang else "eng"
        for lang_item in clang.split("+"):
            if lang_item not in pyocr.libtesseract.tesseract_raw.get_available_languages(handle):
                raise pyocr.TesseractError(
                    "no lang",
                    "language {} is not available".format(lang_item)
                )

        pyocr.libtesseract.tesseract_raw.set_page_seg_mode(
            handle, builder.tesseract_layout
        )
        pyocr.libtesseract.tesseract_raw.set_debug_file(handle, os.devnull)

        pyocr.libtesseract.tesseract_raw.set_image(handle, image)
        if "digits" in builder.tesseract_configs:
            pyocr.libtesseract.tesseract_raw.set_is_numeric(handle, True)

        pyocr.libtesseract.tesseract_raw.recognize(handle)
        res_iterator = pyocr.libtesseract.tesseract_raw.get_iterator(handle)
        if res_iterator is None:
            raise pyocr.TesseractError(
                "no script", "no script detected"
            )
        page_iterator = pyocr.libtesseract.tesseract_raw.result_iterator_get_page_iterator(
            res_iterator
        )

        while True:
            if pyocr.libtesseract.tesseract_raw.page_iterator_is_at_beginning_of(
                    page_iterator, lvl_line):
                (r, box) = pyocr.libtesseract.tesseract_raw.page_iterator_bounding_box(
                    page_iterator, lvl_line
                )
                assert(r)
                box = pyocr.libtesseract._tess_box_to_pyocr_box(box)
                builder.start_line(box)

            last_word_in_line = (
                pyocr.libtesseract.tesseract_raw.page_iterator_is_at_final_element(
                    page_iterator, lvl_line, lvl_word
                )
            )

            word = pyocr.libtesseract.tesseract_raw.result_iterator_get_utf8_text(
                res_iterator, lvl_word
            )

            confidence = pyocr.libtesseract.tesseract_raw.result_iterator_get_confidence(
                res_iterator, lvl_word
            )

            if word is not None and confidence is not None and word != "":
                (r, box) = pyocr.libtesseract.tesseract_raw.page_iterator_bounding_box(
                    page_iterator, lvl_word
                )
                assert(r)
                box = pyocr.libtesseract._tess_box_to_pyocr_box(box)
                builder.add_word(word, box, confidence)

                if last_word_in_line:
                    builder.end_line()

            if not pyocr.libtesseract.tesseract_raw.page_iterator_next(page_iterator, lvl_word):
                break

    finally:
        pass

    return builder.get_output()

if __name__=='__main__':
    main()
