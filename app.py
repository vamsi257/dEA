import jwt
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, abort, flash, send_file, jsonify, \
    send_from_directory, session
from flask_login import UserMixin, logout_user, current_user, login_user, LoginManager, login_required
from wtforms import StringField, PasswordField, SubmitField, MultipleFileField, FileField
from wtforms.validators import InputRequired, Length
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy.orm.exc import NoResultFound
from pytz import timezone
from flask_bcrypt import Bcrypt
import socket
from functools import wraps
import base64
import datetime
import shutil
import json
from werkzeug.utils import secure_filename
import pandas as pd
from pdf2image import convert_from_path
import pickle
import csv
import uuid
import cv2
import pytesseract
import threading
import os
from google.cloud import vision

# Define a list to store coordinates (regions of interest).
roi_coordinates = []

# Create a Flask app instance.
app = Flask(__name__)

# Configuration settings for the app.
app.config["IMAGES"] = "./static/upload/images"
app.config["LABELS"] = []
app.config["HEAD"] = 0
app.config["uploaded_files"] = []
app.config["TEMP_NAME"] = []
app.config["TEMP_Imagecode"] = ""
app.config["Data"] = []
app.config['UPLOAD_FOLDER'] = './static/uploads'  # Folder to store uploaded files
app.config['STATIC_FOLDER'] = './static'  # Folder to serve static files
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///extract.db' # Database connection
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["SECRET_KEY"] = "90a685b9e1477480d8c1cce1f545e0504c84d7f2041dc733ceabe26597a6b5f6"
app.config["UPLOAD_FOLDER"] = "./static/upload"
app.config["UPLOAD_FOLDER_NORMAL"] = "upload_normal"
app.config["OUT"] = "out.csv"
# Configure the allowed file extensions for upload
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "pdf", 'tif', 'tiff'}

# Initialize the database using SQLAlchemy.
db = SQLAlchemy(app)
login_manager = LoginManager()  # To manage Login
login_manager.init_app(app)
login_manager.login_view = "login"
scheduled_tasks = {}

# Create a Bcrypt instance for password hashing.
bcrypt = Bcrypt(app)


# Function to load the User object using user_id.
@login_manager.user_loader
def load_user(user_id):
    return tbl_user.query.get(int(user_id))


def detectText(content):
    dir_list = os.listdir("./jsonfile")
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f"./jsonfile/{dir_list[0]}"
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    texts = response.text_annotations
    data = ""
    for text in texts:
        data += text.description
        break
    return data


def MainImg(user_id, image_folder, option, data):
    with app.app_context():
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        csv_filename = f'{uuid.uuid1()}extracted_data.csv'
        coordinates_data = []
        input_string = data.cordinates
        lines = input_string.splitlines()
        for line in lines:
            split_values = line.split(',')
            coordinates_data.append(split_values)

        # Define a data structure to store extracted data for all images
        all_extracted_data = []

        # Process each image in the folder
        for image_filename in os.listdir(image_folder):
            if image_filename.endswith(('.jpg', '.png', '.jpeg', '.tif', '.tiff')):
                print(f"Processing image: {image_filename}")

                # Define a data structure to store extracted data for this image
                extracted_data = {}

                # Load the image using OpenCV
                image = cv2.imread(os.path.join(image_folder, image_filename))

                # Process each set of coordinates
                for coord in coordinates_data:
                    _, column_title, x_min, x_max, y_min, y_max, data_type = coord

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
                        extracted_data[column_title] = extracted_text.strip()
                    elif option == "2":
                        # Google Cloud Vision
                        success, roi_encoded = cv2.imencode('.png', roi)
                        roi_content = roi_encoded.tobytes()
                        extracted_text = detectText(roi_content)
                        extracted_data[column_title] = extracted_text.strip()

                # Append extracted data for this image to the list of all_extracted_data
                all_extracted_data.append(extracted_data)

        # Save all extracted data as CSV
        csv_file_path = os.path.join("./static/csvfile", csv_filename)
        with open(csv_file_path, 'w', newline='') as csv_file:
            if all_extracted_data:
                csv_writer = csv.DictWriter(csv_file, fieldnames=all_extracted_data[0].keys())

                # Write the CSV header
                csv_writer.writeheader()

                # Write the extracted data rows
                csv_writer.writerows(all_extracted_data)
                print(all_extracted_data)

        encoded_csv_filename = os.path.basename(csv_file_path).encode('utf-8')
        extract = ExtractedFiles(user_id=user_id, csvfilename=encoded_csv_filename)
        db.session.add(extract)
        db.session.commit()
        # Clean up the saved file      
        os.remove(image_folder)
        print(f"Extracted data Successfully!!")


def schedule_extraction(user_id, image_folder, option, data, scheduled_time):
    current_time = datetime.datetime.now()
    extraction_time = datetime.datetime.strptime(scheduled_time, "%Y-%m-%dT%H:%M")

    if extraction_time < current_time:
        flash("Scheduled time should be in the future.")
        return redirect(url_for("template"))

    time_difference = (extraction_time - current_time).total_seconds()
    timer = threading.Timer(time_difference, MainImg, args=(user_id, image_folder, option, data,))
    timer.start()
    print(f'Scheduled{timer}')
    scheduled_tasks[image_folder] = timer


class tbl_user(db.Model, UserMixin):  # User table
    id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(20), nullable=True)
    username = db.Column(db.String(20), nullable=True, unique=True)
    password = db.Column(db.String(80), nullable=False)
    status = db.Column(db.Integer)
    token = db.Column(db.String(1000))
    dateformat = db.Column(db.String(80), nullable=False, default="No")
    Date_time = db.Column(db.DateTime, default=datetime.datetime.now(timezone('Asia/Kolkata')))
    ip = db.Column(db.String(20), default="None")
    data = db.relationship("Cordinate_Data", backref="author", lazy=True)

    def __repr__(self) -> str:
        return "<tbl_user %r>" % self.User_Name


class Task(db.Model):
    task_id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50))
    time = db.Column(db.String(50))
    filenames = db.Column(db.LargeBinary)
    filetype = db.Column(db.String(50))
    result = db.Column(db.String(50))
    status = db.Column(db.String(50))


class ExtractedFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    date_time = db.Column(db.String(50), default=datetime.datetime.now(timezone('Asia/Kolkata')))
    jsonfilenames = db.Column(db.LargeBinary)
    csvfilename = db.Column(db.LargeBinary)


def save_task(date, time, filenames, filetype):
    date = request.form.get("date")
    time = request.form.get("time")
    filenames = request.form.getlist("filenames")
    filetype = request.form.get("filetype")

    # Serialize filenames using pickle
    serialized_filenames = pickle.dumps(filenames)

    # Create a new Task object
    new_task = Task(date=date, time=time, filenames=serialized_filenames, filetype=filetype, status='pending')

    # Add the task to the database
    db.session.add(new_task)
    db.session.commit()

    return new_task.task_id


class Cordinate_Data(UserMixin, db.Model):  # Coordinate table
    __tablename__ = "cordinate_data"
    cord_id = db.Column(db.Integer, primary_key=True)
    Tem_name = db.Column(db.String(80), nullable=False)
    Tem_format = db.Column(db.String(80), nullable=False)
    cordinates = db.Column(db.Text)
    Date = db.Column(db.String(80), nullable=False)
    Time = db.Column(db.String(80), nullable=False)
    Day = db.Column(db.String(80), nullable=False)
    tempimage = db.Column(db.Text)
    file = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("tbl_user.id"), nullable=False)

    def __repr__(self) -> str:
        return f"{self.cord_id}"


# registration flask form
class RegisterForm(FlaskForm):
    Name = StringField(
        validators=[InputRequired(), Length(min=4, max=20)],
        render_kw={"placeholder": "Name"},
    )
    username = StringField(
        validators=[InputRequired(), Length(min=4, max=20)],
        render_kw={"placeholder": "Username"},
    )
    password = PasswordField(
        validators=[InputRequired(), Length(min=8, max=20)],
        render_kw={"placeholder": "Password"},
    )
    submit = SubmitField("Register")


# login flask form
class LoginForm(FlaskForm):
    username = StringField(
        validators=[InputRequired(), Length(min=4, max=20)],
        render_kw={"placeholder": "Username"},
    )
    password = PasswordField(
        validators=[InputRequired(), Length(min=8, max=20)],
        render_kw={"placeholder": "Password"},
    )
    submit = SubmitField("Login")


# Define a FlaskForm for file upload.
class UploadFileForm(FlaskForm):
    jsonfile = FileField("jsonfile")
    file = MultipleFileField(validators=[InputRequired()])
    Temp_name = StringField(validators=[InputRequired(), Length(min=4, max=20)])


# Dashboard route accessible after login, showing user information.
@app.route('/dashboard')
@login_required
def dashboard():
    current_year = datetime.datetime.now().year
    name = current_user.Name
    username = current_user.username
    date = current_user.Date_time
    row = [name, current_user.id, username, date]
    return render_template('dashboard.html', data=row)


# registration
@app.route("/register", methods=["GET", "POST"])
def signup():
    current_year = datetime.datetime.now().year
    form = RegisterForm()
    if request.method == 'POST':
        # Get user details from the registration form.
        username = form.username.data
        user = tbl_user.query.filter_by(username=username).first()
        if user:
            # If user already exists, show a flash message.
            flash("You already having the account on this email!")
            return render_template("login.html")
        else:
            # Hash the password and create a new user in the database.
            hashed_password = bcrypt.generate_password_hash(form.password.data)
            hostname = socket.gethostname()
            IPadd = socket.gethostbyname(hostname)
            new_user = tbl_user(
                Name=form.Name.data,
                username=form.username.data,
                password=hashed_password,
                status=0,
                ip=str(IPadd),
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login"))
    return render_template("register.html", form=form)


# login
@app.route("/login", methods=["GET", "POST"])
def login():
    current_year = datetime.datetime.now().year
    form = LoginForm()
    if form.validate_on_submit():
        # Get user details from the login form.
        user = tbl_user.query.filter_by(username=form.username.data).first()
        hostname = socket.gethostname()
        IPadd = socket.gethostbyname(hostname)
        if user:
            if user.ip == "None":
                # Update user's IP address in the database.
                user.ip = str(IPadd)
                db.session.add(user)
                db.session.commit()
                return redirect(url_for('login'))
            elif user.ip != IPadd:
                # If user's IP address does not match, show an error message.
                abort(400, "You cannot access this application, contact to owner")
            elif bcrypt.check_password_hash(user.password, form.password.data) and user.ip == str(IPadd):
                # If the password is correct and IP address matches, log the user in.
                login_user(user)
                token = jwt.encode(
                    {
                        "user": form.username.data,
                        "exp": datetime.datetime.utcnow() + timedelta(minutes=60),
                    },
                    app.config["SECRET_KEY"],
                )
                user.token = token
                db.session.add(user)
                db.session.commit()
                return redirect(url_for("template"))
        else:
            flash("please enter correct details")
    return render_template("Login.html", form=form)


# Route to save data received via AJAX to JSON and CSV files.
@app.route('/save-data', methods=['POST'])
def save_data():
    data = request.get_json()  # Receive the data from the AJAX request
    save_as_json(data)
    save_as_csv(data)
    return jsonify({'message': 'Data saved successfully'})


# Function to save data as JSON file.
def save_as_json(data):
    with open('data.json', 'w') as file:
        json.dump(data, file)


# Function to save data as CSV file.
def save_as_csv(data):
    with open('data.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['x', 'y'])  # Replace with the appropriate column headers
        for area in data:
            writer.writerow([area['x'], area['y']])  # Replace with the appropriate data fields


# Decorator to token authentication for some routes.
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = current_user.token
        if not token:
            return render_template("alert.html", message="Token is missing")
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except:
            return render_template("alert.html", message="Token is invalid")
        return f(*args, **kwargs)

    return decorated


# Route to log out the user.
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    current_year = datetime.datetime.now().year
    flash("You Have Been Logged Out!")
    return redirect(url_for('login'))


# Function to check if the file extension is allowed
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


@app.route('/temp_success', methods=['GET', 'POST'])
@login_required
def temp_success():
    current_year = datetime.datetime.now().year
    flash("Template uploaded successfully!")
    return render_template("temp.html")


# Route for managing uploads of templates and image/PDF files.
@app.route("/", methods=["GET", "POST"])
@login_required
def template():
    current_year = datetime.datetime.now().year
    token = current_user.token
    app.config["IMAGES"] = "./static/upload/images"
    app.config["LABELS"] = []
    app.config["uploaded_files"] = []
    app.config["TEMP_NAME"] = []
    app.config["TEMP_Imagecode"] = ""
    app.config["Data"] = []
    file_list = os.listdir(app.config["IMAGES"])

    # Loop through the files and delete each one
    for file_name in file_list:
        file_path = os.path.join(app.config["IMAGES"], file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)
    form = UploadFileForm()
    # Open the CSV file in write mode, which will overwrite the existing data
    with open("./out.csv", 'w', newline='') as csv_file:
        # Create a CSV writer
        csv_writer = csv.writer(csv_file)

        # Write an empty list to the file, effectively erasing all data
        csv_writer.writerows([])

    if request.method == "POST":
        # Process uploaded files and store them in the appropriate folders.
        files = form.file.data
        if len(files) == 0:
            flash('No files selected')
            return redirect(url_for('template', token=token))
        else:
            # Create directories if they don't exist
            os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "images"), exist_ok=True)
            os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "upload"), exist_ok=True)
            os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "jsonfile"), exist_ok=True)
            app.config["OUT"] = "out.csv"

            tmp = form.Temp_name.data
            app.config["TEMP_NAME"].insert(0, tmp)

            # Process each file and save it to the appropriate folder
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config["UPLOAD_FOLDER"], "images", filename)
                    file.save(file_path)  # Save the file to the desired path
                    app.config["uploaded_files"].append(filename)
                    if "pdf" not in os.path.splitext(filename)[1].lower():
                        app.config["TEMP_NAME"].insert(1, "Image")
                    else:
                        # Convert PDF files to PNG using pdf2image
                        pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], "upload", secure_filename(file.filename))
                        file.save(pdf_path)
                        try:
                            # Convert each PDF page to a PNG image
                            first_page_images = convert_from_path(pdf_path, first_page=0, last_page=0)

                            if first_page_images:
                                png_path = os.path.join(app.config["TEMP_NAME"], f"page_1.png")
                                first_page_images[0].save(png_path, format="PNG")  # Then save the file
                            os.remove(pdf_path)
                        except Exception as e:
                            flash("PDF to PNG conversion error: " + str(e))
                            print("PDF to PNG conversion error:", e)
            app.config["uploaded_files"].sort()

        for (dirpath, dirnames, filenames) in os.walk(os.path.join(app.config["UPLOAD_FOLDER"], "images")):
            files = filenames
            break
        print("filenames:", files)
        app.config["FILES"] = files
        return redirect(f"/tagger?token={token}", code=302)
    else:
        # Fetch data related to templates from the database.
        Data = Cordinate_Data.query.filter_by(user_id=current_user.id).all()
        d = tbl_user.query.filter_by(id=current_user.id).first()
        return render_template(
            "template.html",
            token=token,
            current_year=current_year,
            current_user=current_user,
            Data=Data,
            status=int(d.status),
            total=len(Data),
            form=form,
        )


@app.route("/image/<filename>")
def serve_image(filename):
    images_folder = app.config["IMAGES"]
    return send_from_directory(images_folder, filename)


# Route for tagging images and PDFs with coordinates.
@app.route("/tagger", methods=["GET", "POST"])
@token_required
@login_required
def tagger():
    try:
        token = request.args.get("token")
        done = request.args.get("done")
        image = request.args.get("image")
        if done == "Yes":
            with open(app.config["OUT"], "a") as f:
                for label in app.config["LABELS"]:
                    f.write(label["id"]
                            + ","
                            + label["name"]
                            + ","
                            + str(round(float(label["xMin"])))
                            + ","
                            + str(round(float(label["xMax"])))
                            + ","
                            + str(round(float(label["yMin"])))
                            + ","
                            + str(round(float(label["yMax"])))
                            + ","
                            + str(label["dformat"])
                            + "\n"
                            )
                    # coTox(image,label["id"],label["name"],round(float(label["xMin"])),round(float(label["yMin"])),round(float(label["xMax"])),round(float(label["yMax"])))
            with open(app.config["OUT"], "r") as s:
                data = s.read()
            x = datetime.datetime.now(timezone("Asia/Kolkata"))
            cordinates = data
            templateName = app.config["TEMP_NAME"][0]
            Template_format = app.config["TEMP_NAME"][1]
            print(Template_format)
            current_time = x.strftime("%I:%M:%S %p")
            Date = f"{x.day}/{x.month}/{x.year}"
            Day = x.strftime("%A")
            adddata = Cordinate_Data(
                cordinates=cordinates,
                user_id=current_user.id,
                Tem_name=templateName,
                Date=Date,
                Time=current_time,
                Day=Day,
                tempimage=app.config["TEMP_Imagecode"],
                file=image,
                Tem_format=Template_format,
            )
            db.session.add(adddata)
            db.session.commit()
            with open(app.config["OUT"], "r+") as f:
                f.truncate(0)
            return redirect(url_for("temp_success"))
        # image = app.config["FILES"][app.config["HEAD"]]
        # image=str(app.config["HEAD"])+".jpg"
        if type(app.config["uploaded_files"][app.config["HEAD"]]) == str:
            image = app.config["FILES"][app.config["HEAD"]]
        else:
            image = str(app.config["uploaded_files"][app.config["HEAD"]])
        labels = app.config["LABELS"]
        not_end = not (app.config["HEAD"] == len(app.config["FILES"]) - 1)
        d = tbl_user.query.filter_by(id=current_user.id).first()

        return render_template(
                "tagger.html",
                not_end=not_end,
                image=image,
                labels=labels,
                head=app.config["HEAD"] + 1,
                len=len(app.config["FILES"]),
                token=token,
                status=int(d.status),
            )
    except IndexError:
        return render_template("nolong.html")


@app.route("/next")
@token_required
@login_required
def next():
    token = request.args.get("token")
    done = request.args.get("done")
    app.config["HEAD"] = app.config["HEAD"] + 1
    with open(app.config["OUT"], "a") as f:
        for label in app.config["LABELS"]:
            f.write(label["id"]
                    + ","
                    + label["name"]
                    + ","
                    + str(round(float(label["xMin"])))
                    + ","
                    + str(round(float(label["xMax"])))
                    + ","
                    + str(round(float(label["yMin"])))
                    + ","
                    + str(round(float(label["yMax"])))
                    + ","
                    + str(label["dformat"])
                    + "\n"
                    )
            # coTox(image,label["id"],label["name"],round(float(label["xMin"])),round(float(label["yMin"])),round(float(label["xMax"])),round(float(label["yMax"])))
    app.config["LABELS"] = []
    return redirect(url_for("tagger", token=[token], done=[done]))


@app.route("/previous")
@token_required
@login_required
def previous():
    token = request.args.get("token")
    done = request.args.get("done")
    # image = app.config["FILES"][app.config["HEAD"]]
    # image=str(app.config["HEAD"])+".jpg"
    image = str(app.config["uploaded_files"][app.config["HEAD"]])

    with open(app.config["OUT"], "a") as f:
        for label in app.config["LABELS"]:
            f.write(label["id"]
                    + ","
                    + label["name"]
                    + ","
                    + str(round(float(label["xMin"])))
                    + ","
                    + str(round(float(label["xMax"])))
                    + ","
                    + str(round(float(label["yMin"])))
                    + ","
                    + str(round(float(label["yMax"])))
                    + ","
                    + str(label["dformat"])
                    + "\n"
                    )
            # coTox(image,label["id"],label["name"],round(float(label["xMin"])),round(float(label["yMin"])),round(float(label["xMax"])),round(float(label["yMax"])))
    app.config["LABELS"] = []

    app.config["HEAD"] = app.config["HEAD"] - 1
    return redirect(url_for("tagger", token=[token], done=[done], image=[image]))


@app.route("/add/<id>")
@token_required
@login_required
def add(id):
    token = request.args.get("token")
    xMin = request.args.get("xMin")
    xMax = request.args.get("xMax")
    yMin = request.args.get("yMin")
    yMax = request.args.get("yMax")
    app.config["LABELS"].append(
        {
            "id": id,
            "name": "",
            "xMin": xMin,
            "xMax": xMax,
            "yMin": yMin,
            "yMax": yMax,
            "dformat": "",
        }
    )
    return redirect(url_for("tagger", token=[token]))


@app.route("/remove/<id>")
@token_required
@login_required
def remove(id):
    token = request.args.get("token")
    index = int(id) - 1
    del app.config["LABELS"][index]
    for label in app.config["LABELS"][index:]:
        label["id"] = str(int(label["id"]) - 1)
    return redirect(url_for("tagger", token=[token]))


# Route for managing uploads of templates and image/PDF files.
@app.route("/upload/<int:id>", methods=["GET", "POST"])
@token_required
@login_required
def upload(id):
    files = None
    already_posted_files = "no"
    token = request.args.get("token")
    app.config["HEAD"] = 0
    date = request.form.get("date")
    time = request.form.get("time")
    choose_scheduler = request.form.get("choose-scheduler")
    print("choose-scheduler", choose_scheduler)
    cor_data = Cordinate_Data.query.filter_by(cord_id=id).first()
    form = UploadFileForm()
    if request.method == "POST":
        already_posted_files = "yes"
        files = form.file.data
        jsonfile = form.jsonfile.data
        option = request.form["option"]
        if option == "2":
            jsonfile.save(
                os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    "./static/jsonfile",
                    secure_filename(jsonfile.filename),
                )
            )
        app.config["Data"] = []
        new_data = {}
        count_img = 0
        filenames = []
        folder_path = os.path.join(

            os.path.abspath(os.path.dirname(__file__)),

            app.config["UPLOAD_FOLDER_NORMAL"],

            str(uuid.uuid4()))
        os.mkdir(folder_path)
        if choose_scheduler:
            # If the scheduler is chosen, save the task to the database and redirect to the thank you page.
            print("INSIDE CHOOSE")
            app.config["Data"] = []
            new_data = {}
            count_img = 0

            for file in files:
                extention = os.path.splitext(file.filename)[1].lower()

                # Generate a unique filename for the PNG conversion
                png_filename = str(uuid.uuid4()) + ".png"

                if extention in ['.jpg', '.jpeg', '.gif', '.png', '.tif', '.tiff']:
                    # Convert image files to PNG using PIL
                    with Image.open(file) as img:
                        # Convert the image to RGB mode if it's not already
                        if img.mode != "RGB":
                            img = img.convert("RGB")

                        # Convert and save the image to PNG format
                        png_path = os.path.join(folder_path, secure_filename(png_filename))
                        img.save(png_path, format="PNG")
                elif extention == ".pdf":
                    # Convert PDF files to PNG using pdf2image
                    pdf_path = os.path.join(folder_path, secure_filename(file.filename))
                    file.save(pdf_path)

                    # Convert each PDF page to a PNG image
                    pdf_images = convert_from_path(pdf_path, dpi=300)
                    for page_num, pdf_image in enumerate(pdf_images):
                        if page_num >= 100:
                            break  # Limit to 100 pages
                        png_path = os.path.join(folder_path, f"page_{page_num + 1}.png")
                        pdf_image.save(png_path, format="PNG")  # Then save the file

            scheduled_time = request.form.get('scheduled_time')  # Get the scheduled extraction time from the form
            schedule_extraction(current_user.id, folder_path, option, cor_data, scheduled_time)
            if already_posted_files == "yes":
                return render_template("thanks.html")


        else:

            print("INSIDE NORMAL")

            app.config["Data"] = []

            new_data = {}

            count_img = 0

            for file in files:
                extention = os.path.splitext(file.filename)[1].lower()

                # Generate a unique filename for the PNG conversion
                png_filename = str(uuid.uuid4()) + ".png"

                if extention in ['.jpg', '.jpeg', '.gif', '.png', '.tif', '.tiff']:
                    # Convert image files to PNG using PIL
                    with Image.open(file) as img:
                        # Convert the image to RGB mode if it's not already
                        if img.mode != "RGB":
                            img = img.convert("RGB")

                        # Convert and save the image to PNG format
                        png_path = os.path.join(folder_path, secure_filename(png_filename))
                        img.save(png_path, format="PNG")
                elif extention == ".pdf":
                    # Convert PDF files to PNG using pdf2image
                    pdf_path = os.path.join(folder_path, secure_filename(file.filename))
                    file.save(pdf_path)

                    # Convert each PDF page to a PNG image
                    pdf_images = convert_from_path(pdf_path, dpi=300)
                    for page_num, pdf_image in enumerate(pdf_images):
                        if page_num >= 100:
                            break  # Limit to 100 pages
                        png_path = os.path.join(folder_path, f"page_{page_num + 1}.png")
                        pdf_image.save(png_path, format="PNG")  # Then save the file

            MainImg(current_user.id, folder_path, option, cor_data)

        return redirect(url_for("download_list", token=[token]))

    try:
        shutil.rmtree("./static/jsonfile_normal")
        shutil.rmtree("./static/static/images_normal")
        flash("Please wait for converting")
        os.mkdir("./static/jsonfile_normal")
        os.mkdir("./static/static/images_normal")

    except:
        pass

    d = tbl_user.query.filter_by(id=current_user.id).first()
    return render_template("upload.html", form=form, token=token, status=int(d.status))


# Route for changing user status
@app.route("/HelpChange", methods=["POST", "GET"])
@token_required
@login_required
def Helpchange():
    # Get the 'token' and 'status' from the request arguments
    token = request.args.get("token")
    status = request.args.get("status")

    # Update the status of the user in the database
    d = tbl_user.query.filter_by(id=current_user.id).first()
    d.status = status
    db.session.add(d)
    db.session.commit()

    print("yes")
    return redirect(url_for("setting", token=[token]))


# Route for changing the date format
@app.route("/changedate", methods=["POST", "GET"])
def FormatChange():
    print("hello" * 50)
    # Get the 'token' and 'dateformat' from the request arguments
    token = request.args.get("token")
    dateformat = request.args.get("dateformat")

    # Update the date format of the user in the database
    d = tbl_user.query.filter_by(id=current_user.id).first()
    d.dateformat = str(dateformat)
    db.session.add(d)
    db.session.commit()

    print("yes")
    return redirect(url_for("setting", token=[token]))


# Route for deleting data
@app.route("/delete/<int:id>")
@token_required
@login_required
def delete(id):
    # Get the 'token' from the request arguments
    token = request.args.get("token")

    # Delete data from the Cordinate_Data table for the specified user
    d = Cordinate_Data.query.filter_by(cord_id=id, user_id=current_user.id).first()
    db.session.delete(d)
    db.session.commit()

    return redirect(url_for("template", token=[token]))


# Route for updating label information
@app.route("/label/<id>")
def label(id):
    # Get the 'token', 'name', and 'dformat' from the request arguments
    token = request.args.get("token")
    name = request.args.get("name")
    dformat = request.args.get("dformat")
    print(id, name, dformat)
    # Update the label information in the app configuration
    app.config["LABELS"][int(id) - 1]["name"] = name
    app.config["LABELS"][int(id) - 1]["dformat"] = dformat

    return redirect(url_for("tagger", token=[token]))


# Route for sending images
@app.route("/image/<f>")
def images(f):
    images = app.config["IMAGES"]
    return send_file(images + f"/{f}")


@app.route('/download_list', methods=["POST", "GET"])
@token_required
@login_required
def download_list():
    Data = ExtractedFiles.query.filter_by(user_id=current_user.id).all()
    return render_template("extracted_files.html", data=Data)


# Route for downloading data as JSON
@app.route("/download/<int:id>", methods=["POST", "GET"])
@login_required
def download(id):
    # Get the 'token' from the request arguments
    token = current_user.token

    try:
        # Fetch user data from the database
        d = ExtractedFiles.query.filter_by(id=id).first()

        # Decode the filename from bytes to strings
        csv_filename = d.csvfilename.decode('utf-8')

        # Construct file path
        csv_path = os.path.join("./static/csvfile", csv_filename)

        # Load CSV data using pandas
        df = pd.read_csv(csv_path)

        # Convert the DataFrame to JSON
        json_data = df.to_json(orient='records', indent=4)

        # Render the template with data
        return render_template(
            "JsonData.html",
            current_year=datetime.datetime.now().year,
            tables=df.to_dict("records"),  # Convert DataFrame to a list of dictionaries
            columns=df.columns.tolist(),  # Convert DataFrame columns to a list
            data_json=json_data,
            token=token
        )

    except NoResultFound:
        flash("No data found for the specified ID.")
        return redirect(url_for("dashboard"))


# Route for applying changes on a folder
@app.route("/apply/<int:id>")
@token_required
@login_required
def applyonfolder(id):
    # Get the 'token' from the request arguments
    token = request.args.get("token")

    # Fetch Cordinate_Data for the specified id and user
    data = Cordinate_Data.query.filter_by(cord_id=id, user_id=current_user.id).first()

    # Write the coordinates to a CSV file named "out.csv"
    with open("out.csv", "w") as f:
        f.write(data.cordinates)

    return redirect(url_for("upload", id=id))


@app.route("/setting", methods=["POST", "GET"])
@login_required
def setting():
    d = tbl_user.query.filter_by(id=current_user.id).first()
    return render_template(
        "setting.html", status=int(d.status), dateformat=d.dateformat
    )


@app.route('/switch_theme', methods=['GET', 'POST'])
@login_required
def switch_theme():
    selected_theme = request.form.get('theme')
    if selected_theme:
        session['theme'] = selected_theme
    return redirect(url_for('setting'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    # Your Flask app run code
    app.run()
    # Create and start the image processing thread
    thread = threading.Thread(target=MainImg, args=(user_id, image_folder, option, data))
    thread.start()
