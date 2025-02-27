import os
import json
import tempfile
import firebase_admin
from firebase_admin import credentials, storage
from werkzeug.utils import secure_filename

def get_firebase_cred_path():
    firebase_json = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_json:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json') as temp_file:
            temp_file.write(firebase_json)
            return temp_file.name, True
    else:
        return os.path.join(os.getcwd(), 'serviceAccountKey.json'), False

cred_path, is_temp = get_firebase_cred_path()

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': os.environ.get('FIREBASE_BUCKET', 'your-project-id.appspot.com')
    })
    if is_temp:
        try:
            os.remove(cred_path)
        except Exception as e:
            print("Could not delete temporary Firebase credential file:", e)

def upload_file_to_firebase(file, folder):
    bucket = storage.bucket()
    filename = secure_filename(file.filename)
    blob = bucket.blob(f"{folder}/{filename}")
    try:
        blob.upload_from_file(file, content_type=file.content_type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print("Error uploading file to Firebase:", e)
        return None
