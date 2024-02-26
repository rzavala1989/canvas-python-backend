# Project Name

This is a Flask-based web application that provides various image processing functionalities. It uses MongoDB for data storage and OpenAI for image generation.

## Features

- Image background removal
- Image upload
- Image generation
- Image upscaling
- Image inpainting
- Image outpainting

## Installation

1. Clone the repository:
```bash
git clone https://github.com/rzavala1989/project.git
```
2. Navigate to the project directory:
```bash
cd project
```
3. Create a virtual environment:
```bash
python -m venv venv
```
4. Activate the virtual environment:
```bash
source venv/bin/activate
```

5. Install the required packages:
```bash
pip install -r requirements.txt
```

6. Set the environment variables in a .env file in root of the project:
```bash
GOAPI_KEY=your_goapi_key_here
MONGO_URI=your_mongo_uri_here
```

7. Run the application:
```bash
python app.py
```

### Endpoints

- POST /remove-background: Removes the background of an image.
- POST /upload-image: Uploads an image to the server.
- GET /get-uploads: Retrieves all uploaded images.
- POST /generate-image: Generates an image based on a text prompt.
- GET /get-images: Retrieves all generated images.
- POST /upscale: Upscales an image.
- POST /inpaint: Inpaints an image based on a mask and a prompt.
- POST /outpaint: Outpaints an image based on a zoom ratio, aspect ratio, and a prompt



