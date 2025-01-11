from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import os
from docx import Document

app = Flask(__name__)

# Set the upload folder and allowed file extensions
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to check file extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def upload_page():
    return render_template('index.html')  # Serves the HTML form

# Route to upload and process a docx file
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Extract text from the docx file
        extracted_text = extract_text_from_docx(file_path)
        return jsonify({"text": extracted_text})

    return jsonify({"error": "Invalid file type. Only .docx allowed."}), 400

# Function to extract text from a docx file
def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text.strip()

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
