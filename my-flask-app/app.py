from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
app.secret_key = 'your_secret_key'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        api_key = request.form['api_key']
        if api_key:
            os.environ['DASHSCOPE_API_KEY'] = api_key
            flash('API Key 已成功绑定', 'success')
        else:
            flash('请提供有效的API Key', 'danger')
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        api_key = os.getenv('DASHSCOPE_API_KEY')
        if not api_key:
            flash('请先绑定API Key', 'danger')
            return redirect(url_for('index'))

        prompt = request.form['prompt']
        uploaded_files = request.files.getlist('images')
        image_urls = []

        if not uploaded_files or prompt == '':
            flash('请上传图片并填写提示词', 'danger')
            return redirect(request.url)

        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_urls.append(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        session['image_urls'] = image_urls
        session['prompt'] = prompt

        return redirect(url_for('results'))

    return render_template('upload.html')

def call_qwen_vl_api(image_urls, prompt):
    api_key = os.getenv('DASHSCOPE_API_KEY')
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    data = {
        "model": "qwen-vl-max",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *[{"type": "image_url", "image_url": {"url": image_url}} for image_url in image_urls]
                ]
            }
        ]
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()

@app.route('/results')
def results():
    image_urls = session.get('image_urls', [])
    prompt = session.get('prompt', '')

    if not image_urls or not prompt:
        flash('没有找到上传的图片或提示词', 'danger')
        return redirect(url_for('upload'))

    response = call_qwen_vl_api(image_urls, prompt)
    return render_template('results.html', response=response)

if __name__ == '__main__':
    app.run(debug=True)
