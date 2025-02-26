from datetime import datetime, timedelta
from config import Config

def is_subscription_valid(user):
    """
    Returns True if the user's subscription is valid.
    Checks for both monthly subscription and free trial validity.
    
    For monthly subscriptions:
      - subscription_tier must be "monthly"
      - subscription_start_date must be set
      - The current time must be before (subscription_start_date + SUBSCRIPTION_MONTHLY_DAYS)
      - And subscription_status must be either "active" or "cancelled" (allowing a grace period)
    
    For free trials:
      - trial_start_date must be set and the current time is before (trial_start_date + SUBSCRIPTION_FREE_TRIAL_DAYS)
    """
    now = datetime.utcnow()
    if user.subscription_tier == "monthly" and user.subscription_start_date:
        expiry = user.subscription_start_date + timedelta(days=Config.SUBSCRIPTION_MONTHLY_DAYS)
        if now <= expiry and user.subscription_status in ["active", "cancelled"]:
            return True
    if user.trial_start_date:
        trial_expiry = user.trial_start_date + timedelta(days=Config.SUBSCRIPTION_FREE_TRIAL_DAYS)
        if now <= trial_expiry:
            return True
    return False

def generate_qr_code(data, as_base64=False):
    """
    Generates a QR code image for the provided data.
    If as_base64 is True, returns a base64-encoded string (prefixed with the appropriate header)
    suitable for inline display in HTML. Otherwise, returns a BytesIO object containing the PNG image.
    """
    import qrcode, io, base64
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    if as_base64:
        return "data:image/png;base64," + base64.b64encode(img_io.getvalue()).decode('ascii')
    else:
        return img_io