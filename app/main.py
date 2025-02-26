from flask import Blueprint, render_template, request, flash
import uuid
from app.utils import generate_qr_code

main = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
def front_page():
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
