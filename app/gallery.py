import os
from flask import (Blueprint, render_template, redirect, url_for, request, flash,
                   send_file, send_from_directory, current_app, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Gallery
from app.decorators import subscription_required
from app.utils import generate_qr_code

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
                orig_filename = secure_filename(file.filename)
                name_part, ext = os.path.splitext(orig_filename)
                ext = ext.lower()
                filename = f"gallery_{current_user.id}_{name_part}{ext}"
                file_path = os.path.join(current_app.config['GALLERY_FOLDER'], filename)
                try:
                    file.save(file_path)
                    current_app.logger.info(f"Saved gallery file: {file_path}")
                except Exception as e:
                    flash(f"Error saving gallery file {filename}: {str(e)}", "danger")
                    return redirect(request.url)
                saved_files.append(filename)
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
    display_gallery_url = url_for('gallery.gallery_view', user_id=current_user.id, _external=True)
    img_io = generate_qr_code(display_gallery_url)
    return send_file(img_io, mimetype='image/png')

@gallery.route('/gallery_files/<path:filename>')
def gallery_file(filename):
    return send_from_directory(current_app.config['GALLERY_FOLDER'], filename)

@gallery.route('/debug/list_gallery_files')
def list_gallery_files():
    folder = current_app.config['GALLERY_FOLDER']
    files = os.listdir(folder)
    return jsonify(files)