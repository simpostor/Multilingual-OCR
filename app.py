from flask import Flask, request, render_template, send_file
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import numpy as np
import os
import tempfile
from io import BytesIO
from groq import Groq

# Initialize the Groq client with your API key
client = Groq(api_key='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')

def ocr_core(image, languages):
    return pytesseract.image_to_string(image, lang=languages)

def translate_text(text):
    prompt = f"Translate the following text into English and generate only the translation in plain text format: {text}"
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],model="llama-3.2-90b-vision-preview",
    )
    return chat_completion.choices[0].message.content

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        languages = request.form.getlist('languages')
        ocr_text = None
        if file:
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext in ['.png', '.jpg', '.jpeg']:
                img = np.array(Image.open(file))
                ocr_text = ocr_core(img, '+'.join(languages))
            elif file_ext == '.pdf':
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    file.save(temp_file.name)
                    pdf_images = convert_from_path(temp_file.name)
                    ocr_text = ""
                    for page_image in pdf_images:
                        ocr_text += ocr_core(page_image, '+'.join(languages)) + "\n"
                    os.remove(temp_file.name)
            else:
                ocr_text = "Unsupported file type."

            # Redirect to intermediary page to display OCR result
            if ocr_text:
                return render_template('intermediary.html', ocr_text=ocr_text)
    return render_template('index.html', selected_language=[])

@app.route('/translate', methods=['POST'])
def translate_text_view():
    ocr_text = request.form.get('ocr_text')
    if ocr_text:
        translated_text = translate_text(ocr_text)
        return render_template('display.html', ocr_text=ocr_text, translated_text=translated_text)
    return 'No text to translate', 400

@app.route('/download', methods=['GET'])
def download_file():
    text = request.args.get('text', '')
    file_type = request.args.get('file_type', 'ocr')
    if text:
        text_stream = BytesIO(str.encode(text))
        text_stream.seek(0)
        file_name = f"{file_type}_result.txt"
        return send_file(text_stream, as_attachment=True, download_name=file_name, mimetype='text/plain')
    return 'No text to download', 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
