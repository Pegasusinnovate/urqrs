import os
from app import create_app, db
from flask import redirect, url_for, request, render_template, flash
import uuid
from app.utils import generate_qr_code

app = create_app()

@app.route('/', methods=['GET', 'POST'])
def front_page():
    """
    Front Page:
    - Displays login/sign-up options for non-logged-in users.
    - Provides a free QR code generator.
    """
    qr_code_url = None
    input_link = ''
    if request.method == 'POST':
        input_link = request.form.get('link')
        if input_link:
            try:
                # Append a random parameter to ensure uniqueness
                random_value = uuid.uuid4().hex
                if '?' in input_link:
                    input_link += f"&rand={random_value}"
                else:
                    input_link += f"?rand={random_value}"
                qr_code_url = generate_qr_code(input_link, as_base64=True)
                input_link = ""
            except Exception as e:
                flash(f"Error generating QR code: {e}", "danger")
        else:
            flash("Please enter a valid link.", "danger")
    return render_template('front_page.html', qr_code_url=qr_code_url, link=input_link, nav_flow="public")

@app.route('/login_redirect')
def login_redirect():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure that all tables are created
    # In production, Render will use the Procfile to run gunicorn.
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
