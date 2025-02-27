import os
from flask import (Blueprint, render_template, redirect, url_for, request, flash,
                   current_app, jsonify, Response)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Gallery
from app.decorators import subscription_required
from app.utils import generate_qr_code
from app.firebase_helper import upload_file_to_firebase

gallery = Blueprint('gallery', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@gallery.route('/manage_gallery', methods=['GET', 'POST'])
@login_required
@subscription_required
def manage_gallery():
    gallery_obj = Gallery.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        uploaded_files = request.files.getlist('gallery_files')
        saved_files = []
        for file in uploaded_files:
            if file and allowed_file(file.filename) and file.mimetype in ['image/jpeg', 'image/png', 'application/pdf']:
                # Upload file to Firebase and get its public URL.
                file_url = upload_file_to_firebase(file, folder="gallery")
                if not file_url:
                    flash("Error uploading file to Firebase.", "danger")
                    return redirect(request.url)
                saved_files.append(file_url)
        if gallery_obj:
            gallery_obj.items = saved_files
        else:
            new_gallery = Gallery(user_id=current_user.id, items=saved_files)
            db.session.add(new_gallery)
        db.session.commit()
        flash('Gallery updated successfully!', 'success')
        return redirect(url_for('gallery.manage_gallery'))
    return render_template('manage_gallery.html', title="Manage Gallery", gallery=gallery_obj, nav_flow="gallery")

@gallery.route('/gallery/<int:user_id>')
def gallery_view(user_id):
    gallery_obj = Gallery.query.filter_by(user_id=user_id).first()
    if not gallery_obj or not gallery_obj.items:
        return render_template('gallery.html', title="Gallery", gallery={'items': []}, user_id=user_id, nav_flow="gallery")
    return render_template('gallery.html', title="Gallery", gallery=gallery_obj, user_id=user_id, nav_flow="gallery")

@gallery.route('/generate_gallery_qr')
@login_required
def generate_gallery_qr():
    gallery_obj = Gallery.query.filter_by(user_id=current_user.id).first()
    if not gallery_obj or not gallery_obj.items or len(gallery_obj.items) == 0:
        flash("No gallery items available to generate QR code.", "warning")
        return redirect(url_for('gallery.manage_gallery'))
    # Create an external URL to view the gallery
    display_gallery_url = url_for('gallery.gallery_view', user_id=current_user.id, _external=True)
    # Generate QR code as a base64-encoded data URI
    qr_data_uri = generate_qr_code(display_gallery_url, as_base64=True)
    return Response(qr_data_uri, mimetype='text/plain')

@gallery.route('/debug/list_gallery_files')
def list_gallery_files():
    gallery_obj = Gallery.query.first()
    if gallery_obj and gallery_obj.items:
        return jsonify(gallery_obj.items)
    return jsonify([])
