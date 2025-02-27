import os
import json
import tempfile
import firebase_admin
from firebase_admin import credentials, storage
from werkzeug.utils import secure_filename

def get_firebase_cred_path():
    # Try to get the JSON content from environment variable
    firebase_json = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_json:
        # Write the JSON content to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json') as temp_file:
            temp_file.write(firebase_json)
            return temp_file.name
    else:
        # Fallback: look for a file named 'serviceAccountKey.json' in the project root
        return os.path.join(os.getcwd(), 'serviceAccountKey.json')

cred_path = get_firebase_cred_path()

# Initialize Firebase Admin SDK if not already initialized.
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': os.environ.get('FIREBASE_BUCKET', 'your-project-id.appspot.com')
    })

def upload_file_to_firebase(file, folder):
    """
    Uploads a file to Firebase Cloud Storage within the specified folder.
    Returns the public URL of the uploaded file, or None if an error occurs.
    
    :param file: A FileStorage object from Flask representing the uploaded file.
    :param folder: The folder (prefix) in the bucket where the file should be stored.
    :return: The public URL of the uploaded file, or None if there was an error.
    """
    bucket = storage.bucket()
    filename = secure_filename(file.filename)
    blob = bucket.blob(f"{folder}/{filename}")
    try:
        blob.upload_from_file(file, content_type=file.content_type)
        # Make the file public; adjust this based on your security requirements.
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print("Error uploading file to Firebase:", e)
        return None
