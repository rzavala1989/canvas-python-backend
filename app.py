import os
import requests
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
import rembg
import numpy as np
from PIL import Image
from io import BytesIO
from openai import OpenAI
import time
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from flask_caching import Cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App and CORS
app = Flask(__name__)
CORS(app)

# Configure Cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MongoDB
# client = MongoClient('{MONGODB Connection string}', tls=True, tlsAllowInvalidCertificates=True)
db = client['test-database']
uploads_collection = db['uploads-collection']
generated_images_collection = db['generated-images-collection']
print(client.server_info())

# OpenAI
client = OpenAI()

# Define the allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'

@app.route('/remove-background', methods=['POST'])
def remove_background():
    # Check if the request contains a file
    if 'file' in request.files:
        file = request.files['file']
        # Convert the file to an image
        image = Image.open(file.stream)
    else:
        # Extract the necessary parameters from the request
        image_url = request.json.get('image_url')
        # Make a GET request to the image URL
        r = requests.get(image_url)
        # Convert the response content to an image
        image = Image.open(BytesIO(r.content))

    # Convert the image to RGBA
    image = image.convert('RGBA')

    # Convert the image to a numpy array
    image = np.array(image)

    # Use rembg to remove the background
    result = rembg.remove(image)

    # Convert the result to an image
    result = Image.fromarray(result)

    # Save the result to a BytesIO object
    output = BytesIO()
    result.save(output, format='PNG')
    output.seek(0)

    # Return the result
    return send_file(output, mimetype='image/png')


@app.route('/upload-image', methods=['POST'])
def upload_image():
    # check if the post request has the file part
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return 'No selected file', 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # Save the file path to the MongoDB database
        result = uploads_collection.insert_one({'image_path': os.path.join(app.config['UPLOAD_FOLDER'], filename)})
        print(f"Data saved with ID: {result.inserted_id}")
        return 'File uploaded successfully', 200
    else:
        return 'Unsupported file type', 400


@app.route('/get-uploads', methods=['GET'])
@cache.cached(timeout=60)
def get_uploads():
    uploads = uploads_collection.find()  # Assuming 'collection' is your MongoDB collection for uploads
    return jsonify([{**upload, '_id': str(upload['_id'])} for upload in uploads])

# GoAPI
@app.route('/generate-image', methods=['POST'])
def generate_image():
    text = request.json.get('text')
    # Make a POST request to the imagine endpoint
    imagine_url = "https://api.midjourneyapi.xyz/mj/v2/imagine"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': os.getenv('GOAPI_KEY')
    }
    data = {
        'prompt': text,
        'process_mode': 'fast'
    }
    r = requests.post(imagine_url, headers=headers, json=data)
    response = r.json()
    print(response)
    # Check if the request was successful
    if response['status'] != 'success':
        return 'Failed to generate image', 400

    # Get the task_id from the response
    task_id = response['task_id']

    # Make a POST request to the fetch endpoint
    fetch_url = "https://api.midjourneyapi.xyz/mj/v2/fetch"
    data = {
        'task_id': task_id
    }
    r = requests.post(fetch_url, headers=headers, json=data)
    response = r.json()
    time.sleep(10)
    while response['status'] != 'finished':
        r = requests.post(fetch_url, headers=headers, json=data)
        response = r.json()
        time.sleep(10)

    # Save the response to the MongoDB database
    generated_images = generated_images_collection.insert_one(response)
    print(f"Data saved with ID: {str(generated_images.inserted_id)}")  # Convert ObjectId to string

    # Exclude the '_id' field when returning the response
    response.pop('_id', None)
    return response


@app.route('/get-images', methods=['GET'])
def get_images():
    images = generated_images_collection.find()
    return jsonify([{**image, '_id': str(image['_id'])} for image in images])

@app.route('/upscale', methods=['POST'])
def upscale():
    # Extract the necessary parameters from the request
    origin_task_id = request.json.get('origin_task_id')
    index = request.json.get('index', '1')

    # Make a POST request to the upscale endpoint
    upscale_url = "https://api.midjourneyapi.xyz/mj/v2/upscale"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': os.getenv('GOAPI_KEY')
    }
    data = {
        'origin_task_id': origin_task_id,
        'index': index,
    }
    r = requests.post(upscale_url, headers=headers, json=data)
    response = r.json()

    # Check if the request was successful
    if response['status'] != 'success':
        return 'Failed to upscale image', 400

    # Get the task_id from the response
    task_id = response['task_id']

    # Make a POST request to the fetch endpoint
    fetch_url = "https://api.midjourneyapi.xyz/mj/v2/fetch"
    data = {
        'task_id': task_id
    }
    r = requests.post(fetch_url, headers=headers, json=data)
    response = r.json()
    time.sleep(10)
    while response['status'] != 'finished':
        r = requests.post(fetch_url, headers=headers, json=data)
        response = r.json()
        time.sleep(10)

    # Save the response to the MongoDB database
    generated_images = generated_images_collection.insert_one(response)
    print(f"Data saved with ID: {str(generated_images.inserted_id)}")  # Convert ObjectId to string

    # Exclude the '_id' field when returning the response
    response.pop('_id', None)
    return response

@app.route('/inpaint', methods=['POST'])
def inpaint():
    # Extract the necessary parameters from the request
    origin_task_id = request.json.get('origin_task_id')
    prompt = request.json.get('prompt')
    mask = request.json.get('mask')

    # Make a POST request to the inpaint endpoint
    inpaint_url = "https://api.midjourneyapi.xyz/mj/v2/inpaint"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': os.getenv('GOAPI_KEY')
    }
    data = {
        'origin_task_id': origin_task_id,
        'prompt': prompt,
        'mask': mask,
    }
    r = requests.post(inpaint_url, headers=headers, json=data)
    response = r.json()

    # Check if the request was successful
    if response['status'] != 'success':
        error_message = response.get('error', response.get('message', 'Unknown error'))
        return f'Failed to inpaint image: {error_message}', 400

    # Get the task_id from the response
    task_id = response['task_id']

    # Make a POST request to the fetch endpoint
    fetch_url = "https://api.midjourneyapi.xyz/mj/v2/fetch"
    data = {
        'task_id': task_id
    }
    r = requests.post(fetch_url, headers=headers, json=data)
    response = r.json()
    time.sleep(10)
    while response['status'] != 'finished':
        r = requests.post(fetch_url, headers=headers, json=data)
        response = r.json()
        time.sleep(10)

    # Save the response to the MongoDB database
    generated_images = generated_images_collection.insert_one(response)
    print(f"Data saved with ID: {str(generated_images.inserted_id)}")  # Convert ObjectId to string

    # Exclude the '_id' field when returning the response
    response.pop('_id', None)
    return response

@app.route('/outpaint', methods=['POST'])
def outpaint():
    # Extract the necessary parameters from the request
    origin_task_id = request.json.get('origin_task_id')
    zoom_ratio = request.json.get('zoom_ratio', '1')
    aspect_ratio = request.json.get('aspect_ratio', '1:1')
    prompt = request.json.get('prompt', '')


    # Make a POST request to the outpaint endpoint
    outpaint_url = "https://api.midjourneyapi.xyz/mj/v2/outpaint"
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': os.getenv('GOAPI_KEY')
    }
    data = {
        'origin_task_id': origin_task_id,
        'zoom_ratio': zoom_ratio,
        'aspect_ratio': aspect_ratio,
        'prompt': prompt,
    }
    r = requests.post(outpaint_url, headers=headers, json=data)
    response = r.json()

    # Check if the request was successful
    if response['status'] != 'success':
        return 'Failed to outpaint image', 400

    # Get the task_id from the response
    task_id = response['task_id']

    # Make a POST request to the fetch endpoint
    fetch_url = "https://api.midjourneyapi.xyz/mj/v2/fetch"
    data = {
        'task_id': task_id
    }
    r = requests.post(fetch_url, headers=headers, json=data)
    response = r.json()
    time.sleep(10)
    while response['status'] != 'finished':
        r = requests.post(fetch_url, headers=headers, json=data)
        response = r.json()
        time.sleep(10)

    # Save the response to the MongoDB database
    generated_images = generated_images_collection.insert_one(response)
    print(f"Data saved with ID: {str(generated_images.inserted_id)}")  # Convert ObjectId to string

    # Exclude the '_id' field when returning the response
    response.pop('_id', None)
    return response




if __name__ == '__main__':
    app.run()
