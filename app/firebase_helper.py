import os
import firebase_admin
from firebase_admin import credentials, storage
from werkzeug.utils import secure_filename

# Use environment variable to get the path to the Firebase service account JSON file.
# If not set, default to 'serviceAccountKey.json' in the project root.
cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', os.path.join(os.getcwd(), 'serviceAccountKey.json'))

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
