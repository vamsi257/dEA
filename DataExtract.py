import cv2
import pytesseract
import os
from google.cloud import vision
import json
import csv
import uuid

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def detectText(content):
    dir_list = os.listdir("./jsonfile")
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f"./jsonfile/{dir_list[0]}"
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
def coTox(img, L_id, name, x, y, W, H, file_name, page_n, option, dformat):
    image = cv2.imread(img, 0)
    thresh = 255 - cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    w = W - x
    h = H - y
    ROI = thresh[y:y + h, x:x + w]
    # Pytesseract
    if option == "1":
        data = pytesseract.image_to_string(ROI, lang='eng', config='--psm 6')
        print("data")
    elif option == "2":
        # cloud vision
        success, image = cv2.imencode('.png', ROI)
        content = image.tobytes()
        data = detectText(content)
        print(data)

    extracted_data = {"folder_name": file_name.split("/")[0], "filename": file_name, "Page_n": page_n, "id": L_id,
                      "field_name": name, "label_data": data, "Format": dformat}
    # except:
    # extracted_data={"folder_name":file_name.split("/")[0],"filename":file_name,"Page_n":"None","id":"None","field_name":"None","label_data":"None"}

    # cv2.waitKey()
    return extracted_data


# this is for pdf file
def Main(img_name, file_name, page_n, option, coordinates):
    All_Data = {}

    for line in coordinates:
        parts = line.split(',')
        if img_name == parts[0]:
            try:
                L_id = parts[1]
                name = parts[2]
                x, y, w, h = int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6])
                dformat = parts[7]

                extracted_data = coTox(img_name, L_id, name, x, y, w, h, file_name, page_n, option, dformat)
                All_Data[L_id] = extracted_data
            except:
                pass

    return All_Data


def MainImg(image_folder, option, data):
    csv_filename = f'{uuid.uuid1()}extracted_data.csv'
    coordinates_data = []
    input_string = data.cordinates
    lines = input_string.splitlines()
    for line in lines:
        split_values = line.split(',')
        coordinates_data.append(split_values)
    # Process each image in the folder
    for image_filename in os.listdir(image_folder):
        if image_filename.endswith(('.jpg', '.png', '.jpeg', '.tif', '.tiff')):
            print(f"Processing image: {image_filename}")

            # Define a data structure to store extracted data
            extracted_data = {}
            # Process each set of coordinates
            for coord in coordinates_data:
                _, column_title, x_min, x_max, y_min, y_max, data_type = coord

                # Load the image using OpenCV
                image = cv2.imread(os.path.join(image_folder, image_filename))

                # Print image dimensions and coordinates for debugging
                print(f"Image dimensions: {image.shape}")
                print(f"Coordinates: x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max}")

                x_min = int(x_min)
                x_max = int(x_max)
                y_min = int(y_min)
                y_max = int(y_max)

                # Check if coordinates are within image boundaries
                if x_min < 0 or x_max > image.shape[1] or y_min < 0 or y_max > image.shape[0]:
                    print("Error: Coordinates are outside image boundaries")
                    continue  # Skip this iteration

                # Extract the region of interest (ROI) using coordinates
                roi = image[y_min:y_max, x_min:x_max]
                if option == "1":
                    # Perform OCR on the ROI
                    extracted_text = pytesseract.image_to_string(roi, lang='eng', config='--psm 6')

                    # Add extracted data to the data structure
                    extracted_data[column_title] = extracted_text.strip()
                elif option == "2":
                    # cloud vision
                    success, image = cv2.imencode('.png', roi)
                    content = image.tobytes()
                    extracted_data[column_title] = detectText(content)  # Add extracted data

            # Save extracted data as CSV
            csv_file = os.path.join("./static/csvfile", csv_filename)
            with open(csv_file, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)

                # Write the CSV header
                csv_writer.writerow(extracted_data.keys())

                # Write the extracted data row
                csv_writer.writerow(extracted_data.values())

    return csv_filename

