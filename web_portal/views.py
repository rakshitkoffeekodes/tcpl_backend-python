from datetime import datetime, timedelta
import os
import re
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.views import APIView  # Importing the APIView class for creating API endpoints.
from rest_framework.permissions import IsAuthenticated, AllowAny  # Importing permission classes for authentication.
from rest_framework.response import Response  # Importing Response class for generating HTTP responses.
from rest_framework import status  # Importing status module for HTTP status codes.
from django.core.paginator import Paginator, EmptyPage  # Importing pagination support.
from django.db.models import Q
import jwt
from django.conf import settings as jwt_settings
from tcpl_backend import settings  # Importing Q objects for complex queries.
from .models import *
from .serializers import *
import pyotp  # Importing library for generating one-time passwords (OTP).
import qrcode  # Importing library for generating QR codes.
import base64  # Importing base64 encoding and decoding support.
from io import BytesIO  # Importing BytesIO for working with byte streams.
from django.contrib.auth import authenticate  # Importing Django's authentication function.
from django.core.mail import send_mail, \
    EmailMultiAlternatives  # Importing Django's send_mail function for sending emails.
from django.utils.html import strip_tags
from rest_framework_simplejwt.tokens import RefreshToken  # Importing tokens for JWT authentication.
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.core.mail.backends.smtp import EmailBackend
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from tcpl_backend.custom_jwt_auth import get_tokens_for_user, IsAdmin, IsSuperAdmin, IsRetailer, IsDistributor, CustomJWTAuthentication
from validation.custom_validation import *
from .super_admin_provide_data import *

ALLOWED_DOMAIN = ['127.0.0.1:8000', '149.28.56.227', 'localhost:3000', 'localhost:3001', 'dev.tapicashless.com', 'api.tapipe.in']


def smtp_configuration_get():
    try:
        config = SMTPConfiguration.objects.first()
        if config:
            config = {
                'smtp_server': config.smtp_server,
                'port': config.port,
                'encryption_method': config.encryption_method,
                'sender_email': config.sender_email,
                'password': config.password
            }
        else:
            config = {
                'smtp_server': 'smtp.gmail.com',
                'port': 587,
                'encryption_method': "SSL/TLS",
                'sender_email': 'nayan.koffeekodes@gmail.com',
                'password': 'iuli pavc fjyt thzs'
            }
    except SMTPConfiguration.DoesNotExist:
        config = {
            'smtp_server': 'smtp.gmail.com',
            'port': 587,
            'encryption_method': "SSL/TLS",
            'sender_email': 'nayan.koffeekodes@gmail.com',
            'password': 'iuli pavc fjyt thzs'
        }
    return config


class DynamicEmailBackend(EmailBackend):
    def __init__(self, *args, **kwargs):
        config = smtp_configuration_get()
        kwargs.update({
            'host': config['smtp_server'],
            'port': config['port'],
            'use_tls': True if config['encryption_method'] == "SSL/TLS" else
            True if config['encryption_method'] == None else False,
            'use_ssl': True if config['encryption_method'] == "STARTTLS" else False,
            'username': config['sender_email'],
            'password': config['password'],
        })
        super().__init__(*args, **kwargs)


import socket
from user_agents import parse


class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        try:
            username = request.data.get('username')
            password = request.data.get('password')

            # Check if username and password are provided
            if not username or not password:
                response_data = {
                    'status': 'fail',
                    'message': 'Username and password are required'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            # Authenticate user
            user = authenticate(request, username=username, password=password)
            if user is None:
                response_data = {
                    'status': 'fail',
                    'message': 'Invalid credentials'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # Check if it's the user's first login
                first_login = not LoginLog.objects.filter(user=user).exists()
                if first_login:
                    # Generate QR code for two-factor authentication
                    if not user.totp_secret:
                        user.totp_secret = pyotp.random_base32()
                        user.save()

                    totp = pyotp.TOTP(user.totp_secret)
                    otp_uri = totp.provisioning_uri(name=user.username, issuer_name="TCPL")
                    qr_code = qrcode.make(otp_uri)

                    # Convert QR code image to base64 for embedding in email
                    buffered = BytesIO()
                    qr_code.save(buffered, format='PNG')
                    qr_code_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

                    # Prepare HTML content for email
                    subject = 'Your QR Code for TCPL Login Authentication'
                    html_content = """
                        <html>
                        <head></head>
                        <body>
                            <p>Dear {username},</p>
                            <p>Attached document is your QR code for login authentication to TCPL. Please use this QR code with your google authenticator app to securely access your OTP.</p>
                            <p>If you have any questions or encounter any issues, please feel free to contact our support team.</p>
                            <p>Best regards,<br>TCPL</p>
                        </body>
                        </html>
                    """.format(username=user.username)

                    # Send email with HTML content and QR code as attachment
                    message = EmailMultiAlternatives(subject, strip_tags(html_content), settings.EMAIL_HOST_USER, [user.email])
                    # Attach QR code image
                    message.attach('qrcode.png', buffered.getvalue(), 'image/pdf')
                    message.attach_alternative(html_content, "text/html")

                    # Send email
                    message.send(fail_silently=False)
                    upload_all_data(request)
                    response_data = {
                        'status': 'success',
                        'message': 'QR code generated successfully and sent to your email'
                    }

                else:
                    response_data = {
                        'status': 'success',
                        'message': 'Login successful. Please verify your OTP.'
                    }

                # Return appropriate response status
                return Response(response_data,
                                status=status.HTTP_200_OK if not first_login else status.HTTP_201_CREATED)

        except Exception as e:
            # Handle any unexpected errors
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        """
        Handle POST requests to verify the provided OTP against users with TOTP secrets.
        Generates JWT tokens upon successful OTP verification and logs the login event.
        """
        try:
            otp = request.data.get('otp')

            # Validate that OTP is provided
            if not otp:
                return Response({'status': 'fail', 'message': 'OTP is required'}, status=status.HTTP_400_BAD_REQUEST)

            # Iterate through users with TOTP secrets and verify the OTP
            for user in CustomUser.objects.filter(totp_secret__isnull=False):
                totp = pyotp.TOTP(user.totp_secret)
                if totp.verify(otp):
                    try:
                        with transaction.atomic():
                            # Generate JWT tokens for the authenticated user
                            access_token = get_tokens_for_user(user, timedelta(days=1))
                            
                            ip_address = request.META.get('REMOTE_ADDR')
                            user_agent = parse(request.META['HTTP_USER_AGENT'])
                            browser_name = user_agent.browser.family
                            # Log the successful login
                            login_obj = LoginLog.objects.create(user=user,
                                                                ip_address=ip_address,
                                                                browser_name=browser_name
                                                                )

                            # Return success response with JWT tokens
                            return Response({'status': 'success', 'message': 'OTP is valid.', "access_token": str(access_token)})

                    except Exception as e:
                        return Response({'status': 'error', 'message': f'Error logging login: {str(e)}'},
                                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # If no user matches the OTP, return an invalid OTP response
            return Response({'status': 'fail', 'message': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any unexpected errors
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BannerView(APIView):
    # Ensure the user is authenticated for all methods
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if 'page_number' in request.data or 'page_size' in request.data:
            return self.fetch_data(request)
        elif 'title' in request.data and 'description' in request.data:
            return self.create_banner(request)
        else:
            return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)

    def create_banner(self, request):
        try:
            banner_title = request.data.get('title')
            image_for_mobile = request.FILES.getlist('image_for_mobile')
            image_for_web = request.FILES.getlist('image_for_web')
            banner_description = request.data.get('description')

            # Check for existing banner title
            if Banner.objects.filter(title=banner_title, is_deleted=False).exists():
                return Response({
                    'status': 'fail',
                    'message': 'A banner with this title already exists.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Function to save files
            def save_files(files, directory):
                if not os.path.exists(directory):
                    os.makedirs(directory)
                print(f'------------>{directory}')
                urls = []
                for file in files:
                    # Ensure the file is valid
                    if not hasattr(file, 'name'):
                        return None  # Indicate an error state
                    
                    file_extension = file.name.split('.')[-1].lower()
                    if file_extension not in ['png', 'jpg']:
                        return None  # Indicate an error state

                    # Sanitize file name
                    sanitized_file_name = file.name.replace(' ', '').replace('(', '').replace(')', '')
                    file_path = os.path.join(directory, sanitized_file_name)
                    
                    # Save the file
                    with open(file_path, "wb") as f:
                        f.write(file.read())

                    # Construct URL
                    urls.append(f'/{directory}{sanitized_file_name}')
                
                return urls
            # Check if there are images to save
            if not image_for_web :return Response({'status': 'fail','message': 'No web image provided.'}, status=status.HTTP_400_BAD_REQUEST)
            if not image_for_mobile :return Response({'status': 'fail','message': 'No mobile image provided.'}, status=status.HTTP_400_BAD_REQUEST)

            # Save the images
            web_banner_image_urls = save_files(image_for_web, 'media/Banners/Web/')
            mobile_banner_image_urls = save_files(image_for_mobile, 'media/Banner/Mobile/')
            if web_banner_image_urls is None or mobile_banner_image_urls is None:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid file type. Only PNG and JPG files are allowed.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Limit to active banners
            active_banners_count = Banner.objects.filter(is_deactive=False, is_deleted=False).count()
            is_deactive = active_banners_count >= 5

            # Create new banner
            Banner.objects.create(
                title=banner_title,
                image_for_web=web_banner_image_urls[0],  # Use the first image URL
                image_for_mobile=mobile_banner_image_urls[0],  # Use the first image URL
                description=banner_description,
                is_deactive=is_deactive,
                created_by=request.user
            )

            return Response({'status': 'success', 'message': 'Banner added successfully.'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_data(self, request):
        data = {
            "total_pages": 0,
            "current_page": 0,
            "total_items": 0,
            "results": []
        }
        try:
            page_number = request.POST.get('page_number', 1)
            page_size = request.POST.get('page_size', 10)
            banner_id = request.POST.get('banner_id', None)
            search = request.POST.get('search', '')

            if not isnumber(page_number) or int(page_number) <= 0:
                return Response({'status': 'fail', 'message': 'Invalid page number. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(page_size) or int(page_size) <= 0:
                return Response({'status': 'fail', 'message': 'Invalid page size. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            if banner_id and (not isnumber(banner_id) or int(banner_id) <= 0):
                return Response({'status': 'fail', 'message': 'Invalid banner ID. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            banners = Banner.objects.filter(is_deleted=False)
            print(banners, 'banners')
            if banner_id:
                banners = banners.filter(banner_id=banner_id)
                if not banners.exists():
                    return Response({'status': 'fail', 'message': 'Banner ID does not exist.', 'data': data}, status=status.HTTP_404_NOT_FOUND)

            if search:
                banners = banners.filter(
                    Q(title__icontains=search) | Q(description__icontains=search)
                )

            total_items = banners.count()
            print('total_items', total_items)
            total_pages = (total_items + page_size - 1) // page_size

            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size
            paginated_banners = banners[start_index:end_index]

            serialized_banners = BannerSerializer(paginated_banners, many=True)
            print(serialized_banners.data, 'serialized_banners.data')
            for banner in serialized_banners.data:
                banner['image_for_web'] = f'http://{request.META["HTTP_HOST"]}{banner["image_for_web"]}'
                banner['image_for_mobile'] = f'http://{request.META["HTTP_HOST"]}{banner["image_for_mobile"]}'
            data = {
                'total_pages': total_pages,
                'current_page': page_number,
                'total_items': total_items,
                'results': serialized_banners.data
            }
            return Response({'status': 'success', 'message': 'Banners retrieved successfully.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}', 'data': data}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def put(self, request):
        banner_id = request.data.get('banner_id')
        banner_title = request.data.get('title', None)
        image_for_web = request.FILES.getlist('image_for_web', None)
        image_for_mobile = request.FILES.getlist('image_for_mobile', None)
        banner_description = request.data.get('description', None)
        message = 'Banner Updated Successfully.'

        # Validate banner_id
        if not banner_id:
            return Response({'status': 'fail', 'message': 'Banner ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if not isnumber(banner_id):
                return Response({'status': 'fail', 'message': 'Invalid banner ID. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            # Check for existing banner with the same title
            existing_banner = Banner.objects.filter(title=banner_title, is_deleted=False).exclude(banner_id=banner_id).first()
            if existing_banner:
                return Response({'status': 'fail', 'message': 'A banner with this title already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if banner exists
            banner_data = Banner.objects.filter(banner_id=banner_id, is_deleted=False).first()
            if not banner_data:
                return Response({'status': 'fail', 'message': 'Banner does not exist.'}, status=status.HTTP_404_NOT_FOUND)

            # File saving utility
            def save_files(files, directory):
                if not os.path.exists(directory):
                    os.makedirs(directory)
                urls = []
                for file in files:
                    file_ext = file.name.split('.')[-1].lower()
                    if file_ext not in ['png', 'jpg']:
                        return Response({
                            'status': 'fail',
                            'message': 'Invalid file type. Only PNG and JPG files are allowed.'
                        }, status=status.HTTP_400_BAD_REQUEST)

                    file_path = os.path.join(directory, file.name.replace(' ', '').replace('(', '').replace(')', ''))
                    with open(file_path, "wb") as f:
                        f.write(file.read())

                    urls.append(f'/{directory}{file.name.replace(" ", "").replace("(", "").replace(")", "")}')
                return urls

            # Update banner fields if provided
            if banner_title:
                banner_data.title = banner_title

            if image_for_web:
                banner_image_urls = save_files(image_for_web, 'media/Banners/Web/')
                if isinstance(banner_image_urls, Response):
                    return banner_image_urls  # Return error if file validation failed
                banner_data.image_for_web = banner_image_urls[0]

            if image_for_mobile:
                banner_image_urls = save_files(image_for_mobile, 'media/Banners/Mobile/')
                if isinstance(banner_image_urls, Response):
                    return banner_image_urls  # Return error if file validation failed
                banner_data.image_for_web = banner_image_urls[0]

            if banner_description:
                banner_data.description = banner_description

            # Banner activation/deactivation logic
            if banner_id and not any([banner_title, image_for_web, image_for_mobile, banner_description]):
                active_banners_count = Banner.objects.filter(is_deactive=False, is_deleted=False).count()

                if active_banners_count >= 5 and not banner_data.is_deactive:
                    return Response({
                        'status': 'fail',
                        'message': 'Maximum of 5 active banners allowed. Please deactivate an existing banner before activating this one.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if active_banners_count <= 1 and not banner_data.is_deactive:
                    return Response({
                        'status': 'fail',
                        'message': 'You cannot deactivate this banner. You need to have at least one active banner.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                banner_data.is_deactive = not banner_data.is_deactive
                message = 'Banner Deactivated Successfully.' if banner_data.is_deactive else 'Banner Activated Successfully.'

            # Update audit fields and save
            banner_data.modified_at = timezone.now()
            banner_data.save()

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        banner_id = request.data.get("banner_id")

        # Check if banner_id is provided
        if not banner_id:
            response_data = {
                'status': 'fail',
                'message': "banner_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Retrieve the banner object by ID
                banner = Banner.objects.get(banner_id=banner_id, is_deleted=False)

                # Check if this banner is the only active one
                active_banners_count = Banner.objects.filter(is_deactive=False, is_deleted=False).count()

                if active_banners_count <= 1 and not banner.is_deactive:
                    response_data = {
                        'status': 'fail',
                        'message': 'You cannot delete this banner. You need to have at least one active banner.'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                # Mark the banner object as deleted
                banner.is_deleted = True
                banner.is_deactive = True
                banner.save()

                # Log the activity
                activity = UserActivity(
                    table_id=banner.pk,  # ID of the banner
                    table_name='Banner',  # Name of the model
                    ua_action='Delete',  # Action performed
                    ua_description=f'Deleted banner with ID {banner.pk}',  # Action description
                    created_by=request.user,  # Current user performing the action
                    request_data=request.data,  # Request data
                )
                activity.save()

                response_data = {
                    'status': 'success',
                    'message': 'Banner Deleted Successfully'
                }
                # Return a success response
                return Response(response_data, status=status.HTTP_200_OK)

        except Banner.DoesNotExist:
            # Handle case where banner is not found
            response_data = {
                'status': 'fail',
                'message': "Banner not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# TestimonialView class provides CRUD operations for managing testimonials, including creation, retrieval, updating, and deletion.
class TestimonialView(APIView):
    permission_classes = [IsAuthenticated]
    # Ensure the user is authenticated for all methods
    
    def post(self, request):
        if 'page_number' in request.data or 'page_size' in request.data:
            return self.fetch_testimonials(request)
        elif 'name' in request.data and 'title' in request.data and 'email' in request.data and 'comments' in request.data:
            return self.create_testimonial(request)
        else:
            return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)

    def create_testimonial(self, request):
        try:
            name = request.data.get('name')
            title = request.data.get('title')
            email = request.data.get('email')
            comments = request.data.get('comments')

            # Check for existing banner title
            if Testimonial.objects.filter(title=title, name=name, is_deleted=False).exists():
                return Response({
                    'status': 'fail',
                    'message': 'A testimonial with this title already exists.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Limit to active banners
            active_testimonial_count = Testimonial.objects.filter(is_deactive=False, is_deleted=False).count()
            is_deactive = active_testimonial_count >= 10

            # Create new banner
            Testimonial.objects.create(
                title=title,
                name=name,  # Use the first image URL
                email=email,  # Use the first image URL
                comments=comments,
                is_deactive=is_deactive,
                created_by=request.user
            )

            return Response({'status': 'success', 'message': 'Testimonial added successfully.'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_testimonials(self, request):
        data = {
        "total_pages": 0,
        "current_page": 0,
        "total_items": 0,
        "results": []
        }
        try:
            page_number = request.POST.get('page_number', 1)
            page_size = request.POST.get('page_size', 10)
            testimonial_id = request.POST.get('testimonial_id', None)
            search = request.POST.get('search', '')

            if not isnumber(page_number) or int(page_number) <= 0:
                return Response({'status': 'fail', 'message': 'Invalid page number. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(page_size) or int(page_size) <= 0:
                return Response({'status': 'fail', 'message': 'Invalid page size. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            if testimonial_id and (not isnumber(testimonial_id) or int(testimonial_id) <= 0):
                return Response({'status': 'fail', 'message': 'Invalid banner ID. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            testimonial = Testimonial.objects.filter(is_deleted=False)
            print(testimonial, 'testimonial_id')
            if testimonial_id:
                testimonial = testimonial.filter(testimonial_id=testimonial_id)
                if not testimonial.exists():
                    return Response({'status': 'fail', 'message': 'Testimonial ID does not exist.', 'data': data}, status=status.HTTP_404_NOT_FOUND)

            if search:
                testimonial = testimonial.filter(
                    Q(title__icontains=search) | Q(name__icontains=search) | Q(email__icontains=search) | Q(commments__icontains=search)
                )

            total_items = testimonial.count()
            print('total_items', total_items)
            total_pages = (total_items + page_size - 1) // page_size

            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size
            paginated_testimonial = testimonial[start_index:end_index]

            serialized_testimonial = TestimonialSerializer(paginated_testimonial, many=True)
            print(serialized_testimonial.data, 'serialized_banners.data')
            data = {
                'total_pages': total_pages,
                'current_page': page_number,
                'total_items': total_items,
                'results': serialized_testimonial.data
            }
            return Response({'status': 'success', 'message': 'Testimonial retrieved successfully.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}', 'data': data}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        testimonial_id = request.data.get('testimonial_id')
        title = request.data.get('title', None)
        name = request.data.get('name', None)
        email = request.data.get('email', None)
        comments = request.data.get('comments', None)
        message = 'Testimonial Updated Successfully.'

        # Validate banner_id
        if not testimonial_id:
            return Response({'status': 'fail', 'message': 'Testimonial ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if not isnumber(testimonial_id):
                return Response({'status': 'fail', 'message': 'Invalid Testimonial ID. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if banner exists
            testimonial_data = Testimonial.objects.filter(testimonial_id=testimonial_id, is_deleted=False).first()
            if not testimonial_data:
                return Response({'status': 'fail', 'message': 'Testimonial does not exist.'}, status=status.HTTP_404_NOT_FOUND)
            
            if name:
                if Testimonial.objects.filter(name=name, is_deleted=False).exclude(testimonial_id=testimonial_id).exists():
                    return Response({'status': 'fail', 'message': 'A Testimonial with this name already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            # Update banner fields if provided
            if title:
                testimonial_data.title = title

            if name:
                testimonial_data.name = name

            if email:
                testimonial_data.email = email

            if comments:
                testimonial_data.comments = comments

            # Banner activation/deactivation logic
            if testimonial_id and not any([title, name, email, comments]):
                active_testimonial_count = Testimonial.objects.filter(is_deactive=False, is_deleted=False).count()

                if active_testimonial_count >= 10 and not testimonial_data.is_deactive:
                    return Response({
                        'status': 'fail',
                        'message': 'Maximum of 5 active testimonials allowed. Please deactivate an existing testimonial before activating this one.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if active_testimonial_count <= 1 and not testimonial_data.is_deactive:
                    return Response({
                        'status': 'fail',
                        'message': 'You cannot deactivate this testimonial. You need to have at least one active testimonial.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                testimonial_data.is_deactive = not testimonial_data.is_deactive
                message = 'Testimonial Deactivated Successfully.' if testimonial_data.is_deactive else 'Testimonial Activated Successfully.'

            # Update audit fields and save
            testimonial_data.modified_at = timezone.now()
            testimonial_data.save()

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        # Get the testimonial ID from query parameters if provided
        testimonial_id = request.data.get('testimonial_id', None)
        if not testimonial_id:
            response_data = {
                'status': 'fail',
                'message': "Testimonial id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve the testimonial object by ID
            testimonial = Testimonial.objects.get(testimonial_id=testimonial_id, is_deleted=False)

            # Check if this testimonial is the only active one
            active_testimonials_count = Testimonial.objects.filter(is_deactive=False, is_deleted=False).count()

            if active_testimonials_count <= 1 and not testimonial.is_deactive:
                response_data = {
                    'status': 'fail',
                    'message': 'You cannot delete this testimonial. You need to have at least one active testimonial.'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            # Using transaction.atomic() for atomicity
            with transaction.atomic():
                # Mark the testimonial as deleted
                testimonial.is_deleted = True
                testimonial.is_deactive = True
                testimonial.save()

                # Log the delete activity
                activity = UserActivity(
                    table_id=testimonial.pk,  # ID of the deleted testimonial
                    table_name='Testimonial',  # Name of the table
                    ua_action='delete',  # Action performed
                    ua_description=f'Deleted testimonial with ID {testimonial.pk}',  # Action description
                    created_by=request.user,  # Current user performing the action
                    request_data=request.data,  # Request data
                )
                activity.save()

            response_data = {
                'status': 'success',
                'message': 'Testimonial Deleted Successfully'
            }
            # Return a success response
            return Response(response_data, status=status.HTTP_200_OK)

        except Testimonial.DoesNotExist:
            # Handle case where testimonial is not found
            response_data = {
                'status': 'fail',
                'message': "Testimonial not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# AboutUsView class provides CRUD operations for AboutUs model, including listing, creation, updating, and deletion.
class AboutUsView(APIView):
    # Ensure the user is authenticated for all methods
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            # Retrieve the single AboutUs entry
            about_us = AboutUs.objects.first()
            if about_us:
                # Serialize the AboutUs object
                serializer = AboutUsSerializer(about_us, context={'request': request})
                response_data = {
                    'status': 'success',
                    'message': 'AboutUs Data',
                    'data': serializer.data
                }
                # Return the serialized AboutUs data
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Handle case where no AboutUs entry is found
                response_data = {
                    'status': 'fail',
                    'message': "No AboutUs entry found.",
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    """
    API View for updating or creating AboutUs entries.
    """

    def put(self, request):
        try:
            user = request.user

            # Check if an AboutUs entry already exists
            about_us_instance = AboutUs.objects.first()

            # Initialize the serializer with the existing or new AboutUs instance and the new data
            if about_us_instance:
                serializer = AboutUsSerializer(about_us_instance, data=request.data, partial=True,
                                               context={'request': request})
            else:
                serializer = AboutUsSerializer(data=request.data, context={'request': request})

            # Check if the provided data is valid
            if serializer.is_valid():
                # Start a database transaction
                with transaction.atomic():
                    # Save the updated or newly created AboutUs entry
                    if about_us_instance:
                        saved_instance = serializer.save(created_by=user, updated_at=datetime.now())
                    else:
                        saved_instance = serializer.save(created_by=user)
                    action = 'update' if about_us_instance else 'create'
                    description = f'Updated AboutUs with ID {saved_instance.pk}' if about_us_instance else f'Created new AboutUs with ID {saved_instance.pk}'

                    # Log the activity
                    activity = UserActivity(
                        table_id=saved_instance.pk,  # ID of the AboutUs entry
                        table_name='AboutUs',  # Name of the table
                        ua_action=action,  # Action performed
                        ua_description=description,  # Action description
                        created_by=user,  # Current user performing the action
                        request_data=request.data,  # Request data
                        response_data=serializer.data,  # Serialized response data
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'AboutUs Updated Successfully' if about_us_instance else 'AboutUs Created Successfully',
                        'data': serializer.data
                    }
                    # Return a success response with the updated data
                    return Response(response_data,
                                    status=status.HTTP_200_OK if about_us_instance else status.HTTP_201_CREATED)

            # If data is invalid, return the error messages
            response_data = {
                'status': 'fail',
                'message': f'{serializer.errors}'
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RandomstuffView(APIView):
    # Ensure the user is authenticated for all methods
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            # Retrieve the single Randomstuff entry
            randomstuff = Randomstuff.objects.first()
            if randomstuff:
                # Serialize the Randomstuff object
                serializer = RandomstuffSerializer(randomstuff, context={'request': request})
                response_data = {
                    'status': 'success',
                    'message': 'Randomstuff Data',
                    'data': serializer.data
                }
                # Return the serialized Randomstuff data
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Handle case where no Randomstuff entry is found
                response_data = {
                    'status': 'fail',
                    'message': "No Randomstuff entry found.",
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def put(self, request):
        try:
            user = request.user

            # Check if a Randomstuff entry already exists
            randomstuff_instance = Randomstuff.objects.first()

            # Initialize the serializer with the existing or new Randomstuff instance and the new data
            if randomstuff_instance:
                serializer = RandomstuffSerializer(randomstuff_instance, data=request.data, partial=True,
                                                   context={'request': request})
            else:
                serializer = RandomstuffSerializer(data=request.data, context={'request': request})

            # Check if the provided data is valid
            if serializer.is_valid():
                # Start a database transaction
                with transaction.atomic():
                    # Save the updated or newly created Randomstuff entry
                    if randomstuff_instance:
                        saved_instance = serializer.save(created_by=user, updated_at=datetime.now())
                    else:
                        saved_instance = serializer.save(created_by=user)
                    action = 'update' if randomstuff_instance else 'create'
                    description = f'Updated Randomstuff with ID {saved_instance.pk}' if randomstuff_instance else f'Created new Randomstuff with ID {saved_instance.pk}'

                    # Log the activity
                    activity = UserActivity(
                        table_id=saved_instance.pk,  # ID of the Randomstuff entry
                        table_name='Randomstuff',  # Name of the table
                        ua_action=action,  # Action performed
                        ua_description=description,  # Action description
                        created_by=user,  # Current user performing the action
                        request_data=request.data,  # Request data
                        response_data=serializer.data,  # Serialized response data
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Randomstuff Updated Successfully' if randomstuff_instance else 'Randomstuff Created Successfully',
                        'data': serializer.data
                    }
                    # Return a success response with the updated data
                    return Response(response_data,
                                    status=status.HTTP_200_OK if randomstuff_instance else status.HTTP_201_CREATED)

            # If data is invalid, return the error messages
            response_data = {
                'status': 'fail',
                'message': f'{serializer.errors}'
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContactUsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        try:
            user = request.user

            # Check if a ContactUs entry already exists
            contact_us_instance = ContactUs.objects.first()

            # Initialize the serializer with the existing or new ContactUs instance and the new data
            if contact_us_instance:
                serializer = ContactUsSerializer(contact_us_instance, data=request.data, partial=True,
                                                 context={'request': request})
            else:
                serializer = ContactUsSerializer(data=request.data, context={'request': request})

            # Check if the provided data is valid
            if serializer.is_valid():
                # Start a database transaction
                with transaction.atomic():
                    # Save the updated or newly created ContactUs entry
                    if contact_us_instance:
                        saved_instance = serializer.save(created_by=user, updated_at=datetime.now())
                    else:
                        saved_instance = serializer.save(created_by=user)
                    action = 'update' if contact_us_instance else 'create'
                    description = f'Updated ContactUs with ID {saved_instance.pk}' if contact_us_instance else f'Created new ContactUs with ID {saved_instance.pk}'

                    # Log the activity
                    activity = UserActivity(
                        table_id=saved_instance.pk,  # ID of the ContactUs entry
                        table_name='ContactUs',  # Name of the table
                        ua_action=action,  # Action performed
                        ua_description=description,  # Action description
                        created_by=user,  # Current user performing the action
                        request_data=request.data,  # Request data
                        response_data=serializer.data,  # Serialized response data
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'ContactUs Updated Successfully' if contact_us_instance else 'ContactUs Created Successfully',
                        'data': serializer.data
                    }
                    # Return a success response with the updated data
                    return Response(response_data,
                                    status=status.HTTP_200_OK if contact_us_instance else status.HTTP_201_CREATED)

            # If data is invalid, return the error messages
            response_data = {
                'status': 'fail',
                'message': f'{serializer.errors}'
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            # Retrieve the single ContactUs entry
            contactus = ContactUs.objects.first()
            if contactus:
                # Serialize the ContactUs object
                serializer = ContactUsSerializer(contactus, context={'request': request})
                response_data = {
                    'status': 'success',
                    'message': 'ContactUs Data',
                    'data': serializer.data
                }
                # Return the serialized ContactUs data
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Handle case where no ContactUs entry is found
                response_data = {
                    'status': 'fail',
                    'message': "No ContactUs entry found.",
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServiceGroupAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_servicegroup(request)
            elif 'group_name' in request.data:
                return self.create_servicegroup(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_servicegroup(self, request):
        try:
            with transaction.atomic():
                # data = request.data.copy()
                # if 'description' not in data:
                #     data['description'] = 'Default description'  # Set a default value for description
                group_name = request.data.get('group_name')
                if not group_name: return Response({'status': 'fail', 'message': 'Service Group name is required'}, status=status.HTTP_400_BAD_REQUEST)
                service_group = ServiceGroup.objects.filter(group_name=group_name, is_deleted=False).first()
                if service_group:
                    return Response({'status': 'fail', 'message': 'Service Group already exists'}, status=status.HTTP_400_BAD_REQUEST)
                serializer = ServiceGroupSerializer(data=request.data, context={'request': request})
                if serializer.is_valid():
                    serializer.save(created_by=request.user)
                    # Log the activity after successfully saving the ServiceGroup
                    activity = UserActivity(
                        table_id=serializer.instance.pk,
                        table_name='ServiceGroup',
                        ua_action='create',
                        ua_description=f'Created Service Group "{serializer.instance.group_name}"',
                        created_by=request.user,
                        request_data=request.data,  # Request data
                        response_data=serializer.data,  # Serialized response data
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Service Group Created Successfully'
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
                response_data = {
                    'status': 'fail',
                    'message': f'{serializer.errors}'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_servicegroup(self, request):
        try:
            # Retrieve parameters from the request
            servicegroup_id = request.data.get('servicegroup_id', None)
            search_query = request.data.get('search', None)
            page_size = request.data.get('page_size')
            page_number = request.data.get('page_number', 1)
            filter_field = request.data.get('filter_field', None)
            filter_value = request.data.get('filter_value', None)
            order_by = request.data.get('order_by', "ascending")
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            is_deactive = request.data.get('is_deactive', None)

            # Validate page_size and page_number
            if not page_size or not page_size.isdigit() or int(page_size) <= 0:
                response_data = {
                    'status': 'fail',
                    'message': 'page_size parameter is required and must be a positive integer.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            if not page_number or not page_number.isdigit() or int(page_number) <= 0:
                response_data = {
                    'status': 'fail',
                    'message': 'page_number parameter is required and must be a positive integer.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            # Initialize the queryset
            queryset = ServiceGroup.objects.filter(is_deleted=False).order_by('-pk')

            # Apply filters to the queryset
            if servicegroup_id:
                queryset = queryset.filter(servicegroup_id=servicegroup_id)

            if is_deactive == "true":
                queryset = queryset.filter(is_deactive=True)
            elif is_deactive == 'false':
                queryset = queryset.filter(is_deactive=False)

            if start_date and end_date:
                start_date_parsed = parse_date(start_date)
                end_date_parsed = parse_date(end_date)
                queryset = queryset.filter(created_at__range=[start_date_parsed, end_date_parsed + timedelta(days=1)])

            if filter_field:
                if order_by == "descending":
                    queryset = queryset.order_by(f'-{filter_field}')
                else:
                    queryset = queryset.order_by(f'{filter_field}')
                if filter_value:
                    filter_kwargs = {filter_field: filter_value}
                    queryset = queryset.filter(**filter_kwargs)

            if search_query:
                queryset = queryset.filter(
                    Q(group_name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )

            # Check if queryset is empty before paginating
            if not queryset.exists():
                paginated_response_data = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }

                response_data = {
                    'status': 'fail',
                    'message': 'ServiceGroup Data not found',
                    'data': paginated_response_data
                }
                return Response(response_data, status=status.HTTP_200_OK)

            # Paginate the queryset
            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            # Serialize the paginated queryset
            serializer = ServiceGroupSerializer(page_obj.object_list, many=True, context={'request': request,
                                                                                          'exclude_fields': [
                                                                                              "created_at",
                                                                                              "updated_at",
                                                                                              "is_deleted",
                                                                                              "updated_by",
                                                                                              "created_by"]})
            paginated_response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': serializer.data
            }
            response_data = {
                'status': 'success',
                'message': 'ServiceGroup Data',
                'data': paginated_response_data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            response_data = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    
    def put(self, request):
        try:
            with transaction.atomic():
                servicegroup_id = request.data.get('servicegroup_id')
                if not servicegroup_id:
                    return Response({
                        'status': 'fail',
                        'message': 'Service group id is required'
                    }, status=status.HTTP_400_BAD_REQUEST)

                service_group = ServiceGroup.objects.get(servicegroup_id=servicegroup_id)

                # Check if service group is soft deleted
                if service_group.is_deleted:
                    return Response({
                        'status': 'fail',
                        'message': f'Service group not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                is_deactive = 'is_deactive' in request.data
                serializer = ServiceGroupSerializer(service_group, data=request.data, partial=True,
                                                    context={'request': request})
                if serializer.is_valid():
                    serializer.save(modified_at=datetime.now())
                    # Log the update activity
                    activity = UserActivity(
                        table_id=service_group.pk,
                        table_name='ServiceGroup',
                        ua_action='update',
                        ua_description=f'Updated Service Group "{serializer.instance.group_name}"',
                        created_by=request.user,
                        request_data=request.data,  # Request data
                        response_data=serializer.data,  # Serialized response data
                    )
                    activity.save()
                    # return Response({
                    #     'status': 'success',
                    #     'message': f'Service group updated successfully',

                    # })

                    if ('description' in request.data or 'group_name' in request.data) and is_deactive:
                        response_data = {
                            'status': 'success',
                            'message': 'Service group Updated Successfully',

                        }
                    elif is_deactive:
                        response_data = {
                            'status': 'success',
                            'message': 'Service group Deactivate Successfully' if serializer.instance.is_deactive else 'Service group Activate Successfully',

                        }
                    else:
                        response_data = {
                            'status': 'success',
                            'message': 'Service group Updated Successfully',

                        }

                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'status': 'fail',
                        'message': 'Failed to update service group',
                        'data': serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)

        except ServiceGroup.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': f'Service group with id {servicegroup_id} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def delete(self, request):
        servicegroup_id = request.data.get('servicegroup_id', None)
        # delete_services = request.data.get('delete_services', None)

        if not servicegroup_id:
            return Response({
                'status': 'fail',
                'message': 'ServiceGroup id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                service_group = ServiceGroup.objects.get(servicegroup_id=servicegroup_id)

                active_servicegroup_count = ServiceGroup.objects.filter(is_deactive=False, is_deleted=False).count()
                if active_servicegroup_count <= 1 and not service_group.is_deactive:
                    response_data = {
                        'status': 'fail',
                        'message': 'You cannot delete this ServiceGroup. You need to have at least one active ServiceGroup.'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                services = Service.objects.filter(service_group=service_group)
                if services.exists():
                    services.update(is_deleted=True)  # Soft delete all associated services
                    service_group.is_deleted = True  # Soft delete ServiceGroup
                    service_group.is_deactive = True
                    service_group.save()
                    # Log the deletion activity
                    activity = UserActivity(
                        table_id=service_group.pk,
                        table_name='ServiceGroup',
                        ua_action='delete',
                        ua_description=f'Soft deleted Service Group "{service_group.group_name}"',
                        created_by=request.user,
                        request_data=request.data,  # Request data

                    )
                    activity.save()
                    return Response({
                        'status': 'success',
                        'message': 'ServiceGroup and its services deleted successfully'
                    }, status=status.HTTP_200_OK)
                else:
                    service_group.is_deleted = True  # Soft delete ServiceGroup
                    service_group.is_deactive = True
                    service_group.save()
                    # Log the deletion activity
                    activity = UserActivity(
                        table_id=service_group.pk,
                        table_name='ServiceGroup',
                        ua_action='delete',
                        ua_description=f'deleted Service Group "{service_group.group_name}"',
                        created_by=request.user,
                        request_data=request.data,  # Request data

                    )
                    activity.save()
                    return Response({
                        'status': 'success',
                        'message': 'ServiceGroup deleted successfully, no associated services found'
                    }, status=status.HTTP_200_OK)

        except ServiceGroup.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': f'ServiceGroup with id {servicegroup_id} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class YouTubeVideoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def fetch_youtubevideo(self, request):
        try:
            youtube_id = request.data.get('youtubevideo_id', None)
            search_query = request.data.get('search', None)
            filter_field = request.data.get('filter_field', None)
            filter_value = request.data.get('filter_value', None)
            order_by = request.data.get('order_by', "ascending")
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            is_deactive = request.data.get('is_deactive', None)

            page_size = request.data.get('page_size', 10)
            page_number = request.data.get('page_number', 1)

            # Validate page_size and page_number
            if not page_size or not str(page_size).isdigit() or int(page_size) <= 0:
                response_data = {
                    'status': 'fail',
                    'message': 'page_size parameter is required and must be a positive integer.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            if not page_number or not str(page_number).isdigit() or int(page_number) <= 0:
                response_data = {
                    'status': 'fail',
                    'message': 'page_number parameter is required and must be a positive integer.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            # Filter out soft-deleted records
            queryset = YouTubeVideo.objects.filter(is_deleted=False).order_by("-pk")

            if not queryset.exists():
                paginated_response_data = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }

                response_data = {
                    'status': 'fail',
                    'message': 'YouTubeVideo Data not found',
                    'data': paginated_response_data
                }
                return Response(response_data, status=status.HTTP_200_OK)

            # Filter by date range if provided
            if start_date and end_date:
                start_date_parsed = parse_date(start_date)
                end_date_parsed = parse_date(end_date)
                queryset = queryset.filter(created_at__range=[start_date_parsed, end_date_parsed + timedelta(days=1)])

            # Apply dynamic filtering and ordering
            if filter_field:
                if order_by == "descending":
                    queryset = queryset.order_by(f'-{filter_field}')
                else:
                    queryset = queryset.order_by(f'{filter_field}')

                if filter_value:
                    filter_kwargs = {filter_field: filter_value}
                    queryset = queryset.filter(**filter_kwargs)

            # Filter by active or deactivated status
            if is_deactive == "true":
                queryset = queryset.filter(is_deactive=True)
            elif is_deactive == "false":
                queryset = queryset.filter(is_deactive=False)

            # Retrieve a specific YouTube video by ID if provided
            if youtube_id:
                try:
                    youtube_video = queryset.get(youtubevideo_id=youtube_id)
                    serializer = YoutubeSerializer(youtube_video, context={'request': request})
                    response_data = {
                        'status': 'success',
                        'message': 'YouTubeVideo Data',
                        'data': serializer.data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                except YouTubeVideo.DoesNotExist:
                    response_data = {
                        'status': 'fail',
                        'message': f'YouTubeVideo not found.'
                    }
                    return Response(response_data, status=status.HTTP_404_NOT_FOUND)

            # Apply search filter if provided
            if search_query:
                queryset = queryset.filter(
                    Q(video_title__icontains=search_query)
                )

            # Paginate the queryset
            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            # Serialize the paginated queryset
            serializer = YoutubeSerializer(page_obj.object_list, many=True, context={'request': request,
                                                                                     'exclude_fields': ["created_at",
                                                                                                        "updated_at",
                                                                                                        "is_deleted",
                                                                                                        "updated_by",
                                                                                                        "created_by"]})

            paginated_response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': serializer.data
            }

            response_data = {
                'status': 'success',
                'message': 'YouTubeVideo Data',
                'data': paginated_response_data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except YouTubeVideo.DoesNotExist as e:
            response_data = {
                'status': 'fail',
                'message': 'YouTubeVideo not found',
                'data': str(e)
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': 'Internal server error',
                'data': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_youtubevideo(request)
            elif 'video_title' in request.data and 'youtube_thumbnail_image' in request.data:
                return self.create_youtubevideo(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_youtubevideo(self, request):
        try:
            with transaction.atomic():
                is_deactive = None
                status_value = YouTubeVideo.objects.filter(is_deactive=False)
                # print(status_value)

                if status_value:
                    is_deactive = True

                if YouTubeVideo.objects.count() >= 10:
                    return Response(
                        {'error': 'The maximum number of YouTubeVideo records has been reached. Cannot insert more.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Proceed to save the YouTubeVideo
                serializer = YoutubeSerializer(data=request.data, context={'request': request})
                if serializer.is_valid():
                    # Set the created_by field before saving
                    youtubevideo = serializer.save(created_by=request.user)

                    if is_deactive:
                        youtubevideo.is_deactive = True
                        youtubevideo.save()

                    # Log the creation activity
                    activity = UserActivity(
                        table_id=serializer.instance.pk,
                        table_name='YouTubeVideo',
                        ua_action='create',
                        ua_description=f'Created YouTube Video "{serializer.instance.video_title}"',
                        created_by=request.user,
                        request_data=request.data,  # Request data
                        response_data=serializer.data,  # Serialized response data                        
                    )
                    activity.save()
                    respons_data = {
                        'status': 'success',
                        'message': 'YouTube Video Created Successfully',

                    }
                    return Response(respons_data, status=status.HTTP_201_CREATED)

                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            respons_data = {
                'status': 'error',
                'message': 'Internal server error. Please try again later.',
                'data': str(e)
            }
            return Response(respons_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            with transaction.atomic():
                youtubevideo_id = request.data.get('youtubevideo_id', None)
                if not youtubevideo_id:
                    return Response({
                        'status': 'fail',
                        'message': 'YouTubeVideo id is required'
                    }, status=status.HTTP_400_BAD_REQUEST)

                youtube_video = YouTubeVideo.objects.get(youtubevideo_id=youtubevideo_id)

                # Check if YouTubeVideo is soft deleted
                if youtube_video.is_deleted:
                    return Response({
                        'status': 'fail',
                        'message': f'YouTubeVideo not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                is_deactive = request.data.get('is_deactive', None)
                if is_deactive is not None:
                    is_deactive = is_deactive.lower() in ['true']

                if is_deactive is False:  # Check if activating
                    active_video = YouTubeVideo.objects.filter(is_deactive=False, is_deleted=False).exclude(
                        youtubevideo_id=youtubevideo_id).first()
                    # print(active_video)
                    if active_video:
                        active_video.is_deactive = True
                        active_video.save()

                if youtube_video.is_deactive == False and is_deactive is True:
                    return Response({
                        'status': 'fail',
                        'message': 'Cannot deactivate the only active video'
                    }, status=status.HTTP_400_BAD_REQUEST)

                serializer = YoutubeSerializer(youtube_video, data=request.data, partial=True,
                                               context={'request': request})
                if serializer.is_valid():
                    serializer.save(modified_at=datetime.now())
                    # Log the update activity
                    activity = UserActivity(
                        table_id=youtube_video.pk,
                        table_name='YouTubeVideo',
                        ua_action='update',
                        ua_description=f'Updated YouTube Video "{serializer.instance.video_title}"',
                        created_by=request.user,
                        request_data=request.data,  # Request data
                        response_data=serializer.data,  # Serialized response data
                    )
                    activity.save()

                    is_deactive_in_request = 'is_deactive' in request.data
                    if (
                            'video_title' in request.data or 'youtube_link' in request.data or 'youtube_thumbnail_image' in request.data) and is_deactive_in_request:
                        response_data = {
                            'status': 'success',
                            'message': 'YouTubeVideo Updated Successfully',
                        }
                    elif is_deactive_in_request:
                        response_data = {
                            'status': 'success',
                            'message': 'YouTubeVideo Deactivate Successfully' if serializer.instance.is_deactive else 'YouTubeVideo Activate Successfully',
                        }
                    else:
                        response_data = {
                            'status': 'success',
                            'message': 'YouTubeVideo Updated Successfully',
                        }

                    return Response(response_data, status=status.HTTP_200_OK)

                return Response({
                    'status': 'fail',
                    'message': 'Failed to update YouTubeVideo',
                    'data': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            with transaction.atomic():
                youtubevideo_id = request.data.get('youtubevideo_id', None)
                if not youtubevideo_id:
                    return Response({
                        'status': 'fail',
                        'message': 'YouTubeVideo id is required'
                    }, status=status.HTTP_400_BAD_REQUEST)

                try:
                    youtube_video = YouTubeVideo.objects.get(youtubevideo_id=youtubevideo_id)
                except YouTubeVideo.DoesNotExist:
                    return Response({
                        'status': 'fail',
                        'message': f'YouTubeVideo not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                active_youtube_count = YouTubeVideo.objects.filter(is_deactive=False, is_deleted=False).count()

                if active_youtube_count <= 1 and not youtube_video.is_deactive:
                    response_data = {
                        'status': 'fail',
                        'message': 'You cannot delete this youtubevideo. You need to have at least one active youtubevideo.'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                # Soft delete the YouTubeVideo by setting is_deleted=True
                youtube_video.is_deleted = True
                youtube_video.is_deactive = True
                youtube_video.save()
                # Log the deletion activity
                activity = UserActivity(
                    table_id=youtube_video.pk,
                    table_name='YouTubeVideo',
                    ua_action='delete',
                    ua_description=f'deleted YouTube Video "{youtube_video.video_title}"',
                    created_by=request.user,
                    request_data=request.data,  # Request data

                )
                activity.save()

                return Response({
                    'status': 'success',
                    'message': f'YouTubeVideo deleted successfully'
                }, status=status.HTTP_200_OK)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PartnerAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        print(request.data)
        if 'page_number' in request.data or 'page_size' in request.data:
            return self.get_partner(request)
        elif 'partner_name' in request.data and 'logo' in request.data and 'description' in request.data:
            return self.create_partner(request)
        else:
            return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)

    def create_partner(self, request):
        try:
            partner_name = request.data.get('partner_name')
            partners_logo_images = request.FILES.getlist('logo')
            partners_description = request.data.get('description')

            # partner_name_validation = isstring(partner_name)
            # if partner_name_validation == False:
            #     return Response({'status': 'fail', 'message': 'Invalid partner name. It should contain only alphabetic characters and spaces.'}, status=status.HTTP_400_BAD_REQUEST)

            def save_files(files, directory):
                if not os.path.exists(directory):
                    os.makedirs(directory)

                urls = []
                for file in files:
                    # Ensure the file is valid
                    if not hasattr(file, 'name'):
                        return None  # Indicate an error state
                    
                    file_extension = file.name.split('.')[-1].lower()
                    if file_extension not in ['png', 'jpg']:
                        return None  # Indicate an error state

                    # Sanitize file name
                    sanitized_file_name = file.name.replace(' ', '').replace('(', '').replace(')', '')
                    file_path = os.path.join(directory, sanitized_file_name)
                    
                    # Save the file
                    with open(file_path, "wb") as f:
                        f.write(file.read())

                    # Construct URL
                    urls.append(f'/{directory}{sanitized_file_name}')
                
                return urls

            logo_image_urls = save_files(partners_logo_images, 'media/Partners/Logos/')

            if logo_image_urls is None:
                return Response({
                    'status': 'fail',
                    'message': 'Invalid file type. Only PNG and JPG files are allowed.'
                }, status=status.HTTP_400_BAD_REQUEST)

            if Partner.objects.filter(partner_name=partner_name, is_deleted=False).exists():
                return Response({'status': 'fail', 'message': f'Partner with name "{partner_name}" already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            partner = Partner.objects.create(
                partner_name=partner_name,
                logo=logo_image_urls[0] if logo_image_urls else None,  # Use the first image if provided
                description=partners_description,
                created_by=request.user
            )

            return Response({'status': 'success', 'message': 'Partner added successfully.'}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def get_partner(self, request):
        data = {
            "total_pages": 0,
            "current_page": 0,
            "total_items": 0,
            "results": []
        }
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        partner_id = request.data.get('partner_id', None)
        search = request.data.get('search')
        print('==>', page_number, page_size, partner_id, search)
        try:
            page_number_validation = isnumber(page_number)
            if page_number_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid page number. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)
            
            page_size_validation = isnumber(page_size)
            if page_size_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid page size. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            if partner_id:
                partner_id_validation = isnumber(partner_id)
                if partner_id_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid partner ID. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size


            partners = Partner.objects.filter(is_deleted=False)
            print('==>', partners)
            if partner_id is not None:
                paginated_partners = partners.filter(partner_id=partner_id, is_deleted=False)
                if not paginated_partners.exists():
                    return Response({ 'stauts': 'fail', 'message': 'Partner ID does not exist.', 'data': data }, status=status.HTTP_404_NOT_FOUND)

            elif search is not None:
                print('serarch')
                paginated_partners = partners.filter(Q(partner_name__icontains=search) | Q(description__icontains=search), is_deleted=False)
                if not paginated_partners.exists(): 
                    return Response({ 'status': 'fail', 'message': 'No partner found matching the search criteria.', 'data': data }, status=status.HTTP_200_OK)

            else:
                paginated_partners = partners[start_index:end_index]
            total_items = partners.count()
            total_pages = (len(partners) + page_size - 1) // page_size

            serialized_partners = PartnerSerializer(paginated_partners, many=True)
            for partner in serialized_partners.data:
                partner['logo'] = f'http://{request.META["HTTP_HOST"]}{partner["logo"]}'
            data = {
                'total_pages': total_pages,
                'current_page': page_number,
                'total_items': total_items,
                'results': serialized_partners.data
            }
            return Response({
                'status': 'success',
                'message': 'Get all partners.',
                'data': data}, status=status.HTTP_200_OK)

        except Exception as e: 
            return Response({'status': 'error', 'message': str(e), 'data': data}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        partner_id = request.data.get('partner_id')
        partner_name = request.data.get('partner_name', None)
        partner_logo_image = request.FILES.getlist('logo', None)
        partner_description = request.data.get('description', None)
        message = 'Partner updated Successfully.'
        try:
            if not partner_id:
                return Response({'status': 'fail', 'message': 'partner ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if partner_id:
                partner_id_validation = isnumber(partner_id)
                if not partner_id_validation:
                    return Response({'status': 'fail', 'message': 'Invalid partner ID. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            partner_data = Partner.objects.filter(partner_id=partner_id, is_deleted=False).first()
            if not partner_data:
                return Response({'status': 'fail', 'message': 'Partner does not exist.'}, status=status.HTTP_404_NOT_FOUND)

            if partner_name:
                if partner_name != partner_data.partner_name:  # Skip check if name matches current partner name
                    name_validation = isstring(partner_name)
                    if not name_validation:
                        return Response({'status': 'fail', 'message': 'Invalid partner name. It should contain only alphabetic characters and spaces.'}, status=status.HTTP_400_BAD_REQUEST)

                    existing_partner = Partner.objects.filter(partner_name=partner_name, is_deleted=False).first()
                    if existing_partner:
                        return Response({'status': 'fail', 'message': f'Partner with name "{partner_name}" already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            def save_files(files, directory):
                if not os.path.exists(directory):
                    os.makedirs(directory)
                urls = []
                for file in files:
                    file_extension = file.name.split('.')[-1].lower()
                    if file_extension not in ['png', 'jpg']:
                        return Response({'status': 'fail', 'message': 'Invalid file type. Only PNG and JPG files are allowed.'}, status=status.HTTP_400_BAD_REQUEST)

                    sanitized_file_name = file.name.replace(' ', '').replace('(', '').replace(')', '')
                    file_path = os.path.join(directory, sanitized_file_name)
                    with open(file_path, "wb") as f:
                        f.write(file.read())
                    urls.append(f'/{directory}{sanitized_file_name}')
                return urls

            if partner_name is not None:
                partner_data.partner_name = partner_name

            if partner_logo_image:
                logo_image_urls = save_files(partner_logo_image, 'media/Partners/Logos/')
                if isinstance(logo_image_urls, Response):
                    return logo_image_urls
                partner_data.logo = logo_image_urls[0]

            if partner_description is not None:
                partner_data.description = partner_description

            if partner_id and not any([partner_name, partner_logo_image, partner_description]):
                
                active_partner_count = Partner.objects.filter(is_deactive=False, is_deleted=False).count()
                if active_partner_count <= 1:
                    if partner_data.is_deactive:
                        pass
                    else:
                        return Response({'status': 'fail', 'message': 'You cannot update this partner. You need to have at least one active partner.'}, status=status.HTTP_400_BAD_REQUEST)

                partner_data.is_deactive = not partner_data.is_deactive
                message = 'Banner Activated Successfully.' if not partner_data.is_deactive else 'Banner Deactivated Successfully.'

            partner_data.modified_at = timezone.now()
            partner_data.save()

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            with transaction.atomic():
                partner_id = request.data.get('partner_id')
                if not partner_id:
                    response_data = {
                        'status': 'fail',
                        'message': 'ID is required'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                try:
                    partner_data = Partner.objects.get(partner_id=partner_id, is_deleted=False)
                except Partner.DoesNotExist:
                    response_data = {
                        'status': 'fail',
                        'message': 'Partner not found'
                    }
                    return Response(response_data, status=status.HTTP_404_NOT_FOUND)

                # Check if there is more than one active partner
                active_partners_count = Partner.objects.filter(is_deactive=False, is_deleted=False).count()
                if active_partners_count <= 1 and not partner_data.is_deactive:
                    response_data = {
                        'status': 'fail',
                        'message': 'You cannot delete this partner. You need to have at least one active partner.'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                # Soft delete the Partner by setting is_deleted=True
                partner_data.is_deleted = True
                partner_data.is_deactive = True
                partner_data.save()

                # Log the deletion activity
                activity = UserActivity(
                    table_id=partner_data.pk,
                    table_name='Partner',
                    ua_action='delete',
                    ua_description=f'Deleted Partner "{partner_data.partner_name}".',
                    created_by=request.user,
                    request_data=request.data,
                )
                activity.save()

                response_data = {
                    'status': 'success',
                    'message': 'Partner deleted successfully.'
                }
                return Response(response_data, status=status.HTTP_200_OK)

        except Partner.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': 'Partner not found'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServiceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if 'page_number' in request.data or 'page_size' in request.data:
            return self.fetch_service(request)

        elif 'title' in request.data and 'image' in request.data and 'description' in request.data:
            return self.create_service(request)
        
        else:
            return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)

    def create_service(self, request):
        try:
            service_group_data = None
            service_title = request.data.get('title')
            services_group = request.data.get('services_group_id', None)
            service_images = request.FILES.getlist('image')
            service_description = request.data.get('description')

            if services_group:
                service_group_validation = isnumber(services_group)
                if service_group_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid service group ID. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            if services_group is not None:
                print('services_group', services_group)
                service_group_data = ServiceGroup.objects.filter(servicegroup_id=services_group, is_deleted=False).first()
                if not service_group_data:
                    return Response({'status': 'fail', 'message': 'Service group id does not exist.'}, status=status.HTTP_404_NOT_FOUND)

            service = Service.objects.filter(title=service_title, service_group=service_group_data, is_deleted=False).first()
            if service:
                return Response({'status': 'fail', 'message': 'Service already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            def save_files(files, directory):
                if not os.path.exists(directory):
                    os.makedirs(directory)
                urls = []
                for file in files:
                    if file.name.split('.')[-1].lower() not in ['png', 'jpg']:
                        return Response({'status': 'fail', 'message': 'Invalid file type. Only PNG and JPG files are allowed.'}, status=status.HTTP_400_BAD_REQUEST)

                    file_name = file.name.replace(' ', '').replace('(', '').replace(')', '')
                    file_path = os.path.join(directory, file_name)
                    
                    try:
                        with open(file_path, "wb") as f:
                            f.write(file.read())
                        urls.append(f'/media/Service/{file_name}')
                    except Exception as e:
                        return Response({'status': 'error', 'message': f'Error saving file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return urls

            if service_images:
                service_image_urls = save_files(service_images, 'media/Service/')
                if isinstance(service_image_urls, Response):
                    return service_image_urls  
            else:
                return Response({'status': 'fail', 'message': 'No image files provided.'}, status=status.HTTP_400_BAD_REQUEST)
            print('service_group_data', service_group_data)
            service_data = Service.objects.create(
                title=service_title,
                service_group=service_group_data,
                image=service_image_urls[0], 
                description=service_description,
                created_by=request.user
            )
            activity = UserActivity(
                table_id=service_data.pk,
                table_name='Service',
                ua_action='create',
                ua_description=f'Created Service "{service_data.pk}"',
                created_by=request.user,
                request_data=request.data,  # Request data
                response_data=service_data.title,  # Serialized response data
            )
            activity.save()

            return Response({'status': 'success', 'message': 'Service added successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_service(self, request):
        data = {
            "total_pages": 0,
            "current_page": 0,
            "total_items": 0,
            "results": []
        }
        try:
            page_number = request.data.get('page_number', 1)
            page_size = request.data.get('page_size', 10)
            service_id = request.data.get('service_id', None)

            validation_page_number = isnumber(page_number)
            if validation_page_number == False:
                return Response({'status': 'fail', 'message': 'Invalid page number. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            validation_page_size = isnumber(page_size)
            if validation_page_size == False:
                return Response({'status': 'fail', 'message': 'Invalid page size. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)
            
            if service_id:
                validation_banner_id = isnumber(service_id)
                if validation_banner_id == False:
                    return Response({'status': 'fail', 'message': 'Invalid service ID. It must be a positive integer.', 'data': data}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size

            services = Service.objects.filter(is_deleted=False)

            if service_id is not None:
                paginated_service = services.filter(service_id=service_id, is_deleted=False)
                if not paginated_service.exists():
                    return Response({
                        'status': 'fail', 'message': 'Service id does not exist.', 'data': data}, status=status.HTTP_404_NOT_FOUND)

            else:
                paginated_service = services[start_index:end_index]

            total_items = services.count()
            total_pages = (len(services) + page_size - 1) // page_size

            serialized_service = ServiceSerializer(paginated_service, many=True)
            for service in serialized_service.data:
                service['image'] = f'http://{request.META["HTTP_HOST"]}{service["image"]}'
            data = {
                'total_pages': total_pages,
                'current_page': page_number,
                'total_items': total_items,
                'results': serialized_service.data
            }
            return Response({
                'status': 'success', 'message': 'Get all services.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e), 'data': data}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        service_id = request.data.get('service_id')
        service_title = request.data.get('title', None)
        services_group = request.data.get('services_group', None)
        service_image = request.FILES.getlist('image', None)
        service_description = request.data.get('description', None)
        message = 'Service updated Successfully.'

        if not service_id:
            return Response({'status': 'fail', 'message': 'Service ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if not isnumber(service_id):
                return Response({'status': 'fail', 'message': 'Invalid service ID. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            if services_group and not isnumber(services_group):
                return Response({'status': 'fail', 'message': 'Invalid service group ID. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            def save_files(files, directory):
                if not os.path.exists(directory):
                    os.makedirs(directory)
                urls = []
                for file in files:
                    ext = file.name.split('.')[-1].lower()
                    if ext not in ['png', 'jpg']:
                        return {'error': 'Invalid file type. Only PNG and JPG files are allowed.'}
                    file_name = file.name.replace(' ', '').replace('(', '').replace(')', '')
                    file_path = os.path.join(directory, file_name)
                    with open(file_path, "wb") as f:
                        f.write(file.read())
                    urls.append(f"/media/Service/{file_name}")
                return urls

            service = Service.objects.filter(service_id=service_id, is_deleted=False).first()
            if not service:
                return Response({'status': 'fail', 'message': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)

            if service_title and services_group:
                existing_service = Service.objects.filter(
                    Q(title=service_title) & Q(service_group=services_group) & ~Q(service_id=service_id),
                    is_deleted=False
                ).first()
                if existing_service:
                    return Response({'status': 'fail', 'message': 'Service with this title and group already exists.'},
                                    status=status.HTTP_400_BAD_REQUEST)

            if service_image:
                file_save_result = save_files(service_image, 'media/Service/')
                if isinstance(file_save_result, dict) and 'error' in file_save_result:
                    return Response({'status': 'fail', 'message': file_save_result['error']}, status=status.HTTP_400_BAD_REQUEST)
                service.image = file_save_result[0]

            if service_title:
                service.title = service_title

            if services_group:
                print('services_group', services_group)
                service_group_obj = ServiceGroup.objects.filter(servicegroup_id=services_group, is_deleted=False).first()
                print('service_group_obj', service_group_obj)
                if not service_group_obj:
                    return Response({'status': 'fail', 'message': 'Invalid service group provided.'}, status=status.HTTP_404_NOT_FOUND)
                service.service_group = service_group_obj
                print('service.service_group', service.service_group)

            if service_description:
                service.description = service_description

            if service_id and not any([service_title, service_image, services_group, service_description]):
                active_service_count = Service.objects.filter(is_deactive=False, is_deleted=False).count()
                if active_service_count <= 1 and not service.is_deactive:
                    return Response({'status': 'fail', 'message': 'At least one active service is required.'}, status=status.HTTP_400_BAD_REQUEST)

                service.is_deactive = not service.is_deactive
                message = 'Service Activated Successfully.' if not service.is_deactive else 'Service Deactivated Successfully.'

            service.modified_at = timezone.now()
            service.save()

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            service_id = request.data.get('service_id')
            if service_id:
                try:
                    with transaction.atomic():
                        service = Service.objects.get(service_id=service_id)
                        active_service_count = Service.objects.filter(is_deactive=False, is_deleted=False).count()

                        if active_service_count <= 1 and not service.is_deactive:
                            response_data = {
                                'status': 'fail',
                                'message': 'You cannot delete this service. You need to have at least one active service.'
                            }
                            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                        service.is_deleted = True
                        service.is_deactive = True
                        service.save()
                        # Log the deletion activity
                        activity = UserActivity(
                            table_id=service.pk,
                            table_name='Service',
                            ua_action='delete',
                            ua_description=f'deleted Service "{service.pk}"',
                            created_by=request.user,
                            request_data=request.data,  # Request data
                            # Serialized response data
                        )
                        activity.save()
                        response_data = {
                            'status': 'success',
                            'message': 'Service Deleted Successfully'
                        }
                        return Response(response_data, status=status.HTTP_200_OK)

                except Service.DoesNotExist:
                    response_data = {
                        'status': 'fail',
                        'message': f'Service not found'
                    }
                    return Response(response_data, status=status.HTTP_404_NOT_FOUND)

            else:
                response_data = {
                    'status': 'fail',
                    'message': 'Service id is required'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# APIView for ContactEnquiry
class ContactEnquiryView(APIView):
    # Ensure the user is authenticated for all methods
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_data(request)
            elif 'ce_name' in request.data and 'ce_email' in request.data and 'ce_contact_no' in request.data and 'ce_subject' in request.data and 'ce_message' in request.data:
                return self.create_contact_enquiry(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_contact_enquiry(self, request):
        try:
            with transaction.atomic():
                serializer = ContactEnquirySerializer(data=request.data, context={'request': request})
                if serializer.is_valid():
                    enquiry = serializer.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Contact Enquiry Created Successfully'
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
                response_data = {
                    'status': 'fail',
                    'message': serializer.errors
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_data(self, request):
        try:
            contact_id = request.data.get('contact_id', None)
            if contact_id:
                try:
                    contact = ContactEnquiry.objects.get(ce_id=contact_id, is_deleted=False)
                    serializer = ContactEnquirySerializer(contact, context={'request': request})
                    response_data = {
                        'status': 'success',
                        'message': 'Contact Enquiry Data',
                        'data': serializer.data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                except ContactEnquiry.DoesNotExist:
                    response_data = {
                        'status': 'fail',
                        'message': "Contact Enquiry not found.",
                        'data': {}
                    }
                    return Response(response_data, status=status.HTTP_404_NOT_FOUND)
            else:
                page_size = request.data.get('page_size')
                page = request.data.get('page_number')
                filter_field = request.data.get('filter_field', None)
                filter_value = request.data.get('filter_value', None)
                order_by = request.data.get('order_by', "ascending")
                start_date = request.data.get('start_date', None)
                end_date = request.data.get('end_date', None)

                if not page_size or not page_size.isdigit() or int(page_size) <= 0:
                    response_data = {
                        'status': 'fail',
                        'message': 'page_size parameter is required and must be a positive integer.',
                        'data': {}
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                if not page or not page.isdigit() or int(page) <= 0:
                    response_data = {
                        'status': 'fail',
                        'message': 'page parameter is required and must be a positive integer.',
                        'data': {}
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                queryset = ContactEnquiry.objects.filter(is_deleted=False).order_by('-ce_id')
                if start_date and end_date:
                    start_date_parsed = parse_date(start_date)
                    end_date_parsed = parse_date(end_date)
                    queryset = queryset.filter(
                        created_at__range=[start_date_parsed, end_date_parsed + timedelta(days=1)])
                if filter_field:
                    queryset = queryset.order_by(f'{filter_field}')

                    if order_by == "ascending":
                        queryset = queryset.order_by(f'{filter_field}')
                    if filter_value:
                        filter_kwargs = {filter_field: filter_value}
                        queryset = queryset.filter(**filter_kwargs)
                search_query = request.data.get('search', None)
                if search_query:
                    queryset = queryset.filter(
                        Q(ce_name__icontains=search_query) |
                        Q(ce_email__icontains=search_query) |
                        Q(ce_message__icontains=search_query)
                    )

                paginator = Paginator(queryset, page_size)
                try:
                    page_obj = paginator.page(page)
                except EmptyPage:
                    return Response({
                        'status': 'fail',
                        'message': 'Page not found.',
                        'data': {}
                    }, status=status.HTTP_404_NOT_FOUND)
                if page_obj is not None:
                    serializer = ContactEnquirySerializer(page_obj.object_list, many=True, context={'request': request,
                                                                                                    'exclude_fields': [
                                                                                                        "created_at",
                                                                                                        "updated_at",
                                                                                                        "is_deleted",
                                                                                                        "updated_by",
                                                                                                        "created_by"]})
                    paginated_response_data = {
                        'total_pages': paginator.num_pages,
                        'current_page': page_obj.number,
                        'total_items': paginator.count,
                        'results': serializer.data
                    }
                    response_data = {
                        'status': 'success',
                        'message': 'Contact Enquiry Data',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                serializer = ContactEnquirySerializer(queryset, many=True, context={'request': request})
                response_data = {
                    'status': 'success',
                    'message': 'Contact Enquiry Data',
                    'data': serializer.data
                }
                return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            response_data = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        contact_enquiry_id = request.data.get("contact_enquiry_id")
        ce_status = request.data.get("ce_status")

        if not contact_enquiry_id or not ce_status:
            response_data = {
                'status': 'fail',
                'message': "contact_enquiry_id and ce_status are required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            enquiry = ContactEnquiry.objects.get(ce_id=contact_enquiry_id, is_deleted=False)
            enquiry.ce_status = ce_status
            enquiry.update_by = request.user
            enquiry.updated_at = datetime.now()
            enquiry.save()

            activity = UserActivity(
                table_id=enquiry.pk,
                table_name='ContactEnquiry',
                ua_action='update',
                ua_description=f'Updated Contact Enquiry status from "{previous_status}" to "{ce_status}"',
                created_by=request.user,
                request_data=request.data,  # Request data
            )
            activity.save()

            response_data = {
                'status': 'success',
                'message': 'Contact Enquiry Updated Successfully'
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ContactEnquiry.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': "Contact Enquiry not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        contact_enquiry_id = request.data.get("contact_enquiry_id")

        if not contact_enquiry_id:
            response_data = {
                'status': 'fail',
                'message': "contact_enquiry_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            enquiry = ContactEnquiry.objects.get(ce_id=contact_enquiry_id, is_deleted=False)
            enquiry.is_deleted = True
            enquiry.save()

            activity = UserActivity(
                table_id=enquiry.pk,
                table_name='ContactEnquiry',
                ua_action='delete',
                ua_description='Deleted Contact Enquiry',
                created_by=request.user,
                request_data=request.data,
            )
            activity.save()

            response_data = {
                'status': 'success',
                'message': 'Contact Enquiry Deleted Successfully'
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ContactEnquiry.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': "Contact Enquiry not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RequestResetPassword(APIView):
    """
    API view to handle the email input and send a verification code.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = CustomUser.objects.get(email=email)

                # Generate and store the verification code
                verification_code = get_random_string(length=6, allowed_chars='0123456789')
                hashed_code = make_password(verification_code)
                user.verify_code = hashed_code
                user.verify_code_expire_at = timezone.now() + timedelta(minutes=10)
                user.save()

                # Send verification code via email
                send_mail(
                    'Password Reset Verification Code',
                    f'Your verification code is {verification_code}',
                    'from@example.com',
                    [email],
                    fail_silently=False,
                )

                # Log activity (optional)
                created_by = request.user if request.user.is_authenticated else None
                activity = UserActivity(
                    table_id=user.pk,
                    table_name='CustomUser',
                    ua_action='request_reset_code',
                    ua_description=f'Requested password reset code for email {email}',
                    created_by=created_by,
                    request_data=request.data,
                )
                activity.save()

                response_data = {
                    'status': 'success',
                    'message': 'Verification code sent to your email',
                }
                return Response(response_data, status=status.HTTP_200_OK)

            except CustomUser.DoesNotExist:
                response_data = {
                    'status': 'error',
                    'message': 'This email is not registered.'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                response_data = {
                    'status': 'error',
                    'message': 'Internal server error occurred.',
                    'details': str(e)  # Optional: include the error details for debugging
                }
                return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyCode(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')

        try:
            user = CustomUser.objects.get(email=email)

            if user.verify_code and check_password(code,
                                                   user.verify_code) and user.verify_code_expire_at > timezone.now():
                user.verify_code = None
                user.verify_code_expire_at = None
                user.is_verify = True
                user.save()

                # Generate a JWT token
                user_id = user.id
                user_email = user.email
                payload = {
                    'token_type': 'access',
                    'exp': datetime.utcnow() + timedelta(minutes=15),  # Token expiry
                    'iat': datetime.utcnow(),
                    # 'jti': uuid,
                    'user_id': int(user_id),
                    'email': str(user_email)
                }

                token = jwt.encode(payload, jwt_settings.SECRET_KEY, algorithm='HS256')

                # Log activity (optional)
                activity = UserActivity(
                    table_id=user.pk,
                    table_name='CustomUser',
                    ua_action='verify_code',
                    ua_description=f'Verified reset code for user with ID {user.id}',
                    created_by=user,
                    request_data=request.data,
                )
                activity.save()

                response_data = {
                    'status': 'success',
                    'message': 'Code verified successfully.',
                    'token': str(token)
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    'status': 'error',
                    'message': 'Invalid or expired verification code.'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except CustomUser.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'User with specified email does not exist.'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': 'Internal server error',
                'details': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get('Authorization', '')
        if not token:
            return None  # Return None if no token is provided

        try:
            # Decode the token
            payload = jwt.decode(token, jwt_settings.SECRET_KEY, algorithms=['HS256'])

            # if not payload:
            #     raise AuthenticationFailed('Invalid token payload.')
            # print(payload)
            user_id = payload['user_id']
            # Here, you should fetch the user object using user_id
            # For example, assuming you have a User model:
            # user = User.objects.get(id=user_id)
            user = CustomUser.objects.get(pk=user_id)  # Implement this method to fetch user

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired.')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token.')
        except CustomUser.DoesNotExist:
            raise AuthenticationFailed('No user matching this token was found.')

        return (user, None)  # Return a tuple of (user, token)

    def get_user(self, user_id):
        # Implement your logic to fetch and return the user object based on user_id
        # For example:
        from .models import CustomUser  # Replace with your actual User model
        return CustomUser.objects.get(id=user_id)

    def decode_custom_jwt_token(token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


class ResetPassword(APIView):
    """
    API view to handle the new password input and update the user's password.
    """
    permission_classes = [AllowAny]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        new_password = request.data.get('new_password')
        user_id = request.user.id

        if not user_id or not new_password:
            return Response({'status': 'fail', 'message': 'Missing user ID or new password.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(id=user_id)

            # Validate the new password
            serializer = PasswordResetSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                # Ensure the user's verify_code is None and is_verify is True
                if user.verify_code is None and user.is_verify:
                    new_password = serializer.validated_data['new_password']

                    # Update the password
                    user.set_password(new_password)  # This will hash the password
                    user.save()

                    # Log the user activity
                    activity = UserActivity(
                        table_id=user.pk,
                        table_name='CustomUser',
                        ua_action='reset_password',
                        ua_description=f'Password reset for user with ID {user.id}',
                        created_by=user,
                        request_data=request.data,
                    )
                    activity.save()

                    return Response({'status': 'success', 'message': 'Password updated successfully.'},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({'status': 'fail',
                                     'message': 'Cannot reset password due to verification status or active verification code.'},
                                    status=status.HTTP_400_BAD_REQUEST)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except CustomUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User with specified ID does not exist.'},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': 'Internal server error', 'details': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HomePageBannerApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)

            banner_records = Banner.objects.filter(is_deactive=False, is_deleted=False)
            if not banner_records.exists():
                response_data = {
                    'status': 'fail',
                    'message': 'Banners record is not found.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
            serialize_data = BannerSerializer(banner_records, many=True, context={'request': request,
                                                                                  'exclude_fields': ["created_at",
                                                                                                     "modified_at",
                                                                                                     "is_deleted",
                                                                                                     "created_by"]})

            response_data = {
                'status': 'success',
                'message': 'Banner Data',
                'data': serialize_data.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            response_data = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)


class HomePageTestimonialsApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)

            testimonial_records = Testimonial.objects.filter(is_deactive=False, is_deleted=False)
            if not testimonial_records.exists():
                response_data = {
                    'status': 'fail',
                    'message': 'Testimonials record is not found.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
            serialize_data = TestimonialSerializer(testimonial_records, many=True, context={'request': request,
                                                                                            'exclude_fields': [
                                                                                                "created_at",
                                                                                                "modified_at",
                                                                                                "is_deleted",
                                                                                                "created_by",
                                                                                                "status"]})
            response_data = {
                'status': 'success',
                'message': 'Testimonial Data',
                'data': serialize_data.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            response_data = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)


class HomePagePartnerApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)

            partner_records = Partner.objects.filter(is_deactive=False, is_deleted=False)
            if not partner_records.exists():
                response_data = {
                    'status': 'fail',
                    'message': 'Partner record is not found.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
            serialize_data = PartnerSerializer(partner_records, many=True, context={'request': request,
                                                                                    'exclude_fields': ["created_at",
                                                                                                       "modified_at",
                                                                                                       "is_deleted",
                                                                                                       "created_by"]})
            response_data = {
                'status': 'success',
                'message': 'Partner Data',
                'data': serialize_data.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            response_data = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)


class HomePageServicesApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)

            service_records = Service.objects.filter(is_deactive=False, is_deleted=False)
            if not service_records.exists():
                response_data = {
                    'status': 'fail',
                    'message': 'Services record is not found.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
            serialize_data = Service_Serializer(service_records, many=True, context={'request': request,
                                                                                     'exclude_fields': ["created_at",
                                                                                                        "modified_at",
                                                                                                        "is_deleted",
                                                                                                        "created_by"]})
            response_data = {
                'status': 'success',
                'message': 'Service Data',
                'data': serialize_data.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            response_data = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)


class HomePageAboutUsApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)

            # Retrieve the single AboutUs entry
            about_us = AboutUs.objects.first()
            if about_us:
                # Serialize the AboutUs object
                serializer = AboutUsSerializer(about_us, context={'request': request,
                                                                  'exclude_fields': ["created_at", "updated_at",
                                                                                     "is_deleted", "created_by"]})
                response_data = {
                    'status': 'success',
                    'message': 'AboutUs Data',
                    'data': serializer.data
                }
                # Return the serialized AboutUs data
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Handle case where no AboutUs entry is found
                response_data = {
                    'status': 'fail',
                    'message': "No AboutUs entry found.",
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HomePageRandomStuffApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)

            # Retrieve the single Randomstuff entry
            randomstuff = Randomstuff.objects.first()
            if randomstuff:
                # Serialize the Randomstuff object
                serializer = RandomstuffSerializer(randomstuff, context={'request': request,
                                                                         'exclude_fields': ["created_at", "updated_at",
                                                                                            "is_deleted",
                                                                                            "created_by"]})
                response_data = {
                    'status': 'success',
                    'message': 'Randomstuff Data',
                    'data': serializer.data
                }
                # Return the serialized Randomstuff data
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Handle case where no Randomstuff entry is found
                response_data = {
                    'status': 'fail',
                    'message': "No Randomstuff entry found.",
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NewsLetterApi(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)

            email = request.data.get('email', '')

            validator = EmailValidator()
            try:
                validator(email)
            except ValidationError:
                response_data = {
                    'status': 'error',
                    'message': 'Invalid email format.'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            email_exists = NewsLetter.objects.filter(email=email).exists()
            if email_exists:
                response_data = {
                    'status': 'error',
                    'message': 'This email is already exist.'
                }
                return Response(response_data, status=status.HTTP_208_ALREADY_REPORTED)

            with transaction.atomic():
                broadcast_email_add = NewsLetter.objects.create(email=email,
                                                                subscriber_name=re.findall("\w*", email)[0])
                broadcast_email_add.save()

                response_data = {
                    'status': 'success',
                    'message': 'Email added successfully.'
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AddContactEnquiryApi(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)
            with transaction.atomic():
                serializer = ContactEnquirySerializer(data=request.data)
                if serializer.is_valid():
                    enquiry = serializer.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Contact Enquiry Created Successfully'
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
                response_data = {
                    'status': 'fail',
                    'message': serializer.errors
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HomePageServiceGroup(APIView):
    permission_classes = [AllowAny]
    ALLOWED_DOMAIN = ['127.0.0.1:8000', '149.28.56.227', 'localhost:3000']

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in self.ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)

            service_records = ServiceGroup.objects.filter(is_deactive=False, is_deleted=False)
            if not service_records.exists():
                response_data = {
                    'status': 'fail',
                    'message': 'Services Group record is not found.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
            serialize_data = ServiceGroupSerializer(service_records, many=True, context={'request': request,
                                                                                         'exclude_fields': [
                                                                                             "created_at",
                                                                                             "modified_at",
                                                                                             "is_deleted",
                                                                                             "created_by"]})
            response_data = {
                'status': 'success',
                'message': 'Service Group Data',
                'data': serialize_data.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            response_data = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)


class HomePageYoutubeVideoApi(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)

            youtubevideo_records = YouTubeVideo.objects.filter(is_deactive=False, is_deleted=False)
            if not youtubevideo_records.exists():
                response_data = {
                    'status': 'fail',
                    'message': 'youtubevideo record is not found.',
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
            serialize_data = YoutubeSerializer(youtubevideo_records, many=True, context={'request': request,
                                                                                         'exclude_fields': [
                                                                                             "created_at",
                                                                                             "modified_at",
                                                                                             "is_deleted",
                                                                                             "created_by"]})
            response_data = {
                'status': 'success',
                'message': 'youtube Video Data',
                'data': serialize_data.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            response_data = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)


class SMTPConfigurationView(APIView):
    # Ensure the user is authenticated for all methods
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Retrieve the SMTP Configuration entry
            smtp_config = SMTPConfiguration.objects.first()
            if smtp_config:
                # Serialize the SMTP Configuration object
                serializer = SMTPConfigurationSerializer(smtp_config, context={'request': request})
                response_data = {
                    'status': 'success',
                    'message': 'SMTP Configuration Data',
                    'data': serializer.data
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                # Handle case where no SMTP Configuration entry is found
                response_data = {
                    'status': 'fail',
                    'message': "No SMTP Configuration entry found.",
                    'data': {}
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            user = request.user

            # Check if an SMTP Configuration entry already exists
            smtp_config_instance = SMTPConfiguration.objects.first()

            # Initialize the serializer with the existing or new SMTP Configuration instance and the new data
            if smtp_config_instance:
                serializer = SMTPConfigurationSerializer(smtp_config_instance, data=request.data, partial=True,
                                                         context={'request': request})
            else:
                serializer = SMTPConfigurationSerializer(data=request.data, context={'request': request})

            # Check if the provided data is valid
            if serializer.is_valid():
                # Start a database transaction
                with transaction.atomic():
                    # Save the updated or newly created SMTP Configuration entry
                    if smtp_config_instance:
                        saved_instance = serializer.save(updated_by=user, updated_at=datetime.now())
                    else:
                        saved_instance = serializer.save(created_by=user)
                    action = 'update' if smtp_config_instance else 'create'
                    description = f'Updated SMTP Configuration with ID {saved_instance.pk}' if smtp_config_instance else f'Created new SMTP Configuration with ID {saved_instance.pk}'

                    # Log the activity
                    # Log the activity with request and response data
                    activity = UserActivity(
                        table_id=saved_instance.pk,  # ID of the SMTP Configuration entry
                        table_name='SMTPConfiguration',  # Name of the table
                        ua_action=action,  # Action performed
                        ua_description=description,  # Action description
                        request_data=request.data,  # Request data
                        response_data=serializer.data,  # Serialized response data
                        created_by=user  # Current user performing the action
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'SMTP Configuration Updated Successfully' if smtp_config_instance else 'SMTP Configuration Created Successfully',
                        'data': serializer.data
                    }
                    return Response(response_data,
                                    status=status.HTTP_200_OK if smtp_config_instance else status.HTTP_201_CREATED)

            # If data is invalid, return the error messages
            response_data = {
                'status': 'fail',
                'message': serializer.errors
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomuserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        try:

            users = CustomUser.objects.get(id=request.user.id)

            serializer = CustomUserSerializer(users, context={'request': request})

            response_data = {
                'status': 'success',
                'message': 'CustomUser data retrieved successfully',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            response_error = {
                'status': 'error',
                'message': 'Internal server error',
                'data': str(e)
            }
            return Response(response_error, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnnouncementApiView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_data(request)
            elif 'title' in request.data and 'description' in request.data:
                return self.create_announcement(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_announcement(self, request):
        try:
            with transaction.atomic():
                request_data = request.data.copy()
                # Initialize the serializer with the data from the request
                files = request.data.getlist('attachment_doc')
                file_paths = []
                for file in files:
                    # Validate file size
                    if file.size > 10 * 1024 * 1024:
                        raise ValidationError("attachment_doc must be less than 10 MB.")
                    # Construct the relative file path
                    relative_file_path = os.path.join('attachments', file.name)
                    file_paths.append(relative_file_path)

                    # Save the file to the media directory
                    file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directories if they don't exist

                    with open(file_path, 'wb+') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)

                attachment_doc = {'file_paths': file_paths}

                request_data['attachment_doc'] = {}

                serializer = AnnouncementSerializer(data=request_data, context={'request': request})
                # Check if the provided data is valid
                if serializer.is_valid(raise_exception=True):
                    # Save the announcement with the created_by field set to the authenticated user
                    announcement = serializer.save(created_by=request.user)
                    announcement.attachment_doc = attachment_doc
                    announcement.save()

                    # Log the activity
                    activity = UserActivity(
                        table_id=announcement.pk,  # ID of the created announcement
                        table_name='Announcement',  # Name of the model
                        ua_action='create',  # Action performed
                        ua_description='Created a new announcement',  # Action description
                        created_by=request.user,  # Current user performing the action
                        request_data=request.data,  # Request data
                        response_data=serializer.data,
                    )
                    activity.save()

                    response_data = {
                        'status': 'success',
                        'message': 'Announcement Created Successfully'
                    }
                    # Return a success response with status code 201 (Created)
                    return Response(response_data, status=status.HTTP_201_CREATED)
                # If data is invalid, return the error messages
                response_data = {
                    'status': 'fail',
                    'message': f'{serializer.errors}'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            response_data = {
                'status': 'fail',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_data(self, request):
        try:
            announcement_id = request.data.get('announcement_id')
            page_size = request.data.get('page_size')
            page_number = request.data.get('page_number', 1)
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            order_by = request.data.get('order_by', "descending")
            search_query = request.data.get('search', None)
            is_deactive = request.data.get('is_deactive', None)

            # Validate page_size and page_number
            if not page_size or not page_size.isdigit() or int(page_size) <= 0:
                raise ValidationError("page_size parameter is required and must be a positive integer.")

            if not page_number or not page_number.isdigit() or int(page_number) <= 0:
                raise ValidationError("page_number parameter is required and must be a positive integer.")

            queryset = Announcement.objects.filter(is_deleted=False).order_by('-pk')

            if announcement_id:
                queryset = queryset.filter(pk=announcement_id)

            if is_deactive:
                queryset = queryset.filter(is_deactive=True) if is_deactive == 'true' else queryset.filter(
                    is_deactive=False)
            if start_date and end_date:
                start_date_parsed = parse_date(start_date)
                end_date_parsed = parse_date(end_date)
                queryset = queryset.filter(date__range=[start_date_parsed, end_date_parsed + timedelta(days=1)])

            if search_query:
                queryset = queryset.filter(
                    Q(title__icontains=search_query) |
                    Q(description__icontains=search_query)
                )

            if order_by == "ascending":
                queryset = queryset.order_by('pk')
            else:
                queryset = queryset.order_by('-pk')

            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            if page_obj is not None:
                if not queryset.exists():
                    paginated_response_data = {
                        'total_pages': 0,
                        'current_page': 0,
                        'total_items': 0,
                        'results': []
                    }
                    response_data = {
                        'status': 'fail',
                        'message': 'Announcement Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                serializer = AnnouncementSerializer(page_obj.object_list, many=True, context={'request': request,
                                                                                              'exclude_fields': [
                                                                                                  "created_at",
                                                                                                  "updated_at",
                                                                                                  "is_deleted",
                                                                                                  "updated_by",
                                                                                                  "created_by"]})
                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }
                return Response({
                    'status': 'success',
                    'message': 'Announcement Data',
                    'data': paginated_response_data
                }, status=status.HTTP_200_OK)

            serializer = AnnouncementSerializer(queryset, many=True, context={'request': request})
            response_data = {
                'status': 'success',
                'message': 'Announcement Data',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except (DjangoValidationError, ValueError, Exception) as e:
            return Response({
                'status': 'fail',
                'message': str(e),
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        announcement_id = request.data.get("announcement_id")

        # Check if announcement_id is provided
        if not announcement_id:
            response_data = {
                'status': 'fail',
                'message': "announcement_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                try:
                    # Retrieve the announcement object by ID
                    announcement = Announcement.objects.get(announcement_id=announcement_id, is_deleted=False)

                    # Check if is_deactive flag is provided and handle accordingly
                    if 'is_deactive' in request.data:
                        is_deactive = request.data['is_deactive']
                        if is_deactive == 'true':
                            announcement.is_deactive = True
                            announcement.updated_at = datetime.now()
                            announcement.updated_by = request.user
                            announcement.save()
                        elif is_deactive == 'false':
                            announcement.is_deactive = False
                            announcement.updated_at = datetime.now()
                            announcement.updated_by = request.user
                            announcement.save()

                        if is_deactive:
                            message = 'Announcement Deactivated Successfully'
                        else:
                            message = 'Announcement Activated Successfully'
                    else:
                        request_data = request.data
                        attachment_doc = None
                        if 'attachment_doc' in request.data:
                            # Initialize the serializer with the data from the request
                            files = request.data.getlist('attachment_doc')
                            file_paths = []
                            for file in files:
                                # Validate file size
                                if file.size > 10 * 1024 * 1024:
                                    raise ValidationError("attachment_doc must be less than 10 MB.")
                                # Construct the relative file path
                                relative_file_path = os.path.join('attachments', file.name)
                                file_paths.append(relative_file_path)

                                # Save the file to the media directory
                                file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                                os.makedirs(os.path.dirname(file_path),
                                            exist_ok=True)  # Create directories if they don't exist

                                with open(file_path, 'wb+') as destination:
                                    for chunk in file.chunks():
                                        destination.write(chunk)

                            attachment_doc = {'file_paths': file_paths}

                            request_data['attachment_doc'] = {}

                        # Initialize the serializer with the existing announcement object and the new data
                        serializer = AnnouncementSerializer(announcement, data=request_data, partial=True,
                                                            context={'request': request})

                        # Check if the provided data is valid
                        if serializer.is_valid():
                            # Save the updated announcement with partial data
                            serializer.save(updated_at=datetime.now(), updated_by=request.user)
                            if attachment_doc:
                                announcement.attachment_doc = attachment_doc
                                announcement.save()
                            message = 'Announcement Updated Successfully'
                        else:
                            # If data is invalid, return the error messages
                            response_data = {
                                'status': 'fail',
                                'message': f'{serializer.errors}'
                            }
                            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                    # Log the activity
                    activity = UserActivity(
                        table_id=announcement.pk,  # ID of the created announcement
                        table_name='Announcement',  # Name of the model
                        ua_action='Update',  # Action performed
                        ua_description=f'Updated announcement with ID {announcement.pk}',  # Action description
                        created_by=request.user,  # Current user performing the action
                        request_data=request.data,  # Request data
                        response_data=serializer.data,
                    )
                    activity.save()

                    # Return a success response with the appropriate message
                    response_data = {
                        'status': 'success',
                        'message': message
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                # Handle case where announcement is not found
                except Announcement.DoesNotExist:
                    response_data = {
                        'status': 'fail',
                        'message': "Announcement not found."
                    }
                    return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        # Handle any exceptions and return an error response
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        announcement_id = request.data.get("announcement_id")

        # Check if announcement_id is provided
        if not announcement_id:
            response_data = {
                'status': 'fail',
                'message': "announcement_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Retrieve the announcement object by ID
                announcement = Announcement.objects.get(announcement_id=announcement_id, is_deleted=False)
                # Mark the announcement object as deleted
                announcement.is_deleted = True
                announcement.save()
                # Log the activity
                activity = UserActivity(
                    table_id=announcement.pk,  # ID of the announcement
                    table_name='Announcement',  # Name of the model
                    ua_action='Delete',  # Action performed
                    ua_description=f'Deleted announcement with ID {announcement.pk}',  # Action description
                    created_by=request.user,  # Current user performing the action
                    request_data=request.data,  # Request data

                )
                activity.save()

                response_data = {
                    'status': 'success',
                    'message': 'Announcement Deleted Successfully'
                }
                # Return a success response
                return Response(response_data, status=status.HTTP_200_OK)
        except Announcement.DoesNotExist:
            # Handle case where announcement is not found
            response_data = {
                'status': 'fail',
                'message': "Announcement not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubscribeEmailApiView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            broadcast_email_id = request.data.get('broadcast_email_id')

            page_size = request.data.get('page_size')
            page_number = request.data.get('page_number', 1)
            order_by = request.data.get('order_by', "descending")
            search_query = request.data.get('search', None)

            # Validate page_size and page_number
            if not page_size or not page_size.isdigit() or int(page_size) <= 0:
                raise ValidationError("page_size parameter is required and must be a positive integer.")

            if not page_number or not page_number.isdigit() or int(page_number) <= 0:
                raise ValidationError("page_number parameter is required and must be a positive integer.")

            queryset = NewsLetter.objects.filter(is_deleted=False).order_by('-pk')

            if broadcast_email_id:
                queryset = queryset.filter(pk=broadcast_email_id)
            # Apply search filter if search_query is provided
            if search_query:
                queryset = queryset.filter(
                    Q(subscriber_name__icontains=search_query) |
                    Q(email__icontains=search_query)
                )

            # Apply ordering based on order_by parameter
            if order_by == "ascending":
                queryset = queryset.order_by('pk')
            else:
                queryset = queryset.order_by('-pk')

            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            # Handle response for paginated queryset
            if page_obj is not None:
                if not queryset.exists():
                    paginated_response_data = {
                        'total_pages': 0,
                        'current_page': 0,
                        'total_items': 0,
                        'results': []
                    }
                    response_data = {
                        'status': 'fail',
                        'message': 'News Letter Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                serializer = NewsLetterSerializer(page_obj.object_list, many=True, context={'request': request,
                                                                                            'exclude_fields': [
                                                                                                "created_at",
                                                                                                "updated_at",
                                                                                                "is_deleted",
                                                                                                "updated_by",
                                                                                                "created_by"]})
                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }
                return Response({
                    'status': 'success',
                    'message': 'News Letter data retrieved successfully.',
                    'data': paginated_response_data
                }, status=status.HTTP_200_OK)

            # Handle response for non-paginated queryset
            serializer = NewsLetterSerializer(queryset, many=True, context={'request': request})
            response_data = {
                'status': 'success',
                'message': 'News Letter data retrieved successfully.',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except (DjangoValidationError, ValueError, Exception) as e:
            return Response({
                'status': 'fail',
                'message': str(e),
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        try:
            broadcast_email_id = request.data.get('broadcast_email_id')
            updated_email = request.data.get('email', None)
            is_deactive = request.data.get('is_deactive', None)

            # Retrieve the News Letter instance
            broadcast_email = NewsLetter.objects.get(pk=broadcast_email_id)
            if not broadcast_email:
                return Response({
                    'status': 'error',
                    'message': 'News Letter not found.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            existing_email = NewsLetter.objects.filter(is_deactive=False, is_deleted=False).count()
            if existing_email <= 1:
                if broadcast_email.is_deactive:
                    pass
                else:
                    return Response({'status': 'fail', 'message': 'You cannot update this news latter. You need to have at least one active news latter.'}, status=status.HTTP_400_BAD_REQUEST)

            # Update the email and is_deactive fields using serializer
            serializer = NewsLetterSerializer(broadcast_email, data=request.data, partial=True,
                                              context={'request': request})
            if serializer.is_valid():
                if updated_email:
                    serializer.save(updated_by=request.user, subscriber_name=re.findall("\w*", updated_email)[0])
                else:
                    serializer.save(updated_by=request.user)

                if (is_deactive and updated_email) or updated_email:
                    message = 'News Letter updated successfully.'
                else:
                    if broadcast_email.is_deactive == True:
                        message = 'News Letter Deactivet successfully.'
                    elif broadcast_email.is_deactive == False:
                        message = 'News Letter Activet successfully.'
                # Log the update activity
                activity = UserActivity(
                    table_id=serializer.instance.pk,
                    table_name='broadcast_email',
                    ua_action='update',
                    ua_description=message,
                    created_by=request.user,
                    request_data=request.data,  # Request data
                    response_data=serializer.data,  # Serialized response data
                )
                activity.save()
                response_data = {
                    'status': 'success',
                    'message': message
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except NewsLetter.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'News Letter not found.'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        broadcast_email_id = request.data.get("broadcast_email_id")

        # Check if broadcast_email_id is provided
        if not broadcast_email_id:
            response_data = {
                'status': 'fail',
                'message': "broadcast_email_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Retrieve the News Letter object by ID
                broadcast_email = NewsLetter.objects.get(broadcast_email_id=broadcast_email_id, is_deleted=False)
                # Mark the News Letter object as deleted
                broadcast_email.is_deleted = True
                broadcast_email.save()
                # Log the activity
                activity = UserActivity(
                    table_id=broadcast_email.pk,  # ID of the News Letter
                    table_name='NewsLetter',  # Name of the model
                    ua_action='Delete',  # Action performed
                    ua_description=f'Deleted News Letter with ID {broadcast_email.pk}',  # Action description
                    created_by=request.user  # Current user performing the action
                )
                activity.save()

                response_data = {
                    'status': 'success',
                    'message': 'News Letter Deleted Successfully'
                }
                # Return a success response
                return Response(response_data, status=status.HTTP_200_OK)
        except NewsLetter.DoesNotExist:
            # Handle case where News Letter is not found
            response_data = {
                'status': 'fail',
                'message': "News Letter not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Homepage_ServiceById(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error',
                     'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN)
            service_id = request.query_params.get('service_id')

            # Retrieve the service object
            service = Service.objects.filter(service_id=service_id, is_deleted=False, is_deactive=False).first()

            if service is None:
                response_data = {
                    'status': 'fail',
                    'message': 'Service not found'
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)

            serializer = ServiceSerializer(service, context={'request': request})

            response_data = {
                'status': 'success',
                'message': 'Service data retrieved successfully',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            response_error = {
                'status': 'error',
                'message': 'Internal server error',
                'data': str(e)
            }
            return Response(response_error, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Homepage_ServiceGroup_Service(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            domain = request.META.get('HTTP_HOST')
            if domain not in ALLOWED_DOMAIN:
                return Response(
                    {'status': 'error', 'message': 'Invalid domain'},
                    status=status.HTTP_403_FORBIDDEN
                )

            service_groups = ServiceGroup.objects.filter(is_deleted=False, is_deactive=False)
            service_groups_serialized = ServiceGroupDetailSerializer(
                service_groups,
                many=True,
                context={'request': request,
                         'exclude_fields': ["created_at", "modified_at", "is_deleted", "created_by"]}
            ).data

            non_connected_services = Service.objects.filter(service_group__isnull=True, is_deleted=False,
                                                            is_deactive=False)
            non_connected_services_serialized = ServiceDetailSerializer(
                non_connected_services,
                many=True,
                context={'request': request,
                         'exclude_fields': ["created_at", "modified_at", "is_deleted", "created_by"]}
            ).data

            response_data = {
                'status': 'success',
                'message': 'Service data retrieved successfully',
                'service_groups': service_groups_serialized,
                'non_connected_services': non_connected_services_serialized
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            response_data = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
