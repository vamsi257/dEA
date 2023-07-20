import cv2
import pickle
import jwt
from flask import Flask, render_template, request, redirect, url_for, abort, flash, session, jsonify
import os
from flask_login import UserMixin, logout_user, current_user, login_user, LoginManager, login_required
from wtforms import StringField, PasswordField, SubmitField, MultipleFileField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from pytz import timezone
from flask_bcrypt import Bcrypt
import socket
from functools import wraps
import pymysql
import base64
import numpy as np
import shutil
import csv
import json
import uuid
from werkzeug.utils import secure_filename
from task_model import save_task_to_database
import DataExtractNormal
import pandas as pd
from pdf2image import convert_from_path
from page_limiter import page_limiter

roi_coordinates = []

app = Flask(__name__)
app.config["IMAGES"] = "./images"
app.config["LABELS"] = []
app.config["HEAD"] = 0
app.config["uploaded_files"] = []
app.config["TEMP_NAME"] = []
app.config["TEMP_Imagecode"] = ""
app.config["Data"] = []
app.config['UPLOAD_FOLDER'] = r'./uploads'  # Folder to store uploaded files
app.config['STATIC_FOLDER'] = 'static'  # Folder to serve static files
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Passw0rd123@localhost/test'  # Database connection
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["SECRET_KEY"] = "supersecretkeybkiran"
app.config["UPLOAD_FOLDER"] = "./upload"
app.config["UPLOAD_FOLDER_NORMAL"] = "upload_normal"
app.config['poppler_path'] = r"D:\work1\poppler-0.67.0_x86\poppler-0.67.0\bin"
db = SQLAlchemy(app)
login_manager = LoginManager()  # To manage Login
login_manager.init_app(app)
login_manager.login_view = "login"
bcrypt = Bcrypt(app)


@login_manager.user_loader  # To load the User
def load_user(user_id):
    return tbl_user.query.get(int(user_id))


class tbl_user(db.Model, UserMixin):  # User table
    id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(20), nullable=True)
    username = db.Column(db.String(20), nullable=True, unique=True)
    password = db.Column(db.String(80), nullable=False)
    status = db.Column(db.Integer)
    token = db.Column(db.String(1000), nullable=False)
    dateformat = db.Column(db.String(80), nullable=False, default="No")
    Date_time = db.Column(db.DateTime, default=datetime.now(timezone('Asia/Kolkata')))
    ip = db.Column(db.String(20), default="None")
    data = db.relationship("Cordinate_Data", backref="author", lazy=True)

    def __repr__(self) -> str:
        return "<tbl_user %r>" % self.User_Name


class Cordinate_Data(UserMixin, db.Model):  # Coordinate table
    cord_id = db.Column(db.Integer, primary_key=True)
    Tem_name = db.Column(db.String(80), nullable=False)
    Tem_format = db.Column(db.String(80), nullable=False)
    cordinates = db.Column(db.Text)
    Date = db.Column(db.String(80), nullable=False)
    Time = db.Column(db.String(80), nullable=False)
    Day = db.Column(db.String(80), nullable=False)
    tempimage = db.Column(db.Text)
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


class UploadFileForm(FlaskForm):
    file = MultipleFileField(validators=[InputRequired()])
    Temp_name = StringField(validators=[InputRequired(), Length(min=4, max=20)])


# Home page
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    current_year = datetime.now().year
    name = current_user.Name
    username = current_user.username
    date = current_user.Date_time
    row = [name, current_user.id, username, date]
    return render_template('dashboard.html', data=row, current_year=current_year)


# registration
@app.route("/register", methods=["GET", "POST"])
def signup():
    current_year = datetime.now().year
    form = RegisterForm()
    if request.method == 'POST':
        username = form.username.data
        user = tbl_user.query.filter_by(username=username).first()
        if user:
            flash("You already having the account on this email!")
            return render_template("login.html", current_year=current_year)
        else:
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
    current_year = datetime.now().year
    form = LoginForm()
    if form.validate_on_submit():
        user = tbl_user.query.filter_by(username=form.username.data).first()
        hostname = socket.gethostname()
        IPadd = socket.gethostbyname(hostname)
        if user:
            if user.ip == "None":
                user.ip = str(IPadd)
                db.session.add(user)
                db.session.commit()
                return redirect(url_for('login'))
            elif user.ip != IPadd:
                abort(400, "You cannot access this application, contact to owner")
            elif bcrypt.check_password_hash(
                    user.password, form.password.data
            ) and user.ip == str(IPadd):
                login_user(user)
                token = jwt.encode(
                    {
                        "user": form.username.data,
                        "exp": datetime.utcnow() + timedelta(minutes=60),
                    },
                    app.config["SECRET_KEY"],
                )
                user.token = token
                db.session.add(user)
                db.session.commit()
                return redirect(url_for("home", current_year=current_year))
        else:
            flash("please enter correct details")
    return render_template("Login.html", form=form, current_year=current_year)


@app.route('/save-data', methods=['POST'])
def save_data():
    data = request.get_json()  # Receive the data from the AJAX request
    save_as_json(data)
    save_as_csv(data)
    return jsonify({'message': 'Data saved successfully'})


def save_as_json(data):
    with open('data.json', 'w') as file:
        json.dump(data, file)


def save_as_csv(data):
    with open('data.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['x', 'y'])  # Replace with the appropriate column headers
        for area in data:
            writer.writerow([area['x'], area['y']])  # Replace with the appropriate data fields


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get("token")
        if not token:
            return render_template("alert.html", message="Token is missing")
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except:
            return render_template("alert.html", message="Token is invalid")
        return f(*args, **kwargs)

    return decorated


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    current_year = datetime.now().year
    flash("You Have Been Logged Out!")
    return redirect(url_for('login', current_year=current_year))


@app.route("/template", methods=["GET", "POST"])
@login_required
def template():
    current_year = datetime.now().year
    token = current_user.token
    app.config["IMAGES"] = "images"
    app.config["LABELS"] = []
    app.config["uploaded_files"] = []
    app.config["TEMP_NAME"] = []
    form = UploadFileForm()
    if request.method == "POST":
        files = form.file.data
        if len(files) == 0:
            flash('No files selected')
            return redirect(url_for('dashboard', token=token))
        else:
            shutil.rmtree(r"./images")
            if os.path.exists("out.csv"):
                os.remove("out.csv")
            shutil.rmtree(r"./upload")
            shutil.rmtree(r"./jsonfile")
            os.mkdir(r"./images")
            os.mkdir(r"./upload")
            os.mkdir(r"./jsonfile")
            app.config["OUT"] = "out.csv"
            with open("out.csv", "w") as csvfile:
                csvfile.write("image,id,name,xMin,xMax,yMin,yMax,Format\n")
            tmp = form.Temp_name.data
            app.config["TEMP_NAME"].insert(0, tmp)
            for file in files:
                filename = secure_filename(file.filename)
                extension = os.path.splitext(filename)[1]
                if "pdf" not in extension.lower():
                    file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
                    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    new_filename = os.path.join("./images", secure_filename(os.path.splitext(filename)[0] + ".png"))
                    cv2.imwrite(new_filename, img)
                    app.config["uploaded_files"].append(new_filename)
                    app.config["TEMP_NAME"].insert(1, "Image")
                else:
                    file.save(os.path.join("./images", filename))
                    app.config["uploaded_files"].append(filename)
                    app.config["TEMP_NAME"].insert(1, "Pdf")
                with open(os.path.join("./images", filename), "rb") as pdf_file:
                    app.config["TEMP_Imagecode"] = base64.b64encode(pdf_file.read()).decode("UTF")
            app.config["uploaded_files"].sort()
            # ...

        for (dirpath, dirnames, filenames) in os.walk(app.config["IMAGES"]):
            files = filenames
            break
        app.config["FILES"] = files
        return redirect(f"/tagger?token={token}", code=302)
    else:
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


@app.route("/tagger", methods=["GET", "POST"])
@token_required
@login_required
def tagger():
    current_year = datetime.now().year
    token = request.args.get("token")
    done = request.args.get("done")
    if done == "Yes":
        with open(app.config["OUT"], "a") as f:
            for label in app.config["LABELS"]:
                f.write(
                    image
                    + ","
                    + label["id"]
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
        x = datetime.datetime.now()
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
            Tem_format=Template_format,
        )
        db.session.add(adddata)
        db.session.commit()
        return redirect(url_for("upload", token=[token], current_year=current_year))
    directory = app.config["IMAGES"]
    # image = app.config["FILES"][app.config["HEAD"]]
    # image=str(app.config["HEAD"])+".jpg"
    if type(app.config["uploaded_files"][app.config["HEAD"]]) == str:
        image = os.path.join(directory, app.config["FILES"][app.config["HEAD"]])
    else:
        image = str(app.config["uploaded_files"][app.config["HEAD"]]) + ".jpg"
    labels = app.config["LABELS"]
    not_end = not (app.config["HEAD"] == len(app.config["FILES"]) - 1)
    d = tbl_user.query.filter_by(id=current_user.id).first()
    return render_template(
        "tagger.html",
        current_year=current_year,
        not_end=not_end,
        directory=directory,
        image=image,
        labels=labels,
        head=app.config["HEAD"] + 1,
        len=len(app.config["FILES"]),
        token=token,
        status=int(d.status),
    )


@app.route("/upload", methods=["GET", "POST"])
@token_required
@login_required
def upload():
    current_year = datetime.now().year
    choose_scheduler = None
    files = None
    already_posted_files = "no"
    token = request.args.get("token")
    app.config["HEAD"] = 0
    #######################
    date = request.form.get("date")
    time = request.form.get("time")
    choose_scheduler = request.form.get("choose-scheduler")
    print("😊😊😊 choose-scheduler", choose_scheduler)
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
                    "./jsonfile",
                    secure_filename(jsonfile.filename),
                )
            )
        app.config["Data"] = []
        new_data = {}
        count_img = 0
        filenames = []
        if choose_scheduler:
            print("INSIDE CHOOSE")
            app.config["Data"] = []
            new_data = {}
            count_img = 0

            for file in files:

                extention = os.path.splitext(file.filename)[1]

                file.filename = str(uuid.uuid4()) + extention
                print("extention", extention, "filename", file.filename)

                folderpath = os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    app.config["UPLOAD_FOLDER"],
                    secure_filename(file.filename),
                )
                file.save(
                    os.path.join(
                        os.path.abspath(os.path.dirname(__file__)),
                        app.config["UPLOAD_FOLDER"],
                        secure_filename(file.filename),
                    )
                )  # Then save the file

                # print(os.path.splitext(file.filename)[0],extention)
                db_extention = "img"
                if extention in [".pdf", ".PDF"]:
                    db_extention = "pdf"

                # for file in files:
                filenames.append(file.filename)

            print("filenames:", filenames)
            task_id = save_task_to_database(date, time, filenames, db_extention)
            filenames = []
            if already_posted_files == "yes":
                return render_template("thanks.html", current_year=current_year)

        else:
            print("INSIDE NORMAL")

            app.config["Data"] = []
            new_data = {}
            count_img = 0
            for file in files:

                # old_filename, old_extension = file.filename.rsplit(".", 1)
                # file.filename = str(random.randint(0,9999))+"."+old_extension

                folderpath = os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    app.config["UPLOAD_FOLDER_NORMAL"],
                    secure_filename(file.filename),
                )
                file.save(
                    os.path.join(
                        os.path.abspath(os.path.dirname(__file__)),
                        app.config["UPLOAD_FOLDER_NORMAL"],
                        secure_filename(file.filename),
                    )
                )  # Then save the file
                extention = os.path.splitext(file.filename)[1]
                # print(os.path.splitext(file.filename)[0],extention)

                if extention in [".pdf", ".PDF"]:

                    app.config['is_PDF'] = True
                    # ------new code start
                    # pages=convert_from_path(folderpath,poppler_path=r"D:\flask\Assignment\assignment 1\drive-download-20230222T084703Z-001\poppler-0.67.0_x86\poppler-0.67.0\bin")
                    pages = convert_from_path(
                        folderpath, poppler_path=app.config['poppler_path'])
                    path = os.path.join("./images_normal")
                    # os.remove(f'./images/{file.filename}')
                    count = 0
                    for page in pages:
                        count += 1
                        jpg = path + "/" + str(count) + ".jpg"
                        page.save(jpg, "JPEG")
                        data = DataExtractNormal.Main(str(count) + ".jpg", file.filename, count, option)
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
                                print("yes number.........")

                                label_data = [
                                    record['label_data'].strip().replace(",", "").replace("%", "").replace("\n",
                                                                                                           ", ").replace(
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

                    # -----new code end
                elif extention in [".jpg", ".png", ".jpeg", ".tiff", ".tif"]:

                    page_count = 1

                    for f in os.listdir("./upload_normal"):

                        data = DataExtractNormal.MainImg(
                            os.path.join("./upload_normal", f), file.filename, page_count, option
                        )

                        os.remove(os.path.join("./upload_normal", f))

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
                        print("app.conig[data]", app.config["Data"])
                        app.config["Data"].append(record)
                        count_img += 1
                    if page_limiter(count_img):
                        break

        return redirect(url_for("download", token=[token], current_year=current_year))

    try:
        shutil.rmtree("./jsonfile_normal")
        shutil.rmtree("./images_normal")
        flash("Please wait for converting")
        os.mkdir("./jsonfile_normal")
        os.mkdir("./images_normal")

    except:
        pass

    d = tbl_user.query.filter_by(id=current_user.id).first()
    return render_template("upload.html", form=form, token=token, status=int(d.status), current_year=current_year)


if __name__ == '__main__':
    app.run()
