import os, uuid, base64
from flask import (
    Blueprint, render_template, redirect, url_for, request, flash,
    current_app, session, send_file, Response
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db, cache
from app.models import SimpleMenu
from app.decorators import subscription_required
from app.utils import generate_qr_code
from app.firebase_helper import upload_file_to_firebase

menu = Blueprint('menu', __name__)

@menu.route('/choose_qr')
@login_required
def choose_qr():
    return render_template('choose_qr.html', title="Choose QR Facility", nav_flow="menu")

@menu.route('/dashboard')
@login_required
@subscription_required
def dashboard():
    preview_urls = None
    preview_type = None
    preview_format = None  # "iframe" for sample menus, "image" for uploaded files
    if current_user.default_menu == "file" and session.get('uploaded_menu_urls'):
        urls = session.get('uploaded_menu_urls')
        if len(urls) == 1:
            preview_type = "single"
            preview_urls = urls[0]
            preview_format = "image"
        else:
            preview_type = "multiple"
            preview_urls = urls
            preview_format = "image"
    elif current_user.default_menu == "simple":
        # For sample menu, generate the preview URL dynamically.
        # We'll use our display_simple_menu route, which generates HTML on the fly.
        simple_menu = SimpleMenu.query.filter_by(user_id=current_user.id).first()
        if simple_menu:
            preview_type = "single"
            preview_urls = url_for('menu.display_simple_menu', user_id=current_user.id)
            preview_format = "iframe"
    qr_code_url = url_for('menu.generate_qr') if preview_urls else None
    return render_template(
        'dashboard.html',
        title="Dashboard",
        username=current_user.username,
        preview_url=preview_urls,
        preview_type=preview_type,
        preview_format=preview_format,
        qr_code_url=qr_code_url,
        nav_flow="menu"
    )

@menu.route('/uploads/<path:filename>')
def uploaded_file(filename):
    file_path = os.path.join(current_app.config['MENU_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return "Not available", 404

@menu.route('/upload_menu', methods=['GET', 'POST'])
@login_required
@subscription_required
def upload_menu():
    # If a sample menu is active, inform the user and provide a switch option.
    if current_user.default_menu == "simple":
        flash("You are currently using a sample menu. To update your menu, please use the 'Create Menu' option or switch to file upload mode.", "info")
        preview_url = url_for('menu.display_simple_menu', user_id=current_user.id)
        return render_template(
            'manage_menu.html',
            title="Manage Menu",
            preview_url=preview_url,
            preview_type="single",
            default_menu=current_user.default_menu,
            qr_code_url=url_for('menu.generate_qr'),
            extension="html",
            nav_flow="menu"
        )
    
    if request.method == 'POST':
        uploaded_files = request.files.getlist('menu_file')
        if not uploaded_files or uploaded_files[0].filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)
        
        file_urls = []
        allowed_extensions = current_app.config.get('ALLOWED_MENU_EXTENSIONS', {'pdf', 'jpg', 'jpeg', 'png'})
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
                file_url = upload_file_to_firebase(file, folder="menus")
                if not file_url:
                    flash("Error uploading file to Firebase.", "danger")
                    return redirect(request.url)
                file_urls.append(file_url)
        
        session['uploaded_menu_urls'] = file_urls
        flash('Menu updated successfully!', 'success')
        current_user.default_menu = "file"
        db.session.commit()
        return redirect(url_for('menu.upload_menu'))
    
    # GET: retrieve uploaded menu URLs from session.
    uploaded_menu_urls = session.get('uploaded_menu_urls')
    preview_type = None
    preview_url = None
    if uploaded_menu_urls:
        if len(uploaded_menu_urls) == 1:
            preview_type = "single"
            preview_url = uploaded_menu_urls[0]
        else:
            preview_type = "multiple"
            preview_url = uploaded_menu_urls
    return render_template(
        'manage_menu.html',
        title="Manage Menu",
        preview_url=preview_url,
        preview_type=preview_type,
        qr_code_url=url_for('menu.generate_qr'),
        default_menu=current_user.default_menu,
        extension="pdf",  # default; actual extension can be derived client-side if needed
        nav_flow="menu"
    )

@menu.route('/display_menu/<int:user_id>')
def display_menu(user_id):
    # For file-based menus, use the uploaded URL if available.
    if session.get('uploaded_menu_urls'):
        return redirect(session.get('uploaded_menu_urls')[0])
    return "No menu available.", 404

@menu.route('/display_menu_full/<int:user_id>')
@cache.cached(timeout=300, key_prefix=lambda: f"display_menu_full_{request.view_args['user_id']}")
def display_menu_full(user_id):
    # For full display, attempt to show the sample menu if available.
    simple_menu = SimpleMenu.query.filter_by(user_id=user_id).first()
    if simple_menu:
        return redirect(url_for('menu.display_simple_menu', user_id=user_id))
    return "Not available", 404

@menu.route('/display_simple_menu/<int:user_id>')
def display_simple_menu(user_id):
    from app.models import SimpleMenu
    simple_menu = SimpleMenu.query.filter_by(user_id=user_id).first()
    if not simple_menu:
        return "No simple menu created yet.", 404
    # Dynamically generate HTML content from the stored JSON data.
    segments_html = ""
    segments = simple_menu.dishes  # expecting this to be a list of segments
    for segment in segments:
        segment_html = f"<h2 style='border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-top: 20px; text-align: left;'>{segment['heading']}</h2>"
        segment_html += "<table class='table table-bordered'><thead><tr><th class='text-center'>Dish</th><th class='text-center'>Quantities</th><th class='text-center'>Prices</th></tr></thead><tbody>"
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
        <title>{simple_menu.menu_title}</title>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Roboto&display=swap" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
          body {{ padding: 20px; font-family: 'Roboto', sans-serif; background-color: #f8f9fa; }}
          h1, h2 {{ font-family: 'Playfair Display', serif; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center mb-4">{simple_menu.menu_title}</h1>
            {segments_html}
        </div>
    </body>
    </html>
    """
    return html_content

@menu.route('/generate_qr')
@login_required
def generate_qr():
    if current_user.default_menu == "simple":
        display_menu_url = url_for('menu.display_simple_menu', user_id=current_user.id, _external=True)
    else:
        if session.get('uploaded_menu_urls'):
            urls = session.get('uploaded_menu_urls')
            display_menu_url = urls[0] if len(urls) == 1 else urls[0]
        else:
            display_menu_url = None
    if not display_menu_url:
        flash("No menu available to generate QR code.", "warning")
        return redirect(url_for('menu.dashboard'))
    # Generate QR code as a raw image file.
    qr_io = generate_qr_code(display_menu_url, as_base64=False)
    return send_file(qr_io, mimetype='image/png')

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
            flash('Please provide a menu title and at least one segment with a dish.', "danger")
            return redirect(url_for('menu.create_menu'))
        
        # Update the SimpleMenu record in the database (no file write)
        if existing_menu:
            existing_menu.menu_title = menu_title
            existing_menu.dishes = segments
        else:
            new_menu = SimpleMenu(user_id=current_user.id, menu_title=menu_title, dishes=segments)
            db.session.add(new_menu)
        # Set default menu to "simple"
        current_user.default_menu = "simple"
        db.session.commit()
        flash('Simple menu created successfully!', 'success')
        return redirect(url_for('menu.menu_created'))
    else:
        pre_menu_title = existing_menu.menu_title if existing_menu else ""
        pre_dishes = existing_menu.dishes if existing_menu else []
        return render_template(
            'create_menu.html',
            title="Create Simple Menu",
            pre_menu_title=pre_menu_title,
            pre_dishes=pre_dishes,
            nav_flow="menu"
        )

@menu.route('/menu_created')
@login_required
def menu_created():
    from app.models import SimpleMenu
    simple_menu = SimpleMenu.query.filter_by(user_id=current_user.id).first()
    if not simple_menu:
        flash("No menu created yet.", "danger")
        return redirect(url_for('menu.create_menu'))
    return render_template('menu_created.html', user_id=current_user.id, nav_flow="menu")

@menu.route('/download_menu/<int:user_id>')
@login_required
@subscription_required
def download_menu(user_id):
    from app.models import SimpleMenu
    simple_menu = SimpleMenu.query.filter_by(user_id=user_id).first()
    if not simple_menu:
        return "No menu created yet.", 404
    # Generate the HTML dynamically (as in display_simple_menu)
    segments_html = ""
    for segment in simple_menu.dishes:
        segment_html = f"<h2 style='border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-top: 20px; text-align: left;'>{segment['heading']}</h2>"
        segment_html += "<table class='table table-bordered'><thead><tr><th class='text-center'>Dish</th><th class='text-center'>Quantities</th><th class='text-center'>Prices</th></tr></thead><tbody>"
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
        <title>{simple_menu.menu_title}</title>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Roboto&display=swap" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
          body {{ padding: 20px; font-family: 'Roboto', sans-serif; background-color: #f8f9fa; }}
          h1, h2 {{ font-family: 'Playfair Display', serif; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center mb-4">{simple_menu.menu_title}</h1>
            {segments_html}
        </div>
    </body>
    </html>
    """
    from io import BytesIO
    return send_file(BytesIO(html_content.encode('utf-8')),
                     as_attachment=True,
                     download_name=f"simple_menu_{user_id}.html",
                     mimetype='text/html')

@menu.route('/set_default_menu')
@login_required
def set_default_menu():
    current_user.default_menu = "simple"
    db.session.commit()
    flash("Menu set as default!", "success")
    return redirect(url_for('menu.menu_created'))

@menu.route('/generate_simple_menu_qr')
@login_required
def generate_simple_menu_qr():
    display_menu_url = url_for('menu.display_simple_menu', user_id=current_user.id, _external=True)
    qr_io = generate_qr_code(display_menu_url, as_base64=False)
    return send_file(qr_io, mimetype='image/png')

@menu.route('/switch_to_file')
@login_required
def switch_to_file():
    current_user.default_menu = "file"
    db.session.commit()
    flash("Switched to file upload mode.", "success")
    return redirect(url_for('menu.upload_menu'))
