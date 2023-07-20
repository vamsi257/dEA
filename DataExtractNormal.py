import cv2
import pytesseract
import csv
import base64
import os, io
from google.cloud import vision, vision_v1
# from google.cloud.vision_v1 import types
from dateutil import parser
import datetime

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"


def detectText(content):
    dir_list = os.listdir("./jsonfile_normal")
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f"./jsonfile_normal/{dir_list[0]}"
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    texts = response.text_annotations
    data = ""
    for text in texts:
        # data+=text.description
        data += text.description

        break
    return data


# this will extract text using cordinates from csv (out.csv
def coTox(img, L_id, name, X, Y, W, H, file_name, page_n, option, dformat):
    image = cv2.imread(img, 0)
    thresh = 255 - cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # xmin,ymin,xmax,ymax
    x = X
    y = Y
    w = W - x
    h = H - y
    ROI = thresh[y:y + h, x:x + w]
    # Pytesseract
    if option == "1":
        data = pytesseract.image_to_string(ROI, lang='eng', config='--psm 6')
    elif option == "2":
        # cloud vision
        success, image = cv2.imencode('.png', ROI)
        content = image.tobytes()
        data = detectText(content)

    extracted_data = {"folder_name": file_name.split("/")[0], "filename": file_name, "Page_n": page_n, "id": L_id,
                      "field_name": name, "label_data": data, "Format": dformat}
    # except:
    # extracted_data={"folder_name":file_name.split("/")[0],"filename":file_name,"Page_n":"None","id":"None","field_name":"None","label_data":"None"}

    # cv2.waitKey()
    return extracted_data


# this is for pdf file
def Main(img_name, file_name, page_n, option):
    # ['image'=0, 'id'=1, 'name'=2, 'xMin'=3, 'xMax'=4, 'yMin'=5, 'yMax'=6]

    with open('out.csv', 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        All_Data = {}
        next(csv_reader)

        for line in csv_reader:
            if img_name == line[0]:
                try:
                    All_Data[line[1]] = coTox(f"./images_normal/{img_name}", line[1], line[2], int(line[3]),
                                              int(line[5]), int(line[4]), int(line[6]), file_name, page_n, option,
                                              line[7])
                except:
                    pass
    return All_Data


# this is for img files
def MainImg(img_name, file_name, page_n, option):
    # ['image'=0, 'id'=1, 'name'=2, 'xMin'=3, 'xMax'=4, 'yMin'=5, 'yMax'=6]
    with open('out.csv', 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        All_Data = {}
        next(csv_reader)
        for line in csv_reader:
            try:
                All_Data[line[1]] = coTox(img_name, line[1], line[2], int(line[3]), int(line[5]), int(line[4]),
                                          int(line[6]), file_name, page_n, option, line[7])
            except:
                pass
    return All_Data
