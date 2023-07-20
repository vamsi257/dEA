@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return redirect(url_for('process', filename=filename))
    return redirect(url_for('index'))


@app.route('/process/<filename>')
def process(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Process the image using OpenCV
    image = cv2.imread(filepath)

    return render_template('process.html', image=filepath)


@app.route('/save_roi', methods=['POST'])
def save_roi():
    roi = request.get_json()
    roi_coordinates.append(roi)

    # Save the ROI coordinates using pickle
    with open('roi_coordinates.pkl', 'wb') as file:
        pickle.dump(roi_coordinates, file)

    return 'ROI coordinates saved successfully'