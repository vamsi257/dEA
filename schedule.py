import pickle
import sqlite3
import os
from datetime import datetime
from DataExtract import Main, MainImg
import cv2
import random
import pandas as pd
from pdf2image import convert_from_path
from page_limiter import page_limiter
import os


def run_scheduled_tasks(app):
    # from flask import current_app
    # app = current_app

    try:

        # Connect to SQLite database
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()

        # Get all pending tasks
        cursor.execute('''
            SELECT task_id, date,time,filenames,filetype
            FROM tasks
            WHERE  status = 'pending'
        ''')
        tasks = cursor.fetchall()[:1]

        # Run tasks that are due
        if len(tasks) > 0:
            for task_id, date, time, filenames, filetype in tasks:

                # print(task_id,date,time,filenames,filetype)
                # Convert the date and time from the form into a datetime object
                form_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                # Get the current date and time
                current_datetime = datetime.now()

                if current_datetime >= form_datetime:
                    parse_and_extract(filetype, pickle.loads(filenames), app)
                    result = "Check .csv files"
                    data = app.config["Data"]

                    df = pd.DataFrame(data)
                    if not os.path.exists("OUTPUTS"):
                        os.makedirs("OUTPUTS")
                    output_file = os.path.join("OUTPUTS", f'filename{random.randint(0, 9999999)}.csv')
                    df.to_csv(output_file, index=False, encoding='utf-8')

                    cursor.execute('''
                        UPDATE tasks
                        SET status = 'finished', result = ?
                        WHERE task_id = ?
                    ''', (result, task_id))
            conn.commit()
            app.config["Data"] = []
            # conn.close()
            cursor.close()

    except Exception as e:
        print("🐛 in run_scheduled_tasks".encode('utf-8'), e)
    return


def parse_and_extract(extention, filenames, app):
    app.config["Data"] = []
    new_data = {}
    count_img = 0
    for file in filenames:

        if extention in ["pdf", "PDF"]:
            folderpath = os.path.join(os.path.abspath(os.getcwd()), "upload", file)

            # ------new code start
            # pages=convert_from_path(folderpath,poppler_path=r"D:\flask\Assignment\assignment 1\drive-download-20230222T084703Z-001\poppler-0.67.0_x86\poppler-0.67.0\bin")
            pages = convert_from_path(
                folderpath, poppler_path=app.config['poppler_path'])
            path = os.path.join(os.path.abspath(os.getcwd()), "static/images")
            # os.remove(f'./images/{file.filename}')
            count = 0
            for page in pages:
                count += 1
                jpg = path + "/" + str(count) + ".jpg"
                page.save(jpg, "JPEG")
                option = "1"
                data = Main(str(count) + ".jpg", file, count, option)
                if len(data) == 0:
                    data = ""
                    continue

                # app.config["Data"].append(data)

                ###############################combined_data
                combined_data = {}
                id = str(count_img)

                for record in data.values():
                    # id = record['id']
                    if id not in combined_data:
                        combined_data[id] = {
                            'folder_name': record['folder_name'],
                            'filename': record['filename'],
                            'Page_n': record['Page_n'],
                            'id': id,

                        }
                    field_name = record['field_name']

                    # original code
                    label_data = record['label_data'].strip()

                    #########################################
                    # temp code
                    if record['Format'] == "Table":

                        label_data = [
                            record['label_data'].strip().replace(",", "").replace("%", "").replace("\n", ", ").replace(
                                "=", "")]
                        # if label_data[0].split(',')
                        contains_only_numbers = all(num.strip().isdigit() for num in label_data[0].split(','))

                        if contains_only_numbers:
                            # Convert list of strings to list of integers
                            label_data = [int(num.strip()) for num in label_data[0].split(',')]
                            print('int_list')
                        else:
                            label_data = [s.strip() for s in label_data[0].split(',') if s.strip()]

                            print("List contains non-numeric elements.")
                    #########################################
                    combined_data[id][field_name] = label_data

                app.config["Data"].append(combined_data[id])
                count_img += 1
                if page_limiter(count_img):
                    break
            if page_limiter(count_img):
                break


        # elif extention in [".jpg", ".png", ".jpeg", ".tiff", ".tif"]:
        else:
            print("reading IMAGES")

            page_count = 1

            # directory = os.path.join(os.path.abspath(os.getcwd()),"upload")
            # img_list = []

            for f in filenames:
                f = f.replace("/", "_")
                option = "1"
                # file = open(os.path.join(os.path.abspath(os.getcwd()),"upload", f))

                data = MainImg(
                    os.path.join(os.path.abspath(os.getcwd()), "upload", f), f, page_count, option
                )

                # os.remove(os.path.join(os.path.abspath(os.getcwd()),"upload", f))

                ########################combined_data
                combined_data = {}
                id = str(count_img)

                for record in data.values():
                    # id = record['id']
                    if id not in combined_data:
                        combined_data[id] = {
                            'folder_name': record['folder_name'],
                            'filename': record['filename'],
                            'Page_n': record['Page_n'],
                            'id': id
                        }
                    field_name = record['field_name']
                    label_data = record['label_data'].strip() or "nil"
                    combined_data[id][field_name] = label_data

                app.config["Data"].append(combined_data[id])
                count_img += 1

                if page_limiter(count_img):
                    break

            if page_limiter(count_img):
                break

# return redirect(url_for("download", token=[token]))
# try:
# shutil.rmtree("./jsonfile")
# shutil.rmtree("./images")
# flash("Please wait for converting")
# os.mkdir("./jsonfile")
# os.mkdir("./images")

# except:
# pass
# d = tbl_user.query.filter_by(id=current_user.id).first()
# return render_template("upload.html", form=form, token=token, status=int(d.status))
