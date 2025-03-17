import requests
from django.conf import settings
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives

def mobicomm_submit_sms(contact_no, code):
    # Prepare the SMS content
    message = f"Your One Time Verification Code for Tapi Cashless login is {code},Please do not share it with anyone. Thanks Tapi Cashless."

    # Replace the placeholders with actual values
    sms_url = "https://mobicomm.dove-sms.com/submitsms.jsp"
    sms_params = {
        'user': 'TAPICASH',
        'key': '66a1621a84XX',
        'mobile': f"+91{contact_no}",
        'message': message,
        'senderid': 'TAPICL',
        'accusage': '1',
        'entityid': '1701172165114242200',
        'tempid': '1707172206814737429'
    }

    # Send the SMS using a GET request
    response = requests.get(sms_url, params=sms_params)

    return response

def send_email_otp(email, otp, role):
    # Prepare HTML content for email
    subject = 'Verify Code for Email Verification'

    # HTML content
    html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    padding: 20px;
                }}
                .container {{
                    background-color: #ffffff;
                    border-radius: 5px;
                    padding: 20px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }}
                h2 {{
                    color: #333;
                }}
                p {{
                    color: #555;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 0.8em;
                    color: #999;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h4>Hello {role},</h4>
                <p>We hope this message finds you well!</p>
                <p>Your OTP for email verification is: <strong>{otp}</strong></p>
                <p>Please make sure to keep it confidential and do not share it with anyone.</p>
                <p>If you did not request this, please disregard this email.</p>
                <p>If you have any questions or need further assistance, feel free to contact our support team.</p>
                <p>Best regards,<br>TCPL</p>
            </div>
            <div class="footer">
                <p>This email is generated automatically, please do not reply.</p>
            </div>
        </body>
        </html>
    """

    # Create a plain text version by stripping HTML tags (for email clients that don't support HTML)
    text_content = strip_tags(html_content)
    # Create the email object
    email_message = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    # Attach the HTML version of the email
    email_message.attach_alternative(html_content, "text/html")
    email_message.send(fail_silently=False)
