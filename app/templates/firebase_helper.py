import os
import firebase_admin
from firebase_admin import credentials, storage
from werkzeug.utils import secure_filename

# Initialize Firebase Admin SDK if not already initialized.
if not firebase_admin._apps:
    cred = credentials.Certificate(os.path.join(os.getcwd(), 'serviceAccountKey.json'))
    firebase_admin.initialize_app(cred, {
        'storageBucket': os.environ.get('FIREBASE_BUCKET', 'your-project-id.appspot.com')
    })

def upload_file_to_firebase(file, folder):
    """
    Uploads a file to Firebase Cloud Storage in the specified folder.
    Returns the public URL of the uploaded file, or None if an error occurs.
    """
    bucket = storage.bucket()
    filename = secure_filename(file.filename)
    blob = bucket.blob(f"{folder}/{filename}")
    try:
        blob.upload_from_file(file, content_type=file.content_type)
        # Make the file public; adjust as needed for your security rules.
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print("Error uploading file to Firebase:", e)
        return None
