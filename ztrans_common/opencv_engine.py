"""
https://www.pyimagesearch.com/2018/09/17/opencv-ocr-and-text-recognition-with-tesseract/
"""

from imutils.object_detection import non_max_suppression
import numpy as np
import pytesseract
import argparse
import cv2
import numpy
import time
import math
from PIL import Image, ImageDraw

# import the necessary packages
#from sklearn.cluster import KMeans, MiniBatchKMeans

"""
class KMeansImage:
    @classmethod
    def centroid_histogram(cls, clt):
        numLabels = np.arange(0, len(np.unique(clt.labels_)) + 1)
        (hist, _) = np.histogram(clt.labels_, bins = numLabels)
 
        hist = hist.astype("float")
        hist /= hist.sum()
 
        return hist

    @classmethod
    def kmeans(cls, image, clusters, fast=False):
        # load the image and convert it from BGR to RGB so that
        # we can dispaly it with matplotlib
        im = numpy.array(image.convert("RGB"))
        h, w = im.shape[:2]

        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        im = im.reshape((im.shape[0] * im.shape[1], 3))
        t = time.time()
        if fast:
            clt = MiniBatchKMeans(n_clusters=clusters)
        else:
            clt = KMeans(n_clusters=clusters)
        labels = clt.fit_predict(im)
        
        #quant = clt.cluster_centers_.astype("uint8")[labels]
        #quant = quant.reshape((h, w, 3))
        #im = im.reshape((h, w, 3))

        #quant = cv2.cvtColor(quant, cv2.COLOR_LAB2BGR)
        #image = Image.fromarray(im)
        
        hist = cls.centroid_histogram(clt)
        centroids = clt.cluster_centers_
        out = list()
        for (percent, color) in zip(hist, centroids):
            out.append([percent, color.astype("uint8").tolist()])
            print out[-1]
        print time.time()-t
        return out
        
"""

class BoxArea:
    @classmethod
    def _box_intersect(cls, b1,b2):
        dx = min(b1[2], b2[2]) - max(b1[0], b2[0])
        dy = min(b1[3], b2[3]) - max(b1[1], b2[1])
        if dx >= 0 and dy >= 0:
            return dx*dy
        return 0

    @classmethod
    def _box_area(cls, b):
        return cls._box_intersect(b,b)

    @classmethod
    def _box_eq(cls, b1, b2):
        for i in range(4):
            if b1[i] != b2[i]:
                return False
        return True


class HuMoments:
    @classmethod
    def calculate_hu_moments(cls, image, binarized=False):
        cv_image = numpy.array(image.convert("RGB"))
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        if binarized==False:
            _, cv_image = cv2.threshold(cv_image, 128, 255, cv2.THRESH_BINARY)
        moments = cv2.moments(cv_image)
        hu_moments = cv2.HuMoments(moments)
        for i in range(7):
            hu_moments[i] = -1*math.copysign(1.0, hu_moments[i])*math.log10(abs(hu_moments[i])+0.0001)
        return [x[0] for x in hu_moments]

    @classmethod
    def match_shapes(cls, image1, image2, binarized=False):
        im1 = numpy.array(image1.convert("RGB"))
        im2 = numpy.array(image2.convert("RGB"))
        im1 = cv2.cvtColor(im1, cv2.COLOR_BGR2GRAY)
        im2 = cv2.cvtColor(im2, cv2.COLOR_BGR2GRAY)
        if binarized==False:
            _, im1 = cv2.threshold(im1, 128, 255, cv2.THRESH_BINARY)
            _, im2 = cv2.threshold(im2, 128, 255, cv2.THRESH_BINARY)

        d1 = cv2.matchShapes(im1, im2, cv2.CONTOURS_MATCH_I1, 0)
        d2 = cv2.matchShapes(im1, im2, cv2.CONTOURS_MATCH_I2, 0)
        d3 = cv2.matchShapes(im1, im2, cv2.CONTOURS_MATCH_I3, 0)
        return d1,d2,d3


class TextFeatureFinder:
    net = None

    @classmethod
    def _decode_predictions(cls, scores, geometry, min_confidence):
        # grab the number of rows and columns from the scores volume, then
        # initialize our set of bounding box rectangles and corresponding
        # confidence scores
        (numRows, numCols) = scores.shape[2:4]
        rects = []
        confidences = []
         
        # loop over the number of rows
        for y in range(0, numRows):
            # extract the scores (probabilities), followed by the
            # geometrical data used to derive potential bounding box
            # coordinates that surround text
            scoresData = scores[0, 0, y]
            xData0 = geometry[0, 0, y]
            xData1 = geometry[0, 1, y]
            xData2 = geometry[0, 2, y]
            xData3 = geometry[0, 3, y]
            anglesData = geometry[0, 4, y]

            # loop over the number of columns
            for x in range(0, numCols):
                # if our score does not have sufficient probability,
                # ignore it
                if scoresData[x] < min_confidence:
                    continue
 
                # compute the offset factor as our resulting feature
                # maps will be 4x smaller than the input image
                (offsetX, offsetY) = (x * 4.0, y * 4.0)

                # extract the rotation angle for the prediction and
                # then compute the sin and cosine
                angle = anglesData[x]
                cos = np.cos(angle)
                sin = np.sin(angle)

                # use the geometry volume to derive the width and height
                # of the bounding box
                h = xData0[x] + xData2[x]
                w = xData1[x] + xData3[x]

                # compute both the starting and ending (x, y)-coordinates
                # for the text prediction bounding box
                endX = int(offsetX + (cos * xData1[x]) + (sin * xData2[x]))
                endY = int(offsetY - (sin * xData1[x]) + (cos * xData2[x]))
                startX = int(endX - w)
                startY = int(endY - h)

                # add the bounding box coordinates and probability score
                # to our respective lists
                rects.append((startX, startY, endX, endY))
                confidences.append(scoresData[x])
 
        # return a tuple of the bounding boxes and associated confidences
        return (rects, confidences)

    @classmethod
    def find_features(cls, pil_image, east=None, min_confidence=0.5, 
                           width=320, height=320, padding=0.0):
        if east is None:
            east = "frozen_east_text_detection.pb"
        t_time = time.time()
        # load the input image and grab the image dimensionsa
        d = numpy.asarray(pil_image.convert("RGBA"))
        image = cv2.cvtColor(d, cv2.COLOR_RGB2BGR)

        orig = image.copy()
        (origH, origW) = image.shape[:2]
 
        # set the new width and height and then determine the ratio in change
        # for both the width and height
        (newW, newH) = (width, height)
        rW = origW / float(newW)
        rH = origH / float(newH)
 
        # resize the image and grab the new image dimensions
        image = cv2.resize(image, (newW, newH))
        (H, W) = image.shape[:2]

        # define the two output layer names for the EAST detector model that
        # we are interested in -- the first is the output probabilities and the
        # second can be used to derive the bounding box coordinates of text
        layerNames = ["feature_fusion/Conv_7/Sigmoid",
                      "feature_fusion/concat_3"]
 
        if cls.net is None:
            # load the pre-trained EAST text detector
            print("[INFO] loading EAST text detector...")
            cls.net = cv2.dnn.readNet(east)

        t_time = time.time()
        # construct a blob from the image and then perform a forward pass of
        # the model to obtain the two output layer sets
        blob = cv2.dnn.blobFromImage(image, 1.0, (W, H),
                (123.68, 116.78, 103.94), swapRB=True, crop=False)
        cls.net.setInput(blob)
        (scores, geometry) = cls.net.forward(layerNames)
 
        # decode the predictions, then  apply non-maxima suppression to
        # suppress weak, overlapping bounding boxes
        (rects, confidences) = cls._decode_predictions(scores, geometry, min_confidence)
        boxes2 = rects
        boxes = non_max_suppression(np.array(rects), probs=confidences)

        #output best matching box, smallest, largest
        boxes_output = list()
        for i, box in enumerate(boxes):
            l = [{"box": box, "type": "best", "num": i}]
            inter = list()
            for b in boxes2:
                if BoxArea._box_intersect(b,box):
                    inter.append(b)
            small_c = 10000000
            small = box
            large_c = 0
            large = box
            for bb in inter:
                a = BoxArea._box_area(bb)
                if a < small_c:
                    small_c = a
                    small = bb
                if a > large_c:
                    large_c = a
                    large = bb
            if not BoxArea._box_eq(large, box):
                l.append({"box": large, "type": "large", "num": i})
            if not BoxArea._box_eq(small, box):
                l.append({"box": small, "type": "small", "num": i})
            for d in l:
                d['box'] = [d['box'][0]*rW, d['box'][1]*rH, 
                            d['box'][2]*rW, d['box'][3]*rH]
                boxes_output.append(d)
 
        # loop over the bounding boxes
        #print time.time()-t_time
 
        if False or True:
            image = pil_image.convert("RGBA")
            draw = ImageDraw.Draw(image)
            for box in boxes:
                draw.rectangle([(box[0]*rW, box[1]*rH), (box[2]*rW, box[3]*rH)], outline=(255,0,0,255))
        print time.time()-t_time
        return boxes_output, image
        """
        for (startX, startY, endX, endY) in boxes:
            # scale the bounding box coordinates based on the respective
            # ratios
            startX = int(startX * rW)
            startY = int(startY * rH)
            endX = int(endX * rW)
            endY = int(endY * rH)
             
            # in order to obtain a better OCR of the text we can potentially
            # apply a bit of padding surrounding the bounding box -- here we
            # are computing the deltas in both the x and y directions
            dX = int((endX - startX) * padding)
            dY = int((endY - startY) * padding)
             
            # apply padding to each side of the bounding box, respectively
            startX = max(0, startX - dX)
            startY = max(0, startY - dY)
            endX = min(origW, endX + (dX * 2))
            endY = min(origH, endY + (dY * 2))
             
            # extract the actual padded ROI
            roi = orig[startY:endY, startX:endX]


            # in order to apply Tesseract v4 to OCR text we must supply
            # (1) a language, (2) an OEM flag of 4, indicating that the we
            # wish to use the LSTM neural net model for OCR, and finally
            # (3) an OEM value, in this case, 7 which implies that we are
            # treating the ROI as a single line of text
            config = ("-l deu --oem 1 --psm 3")
            text = pytesseract.image_to_string(roi, config=config)
             
            # add the bounding box coordinates and OCR'd text to the list
            # of results
            results.append(((startX, startY, endX, endY), text))


        # sort the results bounding box coordinates from top to bottom
        results = sorted(results, key=lambda r:r[0][1])
        print ("Took", time.time()-t_time)
        # loop over the results
        for ((startX, startY, endX, endY), text) in results:
            # display the text OCR'd by Tesseract
            print("OCR TEXT")
            print("========")
            print("{}\n".format([text]))
             
            # strip out non-ASCII text so we can draw the text on the image
            # using OpenCV, then draw the text and a bounding box surrounding
            # the text region of the input image
            text = "".join([c if ord(c) < 128 else "" for c in text]).strip()
            output = orig.copy()
            cv2.rectangle(output, (startX, startY), (endX, endY),
                          (0, 0, 255), 2)
            cv2.putText(output, text, (startX, startY - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
             
            # show the output image
            cv2.imshow("Text Detection", output)
                  
            cv2.waitKey(0)
        """


"""
  -east text detection:
    -output is a list of box-lists
     - [ [best box, smallest_box, largest_box], ...
  -create a "HU" index of box-level Hu moments and HSV
  -
"""


def main():
    image = Image.open("images.png")
    options = dict()
    east = options.get("east", "data/frozen_east_text_detection.pb")
    min_conf = options.get("min_confidence", 0.5)
    width = options.get("width", 320)
    height = options.get("height", 320)
    padding = options.get("padding", 0.0)
    padding = 0.25
    out = TextFeatureFinder.find_features(image, east=east,
                                          min_confidence=min_conf,
                                          width=width, height=height,
                                          padding=padding)
    print out
    image2 = image.crop(out[0][0]['box'])

    """
    t = time.time()
    KMeansImage.kmeans(image2, 3, fast=True)
    print time.time()-t
    """

if __name__=='__main__':
    main()

