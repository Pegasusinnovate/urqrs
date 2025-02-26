import os, uuid, base64
from flask import (Blueprint, render_template, redirect, url_for, request, flash, 
                   send_file, send_from_directory, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db, cache
from app.models import SimpleMenu
from app.decorators import subscription_required
from app.utils import generate_qr_code

menu = Blueprint('menu', __name__)

@menu.route('/choose_qr')
@login_required
def choose_qr():
    return render_template('choose_qr.html', title="Choose QR Facility", nav_flow="menu")

@menu.route('/dashboard')
@login_required
@subscription_required
def dashboard():
    preview_url = None
    extension = None
    preview_type = None
    if current_user.default_menu == "file":
        user_prefix = f"current_menu_{current_user.id}"
        files = [fname for fname in os.listdir(current_app.config['UPLOAD_FOLDER']) 
                 if fname.startswith(user_prefix)]
        if files:
            if len(files) == 1:
                preview_type = "single"
                preview_url = url_for('menu.uploaded_file', filename=files[0])
                extension = files[0].rsplit('.', 1)[1].lower()
            else:
                preview_type = "multiple"
                preview_url = [url_for('menu.uploaded_file', filename=fname) for fname in files]
                extension = "image"
    else:
        menu_file_path = os.path.join(current_app.config['MENU_FOLDER'], f"simple_menu_{current_user.id}.html")
        if os.path.exists(menu_file_path):
            preview_type = "single"
            preview_url = url_for('menu.display_simple_menu', user_id=current_user.id)
            extension = "html"
    qr_code_url = url_for('menu.generate_qr') if preview_url else None
    return render_template('dashboard.html', title="Dashboard", username=current_user.username,
                           preview_url=preview_url, extension=extension,
                           qr_code_url=qr_code_url, preview_type=preview_type, nav_flow="menu")

@menu.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@menu.route('/upload_menu', methods=['GET', 'POST'])
@login_required
@subscription_required
def upload_menu():
    user_prefix = f"current_menu_{current_user.id}"
    allowed_extensions = current_app.config.get('ALLOWED_MENU_EXTENSIONS', {'pdf', 'jpg', 'jpeg', 'png'})
    
    if request.method == 'POST':
        uploaded_files = request.files.getlist('menu_file')
        if not uploaded_files or uploaded_files[0].filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)
        
        # Validate each file's extension and mimetype
        for file in uploaded_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                if '.' not in filename:
                    flash("File name is missing an extension.", "danger")
                    return redirect(request.url)
                ext = filename.rsplit('.', 1)[1].lower()
                if ext not in allowed_extensions or file.mimetype not in ['image/jpeg', 'image/png', 'application/pdf']:
                    flash(f'File type not allowed: {ext}.', "danger")
                    return redirect(request.url)
        
        # Remove existing files for this user from UPLOAD_FOLDER
        for fname in os.listdir(current_app.config['UPLOAD_FOLDER']):
            if fname.startswith(user_prefix):
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], fname))
                except Exception as e:
                    current_app.logger.error(f"Error deleting file {fname}: {e}")
        
        # Save uploaded file(s)
        if len(uploaded_files) > 1:
            i = 1
            for file in uploaded_files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    if '.' not in filename:
                        flash("One of the files is missing an extension.", "danger")
                        return redirect(request.url)
                    ext = filename.rsplit('.', 1)[1].lower()
                    if ext in {'jpg', 'jpeg', 'png', 'pdf'}:
                        new_filename = f"{user_prefix}_{i}.{ext}"
                        try:
                            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename))
                        except Exception as e:
                            flash(f"Error saving file {new_filename}. Please try again.", "danger")
                            return redirect(request.url)
                        i += 1
            flash('Multiple menu images uploaded successfully!', 'success')
            current_user.default_menu = "file"
        else:
            file = uploaded_files[0]
            if file and file.filename:
                filename = secure_filename(file.filename)
                if '.' not in filename:
                    flash("File name is missing an extension.", "danger")
                    return redirect(request.url)
                ext = filename.rsplit('.', 1)[1].lower()
                new_filename = f"{user_prefix}.{ext}"
                try:
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename))
                except Exception as e:
                    flash("Error saving file. Please try again.", "danger")
                    return redirect(request.url)
                flash('Menu updated successfully!', 'success')
                current_user.default_menu = "file"
            else:
                flash('No file selected.', 'danger')
                return redirect(request.url)
        
        db.session.commit()
        return redirect(url_for('menu.upload_menu'))
    
    # GET: retrieve files for preview
    files = [fname for fname in os.listdir(current_app.config['UPLOAD_FOLDER']) 
             if fname.startswith(user_prefix)]
    if files:
        if current_user.default_menu == "file":
            if len(files) == 1:
                preview_type = "single"
                extension = files[0].rsplit('.', 1)[1].lower()
                preview_url = url_for('menu.uploaded_file', filename=files[0])
            else:
                preview_type = "multiple"
                preview_url = [url_for('menu.uploaded_file', filename=fname) for fname in files]
                extension = "image"
        else:
            preview_url = url_for('menu.display_simple_menu', user_id=current_user.id)
            extension = "html"
            preview_type = "single"
    else:
        preview_url = None
        extension = None
        preview_type = None

    return render_template('manage_menu.html', title="Manage Menu",
                           preview_url=preview_url, preview_type=preview_type,
                           qr_code_url=url_for('menu.generate_qr'), extension=extension,
                           default_menu=current_user.default_menu, nav_flow="menu")

@menu.route('/display_menu/<int:user_id>')
def display_menu(user_id):
    user_prefix = f"current_menu_{user_id}"
    files = sorted([fname for fname in os.listdir(current_app.config['UPLOAD_FOLDER']) 
                     if fname.startswith(user_prefix)])
    if not files:
        return "No menu uploaded yet", 404
    file_to_display = files[0]
    extension = file_to_display.rsplit('.', 1)[1].lower()
    return render_template('display_menu.html', title="Our Menu",
                           menu_file=file_to_display, extension=extension, user_id=user_id)

@menu.route('/display_menu_full/<int:user_id>')
@cache.cached(timeout=300, key_prefix=lambda: f"display_menu_full_{request.view_args['user_id']}")
def display_menu_full(user_id):
    user_prefix = f"current_menu_{user_id}"
    files = sorted([fname for fname in os.listdir(current_app.config['UPLOAD_FOLDER']) 
                     if fname.startswith(user_prefix)])
    if not files:
        return "No menu uploaded yet", 404
    return render_template('display_menu_full.html', title="Our Menu", files=files, user_id=user_id)

@menu.route('/generate_qr')
@login_required
def generate_qr():
    if current_user.default_menu == "simple":
        display_menu_url = url_for('menu.display_simple_menu', user_id=current_user.id, _external=True)
    else:
        display_menu_url = url_for('menu.display_menu_full', user_id=current_user.id, _external=True)
    
    img_io = generate_qr_code(display_menu_url)
    return send_file(img_io, mimetype='image/png')

@menu.route('/create_menu', methods=['GET', 'POST'])
@login_required
@subscription_required
def create_menu():
    from app.models import SimpleMenu
    existing_menu = SimpleMenu.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        menu_title = request.form.get('menu_title')
        segments = []
        segment_headings = request.form.getlist('segment_heading[]')
        if not segment_headings or len(segment_headings) == 0:
            flash('Please add at least one segment with a heading.', 'danger')
            return redirect(url_for('menu.create_menu'))
        for i, heading in enumerate(segment_headings):
            dishes = []
            dish_names = request.form.getlist('dish_name_' + str(i) + '[]')
            dish_quantities = request.form.getlist('dish_quantity_' + str(i) + '[]')
            dish_prices = request.form.getlist('dish_price_' + str(i) + '[]')
            for name, quantity, price in zip(dish_names, dish_quantities, dish_prices):
                sanitized_name = name.strip()
                if sanitized_name:
                    quantity_list = [q.strip() for q in quantity.split('/') if q.strip()]
                    price_list = [p.strip() for p in price.split('/') if p.strip()]
                    if len(quantity_list) != len(price_list):
                        flash(f"For dish '{sanitized_name}' in segment '{heading}', quantities and prices count mismatch.", "danger")
                        return redirect(url_for('menu.create_menu'))
                    options = [{"quantity": q, "price": p} for q, p in zip(quantity_list, price_list)]
                    dishes.append({'name': sanitized_name, 'options': options})
            if dishes:
                segments.append({'heading': heading.strip(), 'dishes': dishes})
        if not menu_title or len(segments) == 0:
            flash('Please provide a menu title and at least one segment with a dish.', 'danger')
            return redirect(url_for('menu.create_menu'))
        
        segments_html = ""
        for segment in segments:
            segment_html = f"""
            <h2 style="border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-top: 20px; text-align: left;">{segment['heading']}</h2>
            <table class="table table-bordered">
              <thead>
                <tr>
                  <th class="text-center">Dish</th>
                  <th class="text-center">Quantities</th>
                  <th class="text-center">Prices</th>
                </tr>
              </thead>
              <tbody>
            """
            for dish in segment['dishes']:
                quantities = "/".join(option['quantity'] for option in dish['options'])
                prices = "/".join(option['price'] for option in dish['options'])
                segment_html += f"<tr><td class='text-center'>{dish['name']}</td><td class='text-center'>{quantities}</td><td class='text-center'>{prices}</td></tr>"
            segment_html += "</tbody></table>"
            segments_html += segment_html
        
        html_content = f"""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <title>{menu_title}</title>
            <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Roboto&display=swap" rel="stylesheet">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
              body {{ padding: 20px; font-family: 'Roboto', sans-serif; background-color: #f8f9fa; }}
              h1, h2 {{ font-family: 'Playfair Display', serif; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="text-center mb-4">{menu_title}</h1>
                {segments_html}
            </div>
        </body>
        </html>
        """
        menu_file_path = os.path.join(current_app.config['MENU_FOLDER'], f"simple_menu_{current_user.id}.html")
        try:
            with open(menu_file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            flash("Error creating menu file. Please try again.", "danger")
            return redirect(url_for('menu.create_menu'))
        if existing_menu:
            existing_menu.menu_title = menu_title
            existing_menu.dishes = segments
        else:
            new_menu = SimpleMenu(user_id=current_user.id, menu_title=menu_title, dishes=segments)
            db.session.add(new_menu)
        db.session.commit()
        flash('Simple menu created successfully!', 'success')
        return redirect(url_for('menu.menu_created'))
    else:
        pre_menu_title = existing_menu.menu_title if existing_menu else ""
        pre_dishes = existing_menu.dishes if existing_menu else []
        return render_template('create_menu.html', title="Create Simple Menu",
                               pre_menu_title=pre_menu_title, pre_dishes=pre_dishes, nav_flow="menu")

@menu.route('/menu_created')
@login_required
def menu_created():
    menu_file_path = os.path.join(current_app.config['MENU_FOLDER'], f"simple_menu_{current_user.id}.html")
    if not os.path.exists(menu_file_path):
        flash("No menu created yet.", "danger")
        return redirect(url_for('menu.create_menu'))
    return render_template('menu_created.html', user_id=current_user.id, nav_flow="menu")

@menu.route('/download_menu/<int:user_id>')
@login_required
@subscription_required
def download_menu(user_id):
    menu_file_path = os.path.join(current_app.config['MENU_FOLDER'], f"simple_menu_{user_id}.html")
    if not os.path.exists(menu_file_path):
        return "No menu created yet.", 404
    return send_file(menu_file_path, as_attachment=True,
                     download_name=f"simple_menu_{user_id}.html", mimetype='text/html')

@menu.route('/set_default_menu')
@login_required
def set_default_menu():
    current_user.default_menu = "simple"
    db.session.commit()
    flash("Menu set as default!", "success")
    return redirect(url_for('menu.menu_created'))

@menu.route('/display_simple_menu/<int:user_id>')
def display_simple_menu(user_id):
    menu_file_path = os.path.join(current_app.config['MENU_FOLDER'], f"simple_menu_{user_id}.html")
    if not os.path.exists(menu_file_path):
        return "No simple menu created yet.", 404
    return send_file(menu_file_path, mimetype='text/html')

@menu.route('/generate_simple_menu_qr')
@login_required
def generate_simple_menu_qr():
    display_menu_url = url_for('menu.display_simple_menu', user_id=current_user.id, _external=True)
    img_io = generate_qr_code(display_menu_url)
    return send_file(img_io, mimetype='image/png')