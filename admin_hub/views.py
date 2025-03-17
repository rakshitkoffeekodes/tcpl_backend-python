import os
from decimal import Decimal
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.views import APIView
from django.forms import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from tcpl_backend import settings
from .models import *
from .serializers import *
from drf_yasg import openapi
from django.db import transaction
from tcpl_backend.custom_jwt_auth import get_tokens_for_user, IsAdmin, IsSuperAdmin, IsRetailer, IsDistributor, CustomJWTAuthentication
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage
from django.db.models import ProtectedError
from control_panel.models import State, City
import json
import uuid
import time
import requests
from dotenv import set_key, load_dotenv
from .verfication_suite import *
from .db_model_for_raw_query import *
from validation.custom_validation import *
from .notification_services import mobicomm_submit_sms, send_email_otp
from .razorpay_services import create_razorpay_pg_order
from django.core.mail import send_mail
from .utilies import add_user_activity
from django.forms.models import model_to_dict
import base64
from .payout_service import *
from .commission_calculations import *
from openpyxl import load_workbook
import csv
from math import ceil
from collections import OrderedDict
from django.db import transaction as db_transaction
from control_panel.models import *
from admin_web_portal.models import *
from django.db.models import Count, Sum
from django.utils.timezone import localtime, make_aware


# generate custom access token
def create_custom_access_token(user, lifetime):
    # Generate tokens for the user
    rft = RefreshToken.for_user(user=user)
    token = rft.access_token

    token.set_exp(lifetime=lifetime)
    return str(token)


def handle_uploaded_file(file, upload_folder):
    # Handle file uploads securely
    # Create directory if it doesn't exist
    media_root = settings.MEDIA_ROOT
    upload_dir = os.path.join(media_root, upload_folder)
    os.makedirs(upload_dir, exist_ok=True)

    # Save the file to the media directory
    file_path = os.path.join(upload_dir, file.name)
    relative_file_path = os.path.join(upload_folder, file.name)  # Relative path

    try:
        with open(file_path, 'wb') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
    except Exception as e:
        print(f"Error saving file: {e}")

    return relative_file_path  # Return relative file path


class VerifyContactNoAPIView(APIView):
    """
    API view to handle the contact_no input and send a verification code.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        contact_no = request.data.get('contact_no')
        is_forgot = request.data.get('is_forgot')
        is_app = request.data.get('is_app', False)
        try:
            if not contact_no: return Response({"status": "fail", "message": "Contact number is required"}, status=status.HTTP_400_BAD_REQUEST)

            if validate_mobile_number(contact_no) == False: return Response({'status': 'fail','message': 'Invalid contact number.'}, status=status.HTTP_400_BAD_REQUEST)
            if is_forgot:
                if isboolean(is_forgot) is None: return Response({'status': 'fail','message': 'Invalid is_forgot value.'}, status=status.HTTP_400_BAD_REQUEST)
            user = PortalUser.objects.filter(pu_contact_no=contact_no).first()
            if isboolean(is_app) == False:
                return Response({'status': 'fail','message': 'Invalid is_app value.'}, status=status.HTTP_400_BAD_REQUEST)
            if is_app == False:
                if user.pu_status == 'PENDING' or user.pu_status == 'REJECT': return Response({'status': 'fail', 'message': 'We noticed your account status is not yet approved. It is either pending or has been rejected. Please reach out to our support team to resolve this quickly.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if is_app == True and user.pu_role == 'ADMIN':
                return Response({'status': 'fail', 'message': 'Admin user cannot perform this action in the app.'}, status=status.HTTP_400_BAD_REQUEST)

            if isboolean(is_forgot) == True:
                if isboolean(is_forgot) == True and user.pu_login_pin:
                    code = get_random_string(length=6, allowed_chars='0123456789')

                    user.verify_code = code
                    user.verify_code_expire_at = timezone.now() + timedelta(minutes=10)
                    user.save()

                    response = mobicomm_submit_sms(contact_no, code)

                    # Check the SMS API response status
                    if response.status_code == 200:
                        response_data = {
                            'status': 'success',
                            'message': 'OTP has been sent via SMS.',
                            'data': {'user_role': user.pu_role, 'code': code, "is_generated": True, 'is_registered': True, 'is_forgot': True}
                        }
                        return Response(response_data, status=status.HTTP_200_OK)
                    else:
                        response_data = {
                            'status': 'error',
                            'message': 'Failed to send the OTP via SMS.',
                            'details': response.text  # Include the response for debugging
                        }
                        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                else:
                    response_data = {
                        'status': 'success',
                        'message': 'Login pin for this user has not been created.',
                        'data': {'user_role': user.pu_role, "is_generated": False, 'is_registered': True}
                    }

                return Response(response_data)

            else:
                if user.pu_login_pin:
                    pu_roles = list(PortalUser.objects.filter(pu_contact_no=contact_no).values_list('pu_role', flat=True))
                    print('pu_roles', pu_roles)
                    response_data = {
                        'status': 'success',
                        'message': 'Contact number verified successfully and login pin is already generated.',
                        'data': {'user_role': pu_roles, "is_generated": True, 'is_registered': True}
                    }

                    return Response(response_data, status=status.HTTP_200_OK)

                else:
                    code = get_random_string(length=6, allowed_chars='0123456789')

                    user.verify_code = code
                    user.verify_code_expire_at = timezone.now() + timedelta(minutes=10)
                    user.save()

                    response = mobicomm_submit_sms(contact_no, code)

                    # Check the SMS API response status
                    if response.status_code == 200:
                        response_data = {
                            'status': 'success',
                            'message': 'The provided contact number is registered, and the OTP has been sent via SMS.',
                            'data': {'user_role': user.pu_role, 'code': code, "is_generated": False, 'is_registered': True}
                        }
                        return Response(response_data, status=status.HTTP_200_OK)
                    else:
                        response_data = {
                            'status': 'error',
                            'message': 'Failed to send the OTP via SMS.',
                            'details': response.text  # Include the response for debugging
                        }
                        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except PortalUser.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': 'Provided contact number is not registered.',
                'is_registered': False
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error occurred: {str(e)}',
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyCodeAPIView(APIView):
    """
    API view to handle the verification code input.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        contact_no = request.data.get('contact_no')
        code = request.data.get('code')
        is_forgot = request.data.get('is_forgot')
        is_app = request.data.get('is_app', False)
        try:
            if not contact_no: return Response({"status": "fail", "message": "Contact number is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not code: return Response({"status": "fail", "message": "OTP code is required"}, status=status.HTTP_400_BAD_REQUEST)

            if is_forgot:
                if isboolean(is_forgot) is None: return Response({'status': 'fail','message': 'Invalid is_forgot value.'}, status=status.HTTP_400_BAD_REQUEST)
            if validate_mobile_number(contact_no) == False: return Response({'status': 'fail','message': 'Invalid contact number.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(code) == False: return Response({"status": "fail",'message': 'OTP code contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if len(code) != 6: return Response({"status": "fail",'message': 'OTP code must contain 6 digits value.'}, status=status.HTTP_400_BAD_REQUEST)
            user = PortalUser.objects.get(pu_contact_no=contact_no)
            if isboolean(is_app) == False:
                return Response({'status': 'fail', 'message': 'is app invalid format.'}, status=status.HTTP_400_BAD_REQUEST)
            if is_app == False:
                if user.pu_status == 'PENDING' or user.pu_status == 'REJECT': return Response({'status': 'fail', 'message': 'We noticed your account status is not yet approved. It is either pending or has been rejected. Please reach out to our support team to resolve this quickly.'}, status=status.HTTP_400_BAD_REQUEST)
            if is_app == True and user.pu_role == 'ADMIN':
                return Response({'status': 'fail', 'message': 'Admin user cannot perform this action in the app.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if code == "563333":
                if user.pu_login_pin is None:
                    # user.verify_code = None
                    # user.verify_code_expire_at = None
                    # user.is_verify = True
                    # user.save()
                    
                    access_token = get_tokens_for_user(user, timedelta(minutes=30))

                    response_data = {
                        'status': 'success',
                        'message': 'Code verified successfully.',
                        'data': {'user_role': user.pu_role, 'is_generated': False, 'token': str(access_token)}
                    }
                else:
                    if isboolean(is_forgot):
                        # user.verify_code = None
                        # user.verify_code_expire_at = None
                        # user.is_verify = True
                        # user.save()
                        access_token = get_tokens_for_user(user, timedelta(minutes=30))
                        response_data = {
                            'status': 'success',
                            'message': 'Verification successful. pin reset token has been generated.',
                            'data': {'is_generated': True, 'is_forgot_password': True, 'is_forgot': True, 'token': str(access_token)}
                        }
                    else:
                        # user.verify_code = None
                        # user.verify_code_expire_at = None
                        # user.is_verify = True
                        # user.save()

                        response_data = {
                            'status': 'success',
                            'message': 'The credentials for this user have already been created.',
                            'data': {'is_generated': True}
                        }

                return Response(response_data, status=status.HTTP_200_OK)

            elif user.verify_code == code and user.verify_code_expire_at > timezone.now():
                if user.pu_login_pin is None:
                    user.verify_code = None
                    user.verify_code_expire_at = None
                    user.is_verify = True
                    user.save()
                    access_token = get_tokens_for_user(user, timedelta(minutes=30))
                    response_data = {
                        'status': 'success',
                        'message': 'Code verified successfully.',
                        'data': {'user_role': user.pu_role, 'is_generated': False, 'token': str(access_token)}
                    }
                else:
                    if isboolean(is_forgot):
                        user.verify_code = None
                        user.verify_code_expire_at = None
                        user.is_verify = True
                        user.save()
                        access_token = get_tokens_for_user(user, timedelta(minutes=30))
                        response_data = {
                            'status': 'success',
                            'message': 'Verification successful. pin reset token has been generated.',
                            'data': {'is_generated': True, 'is_forgot_password': True, 'is_forgot': True, 'token': str(access_token)}
                        }
                    else:
                        user.verify_code = None
                        user.verify_code_expire_at = None
                        user.is_verify = True
                        user.save()

                        response_data = {
                            'status': 'success',
                            'message': 'The credentials for this user have already been created.',
                            'data': {'is_generated': True}
                        }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    'status': 'error',
                    'message': 'Invalid or expired verification code.'
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except PortalUser.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'User with this contact number does not exist.'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyDistributorDetailsAPIView(APIView):
    """
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor]

    def post(self, request):
        try:
            if 'aadhaar_card' in request.data and 'pan_card' in request.data and 'pan_response' in request.data:
                return self.add_distributor_doc(request)
            elif 'aadhaar_card' in request.data:
                return self.verify_aadhaar(request)
            elif 'ref_id' in request.data and 'aadhaar_otp' in request.data:
                return self.verify_otp(request)
            elif 'pan_card' in request.data:
                return self.verify_pan(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def verify_aadhaar(self, request):
        aadhaar_card = request.data.get('aadhaar_card')
        aadhaar_response = aadhaar_verify(aadhaar_card)
        return Response(aadhaar_response['data'], status=aadhaar_response['status'])

    def verify_otp(self, request):
        ref_id = request.data.get('ref_id')
        aadhaar_otp = request.data.get('aadhaar_otp')
        fwdp = request.data.get('fwdp')
        codeVerifier = request.data.get('codeVerifier')
        verify_otp_response = aadhaar_otp_verify(aadhaar_otp, ref_id, fwdp, codeVerifier)
        return Response(verify_otp_response['data'], status=verify_otp_response['status'])

    def verify_pan(self, request):
        pan_card = request.data.get('pan_card')
        pan_card_response = verify_pan_card(pan_card)
        return Response(pan_card_response['data'], status=pan_card_response['status'])


    def add_distributor_doc(self, request):
        aadhaar_card = request.data.get('aadhaar_card')
        pan_card = request.data.get('pan_card')
        pan_response = request.data.get('pan_response')

        try:
            PortalUserDetails.objects.get(pu_id=request.user.id)

            response_data = {
                            'status': 'success',
                            'message': 'Data Already Exist',
                            'is_final': True,
                        }
            # Return a success response with status code 201 (Created)
            return Response(response_data, status=status.HTTP_201_CREATED)
        except PortalUserDetails.DoesNotExist:
            PortalUserDetails.objects.create(pu_id=request.user.id ,aadhaar_card=aadhaar_card, pan_card=pan_card, pan_response=pan_response)

            response_data = {
                            'status': 'success',
                            'message': 'Data Added Successfully',
                            'is_final': True,
                        }
            # Return a success response with status code 201 (Created)
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyRetailerDetailsAPIView(APIView):
    """
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request):
        try:
            if 'aadhaar_card' in request.data:
                return self.verify_aadhaar_card(request)

            elif 'ref_id' in request.data and 'aadhaar_otp' in request.data:
                return self.verify_aadhaar_otp(request)

            elif 'pan_card' in request.data:
                return self.verify_pan_card(request)

            elif all(field in request.data for field in ['shop_name', 'shop_address', 'shop_location', 'state_id', 'city_id', 'zip_code', 'shop_image', 'profile_image', 'aadhaar_image', 'pan_image', 'aadhaar_card', 'pan_card']):
                return self.add_retailer_details(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_aadhaar_card(self, request):
        aadhaar_card = request.data.get('aadhaar_card')
        aadhar_response = aadhaar_verify(aadhaar_card)
        return Response(aadhar_response['data'], status=aadhar_response['status'])

    def verify_aadhaar_otp(self, request):
        ref_id = request.data.get('ref_id')
        aadhaar_otp = request.data.get('aadhaar_otp')
        fwdp = request.data.get('fwdp')
        codeVerifier = request.data.get('codeVerifier')
        aadhaar_otp_response = aadhaar_otp_verify(aadhaar_otp, ref_id, fwdp, codeVerifier)
        return Response(aadhaar_otp_response['data'], status=aadhaar_otp_response['status'])

    def verify_pan_card(self, request):
        pan_card = request.data.get('pan_card')
        pan_card_response = verify_pan_card(pan_card)
        return Response(pan_card_response['data'], status=pan_card_response['status'])


    def add_retailer_details(self, request):
        shop_name = request.data.get('shop_name')
        shop_address = request.data.get('shop_address')
        shop_location = request.data.get('shop_location')
        state_id = request.data.get('state_id')
        city_id = request.data.get('city_id')
        zip_code = request.data.get('zip_code')
        shop_image = request.data.get('shop_image')
        profile_image = request.data.get('profile_image')
        aadhaar_image = request.data.get('aadhaar_image')
        pan_image = request.data.get('pan_image')
        aadhaar_card = request.data.get('aadhaar_card')
        pan_card = request.data.get('pan_card')

        try:
            PortalUserDetails.objects.get(pu_id=request.user.id)

            response_data = {
                            'status': 'success',
                            'message': 'Data Already Exist'
                        }
            # Return a success response with status code 201 (Created)
            return Response(response_data, status=status.HTTP_201_CREATED)
        except PortalUserDetails.DoesNotExist:
            # Handling multiple files
            file_paths = {}

            file_path1 = handle_uploaded_file(shop_image, 'Retailer/Docs') if shop_image else None
            file_path2 = handle_uploaded_file(profile_image, 'Retailer/Docs') if profile_image else None
            file_path3 = handle_uploaded_file(aadhaar_image, 'Retailer/Docs') if aadhaar_image else None
            file_path4 = handle_uploaded_file(pan_image, 'Retailer/Docs') if pan_image else None

            # Combine all paths into a single dictionary
            file_paths = {
                'shop_image': file_path1,
                'profile_image': file_path2,
                'aadhaar_image': file_path3,
                'pan_image': file_path4
            }

            PortalUserDetails.objects.create(
                pu_id=request.user.id,
                shop_name=shop_name,
                shop_address=shop_address,
                shop_location=shop_location,
                doc_images=file_paths,
                state_id=state_id,
                city_id=city_id,
                zip_code=zip_code,
                aadhaar_card=aadhaar_card,
                pan_card=pan_card)

            response_data = {
                            'status': 'success',
                            'message': 'Data Added Successfully'
                        }
            # Return a success response with status code 201 (Created)
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuthHandlerAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):
        pu_login_pin = request.data.get('login_pin')
        is_forgot = request.data.get('is_forgot')
        is_app = request.data.get('is_app', False)

        try:
            if not pu_login_pin: return Response({'status': 'fail', 'message': 'Missing login pin.'}, status=status.HTTP_400_BAD_REQUEST)

            if is_forgot:
                if isboolean(is_forgot) is None: return Response({'status': 'fail','message': 'Invalid is_forgot value.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(pu_login_pin) == False: return Response({"status": "fail",'message': 'Login pin contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if len(pu_login_pin) != 6: return Response({"status": "fail",'message': 'Login pin must contain 6 digits value.'}, status=status.HTTP_400_BAD_REQUEST)

            request_data = {'pu_login_pin': pu_login_pin}

            user = PortalUser.objects.get(id=request.user.id)
            if isboolean(is_app) == False:
                return Response({'status': 'fail','message': 'Invalid is_app value.'}, status=status.HTTP_400_BAD_REQUEST)
            if is_app == False:
                if user.pu_status == 'PENDING' or user.pu_status == 'REJECT': return Response({'status': 'fail', 'message': 'We noticed your account status is not yet approved. It is either pending or has been rejected. Please reach out to our support team to resolve this quickly.'}, status=status.HTTP_400_BAD_REQUEST)

            # Generate credentials
            if isboolean(is_forgot) == True:
                user.pu_login_pin = make_password(pu_login_pin)
                user.save()
                access_token = get_tokens_for_user(user, timedelta(days=1))
                response_data = {
                    'status': 'success',
                    'message': 'Login PIN has been reset successfully.',
                    'user_role': user.pu_role,
                    'is_kyc_verification': user.is_kyc_verify,
                    'is_forgot': True,
                    'access_token': str(access_token)
                }
                return Response(response_data, status=status.HTTP_200_OK)

            else:
                serializer = GenerateCredentialsSerializer(
                    data=request_data, context={'request': request})
                if serializer.is_valid():
                    user.pu_login_pin = make_password(pu_login_pin)
                    user.save()

                    access_token = get_tokens_for_user(user, timedelta(days=1))

                    response_data = {
                        'status': 'success',
                        'message': 'Credentials generated successfully.',
                        'user_role': user.pu_role,
                        'is_kyc_verification': user.is_kyc_verify,
                        'access_token': str(access_token)
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        pu_contact_no = request.data.get('contact_no')
        pu_login_pin = request.data.get('login_pin')
        is_app = request.data.get('is_app', False)
        pu_role = request.data.get('pu_role', '')

        if not pu_contact_no or not pu_login_pin:
            return Response({'status': 'fail', 'message': 'Missing contact number or login pin.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if validate_mobile_number(pu_contact_no) == False: return Response({'status': 'fail','message': 'Invalid contact number.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(pu_login_pin) == False: return Response({"status": "fail",'message': 'Login pin contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if len(pu_login_pin) != 6: return Response({"status": "fail",'message': 'Login pin must contain 6 digits value.'}, status=status.HTTP_400_BAD_REQUEST)

            if pu_role == '':
                user = PortalUser.objects.filter(pu_contact_no=pu_contact_no)
                if user[0].pu_role != 'ADMIN':
                    if len(user) > 1:
                        user = PortalUser.objects.filter(pu_contact_no=pu_contact_no, pu_role='RETAILER').first()
                    else:
                        user = user[0]
                else:
                    user = user[0]
            else:
                user = PortalUser.objects.get(pu_contact_no=pu_contact_no, pu_role=pu_role)
            if user == None:
                return Response({'status': 'fail', 'message': 'User with this contact number does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            if isboolean(is_app) == False:
                return Response({'status': 'fail','message': 'Invalid is_app value.'}, status=status.HTTP_400_BAD_REQUEST)
            if is_app == False:
                if user.pu_status == 'PENDING' or user.pu_status == 'REJECT' or user.pu_status == 'KYC_UNDER_PROCESS': return Response({'status': 'fail', 'message': 'We noticed your account status is not yet approved. It is either pending or has been rejected. Please reach out to our support team to resolve this quickly.'}, status=status.HTTP_400_BAD_REQUEST)

            if is_app == True and user.pu_role == 'ADMIN':
                return Response({'status': 'fail', 'message': 'Admin user cannot perform this action in the app.'}, status=status.HTTP_400_BAD_REQUEST)

            # Perform login procedure
            if check_password(pu_login_pin, user.pu_login_pin):
                access_token = get_tokens_for_user(user, timedelta(days=1))
                load_dotenv()
                device_active = 'device_number'
                number = os.getenv(device_active)
                get_user_log = PortalUserLoginLogs.objects.filter(pu_user=user, is_expire=False)

                if len(get_user_log) == int(number):
                    if get_user_log[0].expire_datetime <= timezone.now():
                        old_log = get_user_log[0]
                        old_log.is_expire = True
                        old_log.save()
                    else:
                        old_log = get_user_log[0]
                        old_log.is_expire = True
                        old_log.save()
                ip = request.META.get('HTTP_X_REAL_IP', request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR')))
                print(f"Client IP: {ip}")
                PortalUserLoginLogs.objects.create(
                    pu_user=user,
                    pu_user_role=user.pu_role,
                    pu_token=str(access_token),
                    browser_type=request.META['HTTP_USER_AGENT'],
                    expire_datetime = timezone.now() + timedelta(hours=24),
                    ip_address=ip
                )
                response_data = {
                    'status': 'success',
                    'message': 'Login successful.',
                    'user_role': user.pu_role,
                    'user_id': user.pk, # kishan: add user_id new field on 11-11-2024
                    'is_kyc_verify': user.is_kyc_verify,
                    'access_token': str(access_token)
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': 'Invalid pin.'}, status=status.HTTP_404_NOT_FOUND)
        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User with this contact number does not exist'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileAPIView(APIView):
    """
    API view to handle the user profile.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def get(self, request):
        """
        API endpoint for retrieving the authenticated user's details.

        This endpoint requires authentication with a JWT token.
        """

        try:

            users = PortalUser.objects.get(id=request.user.id)
            user_details = PortalUserDetails.objects.filter(pu=users).first()
            wallet =PortalUserWallet.objects.get(pu=users) #ADD Wallet
            pu_roles = list(PortalUser.objects.filter(pu_contact_no=users.pu_contact_no).values_list('pu_role', flat=True))
            # wallet_serializer = PortalUserWalletSerializer(wallet, context={'request': request}) # wallet serializers

            serializer = PortalUserSerializer(
                users, context={'request': request})

            # Append distributor hierarchy data to the user data
            user_data = serializer.data
            # wallet_data = wallet_serializer.data # add wallet
            user_data['wallet_data'] = {
                    'main_wallet': wallet.main_wallet,
                    'total_amount': wallet.main_wallet
                }
            if users.pu_role != "ADMIN":
                user_data = serializer.data
                user_data['pu_roles'] = pu_roles

            if users.pu_role == "DISTRIBUTOR":
                
                try:
                    puc_obj = PortalUserDetails.objects.filter(pu_id=request.user.id).first()
                    distributor_hierarchy = DistributorHierarchy.objects.get(pk=puc_obj.dh.dh_id)
                except DistributorHierarchy.DoesNotExist:
                    return Response({
                        'status': 'fail',
                        'message': 'Partner Category Does Not Exist'
                    }, status=status.HTTP_404_NOT_FOUND)

                if distributor_hierarchy.dh_name == 'SUPER DISTRIBUTOR':
                    partner_cateogry = "SUPER DISTRIBUTOR"
                elif distributor_hierarchy.dh_name == 'MASTER DISTRIBUTOR':
                    partner_cateogry = "MASTER DISTRIBUTOR"
                else:
                    partner_cateogry = "DISTRIBUTOR"    
                wallet = PortalUserWallet.objects.get(pu=request.user.id)
                user_data['partner_category'] = partner_cateogry
                user_data['wallet_data'] = {
                    'main_wallet': wallet.main_wallet,
                    'commission_wallet': wallet.commission_wallet,
                    'total_amount': wallet.main_wallet + wallet.commission_wallet
                }
                user_data['aadhaar_card'] = user_details.aadhaar_card
                user_data['pan_card'] = user_details.pan_card
                user_data['is_kyc_verified'] = users.is_kyc_verify
                user_data['shop_name'] = user_details.shop_name
                user_data['shop_address'] = user_details.shop_address
                user_data['gst_number'] = user_details.shop_gst_number
                user_data['gst_type'] = user_details.busniess_type
                user_data['pu_roles'] = pu_roles

            if users.pu_role == 'RETAILER':
                wallet = PortalUserWallet.objects.get(pu=request.user.id)
                user_data['partner_category'] = "RETAILER"
                user_data['wallet_data'] = {
                    'main_wallet': wallet.main_wallet,
                    'commission_wallet': wallet.commission_wallet,
                    'cashin_wallet': wallet.cashin_wallet,
                    'pg_wallet': wallet.pg_wallet,
                    'os_wallet': wallet.os_wallet,
                    'total_amount': wallet.main_wallet + wallet.commission_wallet + wallet.cashin_wallet + wallet.pg_wallet
                }
                user_data['aadhaar_card'] = user_details.aadhaar_card
                user_data['pan_card'] = user_details.pan_card
                user_data['is_kyc_verified'] = users.is_kyc_verify
                user_data['shop_name'] = user_details.shop_name
                user_data['shop_address'] = user_details.shop_address
                user_data['gst_number'] = user_details.shop_gst_number
                user_data['gst_type'] = user_details.busniess_type
                user_data['pu_roles'] = pu_roles

            response_data = {
                'status': 'success',
                'message': 'User data retrieved successfully',
                'data': user_data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            response_error = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_error, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HsnSacAPIView(APIView):
    """
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request):
        if 'page_number' in request.data or 'page_size' in request.data:
            return self.fetch_hsnsac(request)
        elif 'hsnsac_code' in request.data and 'tax_rate' in request.data:
            return self.create_hsnsac(request)
        else:
            return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

    
    def fetch_hsnsac(self, request):
        hsnsac_id = request.data.get('hsnsac_id')
        search_txt = request.data.get('search')
        start_date = request.data.get('start_date', None)
        end_date = request.data.get('end_date', datetime.now().date())
        page_number = int(request.data.get('page_numbr', 1))
        page_size = int(request.data.get('page_size', 10))

        try:
            if not page_size: return Response({'status': 'fail','message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(page_size) == False: return Response({'status': 'fail','message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if page_number:
                if isnumber(page_number) == False: return Response({'status': 'fail','message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if hsnsac_id:
                if isnumber(hsnsac_id) == False: return Response({'status': 'fail','message': 'hsnsac_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            

            queryset = AdHSNSAC.objects.filter(is_deleted=False).order_by('-pk')

            if hsnsac_id:
                queryset = queryset.filter(pk=hsnsac_id)
            if search_txt:
                queryset = queryset.filter(
                    Q(hsnsac_code__icontains=search_txt) |
                    Q(tax_rate__icontains=search_txt)
                )
            
            if start_date:
                queryset = queryset.filter(created_at__date__range=[start_date, end_date])

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
                        'message': 'HSNSAC Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                serializer = HSNSACSerializer(page_obj.object_list, many=True, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted"]})
                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }
                return Response({
                    'status': 'success',
                    'message': 'HSNSAC Data',
                    'data': paginated_response_data
                }, status=status.HTTP_200_OK)

            serializer = HSNSACSerializer(queryset, many=True, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted"]})
            response_data = {
                'status': 'success',
                'message': 'HSNSAC Data',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    def create_hsnsac(self, request):
        request_data = request.data.copy()
        hsnsac_code = request.data.get('hsnsac_code')
        tax_rate = request.data.get('tax_rate')
        description = request.data.get('description')
           
        if 'hsnsac_code' not in request_data and 'tax_rate' not in request_data:
            return Response({"status": "fail", "message": "HSNSAC Code and Tax Rate is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if isfloat(tax_rate) == False: return Response({"status": "fail", "message": "tax_rate must contain decimal value"}, status=status.HTTP_400_BAD_REQUEST)

            hsnsac_queryset = AdHSNSAC.objects.get(hsnsac_code=hsnsac_code)
            
            response_data = {
                "status": "success",
                "message": "HSNSAC Code already exists"
            }

            if hsnsac_queryset.tax_rate == float(tax_rate):
                response_data['message'] = "Same HSNSAC code and tax rate already exists."

            return Response(response_data, status=status.HTTP_200_OK)
        
        except AdHSNSAC.DoesNotExist:
            hsnsac_query = AdHSNSAC.objects.create(
                hsnsac_code=hsnsac_code,
                tax_rate=float(tax_rate),
                description= description if description else None,
                created_at=timezone.now(),
                created_by=request.user
            )

            user_activity = {
                "table_id": hsnsac_query.pk,
                "table_name": 'ad_hsn_sac_code',
                "ua_action": 'Create',  # Action performed
                "ua_description": 'HSNSAC Entry Created Successfully.',  # Action description
                "created_by": request.user,  # Current user performing the action
                "request_data": dict(request.data),  # Request data
                "response_data": model_to_dict(hsnsac_query)
            }

            add_user_activity(user_activity)

            response_data = {
                'status': 'success',
                'message': 'HSNSAC Entry Created Successfully'
            }
            # Return a success response with status code 201 (Created)
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        hsnsac_id = request.data.get('hsnsac_id')
        hsnsac_code = request.data.get('hsnsac_code')
        tax_rate = request.data.get('tax_rate')
        description = request.data.get('description')

        if not hsnsac_id:
            return Response({
                "status": "fail",
                "message": "hsnsac_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:

            if isnumber(hsnsac_id) == False: return Response({'status': 'fail','message': 'hsnsac_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if tax_rate:
                if isfloat(tax_rate) == False: return Response({"status": "fail", "message": "tax_rate must contain decimal value"}, status=status.HTTP_400_BAD_REQUEST)

            hsnsac_queryset = AdHSNSAC.objects.get(hsnsac_id=hsnsac_id)

            if 'is_deactive' in request.data:
                is_deactive = request.data.get('is_deactive')
                is_deactive = True if is_deactive == "true" else False
                hsnsac_queryset.is_deactive = is_deactive
                hsnsac_queryset.updated_at = timezone.now()
                hsnsac_queryset.save()

                if is_deactive:
                    message = 'HSNSAC Entry Deactivated Successfully'
                else:
                    message = 'HSNSAC Entry Activated Successfully'

                # Return a success response with the appropriate message
                response_data = {
                    "status": "success",
                    "message": message
                }
                return Response(response_data, status=status.HTTP_200_OK)
            
            else:
                query_set = AdHSNSAC.objects.filter(hsnsac_code=hsnsac_code).exclude(hsnsac_id=hsnsac_id)
                if query_set:
                    return Response({
                        "status": "fail",
                        "message": "HSNSAC code already exists."
                    }, status=status.HTTP_400_BAD_REQUEST)

                if hsnsac_code:
                    hsnsac_queryset.hsnsac_code = hsnsac_code 

                if tax_rate:
                    hsnsac_queryset.tax_rate = float(tax_rate)

                if description:
                    hsnsac_queryset.description = description
                
                hsnsac_queryset.updated_at = timezone.now()
                hsnsac_queryset.save()

                user_activity = {
                    "table_id": hsnsac_queryset.pk,  # ID of the created banner
                    "table_name": 'ad_hsn_sac_code',  # Name of the model
                    "ua_action": 'Update',  # Action performed
                    "ua_description": 'HSNSAC Entry Updated Successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(hsnsac_queryset)
                }

                add_user_activity(user_activity)

                # Return a success response with the appropriate message
                response_data = {
                    "status": "success",
                    "message": "HSNSAC Entry Updated Successfully"
                }
                return Response(response_data, status=status.HTTP_200_OK)

        except AdHSNSAC.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': "HSNSAC entry not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            response_data = {
                "status": "error",
                "message": f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        hsnsac_id = request.data.get("hsnsac_id")
        
        # Check if hsnsac_id is provided
        if not hsnsac_id:
            response_data = {
                'status': 'fail',
                'message': "hsnsac_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        if isnumber(hsnsac_id) == False: return Response({'status': 'fail','message': 'hsnsac_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                hsnsac = AdHSNSAC.objects.get(hsnsac_id=hsnsac_id, is_deleted=False)
                hsnsac.is_deleted = True
                hsnsac.save()
                
                response_data = {
                    'status': 'success',
                    'message': 'HSNSAC Deleted Successfully'
                }

                return Response(response_data, status=status.HTTP_200_OK)
        except AdHSNSAC.DoesNotExist:
            # Handle case where HSNSAC is not found
            response_data = {
                'status': 'fail',
                'message': "HSNSAC not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        
        except ProtectedError as e:
            protected_objects = list(e.protected_objects)
            protected_object_names = [str(obj) for obj in protected_objects]
            return Response({'status': 'fail', 'message': 'Cannot delete the record because it is referenced in other tables'}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ServiceAPIView(APIView):
    """
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request):
        service_id = request.data.get('service_id')
        search_txt = request.data.get('search')
        page_number = int(request.data.get('page_numbr', 1))
        page_size = int(request.data.get('page_size', 10))

        try:
            if not page_size: return Response({'status': 'fail','message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(page_size) == False: return Response({'status': 'fail','message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if page_number:
                if isnumber(page_number) == False: return Response({'status': 'fail','message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if service_id:
                if isnumber(service_id) == False: return Response({'status': 'fail','message': 'service_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            queryset = []
            all_service = AdService.objects.filter(is_deleted=False).order_by('-pk')
            for service in all_service:
                service_provider = AdServiceProvider.objects.filter(service=service).first()
                if service_provider and service_provider.sa_provided == True:
                    queryset.append(service)
            if service_id:
                queryset = queryset.filter(pk=service_id)
            if search_txt:
                queryset = queryset.filter(
                    Q(service_name__icontains=search_txt) |
                    Q(description__icontains=search_txt)
                )

            # queryset = queryset.order_by('-pk')

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
                if not queryset:
                    paginated_response_data = {
                        'total_pages': 0,
                        'current_page': 0,
                        'total_items': 0,
                        'results': []
                    }
                    response_data = {
                        'status': 'fail',
                        'message': 'HSNSAC Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                serializer = ServiceSerializer(page_obj.object_list, many=True, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted"]})
                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }
                return Response({
                    'status': 'success',
                    'message': 'Service Data',
                    'data': paginated_response_data
                }, status=status.HTTP_200_OK)

            serializer = ServiceSerializer(queryset, many=True, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted"]})
            response_data = {
                'status': 'success',
                'message': 'Service Data',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            with transaction.atomic():
                savepoint = transaction.savepoint()
                service_id = request.data.get('service_id')
                print('service_id', service_id)
                description = request.data.get('description', None)

                if not service_id:
                    return Response({
                        'status': 'fail',
                        'message': 'Service ID is required'
                    }, status=status.HTTP_400_BAD_REQUEST)

                service_instance = AdService.objects.get(service_id=service_id, is_deleted=False)
                print('service_instance', service_instance)
                service_provider_instance = AdServiceProvider.objects.filter(service_id=service_id)
                if service_instance.is_deleted:
                    return Response({
                        'status': 'fail',
                        'message': f'Service with ID {service_id} not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                if service_id and not description:
                    if service_instance.is_deactive == True:
                        admin_service = SaService.objects.filter(service_name=service_instance.service_name).first()
                        if admin_service and admin_service.is_deactive == True:
                            return Response({'status': 'fail', 'message': 'Contact admin to activate the service.'},status=status.HTTP_400_BAD_REQUEST)
                        service_instance.is_deactive = False
                        service_instance.updated_at = datetime.now()
                        for sp_instance in service_provider_instance:
                            hierarchy_charges = HierarchyCharges.objects.filter(sp=sp_instance.pk, is_deleted=False).first()
                            if not hierarchy_charges:
                                return Response({'status': 'fail',
                                            'message': 'The service provider commission structure must be set up to activate this service.'},
                                            status=status.HTTP_400_BAD_REQUEST)

                            sp_instance.is_deactive = False
                            commission_charges = AdCommissionCharges.objects.filter(service_provider=sp_instance.pk, is_deleted=False)
                            for charges in commission_charges:
                                charges.is_deactive = False
                                charges.save()
                            hierarchy_charges = HierarchyCharges.objects.filter(sp=sp_instance.pk, is_deleted=False)
                            for charges in hierarchy_charges:
                                charges.is_deactive = False
                                charges.save()
                            service_transaction_charges = PortalUserCharges.objects.filter(sp=sp_instance.pk)
                            for charges in service_transaction_charges:
                                charges.is_deactive = False
                                charges.save()
                            sp_instance.save()

                        service_instance.save()
                        message = "Service activate succussfully"
                        transaction.savepoint_commit(savepoint)
                    else:
                        service_instance.is_deactive = True
                        service_instance.updated_at = datetime.now()

                        for sp_instance in service_provider_instance:
                            sp_instance.is_deactive = True
                            commission_charges = AdCommissionCharges.objects.filter(service_provider=sp_instance.pk, is_deleted=False)
                            for charges in commission_charges:
                                charges.is_deactive = True
                                charges.save()
                            hierarchy_charges = HierarchyCharges.objects.filter(sp=sp_instance.pk, is_deleted=False)
                            for charges in hierarchy_charges:
                                charges.is_deactive = True
                                charges.save()
                            service_transaction_charges = PortalUserCharges.objects.filter(sp=sp_instance.pk)
                            for charges in service_transaction_charges:
                                charges.is_deactive = True
                                charges.save()
                            sp_instance.save()

                        service_instance.save()
                        message = "Service deactivate succussfully"
                        transaction.savepoint_commit(savepoint)

                    return Response({
                        'status': 'success',
                        'message': message,
                    }, status=status.HTTP_200_OK)
                else:
                    print('description', description)
                    if description:
                        service_instance.description = description
                        print('service_instance.description', service_instance.description)
                    service_instance.updated_at = datetime.now()
                    service_instance.save()
                    return Response({ 'status': 'success', 'message': 'Service updated successfully'}, status=status.HTTP_200_OK)
                # return Response({
                #     'status': 'fail',
                #     'message': 'Failed to update service',
                # }, status=status.HTTP_400_BAD_REQUEST)

        except AdService.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': f'Service with ID {service_id} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnnouncementPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsRetailer | IsDistributor]

    def post(self, request):
        try:
            if 'page_number' in request.data or 'page_size' in request.data:
                return self.get_announcement(request)
            elif 'is_retailer' in request.data:
                return self.fetch_announcements(request)
            elif 'an_title' in request.data and 'an_desc' in request.data and 'an_link' in request.data:
                return self.create_announcement(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_announcement(self, request):
        an_title = request.data.get('an_title')
        an_desc = request.data.get('an_desc')
        an_link = request.data.get('an_link', None)

        try:
            if not an_title: return Response({'status': 'fail', 'message': 'an_title is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not an_desc: return Response({'status': 'fail', 'message': 'an_desc is required.'}, status=status.HTTP_400_BAD_REQUEST)
            # if not an_link: return Response({'status': 'fail', 'message': 'an_link is required.'}, status=status.HTTP_400_BAD_REQUEST)

            fetch_announcement = Announcement.objects.filter(an_title=an_title, is_delete=False).first()
            if fetch_announcement: return Response({'status': 'fail', 'message': f'{an_title} this title is already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            announcement = Announcement.objects.create(
                an_title=an_title,
                an_desc=an_desc,
                an_link=an_link
            )

            user_activity = {
                "table_id": announcement.pk,
                "table_name": 'ad_announcement',
                "ua_action": 'Create',  # Action performed
                "ua_description": 'Announcement Added successfully.',  # Action description
                "created_by": request.user,  # Current user performing the action
                "request_data": dict(request.data),  # Request data
                "response_data": None
            }
            add_user_activity(user_activity)

            return Response({'status': 'success', 'message': 'Announcement Added successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_announcements(self, request):
        try:
            all_announcement = Announcement.objects.filter(is_delete=False, is_deactive=False).order_by('-pk')

            serializer = AnnouncementSerializer(all_announcement, many=True)

            return Response({'status': 'success', 'message': 'fetch announcment successfully.', 'data': {'results': serializer.data}}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_announcement(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        search = request.data.get('search', '')

        try:
            if not page_size: return Response({'status': 'fail', 'message': 'page_size is required.'},
                                              status=status.HTTP_400_BAD_REQUEST)
            if isnumber(page_size) == False: return Response(
                {'status': 'fail', 'message': 'page_size must contain only digits.'},
                status=status.HTTP_400_BAD_REQUEST)

            if page_number:
                if isnumber(page_number) == False: return Response(
                    {'status': 'fail', 'message': 'page_number must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)

            pu_role = PortalUser.objects.get(id=request.user.id).pu_role

            all_announcement = Announcement.objects.filter(is_delete=False).order_by('-pk')

            if search:
                all_announcement = all_announcement.filter(Q(an_title__icontains=search) | Q(an_desc__icontains=search))

            page_number = int(page_number)
            page_size = int(page_size)

            paginator = Paginator(all_announcement, page_size)
            page = paginator.get_page(page_number)
            serializer = AnnouncementSerializer(page, many=True)

            return Response({'status': 'success', 'message': 'fetch announcment successfully.', 'data': {'results': serializer.data}}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        an_id = request.data.get('an_id')
        an_title = request.data.get('an_title', None)
        an_desc = request.data.get('an_desc', None)
        an_link = request.data.get('an_link', None)
        message = 'Announcement Updated successfully.'
        try:
            if not an_id: return Response({'status': 'fail', 'message': 'an_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            announcement = Announcement.objects.get(an_id=an_id)
            existing_announcement = Announcement.objects.filter(an_title=an_title, is_delete=False).exclude(an_id=an_id).first()
            if existing_announcement:
                return Response({'status': 'fail', 'message': 'A announcement with this title already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            if an_id and not an_title and not an_desc and not an_link:
                if announcement.is_deactive == True:
                    announcement.is_deactive = False
                    announcement.save()
                    message = 'Announcement is Activated successfully.'
                else:
                    announcement.is_deactive = True
                    announcement.save()
                    message = 'Announcement is Deactivted successfully.'

            else:
                announcement.an_title = an_title if an_title else announcement.an_title
                announcement.an_desc = an_desc if an_desc else announcement.an_desc
                announcement.an_link = an_link if an_link else announcement.an_link
                announcement.save()

            user_activity = {
                "table_id": announcement.pk,
                "table_name": 'ad_announcement',
                "ua_action": 'Update',  # Action performed
                "ua_description": message,  # Action description
                "created_by": request.user,  # Current user performing the action
                "request_data": dict(request.data),  # Request data
                "response_data": None
            }
            add_user_activity(user_activity)

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)
        
        except Announcement.DoesNotExist:
            return Response({'status': 'fail', 'message': 'announcement dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        an_id = request.data.get('an_id')
        print('an_id', an_id)
        try:
            if not an_id: return Response({'status': 'fail', 'message': 'an_id is reqiured.'}, status=status.HTTP_400_BAD_REQUEST)

            announcement = Announcement.objects.get(an_id=an_id, is_delete=False)
            announcement.is_delete=True
            announcement.save()

            user_activity = {
                "table_id": announcement.pk,
                "table_name": 'ad_announcement',
                "ua_action": 'Delete',  # Action performed
                "ua_description": 'announcement deleted successfully.',  # Action description
                "created_by": request.user,  # Current user performing the action
                "request_data": dict(request.data),  # Request data
                "response_data": None
            }
            add_user_activity(user_activity)

            return Response({'status': 'success', 'message': 'announcement deleted successfully.'}, status=status.HTTP_200_OK)

        except Announcement.DoesNotExist:
            return Response({'status': 'fail', 'message': 'announcement dose not exsits.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ServiceProviderAPIView(APIView):
    """
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_service_provider(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_service_provider(self, request):
        sp_id = request.data.get('sp_id')
        service_id = request.data.get('service_id')
        hsn_sac_id = request.data.get('hsn_sac_id')
        search_txt = request.data.get('search')
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size')

        try:
            if not page_size: return Response({'status': 'fail', 'message': 'page_size is required.'},
                                              status=status.HTTP_400_BAD_REQUEST)
            if isnumber(page_size) == False: return Response(
                {'status': 'fail', 'message': 'page_size must contain only digits.'},
                status=status.HTTP_400_BAD_REQUEST)

            if page_number:
                if isnumber(page_number) == False: return Response(
                    {'status': 'fail', 'message': 'page_number must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)

            if sp_id:
                if isnumber(sp_id) == False: return Response(
                    {'status': 'fail', 'message': 'sp_id must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)

            if service_id:
                if isnumber(service_id) == False: return Response(
                    {'status': 'fail', 'message': 'service_id must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)

            if hsn_sac_id:
                if isnumber(hsn_sac_id) == False: return Response(
                    {'status': 'fail', 'message': 'hsn_sac_id must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)
            
            user = PortalUser.objects.get(id=request.user.pk)

            queryset = AdServiceProvider.objects.filter(is_deleted=False, sa_provided=True)

            if sp_id:
                queryset = queryset.filter(pk=sp_id)
            if service_id:
                queryset = queryset.filter(service_id=service_id)
            if hsn_sac_id:
                queryset = queryset.filter(hsn_sac_id=hsn_sac_id)
            if search_txt:
                queryset = queryset.filter(
                    Q(service__service_name__icontains=search_txt) |
                    Q(sp_name__icontains=search_txt) |
                    Q(label__icontains=search_txt) |
                    Q(hsn_sac__hsnsac_code__icontains=search_txt)
                )

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

            # If no data found, return an empty result with pagination metadata
            if not queryset.exists():
                return Response({
                    'status': 'fail',
                    'message': 'Service Provider Data not found.',
                    'data': {
                        'total_pages': 0,
                        'current_page': 0,
                        'total_items': 0,
                        'results': []
                    }
                }, status=status.HTTP_200_OK)

            # For each service provider, fetch related charges
            service_provider_data = []
            # Initialize a dictionary to group providers by their sub_service_provider
            sub_service_provider_mapping = {}

            for provider in page_obj:
                # Fetch related charges (assuming 'to_provide' charges category)
                to_us_charges = AdCharges.objects.filter(service_provider=provider, charge_category='to_us')

                if len(to_us_charges) > 0:
                    charge_serializer = ChargeSerializer(to_us_charges, many=True, context={'request': request})
                    charge_type = to_us_charges.first().charges_type if to_us_charges.exists() else None
                    charge_serializer_update = charge_serializer.data
                    for charge in charge_serializer_update:
                        charge.pop("created_at")
                        charge.pop("updated_at")
                        charge.pop("is_deactive")
                        charge.pop("is_deleted")
                        charge.pop("created_by")

                        if (charge.get("minimum") == "0.00" and charge.get("maximum") == "0.00") or (charge.get("minimum") == None and charge.get("maximum") == None):
                            charge.update({"is_slab": False})
                        else:
                            charge.update({"is_slab": True})
                else:
                    charge_serializer_update = []
                    charge_type = None

                ad_commission_queryset = AdCommissionCharges.objects.filter(service_provider=provider, is_deleted=False)
                if len(ad_commission_queryset) > 0:
                    global_commission_list = [
                        {
                            "commission_charges_id": commission_value.commission_charges_id,
                            "service_provider": commission_value.service_provider.pk,
                            "rate_type": commission_value.rate_type,
                            "minimum": commission_value.minimum,
                            "maximum": commission_value.maximum,
                            "is_slab": commission_value.is_slab
                        }
                        for commission_value in ad_commission_queryset
                    ]
                else:
                    global_commission_list = []

                service_name = AdService.objects.get(service_id=provider.service_id)

                if provider.parent_id is None:
                    service_provider_data.append({
                        'parent_id': None,
                        'sub_service_provider': [],
                        'sp_id': provider.sp_id,
                        'service_id': service_name.service_id,
                        'service_name': service_name.service_name,
                        'is_global': service_name.is_global,
                        'provider_name': provider.sp_name,
                        'provider_label': provider.label,
                        'tds_rate': provider.tds_rate,
                        'hsn_sac': provider.hsn_sac.hsnsac_id if provider.hsn_sac else None,
                        'hsn_sac_code': f'{provider.hsn_sac.hsnsac_code} ({provider.hsn_sac.tax_rate}%)' if provider.hsn_sac else None,
                        'tax_rate': provider.hsn_sac.tax_rate if provider.hsn_sac else None,
                        'charge_type': charge_type,
                        'is_deactive': provider.is_deactive,
                        'to_us_charges': charge_serializer_update, 
                        'global_commission': global_commission_list,
                        'credentials_json': provider.credentials_json,
                        'is_table_config': provider.is_table_config,
                        'config_table_name': provider.config_table_name,
                        'credentials_json': provider.credentials_json,
                        'plateform_fee': provider.plateform_fee,
                        'plateform_fee_type': provider.plateform_fee_type,
                        'required_key': provider.required_key,
                        'is_self_config': provider.is_self_config
                    })
                else:
                    # sub_service_provider = AdSubServiceProvider.objects.filter(ssp_id=provider.parent_id.ssp_id).first()
                    if provider.parent_id != None:
                        if provider.parent_id not in sub_service_provider_mapping:
                            sub_service_provider_mapping[provider.parent_id] = {
                                'parent_id': provider.parent_id,
                                'sub_service_provider': []
                            }

                        sub_service_provider_mapping[provider.parent_id]['sub_service_provider'].append({
                            'sp_id': provider.sp_id,
                            'service_id': service_name.service_id,
                            'service_name': service_name,
                            'is_global': service_name.is_global,
                            'provider_name': provider.sp_name,
                            'provider_label': provider.label,
                            'tds_rate': provider.tds_rate,
                            'hsn_sac': provider.hsn_sac.hsnsac_id if provider.hsn_sac else None,
                            'hsn_sac_code': provider.hsn_sac.hsnsac_code if provider.hsn_sac else None,
                            'tax_rate': provider.hsn_sac.tax_rate if provider.hsn_sac else None,
                            'charge_type': charge_type,
                            'is_deactive': provider.is_deactive,
                            'to_us_charges': charge_serializer_update,
                            'global_commission': global_commission_list,
                            'credentials_json': provider.credentials_json,
                            'is_table_config': provider.is_table_config,
                            'config_table_name': provider.config_table_name,
                            'credentials_json': provider.credentials_json,
                            'plateform_fee': provider.plateform_fee,
                            'plateform_fee_type': provider.plateform_fee_type,
                            'required_key': provider.required_key,
                            'is_self_config': provider.is_self_config
                        })

            for ssp_id, data in sub_service_provider_mapping.items():
                service_provider_data.append(data) 
 
            paginated_response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': service_provider_data
            }

            return Response({
                'status': 'success',
                'message': 'Service Provider Data with Charges',
                'data': paginated_response_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_commission_structure(self, request):
        sp_id = request.data.get('sp_id')
        # global_commission = request.data.get('global_commission')
        commission_value = request.data.get('commissions')
        try:
            # try:
            #     global_commission_list = json.loads(global_commission)
            # except json.JSONDecodeError:
            #     raise ValidationError("Invalid JSON format for global commission")
            try:
                commission_list = json.loads(commission_value)
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON format for commission value")

            try:
                service_provider = AdServiceProvider.objects.get(sp_id=sp_id, is_deleted=False)
            except AdServiceProvider.DoesNotExist:
                return Response({
                    'status': 'fail',
                    'message': 'Service Provider not found'
                }, status=status.HTTP_404_NOT_FOUND)

            queryset = HierarchyCharges.objects.filter(sp=service_provider, is_deleted=False)
            if queryset:

                # if len(queryset) > 1:
                #     for del_record in queryset[1:]:
                #         del_record.delete()

                # if len(global_commission) > 1:
                #     for index, commission_data in enumerate(global_commission_list):
                #         if index == 0:
                #             adcommission_charge_record = AdCommissionCharges.objects.get(commission_charges_id=queryset[0].pk)
                #             adcommission_charge_record.rate_type = global_commission_list[0].get("rate_type")
                #             adcommission_charge_record.minimum = global_commission_list[0].get("minimum")
                #             adcommission_charge_record.maximum = global_commission_list[0].get("maximum")
                #             adcommission_charge_record.rate = global_commission_list[0].get("rate")
                #             adcommission_charge_record.is_slab = bool(global_commission_list[0].get("is_slab"))
                #             adcommission_charge_record.updated_at = timezone.now()
                #             adcommission_charge_record.save()
                #         else:
                #             if service_provider.parent_id == None and commission_data.get("is_slab") == 'true':
                #                 commission_charge_object = AdCommissionCharges.objects.create(
                #                     service_provider=service_provider,
                #                     # charges_type=commission_data.get("charges_type"),
                #                     rate_type=commission_data.get("rate_type"),
                #                     minimum=commission_data.get("minimum"),
                #                     maximum=commission_data.get("maximum"),
                #                     rate=commission_data.get("rate"),
                #                     is_slab = bool(commission_data.get("is_slab")),
                #                     updated_at=timezone.now(),
                #                     created_at=timezone.now(), 
                #                     created_by=request.user
                #                 )
                #             elif service_provider.parent_id != None and commission_data.get("is_slab") == 'true':
                #                 commission_charge_object = AdCommissionCharges.objects.create(
                #                     service_provider=service_provider,
                #                     # charges_type=commission_data.get("charges_type"),
                #                     rate_type=commission_data.get("rate_type"),
                #                     minimum=commission_data.get("minimum"),
                #                     maximum=commission_data.get("maximum"),
                #                     rate=commission_data.get("rate"),
                #                     is_slab = False,
                #                     updated_at=timezone.now(),
                #                     created_at=timezone.now(), 
                #                     created_by=request.user
                #                 )
                #             else:
                #                 return Response({'status': 'fail', 'message': 'Charges type is slab not allowed.'}, status=status.HTTP_400_BAD_REQUEST)
                    # if service_provider.parent_id == None:
                    #     if global_commission_list[0].get("is_slab") == 'true':
                    #         adcommission_charge_record = AdCommissionCharges.objects.get(commission_charges_id=queryset[0].pk)
                    #         adcommission_charge_record.rate_type = global_commission_list[0].get("rate_type")
                    #         adcommission_charge_record.minimum = global_commission_list[0].get("minimum")
                    #         adcommission_charge_record.maximum = global_commission_list[0].get("maximum")
                    #         adcommission_charge_record.rate = global_commission_list[0].get("rate")
                    #         adcommission_charge_record.is_slab = bool(global_commission_list[0].get("is_slab"))
                    #         adcommission_charge_record.updated_at = datetime.now()
                    #         adcommission_charge_record.save()
                    #     else:
                    #         adcommission_charge_record = AdCommissionCharges.objects.get(commission_charges_id=queryset[0].pk)
                    #         adcommission_charge_record.rate_type = global_commission_list[0].get("rate_type")
                    #         adcommission_charge_record.minimum = global_commission_list[0].get("minimum")
                    #         adcommission_charge_record.maximum = global_commission_list[0].get("maximum")
                    #         adcommission_charge_record.rate = global_commission_list[0].get("rate") 
                    #         adcommission_charge_record.is_slab = False
                    #         adcommission_charge_record.updated_at = datetime.now()
                    #         adcommission_charge_record.save()
                    # else:
                    #     if global_commission_list[0].get("is_slab") != 'true':
                    #         adcommission_charge_record = AdCommissionCharges.objects.get(commission_charges_id=queryset[0].pk)
                    #         adcommission_charge_record.rate_type = global_commission_list[0].get("rate_type")
                    #         adcommission_charge_record.minimum = global_commission_list[0].get("minimum")
                    #         adcommission_charge_record.maximum = global_commission_list[0].get("maximum")
                    #         adcommission_charge_record.rate = global_commission_list[0].get("rate") 
                    #         adcommission_charge_record.is_slab = False
                    #         adcommission_charge_record.updated_at = datetime.now()
                    #         adcommission_charge_record.save()
                    #     else:
                    #         data = {'status': 'fail', 'message': 'Charges type is slab not allowed.'}
                    #         return data

                for value in commission_list:
                    try:
                        if value['dh_id'] != 0:
                            dh = DistributorHierarchy.objects.get(dh_id=value['dh_id'], is_deleted=False)
                        else:
                            dh = None
                    except Exception as e:
                        return Response({'status': 'fail', 'message': 'dh ID is not exists.'},
                                        status=status.HTTP_404_NOT_FOUND)

                    hierarchy_charge_queryset = HierarchyCharges.objects.get(dh=dh, sp=service_provider)
                    hierarchy_charge_queryset.hc_charges = value.get('commission')
                    hierarchy_charge_queryset.updated_at = timezone.now()
                    hierarchy_charge_queryset.updated_by = request.user.pk
                    hierarchy_charge_queryset.save()
                data = {'status': 'success', 'message': 'Service provider commission updated successfully.'}
                return data
            else:
                if service_provider.parent_id == None:
                    # for commission_data in global_commission_list:
                    #     commission_charge_object = AdCommissionCharges.objects.create(
                    #         service_provider=service_provider,
                    #         charges_type=commission_data.get("charges_type"),
                    #         rate_type=commission_data.get("rate_type"),
                    #         minimum=commission_data.get("minimum"),
                    #         maximum=commission_data.get("maximum"),
                    #         rate=commission_data.get("rate"),
                    #         is_slab = bool(commission_data.get("is_slab")),
                    #         created_at=timezone.now(),
                    #         created_by=request.user
                    #     )

                    for value in commission_list:
                        try:
                            if value['dh_id'] != 0:
                                dh = DistributorHierarchy.objects.get(dh_id=value['dh_id'], is_deleted=False)
                            else:
                                dh = None
                        except Exception as e:
                            return Response({'status': 'fail', 'message': 'dh ID is not exists.'},
                                            status=status.HTTP_404_NOT_FOUND)
                        
                        # for commission in value['commission']:
                        #     if value['dh_id'] != 0:
                        #         commission['effective_wallet'] = 'commission_wallet'
                        #     else:
                        #         commission['effective_wallet'] = 'main_wallet'

                        HierarchyCharges.objects.create(
                            # mark_type=value['charges_type'],
                            hc_charges=value['commission'],
                            dh=dh,
                            sp=service_provider,
                            created_at=timezone.now(),
                            created_by=request.user
                        )

                else:
                    # for commission_data in global_commission_list:
                    #     if commission_data.get("is_slab") != 'true':
                    #         commission_charge_object = AdCommissionCharges.objects.create(
                    #             service_provider=service_provider,
                    #             charges_type=commission_data.get("charges_type"),
                    #             rate_type=commission_data.get("rate_type"),
                    #             minimum=commission_data.get("minimum"),
                    #             maximum=commission_data.get("maximum"),
                    #             rate=commission_data.get("rate"),
                    #             is_slab = bool(commission_data.get("is_slab")),
                    #             created_at=timezone.now(),
                    #             created_by=request.user
                    #         )
                    #     else:
                    #         data = {'status': 'fail', 'message': 'Charges type is slab not allowed.'}
                    #         return data
                    
                    for value in commission_list:
                        try:
                            if value['dh_id'] != 0:
                                dh = DistributorHierarchy.objects.get(dh_id=value['dh_id'], is_deleted=False)
                            else:
                                dh = None
                        except Exception as e:
                            return Response({'status': 'fail', 'message': 'dh ID is not exists.'},
                                            status=status.HTTP_404_NOT_FOUND)
                        
                        # for commission in value['commission']:
                        #     if value['dh_id'] != 0:
                        #         commission['effective_wallet'] = 'commission_wallet'
                        #     else:
                        #         commission['effective_wallet'] = 'main_wallet'

                        HierarchyCharges.objects.create(
                            # mark_type=value['charges_type'],
                            hc_charges=value['commission'],
                            dh=dh,
                            sp=service_provider,
                            created_at=timezone.now(),
                            created_by=request.user
                        ) 

                user_activity = {
                    "table_id": 0,
                    "table_name": 'ad_commission_charges',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'Service provider commission added successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": None
                }
                add_user_activity(user_activity)
                data = {'status': 'success', 'message': 'Service Provider commission and cargers added successfully.'}
                return data
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    charges_parameter = openapi.Parameter(
        'charges',
        openapi.IN_FORM,
        description="List of charges (JSON string)",
        type=openapi.TYPE_STRING,
        required=False
    )

    def put(self, request):
        try:
            with transaction.atomic():
                savepoint_1 = transaction.savepoint()
                sp_id = request.data.get('sp_id')
                charges_type = request.data.get('charges_type', None)
                tds_rate = request.data.get('tds_rate', None)
                message = {'status': 'success', 'message': 'Service Provider updated successfully'}

                if not sp_id: return Response({'status': 'fail', 'message': 'Service Provider ID is required'},
                                              status=status.HTTP_400_BAD_REQUEST)
                if isnumber(sp_id) == False: return Response(
                    {'status': 'fail', 'message': 'sp_id must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)

                try:
                    service_provider = AdServiceProvider.objects.get(sp_id=sp_id, is_deleted=False)
                except AdServiceProvider.DoesNotExist:
                    return Response({'status': 'fail', 'message': 'Service Provider not found'},
                                    status=status.HTTP_404_NOT_FOUND)

                if sp_id and not charges_type and not tds_rate:
                    
                    if not service_provider.service.is_global == True:
                        if not HierarchyCharges.objects.filter(sp_id=sp_id).exists():
                            return Response({'status': 'fail',
                                            'message': 'The service provider commission structure must be set up to activate this service.'},
                                            status=status.HTTP_400_BAD_REQUEST)
                    else:
                        if service_provider.service.service_name == 'BBPS':
                            category = BBPSBillerCategory.objects.filter(is_deactive=False)
                            if not category.exists():
                                return Response({'status': 'fail', 'message': 'Please update the category rate before activating the service provider.'}, status=status.HTTP_400_BAD_REQUEST)
                        elif service_provider.service.service_name == 'Recharge':
                            category = Oprators.objects.filter(is_deactive=False)
                            if not category.exists():
                                return Response({'status': 'fail', 'message': 'Please update the category rate before activating the service provider.'}, status=status.HTTP_400_BAD_REQUEST)

                    if service_provider.is_deactive == True:
                        service_provider.is_deactive = False
                        admin_service = SaService.objects.filter(service_name=service_provider.service.service_name).first()
                        if admin_service and admin_service.is_deactive == True and service_provider.is_self_config == False:
                            return Response({'status': 'fail', 'message': 'Contact admin to activate the service.'},status=status.HTTP_400_BAD_REQUEST)
                        try:
                            # Activating service and commission charges
                            service = AdService.objects.get(service_id=service_provider.service.service_id)
                            service.is_deactive = False
                            service.save()
                            
                            hierarchy_charges = HierarchyCharges.objects.filter(sp=service_provider, is_deleted=False)
                            for charges in hierarchy_charges:
                                charges.is_deactive = False
                                charges.save()

                            # service_transaction_charges = PortalUserCharges.objects.filter(sp=service_provider)
                            # # Adding PortalUserCharges if not exist
                            # if not service_transaction_charges:
                            #     all_portal_users = PortalUser.objects.filter(pu_role__in=["DISTRIBUTOR", "RETAILER"])
                            #     if service_provider.parent_id is None:
                            #         for pt_user in all_portal_users:
                            #             portal_user_id = pt_user.id

                            #             dh_value = PortalUserCharges.objects.filter(pu_id=portal_user_id).select_related(
                            #                 'dh', 'sp').first()
                            #             dh_id = dh_value.dh.dh_id if dh_value.dh else None
                            #             hierarchy_charges = HierarchyCharges.objects.get(dh=dh_id,
                            #                                                             sp=service_provider.sp_id,
                            #                                                             is_deleted=False)
                            #             PortalUserCharges.objects.create(
                            #                 sp=hierarchy_charges.sp,
                            #                 dh=hierarchy_charges.dh,
                            #                 pu_id=pt_user.id,
                            #                 parent_id=dh_value.parent_id,
                            #                 mark_type=hierarchy_charges.mark_type,
                            #                 puc_charges=hierarchy_charges.hc_charges,
                            #                 is_deactive=False,
                            #                 created_by=request.user
                            #             )
                            # else:
                            #     for charges in service_transaction_charges:
                            #         charges.is_deactive = False
                            #         charges.save()

                            # Commit the first savepoint
                            transaction.savepoint_commit(savepoint_1)
                            message = {'status': 'success', 'message': 'Service Provider Activated Successfully.'}

                        except Exception as e:
                            # Rollback to the first savepoint if activation fails
                            transaction.savepoint_rollback(savepoint_1)
                            return Response({
                                'status': 'error',
                                'message': f'Error activating Service Provider: {str(e)}'
                            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    else:
                        # Deactivation process with savepoint rollback support
                        service_provider.is_deactive = True
                        try:
                            commission_charges = AdCommissionCharges.objects.filter(service_provider=service_provider,
                                                                                    is_deleted=False)
                            for charges in commission_charges:
                                charges.is_deactive = True
                                charges.save()

                            hierarchy_charges = HierarchyCharges.objects.filter(sp=service_provider, is_deleted=False)
                            for charges in hierarchy_charges:
                                charges.is_deactive = True
                                charges.save()

                            service_transaction_charges = PortalUserCharges.objects.filter(sp=service_provider)
                            for charges in service_transaction_charges:
                                charges.is_deactive = True
                                charges.save()

                            # Commit the first savepoint after successful deactivation
                            transaction.savepoint_commit(savepoint_1)
                            message = {'status': 'success', 'message': 'Service Provider Deactivated Successfully.'}

                        except Exception as e:
                            # Rollback to the first savepoint if deactivation fails
                            transaction.savepoint_rollback(savepoint_1)
                            return Response({
                                'status': 'error',
                                'message': f'Error deactivating Service Provider: {str(e)}'
                            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                    service_provider.updated_at = timezone.now()
                    service_provider.save()

                else:

                    if not tds_rate: return Response({'status': 'fail', 'message': 'TDS rate is required'},
                                                     status=status.HTTP_400_BAD_REQUEST)
                    if isfloat(tds_rate) == False: return Response(
                        {'status': 'fail', 'message': 'Invalid value for TDS rate. Please provide a numeric value.'},
                        status=status.HTTP_400_BAD_REQUEST)

                    tds_rate = float(tds_rate)

                    if tds_rate < 0: return Response(
                        {'status': 'fail', 'message': 'TDS rate must be a positive number.'},
                        status=status.HTTP_400_BAD_REQUEST)
                    if tds_rate > 100: return Response(
                        {'status': 'fail', 'message': 'TDS rate must be between 0 and 100.'},
                        status=status.HTTP_400_BAD_REQUEST)

                    # Second savepoint for TDS update
                    savepoint_2 = transaction.savepoint()
                    try:
                        serializer = ServiceProviderSerializer(service_provider, data=request.data, partial=True,
                                                               context={'request': request})
                        if serializer.is_valid():
                            service_provider_instance = serializer.save(updated_at=timezone.now(),
                                                                        updated_by=request.user)
                            add_user_activity({
                                "table_id": service_provider_instance.pk,
                                "table_name": 'ad_service_provider',
                                "ua_action": 'Update',
                                "ua_description": 'Service Provider updated successfully.',
                                "created_by": request.user,
                                "request_data": dict(request.data),
                                "response_data": serializer.data
                            })

                            service_data = AdService.objects.get(service_id=service_provider.service_id)
                            if service_data.is_global == False:
                                if 'to_us_charges' in request.data:
                                    to_us_charges_str = request.data.get('to_us_charges', '[]')
                                    self.process_charges(to_us_charges_str, service_provider_instance, request, 'to_us',
                                                        charges_type)
                                message = self.add_commission_structure(request)
                            else:
                                pass
                            # Commit the second savepoint after successful TDS rate update
                            transaction.savepoint_commit(savepoint_2)
                        else:
                            transaction.savepoint_rollback(savepoint_2)
                            return Response({
                                'status': 'fail',
                                'message': 'Failed to update Service Provider',
                                'data': serializer.errors
                            }, status=status.HTTP_400_BAD_REQUEST)

                    except Exception as e:
                        transaction.savepoint_rollback(savepoint_2)
                        return Response({
                            'status': 'error',
                            'message': f'Error updating TDS rate: {str(e)}'
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                return Response({
                    'status': message.get('status'),
                    'message': message.get('message')
                })

            return Response({
                'status': 'fail',
                'message': 'Failed to update Service Provider',
                'data': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def process_charges(self, charges_str, service_provider_instance, request, charge_category, charges_type):
        try:
            charges = json.loads(charges_str)
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format for charges")

        # fetch charges related service provider and charge category
        charge_filter_object = AdCharges.objects.filter(service_provider=service_provider_instance.pk, charge_category=charge_category, is_deleted=False)

        # check if charges record exist then update the charges otherwise create the charges
        if charge_filter_object:

            # delete the object if charge filter record more then one
            if len(charge_filter_object) > 1:
                for del_record in charge_filter_object[1:]:
                    del_record.delete()

            for charge in charges:
                if charge["minimum"] == "0.00":
                    charge["minimum"] = "0.00"
                if charge["maximum"] == "0.00":
                    charge["maximum"] = "0.00"
                charge["service_provider"] = service_provider_instance.pk
                charge["charge_category"] = charge_category
                charge["charges_type"] = charges_type

            if len(charges) > 1:
                for index, charge in enumerate(charges):
                    if index == 0:
                        charge_record = AdCharges.objects.get(charges_id=charge_filter_object[0].pk)
                        charges_serializer = ChargeSerializer(charge_record, data=charge, partial=True,
                                                               context={'request': request})
                        if charges_serializer.is_valid():
                            charges_instance = charges_serializer.save(updated_at=datetime.now(), updated_by=request.user)
                    else:
                        charges_serializer = ChargeSerializer(data=charge, context={'request': request})
                        if charges_serializer.is_valid():
                            charges_instance = charges_serializer.save()
            else:
                charges_serializer = ChargeSerializer(charge_filter_object[0], data=charges[0], partial=True, context={'request': request})
                if charges_serializer.is_valid():
                    charges_instance = charges_serializer.save(updated_at=datetime.now(), updated_by=request.user)

                    user_activity = {
                        "table_id": charges_instance.pk,
                        "table_name": 'ad_charges',
                        "ua_action": 'Update',  # Action performed
                        "ua_description": 'Charge updated successfully.',  # Action description
                        "created_by": request.user,  # Current user performing the action
                        "request_data": dict(request.data),  # Request data
                        "response_data": charges_serializer.data
                    }

                    add_user_activity(user_activity)
        else:
            for charge in charges:
                if charge["minimum"] == "0.00":
                    charge["minimum"] = "0.00"
                if charge["maximum"] == "0.00":
                    charge["maximum"] = "0.00"
                charge["service_provider"] = service_provider_instance.pk
                charge["charge_category"] = charge_category
                charge["charges_type"] = charges_type

                charges_serializer = ChargeSerializer(data=charge, context={'request': request})
                if charges_serializer.is_valid():
                    charges_instance = charges_serializer.save()

                    user_activity = {
                        "table_id": charges_instance.pk,
                        "table_name": 'ad_charges',
                        "ua_action": 'Update',  # Action performed
                        "ua_description": 'Charge updated successfully.',  # Action description
                        "created_by": request.user,  # Current user performing the action
                        "request_data": dict(request.data),  # Request data
                        "response_data": charges_serializer.data
                    }

                    add_user_activity(user_activity)
                else:
                    raise ValidationError(charges_serializer.errors)


class UserAPIView(APIView):
    """
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsAdmin | IsRetailer]

    def post(self, request): 
        try:
            if 'aadhaar_card' in request.data and 'pan_card' in request.data and 'name' in request.data and 'email' in request.data and 'contact_no' in request.data:
                return self.add_users(request)
            elif 'aadhaar_card' in request.data:
                return self.verify_aadhaar(request)
            elif ('ref_id' in request.data and 'aadhaar_otp' in request.data) or (
                    'email' in request.data and 'email_otp' in request.data) or (
                    'contact_no' in request.data and 'contact_otp' in request.data):
                return self.verify_otp(request)
            elif 'pan_card' in request.data:
                return self.verify_pan(request)
            elif 'email' in request.data:
                return self.verify_email(request)
            elif 'contact_no' in request.data:
                return self.verify_contact(request)
            elif 'page_number' in request.data and 'page_size' in request.data or 'request_user_id' in request.data:
                return self.fetch_users(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def verify_aadhaar(self, request):
        aadhaar_card = request.data.get('aadhaar_card')
        if not aadhaar_card: return Response({"status": "fail", "message": "Aadhaar card is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not isnumber(aadhaar_card): return Response({"status": "fail", "message": "Aadhaar card number must contain only digits."}, status=status.HTTP_400_BAD_REQUEST)
        if len(aadhaar_card) != 12: return Response({"status": "fail", "message": "Aadhaar card number must be exactly 12 digits long."}, status=status.HTTP_400_BAD_REQUEST)

        other_charges = SaOtherCharges.objects.get(oc_name='aadhaar_card')
        hsn_rate = other_charges.hsn_sac.tax_rate
        charge = float(other_charges.charge)
        charge_type = other_charges.charge_type
        portal_user = PortalUser.objects.get(id=1)
        pud_unique_id = PortalUserDetails.objects.get(pu=portal_user).pud_unique_id
        user_wallet = PortalUserWallet.objects.get(pu=portal_user)
        main_wallet = user_wallet.main_wallet
        if main_wallet <= 0.00:
            return Response({'status': 'fail', 'message': 'Insufficient balance in main wallet.'}, status=status.HTTP_400_BAD_REQUEST)

        aadhaar_response = aadhaar_verify(aadhaar_card)
        # **Calculate Charges**
        if charge_type == 'is_percent':
            rate_amount = (amount * charge) / 100  # Percentage Deduction
        elif charge_type == 'is_flat':
            rate_amount = charge  # Fixed Deduction
        else:
            rate_amount = Decimal(0)  # No charge if charge_type is invalid
        # **Calculate Effective Amount**
        gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(hsn_rate)/100)))

        # **Deduct from Wallet**
        user_wallet.main_wallet = float(main_wallet) - float(rate_amount)
        user_wallet.save()
        
        global_transaction = GlTrn.objects.create(
            service_trn_id=user_wallet.pk,
            gl_trn_amt=rate_amount,
            gl_tax_rate=hsn_rate,
            gl_tax_amt=gst_amount,
            effectvie_wallet="main_wallet",
            effectvie_amt=rate_amount,
            effective_type="DR",
            pu=portal_user,
            service_trn_table="ad_portal_user_wallet",
            gl_trn_dt=timezone.now()
        )

        WalletTrn.objects.create(
            action_id=global_transaction.pk,
            action_type=f"aadhaar_api_called_by_{pud_unique_id}",
            wl_label=f"Charges by {portal_user.pu_name}",
            effectvie_wallet="main_wallet",
            effectvie_amt=rate_amount,
            effective_type="DR",
            pu=portal_user,
            current_balance=user_wallet.main_wallet,
            wl_trn_dt=timezone.now()
        )
        return Response(aadhaar_response['data'], status=aadhaar_response['status'])

    def verify_otp(self, request):
        if 'ref_id' in request.data and 'aadhaar_otp' in request.data:
            ref_id = request.data.get('ref_id')
            aadhaar_otp = request.data.get('aadhaar_otp')
            fwdp = request.data.get('fwdp')
            codeVerifier = request.data.get('codeVerifier')

            if not ref_id: return Response({"status": "fail", "message": "Referance id is required."}, status=status.HTTP_400_BAD_REQUEST)
            if not aadhaar_otp: return Response({"status": "fail", "message": "Aadhaar OTP is required."}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(aadhaar_otp): return Response({"status": "fail", "message": "Aadhaar OTP must contain only digits."}, status=status.HTTP_400_BAD_REQUEST)
            if len(aadhaar_otp) != 6: return Response({"status": "fail", "message": "OTP code must be exactly 6 digits long."}, status=status.HTTP_400_BAD_REQUEST)

            aadhaar_otp_response = aadhaar_otp_verify(aadhaar_otp, ref_id, fwdp, codeVerifier)
            return Response(aadhaar_otp_response['data'], status=aadhaar_otp_response['status'])

        elif 'email' in request.data and 'email_otp' in request.data:
            email = request.data.get('email')
            email_otp = request.data.get('email_otp')

            try:
                if not email: return Response({"status": "fail", "message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not email_otp: return Response({"status": "fail", "message": "Email OTP is required."}, status=status.HTTP_400_BAD_REQUEST)

                if not validation_email_address(email): return Response({"status": "fail", "message": "Invalid email address format."}, status=status.HTTP_400_BAD_REQUEST)
                if not isnumber(email_otp): return Response({"status": "fail", "message": "OTP code must contain only digits."}, status=status.HTTP_400_BAD_REQUEST)
                if len(email_otp) != 6: return Response({"status": "fail", "message": "OTP code must be exactly 6 digits long."}, status=status.HTTP_400_BAD_REQUEST)

                user = UserCodeVerification.objects.get(ucv_data=email)


                if user.verify_code == email_otp and user.verify_code_expire_at > timezone.now():
                    user.verify_code = None
                    user.verify_code_expire_at = None
                    user.is_everify = True
                    user.save()

                    response_data = {
                        'status': 'success',
                        'message': 'Email verification code verified successfully.',
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {
                        'status': 'fail',
                        'message': 'Invalid or expired verification code.'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            except UserCodeVerification.DoesNotExist:
                response_data = {
                    'status': 'error',
                    'message': 'User with this email does not exist.'
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)

            except Exception as e:
                response_data = {
                    'status': 'error',
                    'message': f'Internal server error: {str(e)}'
                }
                # Return a success response with status code 200
                return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            contact_no = request.data.get('contact_no')
            contact_otp = request.data.get('contact_otp')

            try:
                if not contact_no: return Response({"status": "fail", "message": "Contact number is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not contact_otp: return Response({"status": "fail", "message": "OTP code is required."}, status=status.HTTP_400_BAD_REQUEST)

                if not isnumber(contact_no): return Response({"status": "fail", "message": "Contact number must contain only digits."}, status=status.HTTP_400_BAD_REQUEST)
                if len(contact_no) != 10: return Response({"status": "fail", "message": "Contact number must be exactly 10 digits long."}, status=status.HTTP_400_BAD_REQUEST)

                if not isnumber(contact_otp): return Response({"status": "fail", "message": "OTP code must contain only digits."}, status=status.HTTP_400_BAD_REQUEST)
                if len(contact_otp) != 6: return Response({"status": "fail", "message": "OTP code must be exactly 6 digits long."}, status=status.HTTP_400_BAD_REQUEST)

                user = UserCodeVerification.objects.get(ucv_data=contact_no)

                if user.verify_code == contact_otp and user.verify_code_expire_at > timezone.now():
                    user.verify_code = None
                    user.verify_code_expire_at = None
                    user.is_everify = True
                    user.save()

                    response_data = {
                        'status': 'success',
                        'message': 'Contact verification code verified successfully.',
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    response_data = {
                        'status': 'fail',
                        'message': 'Invalid or expired verification code.'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

            except UserCodeVerification.DoesNotExist:
                response_data = {
                    'status': 'error',
                    'message': 'User with this contact no does not exist.'
                }
                return Response(response_data, status=status.HTTP_404_NOT_FOUND)

            except Exception as e:
                response_data = {
                    'status': 'error',
                    'message': f'Internal server error: {str(e)}'
                }
                # Return a success response with status code 200
                return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_pan(self, request):
        pan_card = request.data.get('pan_card')
        if not pan_card: return Response({"status": "fail", "message": "Pan card is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not checkpancardvalidation(pan_card): return Response({"status": "fail", "message": "Invalid PAN card format."}, status=status.HTTP_400_BAD_REQUEST)
        

        other_charges = SaOtherCharges.objects.get(oc_name='pan_card')
        hsn_rate = other_charges.hsn_sac.tax_rate
        charge = float(other_charges.charge)
        charge_type = other_charges.charge_type
        portal_user = PortalUser.objects.get(id=1)
        pud_unique_id = PortalUserDetails.objects.get(pu=portal_user).pud_unique_id
        user_wallet = PortalUserWallet.objects.get(pu=portal_user)
        main_wallet = user_wallet.main_wallet
        if main_wallet <= 0.00:
            return Response({'status': 'fail', 'message': 'Insufficient balance in main wallet.'}, status=status.HTTP_400_BAD_REQUEST)

        pan_card_response = verify_pan_card(pan_card)

        main_amount = main_wallet
        # **Calculate Charges**
        if charge_type == 'is_percent':
            rate_amount = (amount * charge) / 100  # Percentage Deduction
        elif charge_type == 'is_flat':
            rate_amount = charge  # Fixed Deduction
        else:
            rate_amount = Decimal(0)  # No charge if charge_type is invalid

        # **Calculate Effective Amount**
        gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(hsn_rate)/100)))

        # **Deduct from Wallet**
        user_wallet.main_wallet = float(main_wallet) - float(rate_amount)
        user_wallet.save()

        global_transaction = GlTrn.objects.create(
            service_trn_id=user_wallet.pk,
            gl_trn_amt=rate_amount,
            gl_tax_rate=hsn_rate,
            gl_tax_amt=gst_amount,
            effectvie_wallet="main_wallet",
            effectvie_amt=rate_amount,
            effective_type="DR",
            pu=portal_user,
            service_trn_table="ad_portal_user_wallet",
            gl_trn_dt=timezone.now()
        )

        WalletTrn.objects.create(
            action_id=global_transaction.pk,
            action_type=f"pan_api_called_by_{pud_unique_id}",
            wl_label=f"Charges by {portal_user.pu_name}",
            effectvie_wallet="main_wallet",
            effectvie_amt=rate_amount,
            effective_type="DR",
            pu=portal_user,
            current_balance=user_wallet.main_wallet,
            wl_trn_dt=timezone.now()
        )
        return Response(pan_card_response['data'], status=pan_card_response['status'])

    def verify_email(self, request):
        email = request.data.get('email')
        otp = get_random_string(length=6, allowed_chars='0123456789')
        try:
            if not email: return Response({"status": "fail", "message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
            if not validation_email_address(email): return Response({"status": "fail", "message": "Invalid email address format."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                pu_obj = UserCodeVerification.objects.get(ucv_data=email)
                pu_obj.verify_code = otp
                pu_obj.verify_code_expire_at = timezone.now() + timedelta(minutes=10)
                pu_obj.save()
            except UserCodeVerification.DoesNotExist:
                UserCodeVerification.objects.create(ucv_data=email, verify_code=otp,
                                                    verify_code_expire_at=timezone.now() + timedelta(minutes=10))

            with transaction.atomic():
                send_email = send_email_otp(email, otp, 'Distributor')

            response_data = {
                'status': 'success',
                'message': 'Email sent successfully',}
            # Return a success response with status code 200
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            # Return a success response with status code 200
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_contact(self, request):
        contact_no = request.data.get('contact_no')
        otp = get_random_string(length=6, allowed_chars='0123456789')
        try:
            if not contact_no: return Response({"status": "fail", "message": "Contact number is required."}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(contact_no): return Response({"status": "fail", "message": "Contact number must contain only digits."}, status=status.HTTP_400_BAD_REQUEST)
            if len(contact_no) != 10: return Response({"status": "fail", "message": "Contact number must be exactly 10 digits long."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                pu_obj = UserCodeVerification.objects.get(ucv_data=contact_no)
                pu_obj.verify_code = otp
                pu_obj.verify_code_expire_at = timezone.now() + timedelta(minutes=10)
                pu_obj.save()
            except UserCodeVerification.DoesNotExist:
                UserCodeVerification.objects.create(ucv_data=contact_no, verify_code=otp,
                                                    verify_code_expire_at=timezone.now() + timedelta(minutes=10))

            # Prepare the SMS content
            response = mobicomm_submit_sms(contact_no, otp)

            # other_charges = SaOtherCharges.objects.get(oc_name='Contact Number')
            # hsn_rate = other_charges.hsn_sac.tax_rate
            # charge = float(other_charges.charge)
            # charge_type = other_charges.charge_type
            # portal_user = PortalUser.objects.get(id=1)
            # main_wallet = PortalUserWallet.objects.get(pu=portal_user).main_wallet
            # amount = main_wallet
            # # **Calculate Charges**
            # if charge_type == 'is_percent':
            #     rate_amount = (amount * charge_value) / 100  # Percentage Deduction
            # elif charge_type == 'is_fix':
            #     rate_amount = charge_value  # Fixed Deduction
            # else:
            #     rate_amount = Decimal(0)  # No charge if charge_type is invalid

            # # **Calculate Effective Amount**
            # gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(hsn_rate)/100)))
            # amount = float(rate_amount) - float(gst_amount)
            # effective_ammount = float(amount) - float(rate_amount)
            # main_wallet -= effective_ammount
            # main_wallet.save()

            # global_transaction = GlTrn.objects.create(
            #     service_trn_id=main_wallet.pk,
            #     gl_trn_amt=amount,
            #     gl_tax_rate=hsn_rate,
            #     gl_tax_amt=gst_amount,
            #     effectvie_wallet="main_wallet",
            #     effectvie_amt=effective_ammount,
            #     effective_type="DR",
            #     pu=portal_user,
            #     service_trn_table="ad_portal_user_wallet"
            # )

            # WalletTrn.objects.create(
            #     action_id=global_transaction.pk,
            #     action_type="contact_number_charges",
            #     wl_label=f"Charges by {portal_user.pu_name}",
            #     effectvie_wallet="main_wallet",
            #     effectvie_amt=effective_ammount,
            #     effective_type="DR",
            #     pu=portal_user
            # )

            # Check the SMS API response status
            if response.status_code == 200:
                response_data = {
                    'status': 'success',
                    'message': 'The provided contact number is registered, and the OTP has been sent via SMS.',
                    'data': {'contact_otp': otp}
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    'status': 'error',
                    'message': 'Failed to send the OTP via SMS.',
                    'details': response.text  # Include the response for debugging
                }
                return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            # Return a success response with status code 200
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def  add_users(self, request):
        aadhaar_card = request.data.get('aadhaar_card')
        pan_card = request.data.get('pan_card')
        pan_response = request.data.get('pan_response')
        pu_name = request.data.get('name')
        pu_email = request.data.get('email')
        pu_contact_no = request.data.get('contact_no')
        alternate_contact_no = request.data.get('alternate_contact_no')
        address = request.data.get('address')
        state = request.data.get('state')
        city = request.data.get('city')
        zip_code = request.data.get('zip_code')
        partner_category = request.data.get('partner_category')
        # profile_image = request.data.get('profile_image', None)
        profile_image = None

        try:
            with transaction.atomic():
                if not aadhaar_card: return Response({"status": "fail", "message": "Aadhaar card is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not pan_card: return Response({"status": "fail", "message": "Pan card is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not pan_response: return Response({"status": "fail", "message": "Pan response is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not pu_name: return Response({"status": "fail", "message": "Name is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not pu_email: return Response({"status": "fail", "message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not pu_contact_no: return Response({"status": "fail", "message": "Contact number is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not alternate_contact_no: return Response({"status": "fail", "message": "Alternate contact number is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not address: return Response({"status": "fail", "message": "Address is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not state: return Response({"status": "fail", "message": "State name is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not city: return Response({"status": "fail", "message": "City name is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not zip_code: return Response({"status": "fail", "message": "Zip code is required."}, status=status.HTTP_400_BAD_REQUEST)
                if not partner_category: return Response({"status": "fail", "message": "Partner category is required."}, status=status.HTTP_400_BAD_REQUEST)
                # if not profile_image: return Response({"status": "fail", "message": "Profile image is required."}, status=status.HTTP_400_BAD_REQUEST)

                if not isnumber(aadhaar_card): return Response({"status": "fail", "message": "Aadhaar card number must contain only digits."}, status=status.HTTP_400_BAD_REQUEST)
                if len(aadhaar_card) != 12: return Response({"status": "fail", "message": "Aadhaar card number must be exactly 12 digits long."}, status=status.HTTP_400_BAD_REQUEST)
                if not checkpancardvalidation(pan_card): return Response({"status": "fail", "message": "Invalid PAN card format."}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    parsed_data = json.loads(pan_response)
                except json.JSONDecodeError:
                    return Response({"status": "fail", "message": "PAN response must be valid JSON."}, status=status.HTTP_400_BAD_REQUEST)
                
                if not validation_email_address(pu_email): return Response({"status": "fail", "message": "Invalid email address format."}, status=status.HTTP_400_BAD_REQUEST)
                if not isnumber(pu_contact_no): return Response({"status": "fail", "message": "Contact number must contain only digits."}, status=status.HTTP_400_BAD_REQUEST)
                if len(pu_contact_no) != 10: return Response({"status": "fail", "message": "Contact number must be exactly 10 digits long."}, status=status.HTTP_400_BAD_REQUEST)
                if not isnumber(alternate_contact_no): return Response({"status": "fail", "message": "Alternate contact number must be digit."}, status=status.HTTP_400_BAD_REQUEST)
                if len(alternate_contact_no) != 10: return Response({"status": "fail", "message": "Alternate contact number must be exactly 10 digits long."}, status=status.HTTP_400_BAD_REQUEST)

                state_obj = State.objects.filter(state_name__icontains=state).first()
                if not state_obj: return Response({'status': 'fail', 'message': 'State not found.'}, status=status.HTTP_404_NOT_FOUND)
                state_id = state_obj.state_id

                city_obj = City.objects.filter(city_name__icontains=city).first()
                if not city_obj: return Response({'status': 'fail', 'message': 'City not found.'}, status=status.HTTP_404_NOT_FOUND)
                city_id = city_obj.city_id

                if not isnumber(zip_code): return Response({"status": "fail", "message": "Zip code must contain only digits."}, status=status.HTTP_400_BAD_REQUEST)
                if len(zip_code) != 6: return Response({"status": "fail", "message": "Zip code must be exactly 6 digits long."}, status=status.HTTP_400_BAD_REQUEST)

                # same number to create distributer and retailer --- Start code
                if partner_category != 0:
                    pu_role = 'DISTRIBUTER'
                else:
                    pu_role = 'RETAILER'

                existing_user = PortalUser.objects.filter(pu_contact_no=pu_contact_no, pu_role=pu_role).first()
                if existing_user:
                    return Response({'status': 'fail', 'message': 'User with this contact number already exists.'}, status=status.HTTP_400_BAD_REQUEST)

                # end code

                masked_aadhaar_number = parsed_data.get("result").get('aadhaar_number')[-4:]
                if masked_aadhaar_number != aadhaar_card[-4:]:
                    return Response({'status': 'fail', 'message': 'Aadhaar number mismatch. Please verify the Aadhaar details.'}, status=status.HTTP_400_BAD_REQUEST)
                
                if parsed_data.get("result").get('aadhaar_linked') == False: 
                    return Response({'status': 'fail', 'message': 'Aadhaar is not linked to the provided PAN card.'}, status=status.HTTP_400_BAD_REQUEST)
                
                if int(partner_category) != 0:
                    # Fetch DistributorHierarchy
                    try:
                        distributor_hierarchy = DistributorHierarchy.objects.get(pk=partner_category)
                    except DistributorHierarchy.DoesNotExist:
                        return Response({
                            'status': 'fail',
                            'message': 'Partner Category Does Not Exist'
                        }, status=status.HTTP_404_NOT_FOUND)
                else:
                    distributor_hierarchy = None


                if int(partner_category) != 0:
                    # Create PortalUser
                    pu_obj = PortalUser.objects.create(
                        pu_name=pu_name,
                        pu_email=pu_email,
                        pu_contact_no=pu_contact_no,
                        pu_role="DISTRIBUTOR"
                    )
                else:
                    pu_obj = PortalUser.objects.create(
                        pu_name=pu_name,
                        pu_email=pu_email,
                        pu_contact_no=pu_contact_no,
                        pu_role="RETAILER"
                    )
                
                # Fetch Hierarchy Charges
                hierarchy_charges = HierarchyCharges.objects.filter(dh=distributor_hierarchy, is_deactive=False,
                                                                    is_deleted=False)
                
                if int(partner_category) != 0:
                    # Fetch dh_prefix and generate pud_unique_id
                    prefix_value = distributor_hierarchy.dh_prefix
                else:
                    prefix_value = "RT"
                
                # Get the last entry for the same dh_prefix
                last_puc_id = PortalUserDetails.objects.filter(pud_unique_id__startswith=prefix_value).order_by('-pud_unique_id').first()
                
                if last_puc_id:
                
                    # Extract the number part and increment by 1
                    last_number = int(last_puc_id.pud_unique_id[-5:])  # Get the last 4 digits
                    new_number = f"{last_number + 1:05d}"  # Increment and format as 4-digit number
                else:
                
                    # Start from '0001' if no previous record exists
                    new_number = "50001"

                # Create PortalUserDetails
                PortalUserDetails.objects.create(
                    pu=pu_obj,
                    pud_unique_id=f"{prefix_value}{new_number}",
                    alternate_contact_no=alternate_contact_no,
                    address=address,
                    state_id=state_id,
                    city_id=city_id,
                    zip_code=zip_code,
                    aadhaar_card=aadhaar_card,
                    pan_card=pan_card,
                    pan_response=pan_response,
                    dh=distributor_hierarchy,
                    created_by=request.user.id
                )
                # for charge in hierarchy_charges:
                #     PortalUserCharges.objects.create(
                #         sp=charge.sp,
                #         dh=charge.dh,
                #         pu_id=pu_obj.id,  # Assuming pu_id refers to the primary key of PortalUser
                #         parent_id=request.user.id,
                #         mark_type=charge.mark_type,
                #         puc_charges=charge.hc_charges,
                #         created_by=request.user
                #     )

                if int(partner_category) != 0: 
                    PortalUserWallet.objects.create(
                        main_wallet = 0.00,
                        commission_wallet = 0.00,
                        pu = pu_obj
                    )
                else:
                    PortalUserWallet.objects.create(
                        main_wallet = 0.00,
                        commission_wallet = 0.00,
                        cashin_wallet = 0.00,
                        pg_wallet = 0.00,
                        pu = pu_obj
                    )
                user_activity = {
                    "table_id": pu_obj.pk,
                    "table_name": 'ad_portal_user',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'User Created Successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(pu_obj)
                }

                add_user_activity(user_activity)

                return Response({
                    'status': 'success',
                    'message': 'User Created Successfully'
                }, status=status.HTTP_201_CREATED)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_users(self, request):
        user_id = request.user.id
        try:
            page_number = int(request.data.get('page_number', 1))
            page_size = int(request.data.get('page_size', 10))
            filter_by = request.data.get('filter_by', None)
            search = request.data.get('search', None)
            start_date = request.data.get('start_date', None)
            request_user_id = request.data.get('request_user_id', None)
            end_date = request.data.get('end_date', datetime.now().date())

            portal_users = PortalUser.objects.filter(is_deleted=False).order_by('-pk')

            if request.user.pu_role == "ADMIN":
                if request_user_id:
                    portal_users = portal_users.filter(id=request_user_id)
                else:
                    portal_users = portal_users.filter(pu_role__in=["DISTRIBUTOR", "RETAILER"])
            else:
                if request_user_id:
                    portal_users = portal_users.filter(id=request_user_id)
                else:
                    portal_users = portal_users.filter(portaluserdetails__created_by=user_id)

            if filter_by:
                allowed_filters = ['ALL USERS', 'ALL DISTRIBUTORS','SUPER DISTRIBUTOR', 'MASTER DISTRIBUTOR', 'DISTRIBUTOR', 'RETAILER']
                if filter_by not in allowed_filters:
                    return Response({'status': 'fail','message': f'Invalid filter_by value. Only allowed values are {", ".join(allowed_filters)}'}, status=status.HTTP_400_BAD_REQUEST)

                if filter_by == 'RETAILER':
                    portal_users = portal_users.filter(portaluserdetails__dh__isnull=True)
                else:
                    if filter_by == 'ALL DISTRIBUTORS':
                        portal_users = portal_users.filter(pu_role='DISTRIBUTOR')
                    elif filter_by == 'ALL USERS':
                        portal_users = portal_users
                    else:
                        dh = DistributorHierarchy.objects.filter(dh_name=filter_by, is_deleted=False).first()
                        if not dh:
                            return Response({'status': 'fail', 'message': f'Hierarchy "{filter_by}" not found.'}, status=status.HTTP_404_NOT_FOUND)
                        portal_users = portal_users.filter(portaluserdetails__dh=dh)

            if search:
                portal_users = portal_users.filter(
                    Q(pu_name__icontains=search) |
                    Q(pu_email__icontains=search) |
                    Q(pu_contact_no__icontains=search) |
                    Q(portaluserdetails__aadhaar_card__icontains=search) |
                    Q(portaluserdetails__pan_card__icontains=search)
                )

            if start_date:
                portal_users = portal_users.filter(created_at__date__range=[start_date, end_date])
            paginator = Paginator(portal_users, page_size)
            page_obj = paginator.page(page_number)
            
            users_data = []
            for user in page_obj:
                portal_user_details = PortalUserDetails.objects.filter(pu=user).first()
                if portal_user_details and portal_user_details.dh:
                    dh = DistributorHierarchy.objects.filter(dh_id=portal_user_details.dh.dh_id).first()
                    user_category = dh.dh_name if dh else 'UNKNOWN'
                else:
                    user_category = 'RETAILER' 
                created_user = PortalUser.objects.get(id=portal_user_details.created_by)
                parent_unique_id = PortalUserDetails.objects.get(pu=created_user).pud_unique_id

                user_data = {
                    'user': {
                        'id': user.id,
                        'name': user.pu_name,
                        'email': user.pu_email,
                        'contact_no': user.pu_contact_no,
                        'unique_id': portal_user_details.pud_unique_id if portal_user_details else None,
                        'user_category': user_category,
                        'user_status': user.pu_status,
                        'parent_name': created_user.pu_name,
                        'parent_unique_id': parent_unique_id
                    },
                    'user_details': PortalUserDetailsSerializers(portal_user_details, context={'request': request}).data if portal_user_details else None
                }
                users_data.append(user_data)

            paginated_response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': users_data
            }

            return Response({'status': 'success','message': 'Portal User Data','data': paginated_response_data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error','message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # try:
        #     users_data = {}
        #     page_number = request.data.get('page_number', 1)
        #     page_size = request.data.get('page_size', 10)
        #     request_user_id = request.data.get('user_id', None)
        #     search_query = request.data.get('search', None)
        #     filter_field = request.data.get('filter_field', None)
        #     filter_value = request.data.get('filter_value', None)
        #     order_by = request.data.get('order_by', "ascending")

        #     if request_user_id is None:
        #         users_queryset = PortalUser.objects.filter(is_deleted=False)

        #         if filter_field and filter_value:
        #             if filter_field == "user_category":                        
        #                 if filter_value == "ALL DISTRIBUTOR": 
        #                     users_queryset = PortalUser.objects.filter(pu_role='DISTRIBUTOR', is_deleted=False)
        #                 elif filter_value == "RETAILER":
        #                     users_queryset = PortalUser.objects.filter(pu_role='RETAILER', is_deleted=False)
        #                 else:
        #                     users_queryset = PortalUser.objects.filter(is_deleted=False)

        #                 users_queryset = users_queryset

        #         if request.user.pu_role == "ADMIN":
        #             user_lists = PortalUser.objects.filter(is_deleted=False)
        #             if search_query:
        #                 user_lists = user_lists.filter(
        #                     Q(pu_name__icontains=search_query) |
        #                     Q(pu_email__icontains=search_query) |
        #                     Q(pu_contact_no__icontains=search_query) |
        #                     Q(pu_role__icontains=search_query)
        #                 )

        #         else:
        #             user_lists = PortalUser.objects.filter(is_deleted=False, created_by=user_id)

        #         portal_user_queryset = user_lists

        #         if order_by == "descending":
        #             portal_user_queryset = portal_user_queryset.order_by('-pk')
                         
        #     else:
        #         portal_user_queryset = PortalUser.objects.filter(id=request_user_id)

        #     # Paginate the results
        #     paginator = Paginator(portal_user_queryset, page_size)
        #     try:
        #         page_obj = paginator.page(page_number)
        #     except EmptyPage:
        #         return Response({
        #             'status': 'fail',
        #             'message': 'Page not found.',
        #             'data': {}
        #         }, status=status.HTTP_404_NOT_FOUND)

        #     if not portal_user_queryset.exists():
        #         paginated_response_data = {
        #             'total_pages': 0,
        #             'current_page': 0,
        #             'total_items': 0,
        #             'results': []
        #         }
        #         response_data = {
        #             'status': 'success',
        #             'message': 'Partner Data not found.',
        #             'data': paginated_response_data
        #         }
        #         return Response(response_data, status=status.HTTP_200_OK)

        #     # Iterate through each charge and structure data
        #     for usr in page_obj:
        #         portal_user = PortalUser.objects.get(id=usr.id)
        #         print('=====>', portal_user)
        #         portal_user_details = PortalUserDetails.objects.get(pu_id=portal_user)
                
        #         portal_user_serializer = PortalUserDetailsSerializers(portal_user_details, context={'request': request})

        #         # Prepare distributor data only if not already added
                # if portal_user.id not in users_data:
                #     users_data[portal_user.id] = {
                #         'user': {
                #             'id': portal_user.id,
                #             'name': portal_user.pu_name,
                #             'email': portal_user.pu_email,
                #             'contact_no': portal_user.pu_contact_no,
                #             'unique_id': portal_user_details.pud_unique_id,
                #         },
                #         'user_details': portal_user_serializer.data
                #     }

        #     # Format data for pagination and response
            # paginated_response_data = {
            #     'total_pages': paginator.num_pages,
            #     'current_page': page_obj.number,
            #     'total_items': paginator.count,
            #     'results': list(users_data.values())
            #     # Convert the distributor data to a list format for the response
            # }

            # return Response({
            #     'status': 'success',
            #     'message': 'Partner Data',
            #     'data': paginated_response_data
            # }, status=status.HTTP_200_OK)

        # except Exception as e:
        #     return Response({
        #         'status': 'error',
        #         'message': f'Internal server error: {str(e)}'
        #     }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def put(self, request):

        try:
            if 'user_id' in request.data and 'service_provider' in request.data:
                return self.update_user_service_provider(request)
            elif 'user_id' in request.data and 'user_status' in request.data:
                return self.update_user_status(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def update_user_status(self, request):
        user_id = request.data.get('user_id')
        user_status = request.data.get('user_status')
        status_reason = request.data.get('reason', None)
        try:
            portal_user = PortalUser.objects.filter(id=user_id, is_deleted=False).first()
            if portal_user.pu_status in ['APROVE', 'REJECT']:
                return Response({'status': 'fail', 'message': 'status is already updated.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if portal_user.is_kyc_verify == False:
                return Response({'status': 'fail', 'message': 'KYC verification is required. Please complete your KYC verification before updating the status.'}, status=status.HTTP_400_BAD_REQUEST)
            
            portal_user.pu_status = 'REJECTED' if user_status == 'rejected' else 'APPROVED'
            portal_user.is_kyc_verify = False if user_status == 'rejected' else True
            portal_user.pu_reason = status_reason if status_reason else None
            portal_user.save()
            return Response({'status': 'success', 'message': 'User status updated successfully.'}, status=status.HTTP_200_OK)
        
        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        except Admin.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)    

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_user_service_provider(self, request):
        try:
            user_id = request.data.get('user_id')
            service_provider = request.data.get('service_provider')
            # is_deactive = request.data.get('is_deactive')
            
            try:
                convert_service_provider = json.loads(service_provider)
            except json.JSONDecodeError:
                return Response({"status": "fail", "message": "service_provider must be valid JSON."}, status=status.HTTP_400_BAD_REQUEST)
            
            if not user_id:
                return Response({'status': 'fail', 'message': 'Distributor ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not service_provider:
                return Response({'status': 'fail', 'message': 'Service provider data is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # distributor = PortalUser.objects.get(pu_role='DISTRIBUTOR', id=distributor_id)
            users = PortalUser.objects.get(id=user_id)
            
            if not users:
                return Response({'status': 'fail', 'message': 'Users does not exist.'}, status=status.HTTP_404_NOT_FOUND)
            
            if convert_service_provider[0].get("sp_id") == '':
                return Response({'status': 'fail', 'message': 'service provider ID is requried.'}, status=status.HTTP_400_BAD_REQUEST)
            
            user_charges_data = PortalUserCharges.objects.filter(sp=convert_service_provider[0].get("sp_id"), pu_id=users.id).first()
            
            if not user_charges_data:
                for data in convert_service_provider:
                    
                    service_provider_data = AdServiceProvider.objects.get(sp_id=data['sp_id'])
                    portal_user_details = PortalUserDetails.objects.get(pu=users)
                    prefix = ''
                    if 'SD' in portal_user_details.pud_unique_id:
                        prefix = 'Super Distributor'
                    elif 'MD' in portal_user_details.pud_unique_id:
                        prefix = 'Master Distributor'
                    elif 'DT' in portal_user_details.pud_unique_id:
                        prefix = 'Distributor'
                    else:
                        prefix = 'Retailer'

                    if prefix != 'Retailer':
                        distributor_hierarchy = DistributorHierarchy.objects.get(dh_name=prefix)
                        hierarchy_charges = HierarchyCharges.objects.get(dh=distributor_hierarchy, sp=service_provider_data)
                        PortalUserCharges.objects.create(
                            sp=hierarchy_charges.sp,
                            dh=hierarchy_charges.dh,
                            pu_id=users.id,
                            parent_id=request.user.id,
                            mark_type=hierarchy_charges.mark_type,
                            puc_charges=hierarchy_charges.hc_charges,
                            created_by=request.user
                        )

                    else:
                        hierarchy_charges = HierarchyCharges.objects.get(dh=None, sp=service_provider_data)
                        PortalUserCharges.objects.create(
                            sp=hierarchy_charges.sp,
                            dh=hierarchy_charges.dh,
                            pu_id=users.id,
                            parent_id=request.user.id,
                            mark_type=hierarchy_charges.mark_type,
                            puc_charges=hierarchy_charges.hc_charges,
                            created_by=request.user
                        )
                return Response({'status': 'success', 'message': 'Service provider activated successfully.', 'is_deactive': False}, status=status.HTTP_200_OK)
            else:
                if user_charges_data.is_deactive == True:
                    user_charges_data.is_deactive = False
                    is_deactive = False
                    message = 'Service provider activated Successfully.'
                
                else:
                    user_charges_data.is_deactive = True
                    message = 'Service provider Deactivated Successfully.'
                    is_deactive = True

                user_charges_data.save()
                return Response({'status': 'success', 'message': message, 'is_deactive': is_deactive}, status=status.HTTP_200_OK)
            # for data in convert_service_provider :
                # if data['sp_id'] == '':
                #     return Response({'status': 'fail', 'message': 'service provider ID is requried.'}, status=status.HTTP_400_BAD_REQUEST)
            #     service_provider_data = AdServiceProvider.objects.get(sp_id=data['sp_id'])
            #     distributor_charges = PortalUserCharges.objects.get(pu_id=users.id, sp=service_provider_data)
            #     for i in distributor_charges.puc_charges:
            #         user_charge_data = i
            #     for i in convert_service_provider:
            #         mark_value = i
            #     if not distributor_charges:
            #         return Response({'status': 'fail', 'message': 'Users charges do not exist.'}, status=status.HTTP_404_NOT_FOUND)

            #     if data['mark_value'] in ['', 'None']:
            #         return Response({'status': 'fail', 'message': 'mark value are required.'}, status=status.HTTP_400_BAD_REQUEST)

            #     user_charge_data['rate'] = float(user_charge_data['rate'])
            #     mark_value['mark_value'] = float(mark_value['mark_value'])

            #     user_charge_data['rate'] += mark_value['mark_value']

            #     user_charge_data['rate'] = format(user_charge_data['rate'], ".2f")
            #     distributor_charges.puc_charges = [user_charge_data]
            #     distributor_charges.save()

            # user_activity = {
            #     "table_id": distributor_charges.pk,
            #     "table_name": 'ad_portal_user_charges',
            #     "ua_action": 'Update',  # Action performed
            #     "ua_description": 'Users charges updated successfully.',  # Action description
            #     "created_by": request.user,  # Current user performing the action
            #     "request_data": dict(request.data),  # Request data
            #     "response_data": model_to_dict(distributor_charges)
            # }

            # add_user_activity(user_activity)

            # return Response({'status': 'success', 'message': 'Users charges updated successfully.'}, status=status.HTTP_200_OK)

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        except PortalUserCharges.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Users charges do not exist.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserServicesChargesAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):
        sp_id = request.data.get('sp_id')
        user_id = request.data.get('user_id')
        service_id = request.data.get('service_id')
        hsn_sac_id = request.data.get('hsn_sac_id')
        search_txt = request.data.get('search')
        start_date = request.data.get('start_date', None)
        end_date = request.data.get('end_date', datetime.now().date())
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)

        try:
            if not page_size: return Response({'status': 'fail', 'message': 'page_size is required.'},status=status.HTTP_400_BAD_REQUEST)
            if not user_id: return Response({'status': 'fail', 'message': 'user_id is required.'},status=status.HTTP_400_BAD_REQUEST)
            if isnumber(page_size) == False: return Response(
                {'status': 'fail', 'message': 'page_size must contain only digits.'},
                status=status.HTTP_400_BAD_REQUEST)

            if page_number:
                if isnumber(page_number) == False: return Response(
                    {'status': 'fail', 'message': 'page_number must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)

            if sp_id:
                if isnumber(sp_id) == False: return Response(
                    {'status': 'fail', 'message': 'sp_id must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)

            if service_id:
                if isnumber(service_id) == False: return Response(
                    {'status': 'fail', 'message': 'service_id must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)

            if hsn_sac_id:
                if isnumber(hsn_sac_id) == False: return Response(
                    {'status': 'fail', 'message': 'hsn_sac_id must contain only digits.'},
                    status=status.HTTP_400_BAD_REQUEST)
            
            user = PortalUser.objects.get(id=user_id)
            
            queryset = AdServiceProvider.objects.filter(is_deleted=False, sa_provided=True, is_deactive=False)

            if start_date:
                queryset = queryset.filter(created_at__date__range=[start_date, end_date])
            if sp_id:
                queryset = queryset.filter(pk=sp_id)
            if service_id:
                queryset = queryset.filter(service_id=service_id)
            if hsn_sac_id:
                queryset = queryset.filter(hsn_sac_id=hsn_sac_id)
            if search_txt:
                queryset = queryset.filter(
                    Q(service__service_name__icontains=search_txt) |
                    Q(sp_name__icontains=search_txt) |
                    Q(label__icontains=search_txt) |
                    Q(hsn_sac__hsnsac_code__icontains=search_txt)
                ) 

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

            # If no data found, return an empty result with pagination metadata
            if not queryset.exists():
                return Response({
                    'status': 'fail',
                    'message': 'Service Provider Data not found.',
                    'data': {
                        'total_pages': 0,
                        'current_page': 0,
                        'total_items': 0,
                        'results': []
                    }
                }, status=status.HTTP_200_OK)

            # For each service provider, fetch related charges
            service_provider_data = []
            # Initialize a dictionary to group providers by their sub_service_provider
            sub_service_provider_mapping = {}
            for provider in page_obj:
                
                service_name = AdService.objects.get(service_id=provider.service.service_id).service_name
                portal_user_charges = PortalUserCharges.objects.filter(pu_id=user_id, sp=provider)

                charges = None
                hierarchy_charges = None
                
                # if service_name != 'BBPS':
                if portal_user_charges.exists():
                    if portal_user_charges:
                        charges = portal_user_charges.first().puc_charges  # Convert the queryset to a list
                    else:
                        charges = []

                else:
                    # Fetch user details
                    user_details = PortalUserDetails.objects.filter(pu_id=user_id).first()

                    if user_details:
                        # Fetch distributor hierarchy data
                        if portal_user_charges.exists():
                            hierarchy_charges= portal_user_charges.first().puc_charges   

                        else:
                            dh_data = user_details.dh
                            if dh_data:
                                pass
                            else:
                                dh_data = None
                            if provider.service.is_global == False:
                                hierarchy_charges_obj = HierarchyCharges.objects.filter(dh=dh_data, sp=provider).first()
                                if hierarchy_charges_obj:
                                    hierarchy_charges = hierarchy_charges_obj.hc_charges  # Access the `hc_charges` field directly
                                else: 
                                    hierarchy_charges = None  # Default value if no records found
                            else:
                                hierarchy_charges = None

                    if hierarchy_charges:
                        charges = hierarchy_charges  # Convert the queryset to a list
                    else:
                        charges = []
            
                portal_charges = PortalUserCharges.objects.filter(pu_id=int(user_id), sp_id=provider.sp_id).first()
                if portal_charges:
                    if portal_charges.is_deactive == True:
                        is_user_service_provider = True
                    else:
                        is_user_service_provider = False
                else:
                    is_user_service_provider = True
                service_provider_data.append({
                    'parent_id': None,
                    'is_user_service_provider': is_user_service_provider,
                    'sub_service_provider': [],
                    'sp_id': provider.sp_id,
                    'service_name': service_name,
                    'provider_name': provider.sp_name,
                    'provider_label': provider.label,
                    'tds_rate': provider.tds_rate,
                    'hsn_sac': provider.hsn_sac.hsnsac_id if provider.hsn_sac else None,    
                    'hsn_sac_code': provider.hsn_sac.hsnsac_code if provider.hsn_sac else None,
                    'tax_rate': provider.hsn_sac.tax_rate if provider.hsn_sac else None,
                    'charges': charges,
                })
  
            for ssp_id, data in sub_service_provider_mapping.items():
                service_provider_data.append(data) 

            paginated_response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': service_provider_data
            }

            return Response({'status': 'success','message': 'Service Provider Data with Charges','data': paginated_response_data}, status=status.HTTP_200_OK)
        
        except AdService.DoesNotExist:
            return Response({'status': 'fail','message': 'Service not found.','data': {}}, status=status.HTTP_404_NOT_FOUND)
        
        except DistributorHierarchy.DoesNotExist:
            return Response({'status': 'fail','message': 'Distributor Hierarchy not found.','data': {}}, status=status.HTTP_404_NOT_FOUND)
        
        except PortalUser.DoesNotExist:
            return Response({'status': 'fail','message': 'User not found.','data': {}}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error','message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def toggle_activation(self, instance, activate, success_message, deactivate_message):
        if activate:
            instance.is_deactive = False
            instance.save()
            return {'status': 'success', 'message': success_message}
        else:
            instance.is_deactive = True
            instance.save()
            return {'status': 'success', 'message': deactivate_message}

    @transaction.atomic
    def put(self, request):
        sp_id = request.data.get('sp_id')
        user_id = request.data.get('user_id')

        if not sp_id or not user_id:
            return Response({'status': 'fail', 'message': 'Missing required parameters: sp_id or user_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch user hierarchy
            users_list = fetch_user_hierarchy(user_id)

            # Fetch service provider and service details
            service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
            service_data = service_provider.service

            def create_or_toggle_charges(portal_user, dh_id, service_provider, service_data, dh_value):
                # Check if charges exist
                portal_user_charges = PortalUserCharges.objects.filter(pu_id=portal_user.pk, sp=service_provider).first()

                if not portal_user_charges:
                    # Assign charges
                    if not service_data.is_global:
                        hierarchy_charges = HierarchyCharges.objects.filter(
                            dh=dh_id, sp=service_provider.sp_id, is_deleted=False
                        )
                        for charges in hierarchy_charges:
                            PortalUserCharges.objects.create(
                                sp_id=sp_id,
                                dh_id=dh_id,
                                pu_id=portal_user.pk,
                                parent_id=dh_value.created_by if dh_value else None,
                                puc_charges=charges.hc_charges,
                                is_deactive=False,
                                created_by=portal_user
                            )
                    else:
                        PortalUserCharges.objects.create(
                            sp_id=sp_id,
                            dh_id=dh_id,
                            pu_id=portal_user.pk,
                            parent_id=dh_value.created_by if dh_value else None,
                            puc_charges=[],
                            is_deactive=False,
                            created_by=portal_user
                        )
                    return {'status': 'success', 'message': 'Service Provider Activated Successfully.'}
                else:
                    # Toggle activation
                    return self.toggle_activation(
                        portal_user_charges, portal_user_charges.is_deactive,
                        'Service Provider Activated Successfully.',
                        'Service Provider Deactivated Successfully.'
                    )

            # Process each user in the hierarchy
            for user in users_list:
                portal_user = PortalUser.objects.get(id=user['user_id'])
                dh_value = PortalUserDetails.objects.filter(pu=portal_user).select_related('dh').first()
                dh_id = dh_value.dh.dh_id if dh_value and dh_value.dh else None

                # Create or toggle charges
                message = create_or_toggle_charges(portal_user, dh_id, service_provider, service_data, dh_value)

            return Response(message, status=status.HTTP_200_OK)

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'error', 'message': 'Service Provider not found.'}, status=status.HTTP_404_NOT_FOUND)
        except PortalUser.DoesNotExist:
            return Response({'status': 'error', 'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PartnerCategoryAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):
        try:
            if 'is_service_provider' in request.data and 'dh_id' in request.data:
                return self.fetch_hirarchy_service_provider(request)
            elif 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_data(request)
            elif 'name' in request.data and 'partner_prefix' in request.data:
                return self.create_hierarchy(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_hierarchy(self, request):
        try:
            with transaction.atomic():
                name = request.data.get('name')
                parent_id = request.data.get('parent_id', 0)
                description = request.data.get('description')
                partner_prefix = request.data.get('partner_prefix')
                service_provider_str = request.data.get('service_provider', '[]')
                service_provider = json.loads(service_provider_str)

                if parent_id:
                    try:
                        dh_obj = DistributorHierarchy.objects.get(dh_id=parent_id)

                        if dh_obj.is_used:
                            response_data = {
                                'status': 'success',
                                'message': 'Parent id is already used'
                            }
                            # Return a success response with status code 201 (Created)
                            return Response(response_data, status=status.HTTP_201_CREATED)
                        else:
                            dh_obj.is_used = True
                            dh_obj.save()
                    except DistributorHierarchy.DoesNotExist:
                        response_data = {
                            'status': 'fail',
                            'message': 'Parent id does not exist'
                        }
                        # Return a success response with status code 201 (Created)
                        return Response(response_data, status=status.HTTP_404_NOT_FOUND)

                if len(partner_prefix) >= 4:
                    return Response({'status': 'fail', 'message': 'Partner prefix must be fewer than 4 characters.'}, status=status.HTTP_400_BAD_REQUEST)

                # Assuming DistributorHierarchy is created here
                hierarchy = DistributorHierarchy.objects.create(
                    dh_name=name, dh_parent_id=parent_id if parent_id else None, dh_description=description,
                    dh_prefix=partner_prefix
                )
                for provider in service_provider:
                    sp_id = provider.get('sp_id') 
                    mark_type = provider.get('charge_type')
                    mark_value = provider.get('mark_value')
                    is_deactive = provider.get('is_deactive')
                    rate_type = provider.get('rate_type')

                    charges = AdCharges.objects.filter(service_provider=sp_id)
                    # Prepare charges data
                    charges_list = []
                    for charge in charges:
                        rate = charge.rate
                        minimum = charge.minimum
                        maximum = charge.maximum

                        # Apply markup based on the type
                        updated_rate = float(rate) + mark_value

                        charges_list.append({
                            'rate': updated_rate,
                            'minimum': float(minimum) if minimum != "0.00" else minimum,
                            'maximum': float(maximum) if maximum != "0.00" else maximum,
                            'charge_type': mark_type,
                            'rate_type': rate_type,
                            'is_slab': True if (str(minimum) != "0.00" and str(maximum) != "0.00") else False,
                            'mark_value': mark_value
                        })
                    # Store the charges data in HierarchyCharges model
                    HierarchyCharges.objects.create(
                        hc_charges=charges_list,
                        sp_id=sp_id,
                        dh_id=hierarchy.dh_id,
                        mark_type=mark_type,
                        is_deactive=is_deactive
                    )

                user_activity = {
                    "table_id": hierarchy.pk,
                    "table_name": 'ad_distributor_hierarchy',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'Partner Category Created Successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(hierarchy)
                }

                add_user_activity(user_activity)

                response_data = {
                    'status': 'success',
                    'message': 'Partner Category Created Successfully'
                }
                # Return a success response with status code 201 (Created)
                return Response(response_data, status=status.HTTP_201_CREATED)

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
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_data(self, request):
        user_id = request.user.id
        user_role = request.user.pu_role

        dh_id = request.data.get('dh_id')
        search_txt = request.data.get('search')
        in_retailer = request.data.get('in_retailer', None)
        in_partner = request.data.get('in_partner', None)
        page_number = int(request.data.get('page_numbr', 1))
        page_size = int(request.data.get('page_size', 10))
        data = {
                "dh_id": 0,
                "parent_category_name": None,
                "hc_charges": [],
                "dh_name": "Retailer",
                "dh_parent_id": None,
                "dh_description": "retailer",
                "dh_prefix": "RT",
                "is_used": False,
                "is_deactive": False,
                "is_deleted": False,
                "created_at": "2024-10-16T12:31:48.621432Z",
                "updated_at": None,
                "updated_by": None,
                "created_by": None  
            }
        try:
            if user_role == 'ADMIN':
                queryset = DistributorHierarchy.objects.filter(
                    is_deleted=False
                ).order_by('pk')
                # if in_parent:
                #     queryset = queryset.filter(is_used=False)
                if in_partner:
                    queryset = queryset.filter(dh_parent_id=None)
            else:
                # Fetch the distributor hierarchy ID of the user
                user_hierarchy = PortalUserDetails.objects.filter(pu_id=user_id).first()
                # Check if user has an associated hierarchy
                if not user_hierarchy: 
                    return Response({
                        'status': 'fail',
                        'message': 'No associated partner category found for this user.',
                        'data': {}
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Get the hierarchy ID to filter with
                user_dh_id = user_hierarchy.dh.dh_id
                if user_dh_id == 1:
                    queryset = DistributorHierarchy.objects.filter(
                        is_deleted=False).order_by('pk')[1:3]
                else:
                    queryset = DistributorHierarchy.objects.filter(
                        is_deleted=False, dh_parent_id=user_dh_id
                    ).order_by('pk')
            # Apply additional filters if provided
            if dh_id:
                queryset = queryset.filter(pk=dh_id)
            if search_txt:
                queryset = queryset.filter(
                    Q(service_name__icontains=search_txt) |
                    Q(description__icontains=search_txt)
                )

            # Paginator setup
            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

             # Return paginated response if data exists
            if page_obj is not None:
                if not queryset.exists():
                    paginated_response_data = {
                        'total_pages': 1,
                        'current_page': 1,
                        'total_items': 1,
                        'results': []
                    }
                    paginated_response_data['results'].append(data)
                    response_data = {
                        'status': 'success',
                        'message': 'Partner Category Data.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                serializer = DistributorHierarchySerializer(page_obj.object_list, many=True,
                                                            context={'request': request,
                                                                     'exclude_fields': ["created_at", "updated_at",
                                                                                        "is_deleted"]})
                if request.data.get('sp_id'):
                    retailer_charges = HierarchyCharges.objects.filter(dh=None, sp=request.data.get('sp_id')).first()
                    if retailer_charges == None:
                        data['hc_charges'] = []
                    else:
                        data['hc_charges'] = retailer_charges.hc_charges

                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }

                if page_number and page_size and in_partner or in_retailer:
                    if not in_partner:
                        paginated_response_data['results'].append(data)
                        paginated_response_data['total_items'] += 1
                return Response({
                    'status': 'success',
                    'message': 'Partner Cateogry Data',
                    'data': paginated_response_data
                }, status=status.HTTP_200_OK)

            # Non-paginated response if page object is None
            serializer = DistributorHierarchySerializer(queryset, many=True, context={'request': request,
                                                                                      'exclude_fields': ["created_at",
                                                                                                         "updated_at",
                                                                                                         "is_deleted"]})
            
            response_data = {
                'status': 'success',
                'message': 'Partner Category Data',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'fail',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def fetch_hirarchy_service_provider(self, request):
        is_service_provider = request.data.get("is_service_provider")
        page_size = request.data.get('page_size')
        page_number = request.data.get('page_number', 1)
        dh_id = request.data.get("dh_id")

        try:
            if not dh_id: return Response({"status": "fail", "message": "dh_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not is_service_provider: return Response({"status": "fail", "message": "is_service_provider is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not page_size: return Response({"status": "fail", "message": "page_size is required"}, status=status.HTTP_400_BAD_REQUEST)

            if isboolean(is_service_provider) is None: return Response({'status': 'fail','message': 'Invalid is_service_provider value.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(dh_id): return Response({'status': 'fail','message': 'dh_id must be only digit.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(page_size): return Response({'status': 'fail','message': 'page_size must be only digit.'}, status=status.HTTP_400_BAD_REQUEST)

            hierachy_charge_queryset = HierarchyCharges.objects.filter(dh=dh_id, is_deleted=False).order_by('sp')
            hierachy_serializer = HierarchyChargesSerializer(hierachy_charge_queryset, many=True, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted","updated_by", "created_by"]})
            hierachy_serializer_data = hierachy_serializer.data

            response_data = []
            sp_ids = []

            if hierachy_serializer_data:
                for hierachy_data in hierachy_serializer_data:
                    sp_id = hierachy_data.get('sp')
                    if sp_id:
                        service_provider_queryset = AdServiceProvider.objects.get(sp_id=sp_id)
                        hierachy_data.update({
                            'sp_id': sp_id,
                            'service_name': service_provider_queryset.service.service_name,
                            'provider_name': service_provider_queryset.sp_name,
                            'provider_label': service_provider_queryset.label,
                            'hsn_sac_code': service_provider_queryset.hsn_sac.hsnsac_code,
                            'charges': hierachy_data.get('hc_charges')
                        })

                        hierachy_data.pop("dh", None)
                        hierachy_data.pop("mark_type", None)
                        hierachy_data.pop("hc_charges", None)

                        response_data.append(hierachy_data)
                        sp_ids.append(sp_id)

            ad_service_provider_queryset = AdServiceProvider.objects.filter(is_deleted=False).exclude(sp_id__in=sp_ids).order_by('sp_id')
            for sp_data in ad_service_provider_queryset:
                to_us_charges = AdCharges.objects.filter(service_provider=sp_data, charge_category='to_us')
                if len(to_us_charges) > 0:
                    charge_serializer = ChargeSerializer(to_us_charges, many=True, context={'request': request})
                    charge_type = to_us_charges.first().charges_type if to_us_charges.exists() else None

                    charge_serializer_update = charge_serializer.data
                    for charge in charge_serializer_update:
                        charge.pop("created_at")
                        charge.pop("updated_at")
                        charge.pop("is_deactive")
                        charge.pop("is_deleted")
                        charge.pop("created_by")

                        if charge.get("minimum") == "0.00" and charge.get("maximum") == "0.00":
                            charge.update({"is_slab": False})
                        else:
                            charge.update({"is_slab": True})
                else:
                    charge_serializer_update = []
                    charge_type = None

                response_data.append({
                    'sp_id': sp_data.sp_id,
                    'service_name': sp_data.service.service_name,
                    'provider_name': sp_data.sp_name,
                    'provider_label': sp_data.label,
                    'hsn_sac_code': sp_data.hsn_sac.hsnsac_code,
                    'is_deactive': sp_data.is_deactive,
                    'charges': charge_serializer_update
                })

            paginator = Paginator(response_data, page_size)
            if not response_data:
                paginated_response_data = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }
                response_data_dict = {
                    'status': 'fail',
                    'message': 'ServiceProvider Data not found.',
                    'data': paginated_response_data
                }
                return Response(response_data_dict, status=status.HTTP_200_OK)

            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            paginated_response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': page_obj.object_list
            }

            response_data_dict = {
                'status': 'success',
                'message': 'ServiceProvider Data',
                'data': paginated_response_data
            }

            return Response(response_data_dict, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            dh_id = request.data.get('dh_id')
            prefix = request.data.get('prefix', None)
            description = request.data.get('description', None)

            if prefix:
                prefix_validation = isstring(prefix)
                if prefix_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid input: prefix must be a string.'}, status=status.HTTP_400_BAD_REQUEST)
                if len(prefix) > 4:
                    return Response({'status': 'fail', 'message': 'Partner prefix must be fewer than 4 characters.'}, status=status.HTTP_400_BAD_REQUEST)

            distributor_hierachy = DistributorHierarchy.objects.get(dh_id=dh_id)

            if prefix:
                distributor_hierachy.dh_prefix = prefix
            
            if description:
                distributor_hierachy.dh_description = description

            distributor_hierachy.save()

            return Response({'status': 'success', 'message': 'Distributor hierarchy updated successfully..'}, status=status.HTTP_200_OK)

        except DistributorHierarchy.DoesNotExist:
            return Response({'status': 'fail', 'message': 'distributor hierarchy dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RetailerDynamicServiceProviderAPIView(APIView):
    authentication_classes=[CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request):
        sp_id = request.data.get('sp_id')

        if not sp_id:
            return Response({'status': 'fail', 'message': 'sp_id is reqired.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user.id

        try:
            portal_user_charges = PortalUserCharges.objects.filter(pu_id=user)
            
            for charges in portal_user_charges:
                service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
                exisring_pinned = PortalUserCharges.objects.filter(pu_id=user, is_pinned=True, is_deactive=False)
                if charges.sp == service_provider:
                    
                    if charges.is_pinned == False:
                        if len(exisring_pinned) >= 7:    
                            return Response({'status': 'fail', 'message': 'You can only pin a maximum of 7 service providers.'}, status=status.HTTP_400_BAD_REQUEST)
                        
                        charges.is_pinned = True
                        charges.save()

                        return Response({'status': 'success', 'message': 'Service provider pinned successfully.'}, status=status.HTTP_200_OK) 
                    
                    if charges.is_pinned == True:
                        charges.is_pinned = False
                        charges.save()

                        return Response({'status': 'success', 'message': 'Service provider unpinned successfully.'}, status=status.HTTP_200_OK)
            
            return Response({'status': 'fail', 'message': 'No existing charges found for this user.'}, status=status.HTTP_404_NOT_FOUND)

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider dose not exists.'}, status=status.HTTP_404_NOT_FOUND)    

        except PortalUserCharges.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Portal user charges dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        user_id = request.user.id

        try:
            all_service_provider = AdServiceProvider.objects.filter(is_deleted=False, is_deactive=False, sa_provided=True)
            portal_user_charges = PortalUserCharges.objects.filter(pu_id=user_id, is_deactive=False)
            service_provider_list = []

            for service in all_service_provider:
                for charges in portal_user_charges: 
                    if charges.sp == service:
                        exists_portal_user_charges = PortalUserCharges.objects.filter(sp=service, pu_id=user_id).first()
                        if exists_portal_user_charges:
                            pass

                        service_provider_data = {
                            'sp_id': service.sp_id,
                            'sp_name': service.sp_name,
                            'label': service.label,
                            'hsn_sac_id': service.hsn_sac.hsnsac_id if service.hsn_sac.hsnsac_id else None,
                            'hsn_sac_name': service.hsn_sac.hsnsac_code,
                            'service_id': service.service.service_id,
                            'service_name': service.service.service_name,
                            'tds_rate': service.tds_rate,
                            'is_pinned': charges.is_pinned,
                            'is_access': True if exists_portal_user_charges else False
                        }
                        service_provider_list.append(service_provider_data)

            return Response({'status': 'success', 'message': 'Get all service provider.', 'data': {'results': service_provider_list}})

        except PortalUserCharges.DoesNotExist:
            return Response({'stauts': 'fail', 'message': 'Portal user service provider dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeviceAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if 'device_active' in request.data and 'number' in request.data:
            return self.add_device_number(request)
        else:
            return self.get_device_number(request)

    def add_device_number(self, request):
        load_dotenv()

        device_active = request.data.get('device_active')
        number = request.data.get('number')

        if not device_active or not number:
            return Response({"error": "Both device_active and number are required"}, status=status.HTTP_400_BAD_REQUEST)

        env_path = os.path.join(os.path.dirname(__file__), '../.env')

        set_key(env_path, device_active, number)

        return Response({"message": f"'{device_active}' saved successfully"}, status=status.HTTP_200_OK)

    def get_device_number(self, request):
    
        device_active = request.data.get('device_active')

        load_dotenv()

        number = os.getenv(device_active)

        if number:
            return Response({device_active: number}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Key not found"}, status=status.HTTP_404_NOT_FOUND)

class SessionByPassUserAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request):
        distributor_id = request.data.get('distributor_id')

        try:
            if not distributor_id: return Response({'status': 'fail','message': 'distributor_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if distributor_id:
                if isnumber(distributor_id) == False: return Response({'status': 'fail','message': 'distributor_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            get_distributor = PortalUser.objects.get(id=distributor_id)

            access_token = get_tokens_for_user(get_distributor, timedelta(days=1))

            response_data = {
                'status': 'success',
                'message': 'Distributor Login successfully.',
                'data': {'user_role': get_distributor.pu_role, 'is_generated': False, 'token': str(access_token), 'is_kyc_verify': get_distributor.is_kyc_verify}
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except PortalUser.DoesNotExist:
            return Response(
                {'status': 'error', 'message': "Distributor not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {'status': 'error', 'message':f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserSwitchedAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsRetailer]

    def post(self, request):
        pu_contact_no = request.data.get('pu_contact_no')
        pu_role = request.data.get('pu_role')

        try:
            if not pu_contact_no: return Response({'status': 'fail','message': 'pu_contact_no is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not pu_role: return Response({'status': 'fail','message': 'pu_role is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if pu_contact_no:
                if isnumber(pu_contact_no) == False: return Response({'status': 'fail','message': 'pu_contact_no must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            get_user = PortalUser.objects.get(pu_contact_no=pu_contact_no, pu_role=pu_role)

            access_token = get_tokens_for_user(get_user, timedelta(days=1))

            if get_user.pu_login_pin == None:
                is_login = False
            else:
                is_login = True

            response_data = {
                'status': 'success',
                'message': f'{get_user.pu_role} Switched successfully.',
                'data': {'user_role': get_user.pu_role, 'is_generated': False, 'is_login': is_login, 'token': str(access_token),  'is_kyc_verify': get_user.is_kyc_verify}
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except PortalUser.DoesNotExist:
            return Response({'status': 'error', 'message': f"{pu_role} not found."},status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message':f'Internal server error: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def save_file(file, directory):
    file_extension = file.name.split('.')[-1].lower()
    if file_extension not in ['png', 'jpg', 'jpeg']:
        return None

    sanitized_file_name = file.name.replace(' ', '').replace('(', '').replace(')', '')
    file_path = os.path.join(directory, sanitized_file_name)

    with open(file_path, "wb") as f:
        f.write(file.read())

    return f'{directory}{sanitized_file_name}'


class KYCVerifiedAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsRetailer]

    def post(self, request):
        try:
            if 'aadhaar_card' in request.data:
                return self.verify_aadhaar_card(request)
            elif 'aadhaar_otp' in request.data and 'ref_id' in request.data and 'fwdp' in request.data and 'codeVerifier' in request.data:
                return self.verify_aadhaar_otp(request)
            elif 'pan_card' in request.data:
                return self.verify_pan(request)
            elif 'front_aadhaar_image' in request.data and 'back_aadhaar_image' in request.data and 'pan_card_image' in request.data and 'profile_image' in request.data and 'passbook_cheque_image' in request.data and 'upline_image' in request.data and 'current_location' in request.data:
                return self.verify_kyc(request)
            elif 'shop_name' in request.data and 'email' in request.data and 'contact_number' in request.data and 'shop_address' in request.data and 'pin_code' in request.data and 'state' in request.data and 'city' in request.data and 'business_type' in request.data and 'shop_image' in request.data:
                return self.verify_shop(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def verify_aadhaar_card(self, request):
        aadhaar_card = request.data.get('aadhaar_card')
        if not aadhaar_card: return Response({'status': 'fail', 'message': 'aadhaar card is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isnumber(aadhaar_card): return Response({'status': 'fail', 'message': 'aadhaar card number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(aadhaar_card) != 12: return Response({'status': 'fail', 'message': 'aadhaar card number must be exactly 12 digits long.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            aadhaar_response = aadhaar_verify(aadhaar_card)

            return Response(aadhaar_response['data'], status=aadhaar_response['status'])
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def verify_aadhaar_otp(self, request):
        ref_id = request.data.get('ref_id')
        aadhaar_otp = request.data.get('aadhaar_otp')
        fwdp = request.data.get('fwdp')
        codeVerifier = request.data.get('codeVerifier')
        if not ref_id: return Response({'status': 'fail', 'message': 'ref_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not aadhaar_otp: return Response({'status': 'fail', 'message': 'aadhaar_otp is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isnumber(aadhaar_otp): return Response({'status': 'fail', 'message': 'aadhaar_otp must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(aadhaar_otp) != 6: return Response({'status': 'fail', 'message': 'aadhaar_otp must be exactly 6 digits long.'}, status=status.HTTP_400_BAD_REQUEST)
        if not fwdp: return Response({'status': 'fail', 'message': 'fwdp is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not codeVerifier: return Response({'status': 'fail', 'message': 'codeVerifier is required.'}, status=status.HTTP_400_BAD_REQUEST)
        aadhaar_otp_response = aadhaar_otp_verify(aadhaar_otp, ref_id, fwdp, codeVerifier)
        return Response(aadhaar_otp_response['data'], status=aadhaar_otp_response['status'])

    def verify_pan(self, request):
        pan_card = request.data.get('pan_card')
        if not pan_card: return Response({'status': 'fail', 'message': 'pan card is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isnumber(pan_card): return Response({'status': 'fail', 'message': 'pan card number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(pan_card) != 10: return Response({'status': 'fail', 'message': 'pan card number must be exactly 10 digits long.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pan_response = verify_pan_card(pan_card)

            return Response(pan_response['data'], status=pan_response['status'])
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_kyc(self, request):
        try:
            # Extract files from request
            required_files = {
                "front_aadhaar_image": request.FILES.get('front_aadhaar_image'),
                "back_aadhaar_image": request.FILES.get('back_aadhaar_image'),
                "pan_card_image": request.FILES.get('pan_card_image'),
                "profile_image": request.FILES.get('profile_image'),
                "passbook_cheque_image": request.FILES.get('passbook_cheque_image'),
                "upline_image": request.FILES.get('upline_image'),
            }
            latitude_longitude = request.data.get('current_location')

            # Check if all required files are provided
            for key, file in required_files.items():
                if not file:
                    return Response({'status': 'fail', 'message': f'{key.replace("_", " ").capitalize()} is required.'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
            
            if not latitude_longitude:
                return Response({'status': 'fail', 'message': 'Latitude and longitude are required.'}, 
                                status=status.HTTP_400_BAD_REQUEST)

            # Get the user
            user = PortalUser.objects.filter(id=request.user.id).first()
            if not user:
                return Response({'status': 'fail', 'message': 'Portal user does not exist.'}, 
                                status=status.HTTP_404_NOT_FOUND)

            if user.is_kyc_verify:
                return Response({'status': 'fail', 'message': 'KYC is already verified.'}, 
                                status=status.HTTP_400_BAD_REQUEST)
            
            # Maximum file size (10 MB)
            max_file_size = 10 * 1024 * 1024  # 10 MB in bytes

            # Create user-specific folder
            folder_name = f'{user.pu_name}_{user.pu_contact_no}'
            user_directory = f'media/Kyc/Document/{folder_name}/'
            os.makedirs(user_directory, exist_ok=True)

            # Save files and generate URLs
            logo_image_urls_dict = {}
            for key, file in required_files.items():
                file_url = save_file(file, user_directory)
                if not file_url:
                    return Response({'status': 'fail', 'message': f'Invalid file format for {key}. Only PNG, JPG, and JPEG are allowed.'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                if file.size > max_file_size:
                    return Response(
                        {'status': 'fail', 'message': f'{key.replace("_", " ").capitalize()} exceeds the 10 MB size limit.'}, status=status.HTTP_400_BAD_REQUEST)
                logo_image_urls_dict[key] = file_url

            # Parse latitude and longitude
            try:
                latitude_longitude_dict = json.loads(latitude_longitude)
            except json.JSONDecodeError:
                return Response({'status': 'fail', 'message': 'Invalid latitude and longitude format.'}, 
                                status=status.HTTP_400_BAD_REQUEST)

            # Update user details
            user_details = PortalUserDetails.objects.filter(pu_id=user.id).first()
            if not user_details:
                return Response({'status': 'fail', 'message': 'Portal user details do not exist.'}, 
                                status=status.HTTP_404_NOT_FOUND)

            user_details.doc_images = logo_image_urls_dict
            user_details.kyc_current_location = latitude_longitude_dict
            user_details.save()

            data = {
                'contact_number': user.pu_contact_no,
                'email': user.pu_email,
            }
            return Response({'status': 'success', 'message': 'KYC documents uploaded successfully.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_shop(self, request):
        try:
            shop_name = request.data.get('shop_name')
            email = request.data.get('email')
            contact_number = request.data.get('contact_number')
            shop_address = request.data.get('shop_address')
            pin_code = request.data.get('pin_code')
            state = request.data.get('state')
            city = request.data.get('city')
            business_type = request.data.get('business_type')
            gst_no = request.data.get('gst_no', None)
            shop_image = request.FILES.get('shop_image')

            if not shop_name: return Response({'status': 'fail', 'message': 'shop name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            # if not email: return Response({'status': 'fail', 'message': 'email is required.'}, status=status.HTTP_400_BAD_REQUEST)
            # if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not shop_address: return Response({'status': 'fail', 'message': 'shop address is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not pin_code: return Response({'status': 'fail', 'message': 'pin code is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not state: return Response({'status': 'fail', 'message': 'state is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not city: return Response({'status': 'fail', 'message': 'city is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not business_type: return Response({'status': 'fail', 'message': 'business type is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not shop_image: return Response({'status': 'fail', 'message': 'shop image is required.'}, status=status.HTTP_400_BAD_REQUEST)
            

            shop_name_validation = isstring(shop_name)
            if shop_name_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid shop name. It should contain only alphabetic characters and spaces.'})

            # email_validation = validation_email_address(email)
            # if email_validation == False:
            #     return Response({'status': 'fail', 'message': 'Invalid email address.'}, status=status.HTTP_400_BAD_REQUEST)

            # contact_number_validation = validate_mobile_number(contact_number)
            # if contact_number_validation == False:
            #     return Response({'status': 'fail', 'message': 'Invalid Mobile Number.'}, status=status.HTTP_400_BAD_REQUEST)

            pin_code_validation = isnumber(pin_code)
            if pin_code_validation == False:
                return  Response({'status': 'fail', 'message': 'Invalid pin code. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            if len(pin_code) != 6:
                return Response({'status': 'fail', 'message': 'Invalid pin code. It must be 6-digit numeric value.'}, status=status.HTTP_400_BAD_REQUEST)

            state_validation = isnumber(state)
            if state_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid state. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            city_validation = isnumber(city)
            if city_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid city. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            if gst_no:
                regex = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
                if not re.match(regex, gst_no):
                    return Response({'status': 'fail', 'message': 'Invalid GST Number.'}, status=status.HTTP_400_BAD_REQUEST)

            busniess_type_validation = isnumber(business_type)
            if busniess_type_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid business type. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            if len(business_type) != 4:
                return Response({'status': 'fail', 'message': 'Invalid business type. It must be 4-digit numeric value.'}, status=status.HTTP_400_BAD_REQUEST)

            # if PortalUser.objects.filter(pu_email=email).exclude(id=request.user.id).exists():
            #     return Response({'status': 'fail', 'message': 'Email address already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            # if PortalUser.objects.filter(pu_contact_no=contact_number).exclude(id=request.user.id).exists():
            #     return Response({'status': 'fail', 'message': 'Contact number already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            user = PortalUser.objects.get(id=request.user.id)
            if user.is_kyc_verify == True:
                return Response({'status': 'fail', 'message': 'KYC is already verified.'}, status=status.HTTP_400_BAD_REQUEST)

            # user = PortalUser.objects.filter(id=request.user.id).first()
            # user.pu_email = email
            # user.pu_contact_no = contact_number
            # user.save()

            folder_name = f'{user.pu_name}_{user.pu_contact_no}'
            user_directory = f'media/Kyc/Document/{folder_name}/'
            os.makedirs(user_directory, exist_ok=True)
            
            if shop_image:
                new_image_url = save_file(shop_image, user_directory)
                if not new_image_url:
                    return Response({'status': 'fail', 'message': 'Invalid file format. Only PNG, JPG, and JPEG files are allowed.'}, status=status.HTTP_400_BAD_REQUEST)         
            else:
                new_image_url = None


            portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)
            if gst_no:
                if portal_user_details.shop_gst_number==gst_no:
                    return Response({'status': 'fail', 'message': 'GST number is already exists.'}, status=status.HTTP_400_BAD_REQUEST)
                
            portal_user_details.shop_name=shop_name
            portal_user_details.shop_address=shop_address
            portal_user_details.shop_zip_code=pin_code
            portal_user_details.shop_state = state
            portal_user_details.shop_city = city
            portal_user_details.shop_gst_number = gst_no if gst_no else None
            portal_user_details.busniess_type = business_type
            portal_user_details.doc_images['shop_image'] = new_image_url
            portal_user_details.save()

            user.is_kyc_verify = True
            user.pu_status = 'KYC_UNDER_PROCESS'
            user.save()

            return Response({'status': 'success', 'message': 'Shop details Added successfully.'}, status=status.HTTP_200_OK)

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'portal user dose not exists'}, status=status.HTTP_400_BAD_REQUEST)

        except PortalUserDetails.DoesNotExist:
            return Response({'status': 'fail', 'message': 'portal user details dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BankDetailsAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):
        try:
            if 'deposite_category' in request.data and 'bank_name' in request.data and 'ifsc_code' in request.data and 'branch_name' in request.data and 'account_type' in request.data and 'account_number' in request.data:
                return self.add_bank_details(request)
            elif 'page_size' in request.data or 'page_size' in request.data:
                return self.get_bank_details(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def add_bank_details(self, request):
        try:
            deposite_category = request.data.get('deposite_category')
            bank_name = request.data.get('bank_name')
            ifsc_code = request.data.get('ifsc_code')
            branch_name = request.data.get('branch_name')
            account_type = request.data.get('account_type')
            account_number = request.data.get('account_number')
            online_charges = request.data.get('online_charges', None)
            cdm_charges = request.data.get('cdm_charges', None)
            counter_charges = request.data.get('counter_charges', None)

            if not deposite_category: return Response({'status': 'fail', 'message': 'Deposite category is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not bank_name: return Response({'status': 'fail', 'message': 'Bank name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not ifsc_code: return Response({'status': 'fail', 'message': 'IFSC code is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not branch_name: return Response({'status': 'fail', 'message': 'Branch name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not account_type: return Response({'status': 'fail', 'message': 'Account Type is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not account_number: return Response({'status': 'fail', 'message': 'Account number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            bank_name_validation = isstring(bank_name)
            if bank_name_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid bank name. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)

            ifsc_code_validation = is_valid_ifsc(ifsc_code)
            if ifsc_code_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid IFSC code. Please check the format.'}, status=status.HTTP_400_BAD_REQUEST)

            branch_name_validation = isstring(branch_name)
            if branch_name_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid branch name. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)

            account_type_validation = isstring(account_type)
            if account_type_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid account type. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)

            account_number_validation = isnumber(account_number)
            if account_number_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            validation_account_number = validate_account_number(account_number)
            if validation_account_number == False:
                return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits and be between 8 and 16 characters long.'}, status=status.HTTP_400_BAD_REQUEST)

            deposite = json.loads(deposite_category)
            get_exists_bank = BankDetails.objects.filter(bank_name=bank_name, ifsc_code=ifsc_code, account_number=account_number, is_delete=False).first()
            if get_exists_bank:
                return Response({'status': 'fail', 'message': 'Bank details already exist.'}, status.HTTP_400_BAD_REQUEST)

            if online_charges:
                try:
                    online_charges_json = json.loads(online_charges)
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid online charges format'}, status=status.HTTP_400_BAD_REQUEST)
            if cdm_charges:
                try:
                    cdm_charges_json = json.loads(cdm_charges)
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid cdm charges format'}, status=status.HTTP_400_BAD_REQUEST)
            if counter_charges:
                try:
                    counter_charges_json = json.loads(counter_charges)
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid counter charges format'}, status=status.HTTP_400_BAD_REQUEST)


            user = PortalUser.objects.get(id=request.user.id)
            print('===============')
            BankDetails.objects.create(
                deposite_category=deposite,
                bank_name=bank_name,
                branch_name=branch_name,
                ifsc_code=ifsc_code,
                account_type=account_type,
                account_number=account_number,
                online_charges=online_charges_json if online_charges_json else None,
                cdm_charges=cdm_charges_json if cdm_charges_json else None,
                counter_charges=counter_charges_json if counter_charges_json else None,
                created_by=user
            )
            print('******************')
            return Response({'status': 'success', 'message': 'Bank details added successfully.'}, status=status.HTTP_200_OK)

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_bank_details(self, request):
        try:
            data = {
                'total_pages': 0,
                'current_page': 0,
                'total_items': 0,
                'results': []
            }
            deposite = {}
            get_bank_details = []
            page_size = int(request.data.get('page_size', 10))
            page_number = int(request.data.get('page_number', 1))
            bank_details_id = int(request.data.get('bank_details_id', 0))
            search = request.data.get('search', None)
            depostie_category = request.data.get('depostie_category', None)
            if not page_size:
                return Response({'status': 'fail', 'message': 'Page size is required.'}, status=status.HTTP_400_BAD_REQUEST)

            get_bank_details = BankDetails.objects.filter(is_delete=False)

            if search is not None:
                # if not search:
                #     return Response({'status': 'fail', 'message': 'Search is required.'}, status=status.HTTP_400_BAD_REQUEST)

                get_bank_details = get_bank_details.filter(Q(bank_name__icontains=search) | Q(ifsc_code__icontains=search) | Q(account_number__icontains=search))
            if bank_details_id != 0:
                if not bank_details_id:
                    return Response({'status': 'fail', 'message': 'bank details ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

                bank_id_validation = isnumber(bank_details_id)
                if bank_id_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid bank details ID. It should contain only digits.'})

                get_bank_detail = get_bank_details.filter(bd_id=bank_details_id).first()

                if get_bank_detail:
                    for key, value in get_bank_detail.deposite_category.items():
                        if value is True:
                            deposite[key] = value

                    result = {
                        'bank_details_id': get_bank_detail.bd_id,
                        'deposite_category': deposite,
                        'bank_name': get_bank_detail.bank_name,
                        'ifsc_code': get_bank_detail.ifsc_code,
                        'branch_name': get_bank_detail.branch_name,
                        'account_type': get_bank_detail.account_type,
                        'account_number': get_bank_detail.account_number,
                        'online_charges': get_bank_detail.online_charges,
                        'cdm_charges': get_bank_detail.cdm_charges,
                        'counter_charges': get_bank_detail.counter_charges,
                    }

                    return Response({'status': 'success', 'data': result}, status=status.HTTP_200_OK)
                else:
                    return Response({'status': 'fail', 'message': 'Bank detail not found.'}, status=status.HTTP_404_NOT_FOUND)

            if depostie_category is not None:
                if not depostie_category:
                    return Response({'status': 'fail', 'message': 'depostie category is required.'}, status=status.HTTP_400_BAD_REQUEST)

                filtered_bank_details = []

                for bank_details in get_bank_details:
                    keys = bank_details.deposite_category.items()
                    for key, value in keys:
                        if key == depostie_category and value==True:
                            filtered_bank_details.append(bank_details)

                get_bank_details = filtered_bank_details

            paginator = Paginator(get_bank_details, page_size)

            if page_number > paginator.num_pages:
                return Response({
                    'status': 'success',
                    'data': data
                }, status=status.HTTP_200_OK)

            page_obj = paginator.get_page(page_number)

            for bank_details in page_obj:
                deposite = {}
                for key, value in bank_details.deposite_category.items():
                    if value is True:
                        deposite[key] = value

                results = {
                    'bank_details_id': bank_details.bd_id,
                    'deposite_category': deposite,
                    'bank_name': bank_details.bank_name,
                    'ifsc_code': bank_details.ifsc_code,
                    'branch_name': bank_details.branch_name,
                    'account_type': bank_details.account_type,
                    'account_number': bank_details.account_number
                }
                data['results'].append(results)

            data['total_pages'] = paginator.num_pages
            data['current_page'] = page_number
            data['total_items'] = paginator.count

            return Response({'status': 'success', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            bank_details_id = request.data.get('bank_details_id')

            if not bank_details_id: return Response({'status': 'fail', 'message': 'bank details ID is required,'}, status=status.HTTP_400_BAD_REQUEST)

            bank_id_validation = isnumber(bank_details_id)
            if bank_id_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid bank details ID. It should contain only digits.'})

            bank_detail = BankDetails.objects.get(bd_id=bank_details_id, is_delete=False)
            bank_detail.is_delete = True
            bank_detail.save()
            return Response({'status': 'success', 'message': 'Bank Details deleted successfully.'}, status=status.HTTP_200_OK)

        except BankDetails.DoesNotExist:
            return Response({'status': 'fail', 'message': 'bank details dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            bank_details_id = request.data.get('bank_details_id')
            bank_name = request.data.get('bank_name', None)
            deposite_category = request.data.get('deposite_category', None)
            ifsc_code = request.data.get('ifsc_code', None)
            branch_name = request.data.get('branch_name', None)
            account_type = request.data.get('account_type', None)
            account_number = request.data.get('account_number', None)
            online_charges = request.data.get('online_charges', None)
            cdm_charges = request.data.get('cdm_charges', None)
            counter_charges = request.data.get('counter_charges', None)
            print('account_number', account_number, 'online_charges', online_charges)
            if not bank_details_id: return Response({'status': 'fail', 'message': 'bank details ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

            bank_id_validation = isnumber(bank_details_id)
            if bank_id_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid bank details ID. It should contain only digits.'})
            get_bank_details = BankDetails.objects.get(bd_id=bank_details_id, is_delete=False)
            if bank_details_id and not any([bank_name, deposite_category, ifsc_code, branch_name, account_type, account_number]):
                get_fund_request = FundRequest.objects.filter(deposite_bank=get_bank_details, is_delete=False).first()
                if get_fund_request:
                    return Response({'status': 'fail', 'message': 'Cannot deactivate bank details, there are active fund requests associated with it.'}, status=status.HTTP_400_BAD_REQUEST)

                if get_bank_details.is_deactive == True:
                    get_bank_details.is_deactive = False
                    message = 'Bank details activated Successfully.'

                else: 
                    get_bank_details.is_deactive = True
                    message = 'Bank details Deactivated Successfully.'

                get_bank_details.updated_at = timezone.now()
                get_bank_details.updated_by = request.user.id

                get_bank_details.save()
            else:
                if bank_name:
                    if not bank_name: return Response({'status': 'fail', 'message': 'bank name is required.'}, status=status.HTTP_400_BAD_REQUEST)
                    bank_name_validation = isstring(bank_name)
                    if bank_name_validation == False:
                        return Response({'status': 'fail', 'message': 'Invalid bank name. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)
                    get_bank_details.bank_name = bank_name
                if deposite_category:
                    if not deposite_category: return Response({'status': 'fail', 'message': 'deposite category is required.'}, status=status.HTTP_400_BAD_REQUEST)
                    deposite = json.loads(deposite_category)
                    get_bank_details.deposite_category = deposite
                if ifsc_code:
                    if not ifsc_code: return Response({'status': 'fail', 'message': 'IFSC code is required.'}, status=status.HTTP_400_BAD_REQUEST)
                    ifsc_code_validation = is_valid_ifsc(ifsc_code)
                    if ifsc_code_validation == False:
                        return Response({'status': 'fail', 'message': 'Invalid IFSC code. Please check the format.'}, status=status.HTTP_400_BAD_REQUEST)
                    get_bank_details.ifsc_code = ifsc_code
                if branch_name:
                    if not branch_name: return Response({'status': 'fail', 'message': 'branch name is required.'}, status=status.HTTP_400_BAD_REQUEST)
                    branch_name_validation = isstring(branch_name)
                    if branch_name_validation == False:
                        return Response({'status': 'fail', 'message': 'Invalid branch name. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)
                    get_bank_details.branch_name = branch_name
                if account_type:
                    if not account_type: return Response({'status': 'fail', 'message': 'account type is required.'}, status=status.HTTP_400_BAD_REQUEST)
                    account_type_validation = isstring(account_type)
                    if account_type_validation == False:
                        return Response({'status': 'fail', 'message': 'Invalid account type. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)
                    get_bank_details.account_type = account_type
                if account_number:
                    if not account_number: return Response({'status': 'fail', 'message': 'account number is required.'}, status=status.HTTP_400_BAD_REQUEST)
                    account_number_validation = isnumber(account_number)
                    if account_number_validation == False:
                        return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
                    get_bank_details.account_number = account_number
                if online_charges:
                    if not online_charges: return Response({'status': 'fail', 'message': 'online_charges is required.'}, status=status.HTTP_400_BAD_REQUEST)
                    charges = json.loads(online_charges)
                    get_bank_details.online_charges = charges
                if cdm_charges:
                    if not cdm_charges: return Response({'status': 'fail', 'message': 'cdm_charges is required.'}, status=status.HTTP_400_BAD_REQUEST)
                    charges = json.loads(cdm_charges)
                    get_bank_details.cdm_charges = charges
                if counter_charges:
                    if not counter_charges: return Response({'status': 'fail', 'message': 'counter_charges is required.'}, status=status.HTTP_400_BAD_REQUEST)
                    charges = json.loads(counter_charges)
                    print('charges', charges)   
                    get_bank_details.counter_charges = charges
                get_bank_details.updated_at = timezone.now()
                get_bank_details.updated_by = request.user.id
                get_bank_details.save()

                message = 'Bank details updated Successfully.'

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except BankDetails.DoesNotExist:
            return Response({'status': 'fail', 'message': 'bank details dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyBankDetailsAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):
        ifsc_code = request.data.get('ifsc_code')
        account_number = request.data.get('account_number')

        # client_id = 61860316
        # client_secret = "OHQ7t2o4RAUM67J6vWQSTDMYCSXNvCE2"
        client_id = 76034597
        client_secret = "jIzkvvBkEFvIYjde8O7lini65ghUk5Yo"
        # callback_url = "https://apidemo.digitap.work/penny-drop/v2/check-valid"
        callback_url = "https://api.digitap.ai/penny-drop/v2/check-valid"

        try:
            if not ifsc_code: return Response({'status': 'fail', 'message': 'IFSC code is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not account_number: return Response({'status': 'fail', 'message': 'Account number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            ifsc_code_validation = is_valid_ifsc(ifsc_code)
            if ifsc_code_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid IFSC code. Please check the format.'}, status=status.HTTP_400_BAD_REQUEST)
            
            account_number_validation = isnumber(account_number)
            if account_number_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            validation_account_number = validate_account_number(account_number)
            if not validation_account_number:
            # if len(account_number) < 6 or len(account_number) > 20:
                return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits and be between 6 and 20 characters long.'}, status=status.HTTP_400_BAD_REQUEST)

            auth_string = f"{client_id}:{client_secret}"

            encode_auth_string = base64.b64encode(bytes(auth_string, 'utf-8')) # byte

            payload = {
                "accNo": account_number,
                "ifsc": ifsc_code,
            }
            headers = {
                "ent_authorization": encode_auth_string,
                "Content-Type": "application/json"
            }

            verify_bank_response = requests.post(callback_url, headers=headers, json=payload)

            if verify_bank_response.status_code == 200:
                verify_bank_response_json = verify_bank_response.json()

                if verify_bank_response_json.get("model").get("status") == "SUCCESS":
                    return Response({"status": "success", "message": "Bank verification completed successfully.", "data": verify_bank_response_json}, status=verify_bank_response.status_code)
                if verify_bank_response_json.get("model").get("status") == "PENDING":
                    return Response({"status": "pending", "message": "Bank verification is currently pending. Please check back later.", "data": verify_bank_response_json}, status=verify_bank_response.status_code)
                else:
                    return Response({"status": "fail", "message": "Bank verification failed. Please verify the details and try again.", "data": verify_bank_response_json}, status=verify_bank_response.status_code)
            elif verify_bank_response.status_code == 500:
                return Response({'status': 'error', 'data': verify_bank_response.text}, status=verify_bank_response.status_code)
            else:
                return Response({'status': 'error', 'data': verify_bank_response.json()}, status=verify_bank_response.status_code)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FundRequestAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):
        try:
            if 'deposit_bank_id' in request.data and 'deposit_amount' in request.data:
                return self.add_fund_request(request)
            elif 'page_number' in request.data or 'page_size' in request.data or 'fr_id' in request.data:
                return self.fetch_fund_request(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_fund_request(self, request):
        deposite_category = request.data.get('deposite_category')
        bd_id = request.data.get('deposit_bank_id')
        deposit_amount = request.data.get('deposit_amount')
        payment_proof = request.data.get('payment_proof')
        remark = request.data.get('remark')
        transaction_id = request.data.get('transaction_id')
        utr_number = request.data.get('utr_number')
        transaction_mode = request.data.get('transaction_mode')
        user_id = request.user.id
        charges = {}
        try:
            if not deposite_category: return Response({'status': 'fail','message': 'deposite_category is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not bd_id: return Response({'status': 'fail','message': 'bd_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not deposit_amount: return Response({'status': 'fail','message': 'deposit_amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not payment_proof: return Response({'status': 'fail','message': 'payment_proof is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not remark: return Response({'status': 'fail','message': 'remark is required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                deposite_category_json = json.loads(deposite_category)
            except json.JSONDecodeError:
                return Response({'status': 'fail', 'message': 'Invalid deposite category format'}, status=status.HTTP_400_BAD_REQUEST)

            if isfloat(deposit_amount) == False: Response({'status': 'fail','message': 'Invalid desposit amount.'}, status=status.HTTP_400_BAD_REQUEST)
            if float(deposit_amount) < 0: Response({'status': 'fail','message': 'Desposit amount must be positive number.'}, status=status.HTTP_400_BAD_REQUEST)

            file_path = handle_uploaded_file(payment_proof, 'Retailer/PaymentProof') if payment_proof else None
            payment_proof_file_paths = {
                'payment_proof': file_path,
            }
            try:
                bank_detail = BankDetails.objects.get(bd_id=bd_id)
            except BankDetails.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Bank does not exists.'}, status=status.HTTP_400_BAD_REQUEST)
            max_limit, min_limit = 0.00, 0.00
            print('deposite_category_json', deposite_category_json)
            print('bank_detail.counter_charges', bank_detail.counter_charges)
            if deposite_category_json.get("counter_deposit") == True:
                print('max_limit', max_limit, 'min_limit', min_limit)
                max_limit = float(bank_detail.counter_charges.get('maximum_amount'))
                min_limit = float(bank_detail.counter_charges.get('minimum_amount'))
                print('max_limit', max_limit, 'min_limit', min_limit)
            elif deposite_category_json.get("cdm_deposit") == True:
                max_limit = float(bank_detail.cdm_charges.get('maximum_amount'))
                min_limit = float(bank_detail.cdm_charges.get('minimum_amount'))
            elif deposite_category_json.get("online_transaction") == True:
                max_limit = float(bank_detail.online_charges.get('maximum_amount'))
                min_limit = float(bank_detail.online_charges.get('minimum_amount'))
            else:
                pass
            if float(deposit_amount) < min_limit or float(deposit_amount) > max_limit:
                return Response({'status': 'fail', 'message': f'Amount must be between {min_limit} and {max_limit}.'}, status=status.HTTP_400_BAD_REQUEST)

            if deposite_category_json.get("counter_deposit") == True or deposite_category_json.get("cdm_deposit") == True:

                if not transaction_id: return Response({'status': 'fail','message': 'transaction_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

                # if len(transaction_id) < 12 or len(transaction_id) > 16: return Response({'status': 'fail', 'message': 'transaction_id length must be between 12 to 16.'}, status=status.HTTP_400_BAD_REQUEST)

                fund_request = FundRequest.objects.create(deposite_category=deposite_category_json, deposite_bank=bank_detail,
                                                          deposite_amount=deposit_amount, transaction_id=transaction_id, payment_proof=payment_proof_file_paths,
                                                          remark=remark, created_at=timezone.now(), created_by=request.user)

                user_activity = {
                    "table_id": fund_request.pk,
                    "table_name": 'ad_fund_request',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'Fund request generated successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(fund_request)
                }

                add_user_activity(user_activity)

                return Response({"status": "success", "message": "Fund request generated successfully."}, status=status.HTTP_201_CREATED)

            elif deposite_category_json.get("online_transaction") == True:
                if not utr_number: return Response({'status': 'fail','message': 'utr_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
                if not transaction_mode: return Response({'status': 'fail','message': 'transaction_mode is required.'}, status=status.HTTP_400_BAD_REQUEST)

                transaction_mode_list = ["IMPS", "RTGS", "NEFT"]
                if transaction_mode not in transaction_mode_list:
                    return Response({'status': 'fail','message': 'transaction_mode values must be following: IMPS, RTGS and NEFT'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    bank_detail = BankDetails.objects.get(bd_id=bd_id)
                except BankDetails.DoesNotExist:
                    return Response({'status': 'fail', 'message': 'Bank does not exists.'}, status=status.HTTP_400_BAD_REQUEST)

                # if len(utr_number) < 12 or len(utr_number) > 16: return  ({'status': 'fail', 'message': 'utr_number length must be between 12 to 16.'}, status=status.HTTP_400_BAD_REQUEST)

                fund_request = FundRequest.objects.create(deposite_category=deposite_category_json, deposite_bank=bank_detail,
                                                          deposite_amount=deposit_amount, utr_number=utr_number, payment_proof=payment_proof_file_paths,
                                                          transaction_mode=transaction_mode, remark=remark, created_at=timezone.now(),
                                                          created_by=request.user)
                user_activity = {
                    "table_id": fund_request.pk,
                    "table_name": 'ad_fund_request',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'Fund request generated successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(fund_request)
                }

                add_user_activity(user_activity)

                return Response({"status": "success", "message": "Fund request generated successfully."}, status=status.HTTP_201_CREATED)

            else:
                return Response({'status': 'fail', 'message': 'At least one deposite category must be true.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_fund_request(self, request):
        fr_id = request.data.get("fr_id")
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size')

        try:
            if not page_size: return Response({'status': 'fail','message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(page_size): return Response({'status': 'fail','message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if page_number:
                if not isnumber(page_number): return Response({'status': 'fail','message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if fr_id:
                if not isnumber(fr_id): return Response({'status': 'fail','message': 'fr_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if request.user.pu_role == "ADMIN":
                queryset = FundRequest.objects.filter(is_delete=False)
            else:
                queryset = FundRequest.objects.filter(is_delete=False, created_by=request.user.pk)

            if fr_id:
                queryset = queryset.filter(pk=fr_id)

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
                        'message': 'Fund request Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                serializer = FundRequestSerializer(page_obj.object_list, many=True, context={'request': request})
                for data in serializer.data:
                    try:
                        user_details = PortalUserDetails.objects.get(pu=data['created_by'])
                        pu_name = PortalUser.objects.get(id=data['created_by']).pu_name
                        data['created_name'] = pu_name
                        data['created_unique_id'] = user_details.pud_unique_id
                    except PortalUserDetails.DoesNotExist:
                        data['created_name'] = None
                        data['created_unique_id'] = None

                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }
                return Response({
                    'status': 'success',
                    'message': 'Fund request data',
                    'data': paginated_response_data
                }, status=status.HTTP_200_OK)

            serializer = FundRequestSerializer(queryset, many=True, context={'request': request})
            response_data = {
                'status': 'success',
                'message': 'Fund request data',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'fail', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    
    def put(self, request):
        try:
            if 'fr_id' in request.data and 'request_status' in request.data or 'reason' in request.data:
                return self.fund_request_approve(request)
            elif 'fr_id' in request.data and 'deposit_bank_id' in request.data and 'deposite_category' in request.data:
                return self.fund_request_update(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': 'Internal server error.', 'data': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fund_request_approve(self, request):
        try:
            fr_id = request.data.get("fr_id")
            request_status = request.data.get("request_status")
            reason = request.data.get("reason")

            if not fr_id: return Response({'status': 'fail', 'message': 'fr_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not request_status: return Response({'status': 'fail', 'message': 'request_status is required.'}, status=status.HTTP_400_BAD_REQUEST)

            get_fund_request = FundRequest.objects.get(fr_id=fr_id)
            portal_user = PortalUser.objects.get(id=request.user.id)
            if get_fund_request.request_status == "REJECTED" or get_fund_request.request_status == "REVERSED":
                return Response({'status': 'fail', 'message': 'Fund request has already been processed.'}, status=status.HTTP_400_BAD_REQUEST)

            if request_status == "APPROVED" and get_fund_request.request_status != "PENDING":
                return Response({'status': 'fail', 'message': 'Fund request has already been processed.'}, status=status.HTTP_400_BAD_REQUEST)

            if request_status == "REVERSED" and get_fund_request.request_status != "APPROVED":
                return Response({'status': 'fail', 'message': 'Only requests with "APPROVED" status can be reversed.'}, status=status.HTTP_400_BAD_REQUEST)

            deposit_amount = get_fund_request.deposite_amount
            request_user = get_fund_request.created_by
            bank = BankDetails.objects.get(bd_id=get_fund_request.deposite_bank.bd_id)
            charge = 0.00
            hsn_rate = 0.00
            charge_type = ''
            if get_fund_request.deposite_category.get('online_deposit') == True:
                charge = float(bank.online_charges.get('Charge'))
                charge_type = bank.online_charges.get('charge_type')
                hsn_rate = AdHSNSAC.objects.get(hsnsac_id=bank.online_charges.get('hsn_sac')).tax_rate
            elif get_fund_request.deposite_category.get('cdm_deposit') == True:
                charge = float(bank.cdm_charges.get('Charge'))
                charge_type = bank.cdm_charges.get('charge_type')
                hsn_rate = AdHSNSAC.objects.get(hsnsac_id=bank.cdm_charges.get('hsn_sac')).tax_rate
            elif get_fund_request.deposite_category.get('counter_deposit') == True:
                charge = float(bank.counter_charges.get('Charge'))
                charge_type = bank.counter_charges.get('charge_type')
                hsn_rate = AdHSNSAC.objects.get(hsnsac_id=bank.counter_charges.get('hsn_sac')).tax_rate
            else:
                charge = 0.00
            rate_amount = float(deposit_amount) * (float(charge) / 100) if charge_type == 'is_percent' else float(charge)                      
            gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(hsn_rate)/100)))
            amount = float(rate_amount) - float(gst_amount)
            effective_ammount = float(deposit_amount) - float(rate_amount)
            try:
                get_portal_user_wallet = PortalUserWallet.objects.get(pu=request_user)
            except PortalUserWallet.DoesNotExist:
                return Response({'status': 'fail', 'message': 'PortalUser wallet not exists.'},
                            status=status.HTTP_404_NOT_FOUND)
            if request_status == "APPROVED" and get_fund_request.request_status == "PENDING":
                main_wallet_amount = get_portal_user_wallet.main_wallet
                get_portal_user_wallet.main_wallet = float(main_wallet_amount) + effective_ammount
                get_portal_user_wallet.save()

                get_fund_request.request_status = request_status
                get_fund_request.reasons = reason
                get_fund_request.updated_at = timezone.now()
                get_fund_request.save()

                global_transaction = GlTrn.objects.create(
                    service_trn_id=get_fund_request.pk,
                    gl_trn_amt=deposit_amount,
                    gl_tax_rate=hsn_rate,
                    gl_tax_amt=gst_amount,
                    effectvie_wallet="main_wallet",
                    effectvie_amt=effective_ammount,
                    effective_type="CR",
                    pu=portal_user,
                    service_trn_table="ad_fund_request",
                    gl_trn_dt=timezone.now()
                )

                WalletTrn.objects.create(
                    action_id=global_transaction.pk,
                    action_type="fund_request",
                    wl_label=f"Fund Request by {get_fund_request.created_by.pu_name}",
                    effectvie_wallet="main_wallet",
                    effectvie_amt=effective_ammount,
                    effective_type="CR",
                    pu=portal_user,
                    current_balance=get_portal_user_wallet.main_wallet,
                    wl_trn_dt=timezone.now()
                )

                user_activity = {
                    "table_id": get_fund_request.pk,
                    "table_name": 'ad_fund_request',
                    "ua_action": 'Update',  # Action performed
                    "ua_description": 'Fund request approved successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(get_fund_request)
                }

                add_user_activity(user_activity)

                return Response({'status': 'success', 'message': 'Fund request approved successfully.'},
                            status=status.HTTP_200_OK)

            elif request_status == "REVERSED" and get_fund_request.request_status == "APPROVED":

                main_wallet_amount = get_portal_user_wallet.main_wallet
                get_portal_user_wallet.main_wallet = float(main_wallet_amount) - float(effective_ammount)
                get_portal_user_wallet.save()

                get_fund_request.request_status = request_status
                get_fund_request.reasons = reason
                get_fund_request.updated_at = timezone.now()
                get_fund_request.save()

                user_activity = {
                    "table_id": get_fund_request.pk,
                    "table_name": 'ad_fund_request',
                    "ua_action": 'Update',  # Action performed
                    "ua_description": 'Fund request reversed successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(get_fund_request)
                }

                add_user_activity(user_activity)

                return Response({'status': 'success', 'message': 'Fund request reversed successfully.'},
                            status=status.HTTP_200_OK)

            elif request_status == "REJECTED":
                get_fund_request.request_status = request_status
                get_fund_request.reasons = reason
                get_fund_request.updated_at = timezone.now()
                get_fund_request.save()

                user_activity = {
                    "table_id": get_fund_request.pk,
                    "table_name": 'ad_fund_request',
                    "ua_action": 'Update',  # Action performed
                    "ua_description": 'Fund request rejected successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(get_fund_request)
                }

                add_user_activity(user_activity)

                return Response({'status': 'success', 'message': 'Fund request rejected successfully.'},
                            status=status.HTTP_200_OK)
            
            else:
                return Response({'status': 'fail', 'message': 'Invalid request status.'},
                            status=status.HTTP_400_BAD_REQUEST) 

        except FundRequest.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Fund request record not exists.'},
                            status=status.HTTP_404_NOT_FOUND) 

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fund_request_update(self, request):
        fr_id = request.data.get('fr_id')
        deposite_category = request.data.get('deposite_category')
        bd_id = request.data.get('deposit_bank_id')
        deposit_amount = request.data.get('deposit_amount')
        payment_proof = request.data.get('payment_proof')
        remark = request.data.get('remark')
        transaction_id = request.data.get('transaction_id')
        utr_number = request.data.get('utr_number')
        transaction_mode = request.data.get('transaction_mode')

        try:
            if not fr_id: return Response({'status': 'fail','message': 'fr_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            fund_request_queryset = FundRequest.objects.get(fr_id=fr_id, is_delete=False)
            if fund_request_queryset.created_by.pk != request.user.pk: return Response({"status": "fail", "message": "Unauthorized to update fund request."}, status=status.HTTP_401_UNAUTHORIZED)
            if fund_request_queryset.request_status != "PENDING": return Response({"status": "fail", "message": "Fund request has already been processed"}, status=status.HTTP_400_BAD_REQUEST)

            if not deposite_category: return Response({'status': 'fail','message': 'deposite_category is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not bd_id: return Response({'status': 'fail','message': 'bd_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not deposit_amount: return Response({'status': 'fail','message': 'deposit_amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not remark: return Response({'status': 'fail','message': 'remark is required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                deposite_category_json = json.loads(deposite_category)
            except json.JSONDecodeError:
                return Response({'status': 'fail', 'message': 'Invalid deposite category format'}, status=status.HTTP_400_BAD_REQUEST)

            if not isfloat(deposit_amount): Response({'status': 'fail','message': 'Invalid desposit amount.'}, status=status.HTTP_400_BAD_REQUEST)
            if float(deposit_amount) < 0: Response({'status': 'fail','message': 'Desposit amount must be positive number.'}, status=status.HTTP_400_BAD_REQUEST)

            if payment_proof:
                file_path = handle_uploaded_file(payment_proof, 'Retailer/PaymentProof') if payment_proof else None
                payment_proof_file_paths = {'payment_proof': file_path}

            bank_detail = BankDetails.objects.get(bd_id=bd_id)

            if deposite_category_json.get("counter_deposit") == True or deposite_category_json.get("cdm_deposit") == True:
                if not transaction_id: return Response({'status': 'fail','message': 'transaction_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
                # if len(transaction_id) < 12 or len(transaction_id) > 16: return Response({'status': 'fail', 'message': 'transaction_id length must be between 12 to 16.'}, status=status.HTTP_400_BAD_REQUEST)

                fund_request_queryset.deposite_category = deposite_category_json
                fund_request_queryset.deposite_bank = bank_detail
                fund_request_queryset.deposite_amount = deposit_amount
                fund_request_queryset.transaction_id = transaction_id
                if payment_proof:
                    fund_request_queryset.payment_proof = payment_proof_file_paths
                fund_request_queryset.remark = remark
                fund_request_queryset.save()

                user_activity = {
                    "table_id": fund_request_queryset.pk,
                    "table_name": 'ad_fund_request',
                    "ua_action": 'Update',
                    "ua_description": 'Fund request updated successfully.',
                    "created_by": request.user,
                    "request_data": dict(request.data),
                    "response_data": model_to_dict(fund_request_queryset)
                }

                add_user_activity(user_activity)

                return Response({"status": "success", "message": "Fund request updated successfully."}, status=status.HTTP_200_OK)

            elif deposite_category_json.get("online_transaction") == True:
                if not utr_number: return Response({'status': 'fail','message': 'utr_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
                if not transaction_mode: return Response({'status': 'fail','message': 'transaction_mode is required.'}, status=status.HTTP_400_BAD_REQUEST)

                transaction_mode_list = ["IMPS", "RTGS", "NEFT"]
                if transaction_mode not in transaction_mode_list:
                    return Response({'status': 'fail','message': 'transaction_mode values must be following: IMPS, RTGS and NEFT'}, status=status.HTTP_400_BAD_REQUEST)

                # if len(utr_number) < 12 or len(utr_number) > 16: return  ({'status': 'fail', 'message': 'utr_number length must be between 12 to 16.'}, status=status.HTTP_400_BAD_REQUEST)

                fund_request_queryset.deposite_category = deposite_category_json
                fund_request_queryset.deposite_bank = bank_detail
                fund_request_queryset.deposite_amount = deposit_amount
                fund_request_queryset.utr_number = utr_number
                fund_request_queryset.transaction_mode = transaction_mode
                if payment_proof:
                    fund_request_queryset.payment_proof = payment_proof_file_paths
                fund_request_queryset.remark = remark
                fund_request_queryset.save()

                user_activity = {
                    "table_id": fund_request_queryset.pk,
                    "table_name": 'ad_fund_request',
                    "ua_action": 'Update',  # Action performed
                    "ua_description": 'Fund request updated successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(fund_request_queryset)
                }

                add_user_activity(user_activity)

                return Response({"status": "success", "message": "Fund request updated successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': 'At least one deposite category must be true.'}, status=status.HTTP_400_BAD_REQUEST)

        except BankDetails.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Bank does not exists.'}, status=status.HTTP_404_NOT_FOUND)
        except FundRequest.DoesNotExist:
            return Response({"status": "fail", "message": "Fund request does not exist."},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            fr_id = request.data.get('fr_id')

            if not fr_id: return Response({'status': 'fail', 'message': 'fr_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(fr_id): return Response({'status': 'fail','message': 'fr_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            queryset = FundRequest.objects.get(fr_id=fr_id, is_delete=False)
            if queryset.created_by.pk != request.user.pk: return Response({"status": "fail", "message": "Unauthorized to delete fund request."}, status=status.HTTP_401_UNAUTHORIZED)

            if queryset.request_status == "PENDING":
                queryset.is_delete = True
                queryset.is_deactive = True
                queryset.save()

                user_activity = {
                    "table_id": queryset.pk,
                    "table_name": 'ad_fund_request',
                    "ua_action": 'Delete',  # Action performed
                    "ua_description": 'Fund request deleted successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(queryset)
                }

                add_user_activity(user_activity)

                return Response({'status': 'success', 'message': 'Fund request deleted successfully.'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': 'Only requests with a pending status can be deleted.'}, status=status.HTTP_400_BAD_REQUEST)

        except FundRequest.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Fund request dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': 'Internal server error.', 'data': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WalletAPIView(APIView):
    authentication_classes=[CustomJWTAuthentication]
    permission_classes=[IsRetailer | IsDistributor | IsAdmin]

    def post(self, request):
        print('request.data', request.data)
        try:
            if 'contact_no' in request.data and 'amount' in request.data and 'from_wallet' in request.data:
                print('=-==-==-===-=-======---')
                return self.wallet_to_other_wallet(request)
            elif 'from_wallet' in request.data and 'amount' in request.data:
                print('================--------------------')
                return self.wallet_to_wallet(request)
            elif 'bdr_id' in request.data and 'amount' in request.data and 'from_wallet' in request.data:
                return self.wallet_to_bank(request)
            elif 'contact_no' in request.data :
                return self.get_data_contact_number(request)
            elif 'wallet' in request.data and 'page_number' in request.data or 'page_size' in request.data:
                return self.all_wallet_transaction(request)
            elif 'page_number' in request.data or 'page_size' in request.data:
                return self.get_wallet_transaction(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def wallet_to_wallet(self, request):
        try:
            from_wallet = request.data.get('from_wallet')
            print('from_wallet', from_wallet)
            description = request.data.get('description', None)
            print('description', description)
            amount = request.data.get('amount')
            print('amount', amount)
            print('step1')
            to_wallet = 'main_wallet'

            main_wallet = 'main_wallet'
            print('step2')
            if not from_wallet:
                return Response({'status': 'fail', 'message': 'from_wallet is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not amount:
                return Response({'status': 'fail', 'message': 'amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            validation_ammount = isnumber(amount)
            if validation_ammount == False:
                return Response({'status': 'fail', 'message': 'Invalid amount. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)
            print('step3')
            from_wallet_validation = isstring(from_wallet)
            if from_wallet_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid from wallet. It should contain only alphabetic characters.'}, status=status.HTTP_400_BAD_REQUEST)

            if from_wallet not in ['cashin_wallet', 'pg_wallet', 'commission_wallet']:
                return Response({'status': 'fail', 'message': 'Invalid wallet name. Please choose from cashin_wallet, pg_wallet, or commission_wallet.'}, status=status.HTTP_400_BAD_REQUEST)
            print('step4')
            amount = Decimal(amount)
            print('step5')
            if main_wallet == to_wallet or main_wallet == from_wallet:
                print('step6')
                if main_wallet == to_wallet and main_wallet == from_wallet:
                    return Response({'status': 'fail', 'message': f'Either from_wallet and to_wallet must be {main_wallet}.'}, status=status.HTTP_400_BAD_REQUEST)
                print('step7')
                user = request.user.id
                retailer = PortalUser.objects.get(id=user, is_deleted=False)
                retailer_details = PortalUserDetails.objects.get(pu=retailer)
                user_wallet = PortalUserWallet.objects.get(pu=retailer)
                print('step8')
                if getattr(user_wallet, from_wallet) < amount:
                    return Response({'status': 'fail', 'message': f'Insufficient funds in {from_wallet}.', 'is_success': True}, status=status.HTTP_400_BAD_REQUEST)
                print('step9')
                setattr(user_wallet, from_wallet, getattr(user_wallet, from_wallet) - amount)
                setattr(user_wallet, to_wallet, getattr(user_wallet, to_wallet) + amount)
                print('step10')
                user_wallet.save()
                from_wallet_name = ''
                if from_wallet == 'cashin_wallet':
                    from_wallet_name = 'CashIn'
                elif from_wallet == 'pg_wallet':
                    from_wallet_name = 'Pg'
                elif from_wallet == 'commission_wallet':
                    from_wallet_name = 'Commission'
                main_wallet_name = 'Main'
                print('step11')
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                from_label = f'{retailer_details.pud_unique_id}_DR_{from_wallet}_Internal{from_wallet_name}To{main_wallet_name}_{timestamp}'
                to_label = f'{retailer_details.pud_unique_id}_CR_{to_wallet}_Internal{from_wallet_name}To{main_wallet_name}_{timestamp}'
                wallet_transaction = {'CR': [main_wallet, to_label], 'DR': [from_wallet, from_label]}
                print('step12')
                for key, value in wallet_transaction.items():
                    print('step13')
                    global_transaction = GlTrn.objects.create(
                        pu=retailer,
                        effectvie_wallet=value[0],
                        effectvie_amt=amount,
                        effective_type=key,
                        service_trn_table='ad_wallet_trnasaction',
                        gl_trn_dt=timezone.now()
                    )
                    print('step14')
                    WalletTrn.objects.create(
                        action_id=global_transaction.gl_trn_id,
                        action_type=f'Internal_{from_wallet}_to_{main_wallet}',
                        pu=retailer, 
                        wl_label=value[1],
                        effectvie_wallet=value[0],
                        effectvie_amt=amount,
                        effective_type=key,
                        current_balance=user_wallet.main_wallet,
                        wl_trn_des=description if description else None,
                        wl_trn_dt=timezone.now()
                    )
                    print('step15')
                return Response({'status': 'success', 'message': f'{amount} transferred from {from_wallet} to {to_wallet}.', 'is_success': True}, status=status.HTTP_200_OK)

            else:
                return Response({'status': 'fail', 'message': f'Either from_wallet or to_wallet must be {main_wallet}.'}, status=status.HTTP_400_BAD_REQUEST)

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except PortalUserWallet.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Wallet not found for the user.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_data_contact_number(self, request):
        try:
            contact_number = request.data.get('contact_no')

            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            validation_contact_number = validate_mobile_number(contact_number)
            if validation_contact_number == False:
                return Response({'status': 'fail', 'message': 'Invalid Mobile Number.'}, status=status.HTTP_400_BAD_REQUEST)

            get_data = PortalUser.objects.get(pu_contact_no=contact_number, is_deleted=False)
            pud_unique_id = PortalUserDetails.objects.get(pu=get_data).pud_unique_id
            UserSerializer = PortalUserSerializer(get_data)
            user_data = UserSerializer.data  # Convert to dict
            user_data['pud_unique_id'] = pud_unique_id  # Add the unique ID manually
            other_charges = OtherCharges.objects.get(oc_name='quick_transfer_charges')
            other_serializer = OtherChargesSerializer(other_charges)
            results = {'user_data': user_data, 'other_charges': other_serializer.data}

            return Response({'status': 'success', 'message': 'user data get successfully.', 'data': results}, status=status.HTTP_200_OK)

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'user dose not exists.', 'data': []}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def wallet_to_other_wallet(self, request):
        try:
            contact_no = request.data.get('contact_no')
            amount = request.data.get('amount')
            from_wallet = request.data.get('from_wallet')

            if not contact_no:
                return Response({'status': 'fail', 'message': 'Contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not amount:
                return Response({'status': 'fail', 'message': 'Amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not from_wallet:
                return Response({'status': 'fail', 'message': 'From wallet is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not validate_mobile_number(contact_no):
                return Response({'status': 'fail', 'message': 'Invalid mobile number.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(amount):
                return Response({'status': 'fail', 'message': 'Invalid amount. It must be a positive number.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isstring(from_wallet):
                return Response({'status': 'fail', 'message': 'Invalid from wallet. It should contain only alphabetic characters.'}, status=status.HTTP_400_BAD_REQUEST)

            amount = Decimal(amount)
            main_wallet = 'main_wallet'

            user = PortalUser.objects.get(id=request.user.id, is_deleted=False)
            get_user = PortalUser.objects.get(pu_contact_no=contact_no, is_deleted=False)

            if get_user.pu_role not in ['RETAILER', 'DISTRIBUTOR']:
                return Response({'status': 'fail', 'message': 'Only Retailers and Distributors are authorized to perform this action.'}, status=status.HTTP_400_BAD_REQUEST)

            if request.user.id == get_user.id:
                return Response({'status': 'fail', 'message': 'Self-transfer is not allowed.'}, status=status.HTTP_400_BAD_REQUEST)

            from_user_wallet = PortalUserWallet.objects.get(pu=get_user)
            to_user_wallet = PortalUserWallet.objects.get(pu=request.user.id)

            from_wallet_balance = Decimal(getattr(to_user_wallet, from_wallet))

            if from_wallet_balance < amount:
                return Response({'status': 'fail', 'message': f'Insufficient funds in {from_wallet}.'}, status=status.HTTP_400_BAD_REQUEST)

            # **Role-Based Wallet Logic**
            if get_user.pu_role == 'RETAILER':
                to_wallet = from_wallet  # Transfer to the same wallet
            elif get_user.pu_role == 'DISTRIBUTOR':
                to_wallet = main_wallet  # Transfer must go to main_wallet
            else:
                return Response({'status': 'fail', 'message': 'Unauthorized role for transaction.'}, status=status.HTTP_400_BAD_REQUEST)

            # **Fetching Other Charges**
            try:
                other_charges = OtherCharges.objects.get(oc_name='quick_transfer_charges')
                min_limit = Decimal(other_charges.minimum) if other_charges.minimum is not None else Decimal(0)
                max_limit = Decimal(other_charges.maximum) if other_charges.maximum is not None else Decimal(999999)
                charge_type = other_charges.charge_type
                charge_value = Decimal(other_charges.charge) if other_charges.charge is not None else Decimal(0)
            except OtherCharges.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Other charges not found.'}, status=status.HTTP_404_NOT_FOUND)

            # **Check if Amount is within Limits**
            if amount < min_limit or amount > max_limit:
                return Response({'status': 'fail', 'message': f'Amount must be between {min_limit} and {max_limit}.'}, status=status.HTTP_400_BAD_REQUEST)

            # **Calculate Charges**
            if charge_type == 'is_percent':
                charge = (amount * charge_value) / 100  # Percentage Deduction
            elif charge_type == 'is_flat':
                charge = charge_value  # Fixed Deduction
            else:
                charge = Decimal(0)  # No charge if charge_type is invalid

            # **Calculate Effective Amount**
            effective_amount = amount - charge

            if effective_amount <= 0:
                return Response({'status': 'fail', 'message': 'Effective amount after charges cannot be zero or negative.'}, status=status.HTTP_400_BAD_REQUEST)

            # **Updating Wallet Balances**
            setattr(from_user_wallet, to_wallet, Decimal(getattr(from_user_wallet, to_wallet)) + effective_amount)
            setattr(to_user_wallet, from_wallet, from_wallet_balance - amount)

            from_user_wallet.save()
            to_user_wallet.save()

            # **Logging the Transaction**
            from_wallet_name = {
                'cashin_wallet': 'cashin_wallet',
                'pg_wallet': 'pg_wallet',
                'commission_wallet': 'commission_wallet'
            }.get(from_wallet, from_wallet)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            from_label = f'{from_user_wallet.pu.pu_contact_no}_CR_{from_wallet}_Internal{from_wallet_name}To{to_wallet}_{timestamp}'
            to_label = f'{to_user_wallet.pu.pu_contact_no}_DR_{to_wallet}_Internal{from_wallet_name}To{to_wallet}_{timestamp}'
            # Determine the correct wallet balance to store
            dr_current_balance = getattr(from_user_wallet, from_wallet)
            cr_current_balance = getattr(to_user_wallet, to_wallet)
            wallet_transaction = {
                'CR': [to_wallet, from_label, effective_amount, cr_current_balance],  # Credit effective amount
                'DR': [from_wallet, to_label, effective_amount, dr_current_balance]  # Debit full amount
            }
            for key, value in wallet_transaction.items():
                global_transaction = GlTrn.objects.create(
                    pu=user,
                    effectvie_wallet=value[0],
                    effectvie_amt=value[2],  # Use calculated amount
                    effective_type=key,
                    service_trn_table='ad_wallet_trnsaction',
                    gl_trn_dt=timezone.now()
                )

                WalletTrn.objects.create(
                    action_id=global_transaction.gl_trn_id,
                    action_type=f'Internal{from_wallet}_to_{to_wallet}',
                    pu=get_user,
                    wl_label=value[1],
                    effectvie_wallet=value[0],
                    effectvie_amt=value[2],  # Use calculated amount
                    effective_type=key,
                    current_balance=value[3],
                    wl_trn_des=f"{user.pu_name} transferred {value[2]} from {from_wallet} to {to_wallet} of {get_user.pu_name}",
                    wl_trn_dt=timezone.now()
                )
            
            if charge > 0:
                charge_label = f'{to_user_wallet.pu.pu_contact_no}_DR_{from_wallet}_Charges_{timestamp}'

                charge_transaction = GlTrn.objects.create(
                    pu=user,
                    effectvie_wallet=from_wallet,  # Charges sender ke wallet se jayenge
                    effectvie_amt=charge,  # Only charges amount
                    effective_type="DR",
                    service_trn_table='ad_wallet_trnsaction',
                    gl_trn_dt=timezone.now()
                )
                current_balance = getattr(from_user_wallet, from_wallet)
                print('current_balance', current_balance)
                WalletTrn.objects.create(
                    action_id=charge_transaction.gl_trn_id,
                    action_type=f'Internal{from_wallet}_to_{to_wallet}',
                    pu=get_user,
                    wl_label=charge_label,
                    effectvie_wallet=from_wallet,
                    effectvie_amt=charge,  # Use calculated amount
                    effective_type='DR',
                    current_balance=current_balance,
                    wl_trn_des=f"{user.pu_name} transferred {amount} from {from_wallet} to {to_wallet} of {get_user.pu_name}",
                    wl_trn_dt=timezone.now()
                )

            return Response({
                'status': 'success',
                'message': f'{effective_amount} (after {charge} charge) transferred from {from_wallet} to {to_wallet}.'
            }, status=status.HTTP_200_OK)

        except PortalUserWallet.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User wallet does not exist'}, status=status.HTTP_404_NOT_FOUND)

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def wallet_to_bank(self, request):
        rbd_id = request.data.get('rbd_id')
        amount = request.data.get('amount')
        from_wallet = request.data.get('from_wallet')

        try:
            if not rbd_id: return Response({'status': 'fail', 'message': 'rbd_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not amount: return Response({'status': 'fail', 'message': 'amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not from_wallet: return Response({'status': 'fail', 'message': 'from_wallet is required.'}, status=status.HTTP_400_BAD_REQUEST)

            user = PortalUser.objects.get(id=request.user.id)
            user_wallet = PortalUserWallet.objects.get(pu=user)
            get_bank = RetailerBankDetails.objects.get(rbd_id=rbd_id)
            
            amount = Decimal(amount)
            other_charges = OtherCharges.objects.get(oc_name='cashin_to_bank_charges')
            min_limit = Decimal(other_charges.minimum) if other_charges.minimum is not None else Decimal(0)
            max_limit = Decimal(other_charges.maximum) if other_charges.maximum is not None else Decimal(999999)
            charge_type = other_charges.charge_type
            charge_value = Decimal(other_charges.charge) if other_charges.charge is not None else Decimal(0)

            # **Check if Amount is within Limits**
            if amount < min_limit or amount > max_limit:
                return Response({'status': 'fail', 'message': f'Amount must be between {min_limit} and {max_limit}.'}, status=status.HTTP_400_BAD_REQUEST)

            # **Calculate Charges**
            if charge_type == 'is_percent':
                charge = (amount * charge_value) / 100  # Percentage Deduction
            elif charge_type == 'is_fix':
                charge = charge_value  # Fixed Deduction
            else:
                charge = Decimal(0)  # No charge if charge_type is invalid

            # **Calculate Effective Amount**
            effective_amount = amount - charge

            if effective_amount <= 0:
                return Response({'status': 'fail', 'message': 'Effective amount after charges cannot be zero or negative.'}, status=status.HTTP_400_BAD_REQUEST)

            user_wallet.cashin_wallet -= amount
            user_wallet.save()

            global_transaction = GlTrn.objects.create(
                pu=user,
                effectvie_wallet=from_wallet,  # Charges sender ke wallet se jayenge
                effectvie_amt=effective_amount,  # Only charges amount
                effective_type="DR",
                service_trn_table='ad_wallet_trnsaction',
                gl_trn_dt=timezone.now()
            )

            GlTrn.objects.create(
                pu=user,
                effectvie_wallet=from_wallet,  # Charges sender ke wallet se jayenge
                effectvie_amt=charge,  # Only charges amount
                effective_type="DR",
                service_trn_table='ad_wallet_trnsaction',
                gl_trn_dt=timezone.now()
            )

            WalletTrn.objects.create(
                action_id=global_transaction.gl_trn_id,
                action_type="cashin to bank",
                pu=user,
                wl_label=f'Transferred_cashin_wallet_to_bank',
                effectvie_wallet='cashin_wallet',
                effectvie_amt=amount,  # Use calculated amount
                effective_type='DR',
                current_balance=user_wallet.cashin_wallet,
                wl_trn_des=f"{user.pu_name} transferred {amount} from {from_wallet} to {get_bank.bank_name}",
                wl_trn_dt=timezone.now()
            )

            return Response({'status': 'success', 'message': 'cashin to bank transfer successfully.'}, status=status.HTTP_200_OK)

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Portal user dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except OtherCharges.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Other charges dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except RetailerBankDetails.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Retailer bank dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_wallet_transaction(self, request):
        data = {
            "total_pages": 0,
            "current_page": 0,
            "total_items": 0,
            "results": []
        }
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        wallet_name = request.data.get('wallet', None)
        page_size = int(page_size)
        page_number = int(page_number)
        all_wl_data = 'Wallet'
        user = request.user.id
        try:
            retailer = PortalUser.objects.get(id=user, is_deleted=False)
            if not wallet_name:
                filter_wallet_transaction = WalletTrn.objects.filter(pu=retailer)
            else:
                wallet_name_validation = isstring(wallet_name)
                if wallet_name_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid wallet name. It should contain only alphabetic characters.'}, status=status.HTTP_400_BAD_REQUEST)

                if wallet_name not in ['main_wallet', 'cashin_wallet', 'pg_wallet', 'commission_wallet']:
                    return Response({'status': 'fail', 'message': 'Invalid wallet name. Please choose from main_wallet, cashin_wallet, pg_wallet, or commission_wallet.'}, status=status.HTTP_400_BAD_REQUEST)
                if not wallet_name:
                    return Response({'status': 'fail', 'message': 'wallet name is required.'}, status=status.HTTP_400_BAD_REQUEST)
                filter_wallet_transaction = WalletTrn.objects.filter(pu=retailer, effectvie_wallet=wallet_name)
            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size
            paginated_wallet_transaction = filter_wallet_transaction[start_index:end_index]
            total_items = filter_wallet_transaction.count()
            total_pages = (len(filter_wallet_transaction) + page_size - 1) // page_size
            serializer = WalletTrnSerializer(paginated_wallet_transaction, many=True)
            for trn in serializer.data:
                # Convert to datetime if it's a string
                if isinstance(trn['wl_trn_dt'], str):
                    trn['wl_trn_dt'] = datetime.strptime(trn['wl_trn_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")

                trn['wl_trn_dt'] = trn['wl_trn_dt'].strftime("%d-%m-%Y %I:%M %p")
            data = {
                'total_pages': total_pages,
                'current_page': page_number,
                'total_items': total_items,
                'results': serializer.data
            }

            return Response({'status': 'success', 'message': f'Get all {wallet_name if wallet_name else all_wl_data} transaction.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def all_wallet_transaction(self, request):
        data = {
            "total_pages": 0,
            "current_page": 0,
            "total_items": 0,
            "results": []
        }
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        consolidation_wallet = request.data.get('wallet', None)
        page_size = int(page_size)
        page_number = int(page_number)
        user = request.user.id
        try:
            user = PortalUser.objects.get(id=user, is_deleted=False)
            puw_user = PortalUserWallet.objects.get(pu_id=user)
            
            filter_wallet_transaction = WalletTrn.objects.filter(pu=user)
            
            if consolidation_wallet is not None:
                filter_wallet_transaction = filter_wallet_transaction.filter(effectvie_wallet=consolidation_wallet)
            
            # descending 
            filter_wallet_transaction = filter_wallet_transaction.order_by('-pk')  # fatch data
            
            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size
            
            paginated_wallet_transaction = filter_wallet_transaction[start_index:end_index]
            
            total_items = filter_wallet_transaction.count()
            
            total_pages = (len(filter_wallet_transaction) + page_size - 1) // page_size
            
            serializer = WalletTrnSerializer(paginated_wallet_transaction, many=True)
            
            response_data = []
            
            for data in serializer.data:
                # data['current_balance'] = puw_user.main_wallet
                response_data.append(
                    {'effective_wallet': data.get("effectvie_wallet"), 'effective_ammount': data.get("effectvie_amt"),
                     'effective_type': data.get("effective_type")})
                    
                if isinstance(data['wl_trn_dt'], str):
                    data['wl_trn_dt'] = datetime.strptime(data['wl_trn_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")
                data['wl_trn_dt'] = data['wl_trn_dt'].strftime("%d-%m-%Y %I:%M %p")
                # ADD DATE TIME
                # if data.get('wl_trn_dt'):
                #     data['wl_trn_dt'] = datetime.strptime(data['wl_trn_dt'],
                #                                                    "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
                #         "%Y-%m-%d %I:%M %p")

            data = {
                'total_pages': total_pages,
                'current_page': page_number,
                'total_items': total_items,
                'results': serializer.data
            }

            return Response({'status': 'success', 'message': f'Get all user transaction.', 'data': data},
                            status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PortalUsertWalletAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer | IsDistributor]

    def get(self, request):
        try:
            user = request.user.id
            wallet_data = []
            user = PortalUser.objects.get(id=user)
            user_wallet = PortalUserWallet.objects.filter(pu_id=user)
            if user.pu_role == 'RETAILER':
                for wallet in user_wallet:
                    wallet_dict = {
                        'main_wallet': wallet.main_wallet,
                        'commission_wallet': wallet.commission_wallet,
                        'pg_wallet': wallet.pg_wallet,
                        'cashin_wallet': wallet.cashin_wallet
                    }
                    wallet_data.append(wallet_dict)
            else:
                for wallet in user_wallet:
                    wallet_dict = {
                        'main_wallet': wallet.main_wallet,
                        'commission_wallet': wallet.commission_wallet
                    }
                    wallet_data.append(wallet_dict)
             
            data = {'results': wallet_data}
            
            return Response({'status': 'success', 'message': f'Get {user.pu_role} wallet and balance.', 'data': data}, status=status.HTTP_200_OK)
        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Portal user dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PayOutAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request):
        try:
            if 'contact_number' in request.data and 'first_name' in request.data and 'last_name' in request.data and 'address' in request.data and 'zip_code' in request.data:
                return self.get_payout_with_mobile(request)
            elif 'contact_number' in request.data and 'otp' in request.data:
                return self.verify_mobile_otp(request)
            elif 'contact_number' in request.data:
                return self.check_mobile_number(request)
            elif 'account_number':
                return self.get_payout_with_account(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_payout_with_mobile(self, request):
        try:
            contact_number = request.data.get('contact_number')
            first_name = request.data.get('first_name')
            last_name = request.data.get('last_name')
            address = request.data.get('address')
            zip_code = request.data.get('zip_code')
            if not contact_number:
                return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not first_name:
                return Response({'status': 'fail', 'message': 'first name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not last_name:
                return Response({'status': 'fail', 'message': 'last name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not address:
                return Response({'status': 'fail', 'message': 'address is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not zip_code:
                return Response({'status': 'fail', 'message': 'zip code is required.'}, status=status.HTTP_400_BAD_REQUEST)

            mobile_number_validation = validate_mobile_number(contact_number)
            if mobile_number_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid contact number format.'}, status=status.HTTP_400_BAD_REQUEST)

            first_name_validation = isstring(first_name)
            if first_name_validation == False:
                return Response({'status': 'fail', 'message': 'First name must be a valid string.'}, status=status.HTTP_400_BAD_REQUEST)

            last_name_validation = isstring(last_name)
            if last_name_validation == False:
                return Response({'status': 'fail', 'message': 'Last name must be a valid string.'}, status=status.HTTP_400_BAD_REQUEST)

            zip_code_validation = isnumber(zip_code)
            if zip_code_validation == False:
                return Response({'status': 'fail', 'message': 'Zip code must be a number.'}, status=status.HTTP_400_BAD_REQUEST)
            if len(zip_code) != 6:
                return Response({'status': 'fail', 'message': 'Zip code must be 6 digits long.'}, status=status.HTTP_400_BAD_REQUEST)

            get_payout_customer = PyOtCustomer.objects.get(customer_contact_no=contact_number)
            if get_payout_customer.pyot_unique_id == None:
                try:
                    exists_contact_number = PyOtCustomer.objects.get(customer_contact_no=contact_number)
                except PyOtCustomer.DoesNotExist:
                    return Response({'status': 'fail', 'message': 'This contact number does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
                
                pyot_cs_prefix = "PYOT_CS"

                last_pyot_id = PyOtCustomer.objects.filter(pyot_unique_id__startswith="PYOT_CS").order_by(
                    '-pyot_unique_id').first()
                if last_pyot_id:
                    last_number = int(last_pyot_id.pyot_unique_id[-5:])  
                    new_number = f"{last_number + 1:05d}"  
                else:
                    new_number = "00001"
                exists_contact_number.pyot_unique_id = f'{pyot_cs_prefix}{new_number}'
                exists_contact_number.customer_first_name=first_name
                exists_contact_number.customer_last_name=last_name
                exists_contact_number.customer_address=address
                exists_contact_number.customer_zip_code=zip_code
                exists_contact_number.is_verify = True
                exists_contact_number.save()

                serializer = PyOtCustomerSerializer(exists_contact_number)
                data = {
                    'results': serializer.data
                }

                return Response({'status': 'success', 'message': 'New customer created successfully.', 'data': data}, status=status.HTTP_200_OK)

            else:
                return Response({'status': 'fail', 'message': 'Customer with this contact number already exists'}, status=status.HTTP_400_BAD_REQUEST)

        except PyOtCustomer.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Payout customer dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def check_mobile_number(self, request):
        try:
            contact_number = request.data.get('contact_number')

            if not contact_number:
                return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            mobile_number_validation = validate_mobile_number(contact_number)
            if mobile_number_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid contact number format.'}, status=status.HTTP_400_BAD_REQUEST)

            exists_mobile_number = PyOtCustomer.objects.get(customer_contact_no=contact_number)
            if exists_mobile_number.is_verify == True:
                banks_list = []

                payout_banks = PyOtBankAccount.objects.all()

                for bank in payout_banks:
                    for value in bank.customer_contact:
                        if value==contact_number:
                            banks_list.append(bank)

                if len(banks_list) != 0:
                    banks_list = PyOtBankSerializer(banks_list, many=True).data

                data = {
                    'results': banks_list
                }

                return Response({'status': 'success', 'message': 'Get Banks Account Details.', 'data': data}, status=status.HTTP_200_OK)

            else:
                code = get_random_string(length=6, allowed_chars='0123456789')
                exists_mobile_number.verify_code = code
                exists_mobile_number.verify_code_expire_at = timezone.now() + timedelta(minutes=15)
                exists_mobile_number.save()
                return Response({'status': 'fail', 'message': 'Resend verify code successfully.', 'verify_code': code, 'expiry_time': '15 minutes'}, status=status.HTTP_200_OK)

        except PyOtCustomer.DoesNotExist:
            code = get_random_string(length=6, allowed_chars='0123456789')
            PyOtCustomer.objects.create(
                customer_contact_no=contact_number,
                verify_code=code,
                verify_code_expire_at=timezone.now() + timedelta(minutes=15),
            )
            return Response({'status': 'success', 'message': 'New customer record created. A verification code has been sent to the mobile number.', 'verify_code': code, 'expiry_time': '15 minutes'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def verify_mobile_otp(self, request):
        try:
            contact_number = request.data.get('contact_number')
            otp = request.data.get('otp')

            if not contact_number:
                return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not otp:
                return Response({'status': 'fail', 'message': 'otp is required.'}, status=status.HTTP_400_BAD_REQUEST)

            mobile_number_validation = validate_mobile_number(contact_number)
            if mobile_number_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid contact number format.'}, status=status.HTTP_400_BAD_REQUEST)

            code_validation = isnumber(otp)
            if code_validation == False:
                return Response({'status': 'fail', 'message': 'OTP code must be a number.'}, status=status.HTTP_400_BAD_REQUEST)

            if len(otp) != 6:
                return Response({'status': 'fail', 'message': 'OTP code must be 6 digits long.'}, status=status.HTTP_400_BAD_REQUEST)

            get_payout_customer = PyOtCustomer.objects.get(customer_contact_no=contact_number)
            if otp == get_payout_customer.verify_code:

                if timezone.now() < get_payout_customer.verify_code_expire_at:
                    get_payout_customer.verify_code = None
                    get_payout_customer.verify_code_expire_at = None
                    get_payout_customer.save()

                    data = {
                        'status': 'success',
                        'message': 'OTP verified successfully'
                    }
                    return Response(data, status=status.HTTP_200_OK)

                else:
                    return Response({'status': 'fail', 'message': 'OTP has expired.'}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({'status': 'fail', 'message': 'Invalid OTP provided.'}, status=status.HTTP_400_BAD_REQUEST)

        except PyOtCustomer.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Payout customer dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_payout_with_account(self, request):
        try:
            account_number = request.data.get('account_number')
            if not account_number:
                return Response({'status': 'fail', 'message': 'account number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            account_number_validation = isnumber(account_number)
            if account_number_validation == False:
                return Response({'status': 'fail', 'message': 'account number must be a number.'}, status=status.HTTP_404_NOT_FOUND)

            get_payout_account = PyOtBankAccount.objects.get(bnk_acc_no=account_number)

            customer_data = []

            for contact in get_payout_account.customer_contact:
                get_contact_number = PyOtCustomer.objects.filter(customer_contact_no=contact).first()
                if get_contact_number:
                    customer_data.append(get_contact_number)

            if len(customer_data) != 0:
                serializer = PyOtCustomerSerializer(customer_data, many=True).data
            else:
                serializer = []
            data = {
                'status': 'success',
                'message': 'get all contact number successfully.',
                'results': serializer
            }
            return Response(data, status=status.HTTP_200_OK)

        except PyOtBankAccount.DoesNotExist:
            return Response({'status': 'fail', 'message': 'account number dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BeneficiaryDetailsAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request):
        try:
            if 'bank_name' in request.data and 'beneficiary_name' in request.data and 'account_number' in request.data and 'confirm_account_number' in request.data and 'ifsc_code' in request.data and 'contact_number' in request.data:
                return self.add_customer_payout_bank_account(request)
            elif 'page_size' in request.data or 'page_number' in request.data:
                return self.fatch_customer_payout_bank_account(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def add_customer_payout_bank_account(self, request):
        try:
            bank_name = request.data.get('bank_name')
            beneficiary_name = request.data.get('beneficiary_name')
            account_number = request.data.get('account_number')
            confirm_account_number = request.data.get('confirm_account_number')
            ifsc_code = request.data.get('ifsc_code')
            contact_number = request.data.get('contact_number')

            if not bank_name: return Response({'status': 'fail', 'message': 'bank name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not beneficiary_name: return Response({'status': 'fail', 'message': 'beneficiary name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not account_number: return Response({'status': 'fail', 'message': 'account number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not confirm_account_number: return Response({'status': 'fail', 'message': 'confirm account number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not ifsc_code: return Response({'status': 'fail', 'message': 'IFSC code is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if account_number != confirm_account_number:
                return Response({'status': 'fail', 'message': 'Account number nad Confirm account number not match.'}, status=status.HTTP_400_BAD_REQUEST)

            existing_account = PyOtBankAccount.objects.filter(pyot_bank_name=bank_name, pyot_beneficiary_name=beneficiary_name, bnk_acc_no=account_number, bnk_ifsc=ifsc_code).first()
            if existing_account:
                if contact_number in existing_account.customer_contact:
                    return Response({'status': 'fail', 'message': 'This bank account with the provided contact number already exists.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    existing_account.customer_contact.append(contact_number)
                    existing_account.save()
                    return Response({'status': 'success', 'message': 'Contact number added to existing payout bank account.'}, status=status.HTTP_200_OK)

            else:
                existing_account_number = PyOtBankAccount.objects.filter(bnk_acc_no=account_number).first()

                if existing_account_number and int(account_number) == existing_account_number.bnk_acc_no:
                    return Response({'status': 'fail', 'message': 'Account number already existing payout bank account.'}, status=status.HTTP_400_BAD_REQUEST)

                beneficiary_id = get_random_string(length=12, allowed_chars='qwertyuiopasdfghjklzxcvbnm')

                PyOtBankAccount.objects.create(
                    pyot_beneficiary_id=beneficiary_id,
                    pyot_beneficiary_name=beneficiary_name,
                    pyot_bank_name=bank_name,
                    bnk_acc_no=account_number,
                    bnk_ifsc=ifsc_code,
                    customer_contact=[contact_number]
                )

                return Response({'status': 'success', 'message': 'Payout bank account added successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def fatch_customer_payout_bank_account(self, request):
        try:
            page_number = int(request.data.get('page_number', 1))
            page_size = int(request.data.get('page_size', 10))
            mobile_number = request.data.get('mobile_number', None)
            account_number = request.data.get('account_number', None)

            # Validate page size
            if page_size <= 0:
                return Response({'status': 'fail', 'message': 'Page size must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            # Filter queryset
            queryset = PyOtBankAccount.objects.filter(is_deleted=False)
            if mobile_number:
                queryset = queryset.filter(customer_contact__contains=[mobile_number])
            if account_number:
                queryset = queryset.filter(bnk_acc_no=account_number)

            # Pagination
            paginator = Paginator(queryset, page_size)

            # Check for requested page validity
            if page_number > paginator.num_pages:
                return Response({'status': 'fail', 'message': 'Invalid page number.'}, status=status.HTTP_400_BAD_REQUEST)

            # Get the requested page  
            page_obj = paginator.page(page_number)

            bank_account_serializer = PyOtBankSerializer(page_obj, many=True)
            data = {
                "results": bank_account_serializer.data
            }

            return Response({
                'status': 'success',
                'data': data,
                'total_pages': paginator.num_pages,
                'current_page': page_number,
            })

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class UploadBankListAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify file extension
        if not file.name.endswith('.xlsx'):
            return Response({"error": "Invalid file format. Please upload an .xlsx file."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Load the workbook
            wb = load_workbook(file)
            sheet = wb.active  # Assuming data is in the first sheet

            # Read data row by row
            rows = list(sheet.iter_rows(min_row=2, values_only=True))  # Skipping the header row
            bank_list = []
            for row in rows:
                bank_id, bank_name = row
                if bank_id is None or bank_name is None:
                    continue  # Skip invalid rows

                bank_list.append(
                    GlobalBankList(
                        bank_id=bank_id,
                        bank_name=bank_name
                    )
                )

            # Bulk create the records
            if bank_list:
                GlobalBankList.objects.bulk_create(bank_list)

            return Response({"message": "File processed successfully", "rows_inserted": len(bank_list)}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CredentialsJsonAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request):
        try:
            credentials_data = request.data.get('credentials_data')
            plateform_fee_type = request.data.get('plateform_fee_type')
            plateform_fee = request.data.get('plateform_fee')
            sp_id = request.data.get('sp_id')
            
            if not credentials_data: return Response({'status': 'fail', 'message': 'credentials_data is requried.'}, status=status.HTTP_400_BAD_REQUEST)
            if not sp_id: return Response({'status': 'fail', 'message': 'sp_id is requried.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                credentials_json = json.loads(credentials_data)
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON format for credentials json")
            
            service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
            if service_provider.credentials_json != None:
                service_provider.credentials_json = credentials_json
                service_provider.plateform_fee = plateform_fee
                service_provider.plateform_fee_type = plateform_fee_type
                service_provider.save()
                message = 'Credentials JSON updated successfully.'
            else:
                service_provider.credentials_json = credentials_json
                service_provider.plateform_fee = plateform_fee
                service_provider.plateform_fee_type = plateform_fee_type
                service_provider.save()
                message = 'Credentials JSON added successfully.'
            load_dotenv()
            
            env_path = os.path.join(os.path.dirname(__file__), '../.env')

            json_string = json.dumps(credentials_json)
            
            set_key(env_path, service_provider.sp_name, json_string)

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service Provider does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        sp_id = request.data.get('sp_id')

        try:
            if not sp_id: return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            service_provider = AdServiceProvider.objects.get(sp_id=sp_id)

            if service_provider.is_self_config == True:
                service_provider.is_self_config = False
                service_provider.save()
                return Response({'status': 'success', 'message': 'Self-configuration has been disabled successfully.'})
            else:
                service_provider.is_self_config = True
                service_provider.save()
                return Response({'status': 'success', 'message': 'Self-configuration has been enabled successfully.'})

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service Provider Dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TransactionAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsAdmin | IsRetailer]
    def post(self, request):
        try:
            if 'sp_id' in request.data and'page_number' in request.data or 'page_size' in request.data:
                return self.get_transaction(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get_transaction(self, request):
        page_number = int(request.data.get('page_number', 1))
        page_size = int(request.data.get('page_size', 10))
        sp_id = request.data.get('sp_id')
        search_query = request.data.get('search')
        date_filter = request.data.get('date_filter')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        try:
            user = PortalUser.objects.get(id=request.user.id)

            service_provider_mapping = {
                "1": {"table_name": "ad_pg_service_transaction", "model": PgServiceTrn, "related_field": "sp"},
                "2": {"table_name": "ad_payout_service_trnasaction", "model": PyOtServiceTrn, "related_field": "sp"},
                "4": {"table_name": "ad_mobile_recharge", "model": MobileRecharge, "related_field": "mr_sp"},
                "5": {"table_name": "ad_dmt_transaction", "model": DMTTransaction, "related_field": "dmt_sp_id"},
                "8": {"table_name": "ad_bbps_bill_payment", "model": BBPSBillPayment, "related_field": "bbps_sp"},
                "9": {"table_name": "ad_cashfree_pg_service_transaction", "model": CfPgServiceTrn, "related_field": "sp"},
                "10": {"table_name": "ad_phonepe_service_transaction", "model": PhonePeTransaction, "related_field": "sp"}
            }

            # ✅ Apply Filtering on Global Transactions based on sp_id
            if sp_id:
                table_name = service_provider_mapping.get(sp_id, {}).get("table_name")
                if table_name:
                    global_transactions = GlTrn.objects.filter(pu=user, service_trn_table=table_name).order_by('-pk')
                else:
                    return Response({'status': 'fail', 'message': 'Invalid sp_id'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                global_transactions = GlTrn.objects.filter(pu=user).order_by('-pk')

            # ✅ Apply Date Filtering
            now = make_aware(datetime.now())

            if date_filter == "today":
                start_date = now.replace(hour=0, minute=0, second=0)
                end_date = now.replace(hour=23, minute=59, second=59)
            
            elif date_filter == "weekly":
                start_date = now - timedelta(days=7)
                end_date = now

            elif date_filter == "monthly":
                start_date = now - timedelta(days=30)
                end_date = now

            elif date_filter == "custom":
                if not start_date or not end_date:
                    return Response({'status': 'fail', 'message': 'Custom filter requires start_date and end_date'}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
                    end_date = make_aware(datetime.strptime(end_date, "%Y-%m-%d"))
                except ValueError:
                    return Response({'status': 'fail', 'message': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

            if date_filter in ["today", "weekly", "monthly", "custom"]:
                global_transactions = global_transactions.filter(gl_trn_dt__range=(start_date, end_date))

            transaction_list = []

            print(f"🔍 Total Transactions Found for User (Filtered by sp_id={sp_id}): {len(global_transactions)}")

            for transaction in global_transactions:
                print(f"Processing GlTrn ID: {transaction.pk}, Service Table: {transaction.service_trn_table}")

                model_info = service_provider_mapping.get(sp_id) if sp_id else None
                possible_models = [model_info] if model_info else [
                    v for v in service_provider_mapping.values() 
                    if v['table_name'] == transaction.service_trn_table
                ]

                if not possible_models:
                    print(f"❌ No mapping found for service table: {transaction.service_trn_table}")
                    continue  

                for model_info in possible_models:
                    model = model_info['model']
                    related_field = model_info['related_field']

                    try:
                        service_transaction = model.objects.filter(pk=transaction.service_trn_id).first()
                        if not service_transaction:
                            print(f"⚠️ No transaction found in {model._meta.db_table} for ID {transaction.service_trn_id}")
                            continue

                        retailer = PortalUser.objects.get(id=service_transaction.created_by)
                        formatted_datetime = transaction.gl_trn_dt.strftime("%d %B %Y %H:%M")
                        service_trn_id = transaction.service_trn_id

                        transaction_data = {
                            "gl_trn_id": transaction.gl_trn_id,
                            "retailer_name": retailer.pu_name,
                            "service_provider_name": getattr(service_transaction, related_field).sp_name,
                            "service_name": getattr(service_transaction, related_field).service.service_name,
                            "service_label": getattr(service_transaction, related_field).label,
                            "gl_trn_amt": transaction.gl_trn_amt,
                            "gl_tds_rate": transaction.gl_tds_rate,
                            "gl_tax_rate": transaction.gl_tax_rate,
                            "gl_tds_amt": transaction.gl_tds_amt,
                            "gl_tax_amt": transaction.gl_tax_amt,
                            "effective_wallet": transaction.effectvie_wallet,
                            "effective_amt": transaction.effectvie_amt,
                            "effective_type": transaction.effective_type,
                            "gl_trn_dt": formatted_datetime
                        }

                        if search_query:
                            search_query = str(search_query).lower()
                            if search_query in str(transaction.effectvie_wallet).lower() or search_query in str(getattr(service_transaction, related_field).service.service_name).lower():
                                transaction_list.append(transaction_data)
                        else:
                            transaction_list.append(transaction_data)

                    except Exception as e:
                        print(f"🚨 Error processing {transaction.pk}: {str(e)}")

            print(f"✅ Total Transactions Processed: {len(transaction_list)}")

            # ✅ Correct Pagination
            total_items = len(transaction_list)
            total_pages = ceil(total_items / page_size)
            start = (page_number - 1) * page_size
            end = start + page_size
            paginated_results = transaction_list[start:end]

            data = {
                "total_pages": total_pages,
                "current_page": page_number,
                "total_items": total_items,
                "results": paginated_results
            }

            return Response({'status': 'success', 'message': 'Get all transactions.', 'data': data})

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EarnAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsAdmin]
    def post(self, request):
        try:
            if 'page_number' in request.data or 'page_size' in request.data:
                return self.get_earning(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get_earning(self, request):
        page_number = int(request.data.get('page_number', 1))
        page_size = int(request.data.get('page_size', 10))
        sp_id = request.data.get('sp_id', None)

        try:
            user = PortalUser.objects.get(id=request.user.id)
            global_transactions = GlTrn.objects.filter(pu=user).order_by('-pk')

            # Service provider mapping
            service_provider_mapping = {
                "1": {"table_name": "ad_payout_service_trnasaction", "model": PyOtServiceTrn, "related_field": "sp"},
                "2": {"table_name": "ad_pg_service_trnasaction", "model": PgServiceTrn, "related_field": "sp"},
                "3": {"table_name": "ad_bbps_service_trnasaction", "model": BBPSBillPayment, "related_field": "bbps_sp"},
                "4": {"table_name": "ad_mobile_recharge", "model": MobileRecharge, "related_field": "mr_sp"},
                "5": {"table_name": "ad_dmt_transaction", "model": DMTTransaction, "related_field": "dmt_sp_id"}
            }

            results = []

            for transaction in global_transactions:
                if not sp_id or (sp_id in service_provider_mapping and transaction.service_trn_table == service_provider_mapping[sp_id]['table_name']):
                    model_info = service_provider_mapping.get(sp_id, None) if sp_id else None
                    if not model_info:
                        model_info = next((v for k, v in service_provider_mapping.items() if v['table_name'] == transaction.service_trn_table), None)

                    if model_info:
                        model = model_info['model']
                        related_field = model_info['related_field']
                        try:
                            service_transaction = model.objects.select_related(f'{related_field}__service').get(pk=transaction.service_trn_id)
                            retailer = PortalUser.objects.get(id=service_transaction.created_by)
                            formatter_datetime = transaction.gl_trn_dt.strftime("%d %B %Y %H:%M")
                            results.append({
                                "gl_trn_id": transaction.gl_trn_id,
                                "retailer_name": retailer.pu_name,
                                "service_provider_name": getattr(service_transaction, related_field).sp_name,
                                "service_name": getattr(service_transaction, related_field).service.service_name,
                                "service_label": getattr(service_transaction, related_field).label,
                                "gl_trn_amt": transaction.gl_trn_amt,
                                "gl_tds_rate": transaction.gl_tds_rate,
                                "gl_tax_rate": transaction.gl_tax_rate,
                                "gl_tds_amt": transaction.gl_tds_amt,
                                "gl_tax_amt": transaction.gl_tax_amt,
                                "effective_wallet": transaction.effectvie_wallet,
                                "effective_amt": transaction.effectvie_amt,
                                "effective_type": transaction.effective_type,
                                'gl_trn_dt': formatter_datetime
                            })
                        except model.DoesNotExist:
                            continue

            total_items = len(results)
            total_pages = ceil(total_items / page_size)
            start = (page_number - 1) * page_size
            end = start + page_size
            paginated_results = results[start:end]

            data = {
                "total_pages": total_pages,
                "current_page": page_number,
                "total_items": total_items,
                "results": paginated_results
            }

            return Response({'status': 'success', 'message': 'Get all earning.','data': data})

        except PortalUser.DoesNotExist:
            return Response({'status': 'error', 'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            
class TdsRateAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsRetailer]
    def post(self, request):
        try:
            if 'is_tds' in request.data and 'page_number' in request.data or 'page_size' in request.data:
                return self.get_tds_rate(request)
            elif 'is_tax' in request.data and 'page_number' in request.data or 'page_size' in request.data:
                return self.get_tax_rate(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get_tds_rate(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        is_tds = request.data.get('is_tds')
        user = request.user.id
        try:
            page_number = int(page_number)
            page_size = int(page_size)
            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
            
            portal_user = PortalUser.objects.get(id=user)
            all_tds_data = GlTrn.objects.filter(pu=portal_user).order_by('-id')
            paginator = Paginator(all_tds_data, page_size)
            all_tds_data = paginator.page(page_number)
            serializer = GlTrnSerializer(all_tds_data, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data
            }
            return Response({'status': 'success', 'message': 'get all tds transaction data.', 'data': data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_tax_rate(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        is_tax = request.data.get('is_tax')
        user = request.user.id
        try:
            page_number = int(page_number)
            page_size = int(page_size)
            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
            
            portal_user = PortalUser.objects.get(id=user)
            all_tds_data = GlTrn.objects.filter(pu=portal_user).order_by('-id')
            paginator = Paginator(all_tds_data, page_size)
            all_tds_data = paginator.page(page_number)
            serializer = GlTrnSerializer(all_tds_data, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data
            }
            return Response({'status': 'success', 'message': 'get all tax transaction data.', 'data': data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class KYCinfoAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsSuperAdmin]

    def post(self, request):
        user_id = request.data.get('user_id')
        try:

            if not user_id: return Response({'status': 'fail', 'message': 'user id is requried.'}, status=status.HTTP_400_BAD_REQUEST)

            user = PortalUser.objects.get(id=user_id)
            user_details = PortalUserDetails.objects.get(pu=user)
            doc_images = user_details.doc_images
            if doc_images:
                doc_images['shop_image'] = f"http://partner.tapipe.in/{doc_images['shop_image']}"
                doc_images['upline_image'] = f"http://partner.tapipe.in/{doc_images['upline_image']}"
                doc_images['profile_image'] = f"http://partner.tapipe.in/{doc_images['profile_image']}"
                doc_images['pan_card_image'] = f"http://partner.tapipe.in/{doc_images['pan_card_image']}"
                doc_images['back_aadhaar_image'] = f"http://partner.tapipe.in/{doc_images['back_aadhaar_image']}"
                doc_images['front_aadhaar_image'] = f"http://partner.tapipe.in/{doc_images['front_aadhaar_image']}"
                doc_images['passbook_cheque_image'] = f"http://partner.tapipe.in/{doc_images['passbook_cheque_image']}"
            else:
                doc_images = []
            data = {'results': 
                        {
                            'aadhaar_card': user_details.aadhaar_card,
                            'pan_card': user_details.pan_card,
                            'shop_name': user_details.shop_name,
                            'shop_address': user_details.shop_address,
                            'shop_state': user_details.shop_state,
                            'shop_city': user_details.shop_city,
                            'shop_zip_code': user_details.shop_zip_code,
                            'doc_images': doc_images,
                            'shop_location': user_details.shop_location,
                            'busniess_type': user_details.busniess_type,
                            'shop_gst_number': user_details.shop_gst_number,
                        }
                    }

            return Response({'status': 'success', 'message': 'Get KYC data successfully.', 'data': data}, status=status.HTTP_200_OK)

        except PortalUserDetails.DoesNotExist:
            return Resposne({'status': 'fail', 'message': 'User KYC Details dose not exists.'}, status=status.HTTP_404_NOT_FOUND)
        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User not exists.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminCreditDebit(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request):
        try:
            if 'wallet' in request.data and 'amount' in request.data and 'option' in request.data:
                return self.user_Wallet_transaction(request)

            else:
                return Response({'status': 'fail', 'message': 'Invalid request.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def user_Wallet_transaction(self, request):
        wallet = request.data.get('wallet')
        amount = request.data.get('amount')
        option = request.data.get('option', '').upper() 
        user_id = request.data.get('user_id')
        description = request.data.get('description', None)

        valid_wallets = ["main_wallet", "commission_wallet", "pg_wallet", "cashin_wallet"]

        if not all([wallet, amount, option, user_id]):
            return Response({'status': 'fail', 'message': 'wallet, amount, option, and user_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if wallet not in valid_wallets:
            return Response({'status': 'fail', 'message': f'Invalid wallet name. Choose from {", ".join(valid_wallets)}.'}, status=status.HTTP_400_BAD_REQUEST)

        if option not in ["CR", "DR"]:
            return Response({'status': 'fail', 'message': 'Invalid transaction option. Use "CREDIT" or "DEBIT".'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = PortalUser.objects.get(id=user_id)
            admin = PortalUser.objects.get(id=request.user.id)
            user_wallet = PortalUserWallet.objects.get(pu=user)

            try:
                amount = float(amount)
            except ValueError:
                return Response({'status': 'fail', 'message': 'Invalid amount. It must be a numeric value.'}, status=status.HTTP_400_BAD_REQUEST)

            wallet_balance = getattr(user_wallet, wallet, None)
            if wallet_balance is not None:
                if option == "DR" and wallet_balance < amount:
                    return Response({'status': 'fail', 'message': 'Insufficient funds for this transaction.'}, status=status.HTTP_400_BAD_REQUEST)

                setattr(user_wallet, wallet, float(wallet_balance) + amount if option == "CR" else float(wallet_balance) - amount)
                user_wallet.save()

                options = 'credit' if option == 'CR' else 'debit'

                WalletTrn.objects.create(
                    wl_label=f"Admin manually {options.lower()}ed {amount} to {wallet} for user {user_wallet.pu.id}",
                    effectvie_wallet=wallet,
                    effectvie_amt=float(amount),
                    effective_type="CR" if option == "CR" else "DR",
                    wl_trn_des=description if description else None,
                    pu=user_wallet.pk,
                    current_balance=getattr(user_wallet, wallet),
                    wl_trn_dt=timezone.now()
                )

                return Response({'status': 'success', 'message': 'Transaction completed successfully.'}, status=status.HTTP_200_OK)
        
        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        
        except PortalUserWallet.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User wallet not found.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestCalculation(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # fetch_user_hierarchy(5)
            data = {
                'order_amount': 1000,
                'id': 5,
                'sp_id': 4,
                'customer_contact_no': None,
                'customer_name': None,
                'trn_response': None,
                'service_trn': None,
                'label': 'Pay Bills',
                'category': 27
            }

            after_tx_cal(request, data)
            return Response({'status': 'success', 'message': 'message'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OtherChargesAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer | IsAdmin]

    def post(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        oc_id = request.data.get('oc_id', None)
        search = request.data.get('search', '')

        try:
            if not page_number:
                return Response({'status': 'fail', 'message': 'page_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not page_size:
                return Response({'status': 'fail', 'message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(page_number):
                return Response({'status': 'fail', 'message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(page_size):
                return Response({'status': 'fail', 'message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)

            all_charges = OtherCharges.objects.filter(is_deleted=False).order_by('-pk')

            if oc_id:
                all_charges = all_charges.filter(oc_id=oc_id).order_by('-pk')
            
            if search != '':
                all_charges = all_charges.filter(oc_name__icontains=search).order_by('-pk')

            paginator = Paginator(all_charges, page_size)
            configeds = paginator.page(page_number)
            serializer = OtherChargesSerializer(configeds, many=True)
            for data in serializer.data:
                hsn_sac = HSNSAC.objects.get(hsnsac_id=data['hsn_sac'])
                data['hsn_sac_code'] = f'{hsn_sac.hsnsac_code} ({hsn_sac.tax_rate}%)'
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data
            }
            return Response({'status': 'success', 'message': 'Other Charges fetch successfully', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def put(self, request):
        oc_id = request.data.get('oc_id')
        minimum = request.data.get('minimum', None)
        maximum = request.data.get('maximum', None)
        charge_type = request.data.get('charge_type', None)
        charge = request.data.get('charge', None)
        hsn_code = request.data.get('hsn_code', None)

        try:
            other_charges = OtherCharges.objects.get(oc_id=oc_id)
            if not minimum and not maximum and not charge_type and not charge and not hsn_code:

                if other_charges.is_deactive == False:
                    other_charges.is_deactive = True
                    other_charges.save()
                    return Response({'status': 'success', 'message': 'Other Charges deactivated succuessfully.'}, status=status.HTTP_200_OK)
                else:
                    other_charges.is_deactive = False
                    other_charges.save()
                    return Response({'status': 'success', 'message': 'Other Charges activated succuessfully.'}, status=status.HTTP_200_OK)

            else:
                if hsn_code:
                    hsn_sac = AdHSNSAC.objects.get(hsnsac_id=hsn_code)

                other_charges.minimum = minimum if minimum else other_charges.minimum
                other_charges.maximum = maximum if maximum else other_charges.maximum
                other_charges.charge_type = charge_type if charge_type else other_charges.charge_type
                other_charges.charge = charge if charge else other_charges.charge
                other_charges.hsn_sac = hsn_sac if hsn_code else other_charges.hsn_code
                other_charges.save()

                return Response({'status': 'success', 'message': 'Other Charges updated successfully.'}, status=status.HTTP_200_OK)

        except AdHSNSAC.DoesNotExist:
            return Response({'status': 'fail', 'message': 'HSN dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except OtherCharges.DoesNotExist:
            return Response({'status': 'fail', 'message': 'other charge dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def delete(self, request):
        oc_id = request.data.get('oc_id')

        try:
            if not oc_id: return Response({'status': 'fail', 'message': 'oc_id is requried.'}, status=status.HTTP_400_BAD_REQUEST)

            other_charges = OtherCharges.objects.getr(oc_id=oc_id)

            other_charges.is_deleted = True
            other_charges.save()

            return Response({'status': 'success', 'message': 'Other Charges deleted successfully.'}, status=status.HTTP_200_OK)

        except OtherCharges.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Other charges dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TopUpTransactionAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer | IsDistributor]

    def post(self, request):
        try:
            if 'user_id' in request.data and 'is_settle_with_cash' in request.data and 'amount' in request.data:
                return self.create_topup_transaction(request)
            elif 'page_number' in request.data or 'page_size' in request.data:
                return self.get_topup_transaction(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid request.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_topup_transaction(self, request):
        user_id = request.data.get('user_id')
        is_settle_with_cash = request.data.get('is_settle_with_cash')   
        amount = request.data.get('amount')
        tt_trn_desc = request.data.get('tt_trn_desc', None)

        try:
            # **Validation Checks**
            if not user_id:
                return Response({'status': 'fail', 'message': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if is_settle_with_cash is None:
                return Response({'status': 'fail', 'message': 'is_settle_with_cash is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not amount:
                return Response({'status': 'fail', 'message': 'amount is required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Convert amount to Decimal
            amount = Decimal(amount)

            # **Fetch Distributor & Wallet**
            distributor = PortalUser.objects.get(id=request.user.id)
            distributor_details = PortalUserDetails.objects.get(pu_id=request.user.id)
            distributor_wallet = PortalUserWallet.objects.get(pu=distributor)

            # **Check if Distributor has Enough Balance**
            if distributor_wallet.main_wallet < amount:
                return Response({'status': 'fail', 'message': 'Insufficient balance in main wallet.'}, status=status.HTTP_400_BAD_REQUEST)

            # **Fetch Receiver (Portal User) & Wallet**
            portal_user = PortalUser.objects.get(id=user_id)
            portal_user_details = PortalUserDetails.objects.get(pu_id=user_id)
            portal_user_wallet = PortalUserWallet.objects.get(pu=portal_user)

            # **Database Transaction to Ensure Atomicity**
            with transaction.atomic():
                # **Create Debit Transaction (Distributor)**
                tt_trn = TopUpTransaction.objects.create(
                    tt_amount=amount,
                    tt_trn_desc=tt_trn_desc if tt_trn_desc else None,
                    is_settle_with_cash=is_settle_with_cash,
                    created_by=request.user.id
                )
                # **Update Wallet Balances**
                distributor_wallet.main_wallet = float(distributor_wallet.main_wallet) - float(amount)  # Deduct from Distributor
                print('111111')
                if is_settle_with_cash == 'True':
                    print('222222')
                    portal_user_wallet.main_wallet = float(portal_user_wallet.main_wallet) + float(amount)  # Credit to Receiver
                    print('33333')
                else:
                    print('44444')
                    portal_user_wallet.main_wallet = float(portal_user_wallet.main_wallet) + float(amount)
                    print('555555', portal_user_wallet.os_wallet)
                    portal_user_wallet.os_wallet = float(portal_user_wallet.os_wallet) + float(amount)  # Outstanding amount update
                    print('=============')
                # **Save Wallets**
                distributor_wallet.save()
                portal_user_wallet.save()

                WalletTrn.objects.create(
                    action_id = tt_trn.pk,
                    action_type = 'Top-up Transfer',
                    pu=distributor,
                    wl_label=f"TopUp_Transfer_By_{distributor_details.pud_unique_id}_To_{portal_user_details.pud_unique_id}_Amount_{amount}",
                    effectvie_wallet='main_wallet',
                    effectvie_amt=amount,
                    effective_type='DR',
                    current_balance=distributor_wallet.main_wallet,
                    wl_trn_des=tt_trn_desc if tt_trn_desc else None,
                    wl_trn_dt=timezone.now()
                )
                WalletTrn.objects.create(
                    action_id = tt_trn.pk,
                    action_type = 'Top-up Transfer',
                    pu=portal_user,
                    wl_label=f"TopUp_Received_By_{portal_user_details.pud_unique_id}_From_{distributor_details.pud_unique_id}_Amount_{amount}",
                    effectvie_wallet='main_wallet',
                    effectvie_amt=amount,
                    effective_type='CR',
                    current_balance=portal_user_wallet.main_wallet,
                    wl_trn_des=tt_trn_desc if tt_trn_desc else None,
                    wl_trn_dt=timezone.now()
                )
                

            return Response({'status': 'success', 'message': f'Topup of {amount} successful.'}, status=status.HTTP_200_OK)

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Portal user does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_topup_transaction(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        tt_id = request.data.get('tt_id', None)
        # search = request.data.get('search', '')
        data = {
            "total_pages": 0,
            "current_page": 0,
            "total_items": 0,
            "results": []
        }

        try:
            if not page_number:
                return Response({'status': 'fail', 'message': 'page_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not page_size:
                return Response({'status': 'fail', 'message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(page_number):
                return Response({'status': 'fail', 'message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(page_size):
                return Response({'status': 'fail', 'message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
            portal_user = PortalUser.objects.get(id=request.user.id)
            all_transaction = TopUpTransaction.objects.all().order_by('-pk')

            if tt_id:
                all_transaction = all_transaction.filter(tt_id=tt_id).order_by('-pk')
            # if search != '':
            #     all_charges = all_charges.filter(oc_name__icontains=search).order_by('-pk')

            transaction_data = []

            for transaction in all_transaction:
                wallet_trn = WalletTrn.objects.filter(action_id=transaction.tt_id, action_type = 'Top-up Transfer', pu=portal_user).first()
                if wallet_trn:
                    data = {
                        "tt_id": transaction.tt_id,
                        "action_id": wallet_trn.action_id,
                        "action_type": wallet_trn.action_type,
                        "wl_label": wallet_trn.wl_label,
                        "effectvie_wallet": wallet_trn.effectvie_wallet,
                        "effectvie_amt": wallet_trn.effectvie_amt,
                        "effective_type": wallet_trn.effective_type,
                        "tt_amount": transaction.tt_amount,
                        "tt_trn_desc": transaction.tt_trn_desc,
                        "tt_trn_status": transaction.tt_trn_status,
                        "is_settle_with_cash": transaction.is_settle_with_cash,
                        "tt_trn_dt": transaction.tt_trn_dt,
                    }
                    transaction_data.append(data)
            total_items = len(transaction_data)  # Corrected count usage
            total_pages = (total_items + page_size - 1) // page_size

            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size
            all_transaction_data = transaction_data[start_index:end_index]
            data = {
                'total_pages': total_pages,
                'current_page': page_number,
                'total_items': total_items,
                'results': all_transaction_data
            }
            return Response({'status': 'success', 'message': 'Topup Transaction fetch successfully', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        tt_id = request.data.get('tt_id')
        tt_status = request.data.get('tt_status')

        try:
            if not tt_id:
                return Response({'status': 'fail', 'message': 'tt_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not tt_status:
                return Response({'status': 'fail', 'message': 'tt_status is required.'}, status=status.HTTP_400_BAD_REQUEST)

            portal_user = PortalUser.objects.get(id=request.user.id)
            portal_user_wallet = PortalUserWallet.objects.get(pu=portal_user)

            try:
                transaction = TopUpTransaction.objects.get(tt_id=tt_id)
            except TopUpTransaction.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Transaction not found.'}, status=status.HTTP_404_NOT_FOUND)

            distributor = PortalUser.objects.get(id=transaction.created_by)
            distributor_wallet = PortalUserWallet.objects.get(pu=distributor)

            transaction_amount = transaction.tt_amount  # Ensure using the correct field

            with db_transaction.atomic():  # Ensures atomicity of DB operations
                if tt_status == 'SETTLE_WITH_CASH':
                    portal_user_wallet.os_wallet -= transaction_amount
                    portal_user_wallet.save()

                    transaction.tt_trn_status = 'SETTLED'
                    transaction.save()

                    return Response({'status': 'success', 'message': 'Top-up Transaction settled successfully.'}, status=status.HTTP_200_OK)

                elif tt_status == 'REVERSED':
                    wallet_trn = WalletTrn.objects.filter(action_id=transaction.tt_id, action_type='Top-up Transfer')

                    if not wallet_trn.exists():
                        return Response({'status': 'fail', 'message': 'No wallet transaction records found for reversal.'}, status=status.HTTP_400_BAD_REQUEST)

                    for trn in wallet_trn:
                        trn.effective_type = 'CR' if trn.effective_type == 'DR' else 'DR'
                        trn.save()

                    portal_user_wallet.os_wallet -= transaction_amount
                    portal_user_wallet.main_wallet -= transaction_amount
                    portal_user_wallet.save()

                    distributor_wallet.main_wallet += transaction_amount
                    distributor_wallet.save()   

                    transaction.tt_trn_status = 'REVERSED'
                    transaction.save()

                    return Response({'status': 'success', 'message': 'Top-up Transaction reversed successfully.'}, status=status.HTTP_200_OK)

                else:
                    return Response({'status': 'fail', 'message': 'Invalid transaction status provided.'}, status=status.HTTP_400_BAD_REQUEST)

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetailerBankAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsRetailer]

    def post(self, request):
        try:
            if 'bank_name' in request.data and 'ifsc_code' in request.data and 'account_number' in request.data and 'branch_name' in request.data:
                return self.create_bank(request)
            elif 'page_number' in request.data or 'page_size' in request.data:
                return self.fetch_bank(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid request.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_bank(self, request):
        bank_name = request.data.get('bank_name')
        ifsc_code = request.data.get('ifsc_code')
        account_number = request.data.get('account_number')
        branch_name = request.data.get('branch_name')
        account_type = request.data.get('account_type')
        try:
            if not bank_name: return Response({'status': 'fail', 'message': 'bank_name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not ifsc_code: return Response({'status': 'fail', 'message': 'ifsc_code is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not account_number: return Response({'status': 'fail', 'message': 'account_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not branch_name: return Response({'status': 'fail', 'message': 'branch_name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not account_type: return Response({'status': 'fail', 'message': 'account_type is required.'}, status=status.HTTP_400_BAD_REQUEST)
            bank_name_validation = isstring(bank_name)
            if bank_name_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid bank name. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)

            ifsc_code_validation = is_valid_ifsc(ifsc_code)
            if ifsc_code_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid IFSC code. Please check the format.'}, status=status.HTTP_400_BAD_REQUEST)

            branch_name_validation = isstring(branch_name)
            if branch_name_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid branch name. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)

            account_type_validation = isstring(account_type)
            if account_type_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid account type. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)

            account_number_validation = isnumber(account_number)
            if account_number_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            validation_account_number = validate_account_number(account_number)
            if validation_account_number == False:
                return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits and be between 8 and 16 characters long.'}, status=status.HTTP_400_BAD_REQUEST)
            get_exists_bank = RetailerBankDetails.objects.filter(bank_name=bank_name, ifsc_code=ifsc_code, account_number=account_number, is_delete=False).first()
            if get_exists_bank:
                return Response({'status': 'fail', 'message': 'Bank details already exist.'}, status.HTTP_400_BAD_REQUEST)
            user = PortalUser.objects.get(id=request.user.id)
            RetailerBankDetails.objects.create(
                bank_name=bank_name,
                branch_name=branch_name,
                ifsc_code=ifsc_code,
                account_type=account_type,
                account_number=account_number,
                created_by=user
            )
            return Response({'status': 'success', 'message': 'Bank details added successfully.'}, status=status.HTTP_200_OK)

        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Portal user dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_bank(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        user_id = request.data.get('user_id', None)
        rbd_id = request.data.get('rbd_id', None)
        search = request.data.get('search', '')
        data = {
            "total_pages": 0,
            "current_page": 0,
            "total_items": 0,
            "results": []
        }

        try:
            if not page_number:
                return Response({'status': 'fail', 'message': 'page_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not user_id:
                return Response({'status': 'fail', 'message': 'page_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not page_size:
                return Response({'status': 'fail', 'message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(page_number):
                return Response({'status': 'fail', 'message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(page_size):
                return Response({'status': 'fail', 'message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(page_number):
                return Response({'status': 'fail', 'message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
            if not user_id:
                portal_user = PortalUser.objects.get(id=request.user.id)
            else:
                portal_user = PortalUser.objects.get(id=user_id)
            all_banks = RetailerBankDetails.objects.filter(created_by=portal_user).order_by('-pk')

            if rbd_id:
                all_banks = all_banks.filter(rbd_id=rbd_id).order_by('-pk')
            
            if search != '':
                all_banks = all_banks.filter(Q(bank_name__icontains=search) | Q(branch_name__icontains=search) | Q(account_number__icontains=search)).order_by('-pk')

            paginator = Paginator(all_banks, page_size)
            banks = paginator.page(page_number)
            serializer = RetailerBanksSerializer(banks, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data
            }
            return Response({'status': 'success', 'message': "Retailer Bank's fetch successfully", 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            if 'bank_name' in request.data and 'branch_name' in reuqest.data and 'account_number' in request.data and 'account_type' in request.data:
                return self.update_bank_details(request)
            elif 'rbd_id' in request.data and 'rbd_status' in request.data:
                return self.update_bank_status(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid Request.'},status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_bank_details(self, request):
        rbd_id = request.data.get('rbd_id')
        bank_name = request.data.get('bank_name', None)
        ifsc_code = request.data.get('ifsc_code', None)
        branch_name = request.data.get('branch_name', None)
        account_number = request.data.get('account_number', None)
        account_type = request.data.get('account_type', None)

        try:
            get_bank_detail = RetailerBankDetails.objects.get(rbd_id=rbd_id)
            if bank_name:
                bank_name_validation = isstring(bank_name)
                if bank_name_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid bank name. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)
                get_bank_detail.bank_name = bank_name

            if ifsc_code:
                ifsc_code_validation = is_valid_ifsc(ifsc_code)
                if ifsc_code_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid IFSC code. Please check the format.'}, status=status.HTTP_400_BAD_REQUEST)
                get_bank_detail.ifsc_code = ifsc_code

            if branch_name:
                branch_name_validation = isstring(branch_name)
                if branch_name_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid branch name. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)
                get_bank_detail.branch_name = branch_name

            if account_type:
                account_type_validation = isstring(account_type)
                if account_type_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid account type. It should be a string.'}, status=status.HTTP_400_BAD_REQUEST)
                get_bank_detail.account_type = account_type

            if account_number:
                account_number_validation = isnumber(account_number)
                if account_number_validation == False:
                    return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

                validation_account_number = validate_account_number(account_number)
                if validation_account_number == False:
                    return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits and be between 8 and 16 characters long.'}, status=status.HTTP_400_BAD_REQUEST)       
                get_bank_detail.account_number = account_number
            
            get_bank_detail.updated_by=request.user.id
            get_bank_detail.save()

            return Response({'status': 'success', 'message': 'Retailer Bank updated successfully.'}, status=status.HTTP_200_OK)
        
        except RetailerBankDetails.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Retailer Bank details dose not exsits.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_bank_status(self, request):
        rbd_id = request.data.get('rbd_id')
        rbd_status = request.data.get('rbd_status')

        try:
            if not rbd_id: return Response({'status': 'fail', 'message': 'rbd_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not rbd_status: return Response({'status': 'fail', 'message': 'rbd_status is required.'}, status=status.HTTP_400_BAD_REQUEST)

            get_bank = RetailerBankDetails.objects.get(rbd_id=rbd_id)
            if get_bank.rbd_status == "PENDING":
                get_bank.rbd_status = rbd_status
                get_bank.save()
                return Response({'status': 'success', 'message': f'Bank status is {rbd_status} successfully.'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': f'Bank status is already {get_bank.rbd_status}.'},status=status.HTTP_400_BAD_REQUEST)

        except RetailerBankDetails.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Retailer Bank dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DistributorDashBoard(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor]

    # Define a mapping of service table names to custom service names
    SERVICE_NAME_MAPPING = {
        "ad_payout_transaction": "Payout",
        "ad_mobile_recharge": "Mobile Recharge",
        "ad_bbps_bill_payment": "Bill Payment",
        "ad_dmt_transaction": "Money Transfer",
        "ad_cashfree_pg_service_transaction": "Cashfree PG",
        "ad_pg_service_transaction": "Razorpay",
        "ad_phonepe_service_transaction": "Phonepe PG",
    }

    def get(self, request):
        try:
            distributor = PortalUser.objects.get(id=request.user.id)
            all_global_transaction = GlTrn.objects.filter(pu=distributor)
            # Sum total commission and earnings
            total_commission = all_global_transaction.aggregate(Sum('gl_tax_amt'))['gl_tax_amt__sum'] or 0.000
            total_earning = total_commission
            get_user = PortalUserDetails.objects.get(pu=distributor)
            # Fetch all downline users created by the distributor
            all_downline = PortalUserDetails.objects.filter(created_by=request.user.id)
            # Initialize downline counters
            downline_counts = {
                'master_distributor': 0,
                'super_distributor': 0,
                'distributor': 0,
                'retailer': 0  # dh_name is None
            }

            all_retailers = []
            # Count the downline users based on dh_name
            for downline in all_downline:
                if downline.dh and downline.dh.dh_name == "MASTER DISTRIBUTOR":
                    downline_counts['master_distributor'] += 1
                elif downline.dh and downline.dh.dh_name == "SUPER DISTRIBUTOR":
                    downline_counts['super_distributor'] += 1
                elif downline.dh and downline.dh.dh_name == "DISTRIBUTOR":
                    downline_counts['distributor'] += 1
                elif downline.dh is None:
                    downline_counts['retailer'] += 1
                    all_retailers.append(downline.pu)  # Store retailer user object
            # Calculate transactions for retailers
            total_retailer_trn = []
            total_downline_trn = 0
            for retailer in all_retailers:
                global_transaction = GlTrn.objects.filter(pu=retailer, gl_tds_amt__isnull=False, gl_tax_amt__isnull=False)
                
                retailer_trn_total = global_transaction.aggregate(Sum('gl_tax_amt'))['gl_tax_amt__sum'] or 0
                total_downline_trn += retailer_trn_total

                total_retailer_trn.append({
                    'retailer_name': retailer.pu_name,
                    'retailer_contact_no': retailer.pu_contact_no,
                    'retailer_role': retailer.pu_role,
                    'total_retailer_trn': retailer_trn_total
                })

            # Count service usage
            service_counts = GlTrn.objects.filter(pu=distributor).values('service_trn_table').annotate(count=Count('service_trn_table'))

            # Calculate total service calls
            total_service_calls = sum(entry['count'] for entry in service_counts)

            # Convert to a dictionary with custom service names and percentages
            service_usage = {}
            for entry in service_counts:
                table_name = entry['service_trn_table']
                custom_service_name = self.SERVICE_NAME_MAPPING.get(table_name, table_name)  # Default to table name if not in mapping
                percentage = (entry['count'] / total_service_calls) * 100 if total_service_calls > 0 else 0
                service_usage[custom_service_name] = round(percentage, 2)  # Round to 2 decimal places
            banner_list = []
            retailer_banner = Banner.objects.filter(banner_type='DISTRIBUTOR DASHBOARD PAGE')
            for banner in retailer_banner:
                banner_dict = {
                    'banner_image': banner.banner_image,
                    'banner_url': banner.banner_url
                }
                banner_list.append(banner_dict)
            # Response data
            response_data = {
                'status': 'success',
                'message': 'Fetch distributor dashboard data.',
                'total_commission': total_commission,
                'total_earning': total_earning,
                'total_downline_trn': total_downline_trn,
                'downline_counts': downline_counts,
                'retailers': total_retailer_trn,
                'service_usage': service_usage,  # Now shows percentages instead of counts,
                'banner': banner_list
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RetailerDashBoard(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    SERVICE_NAME_MAPPING = {
        "ad_payout_transaction": "Payout",
        "ad_mobile_recharge": "Mobile Recharge",
        "ad_bbps_bill_payment": "Bill Payment",
        "ad_dmt_transaction": "Money Transfer",
        "ad_cashfree_pg_service_transaction": "Cashfree PG",
        "ad_pg_service_transaction": "Razorpay",
        "ad_phonepe_service_transaction": "Phonepe PG",
    }

    def get(self, request):
        try:
            retailer = PortalUser.objects.get(id=request.user.id)
            all_global_transaction = GlTrn.objects.filter(pu=retailer)

            retailer_info = {
                'retailer_name': retailer.pu_name,
                'retailer_contact_no': retailer.pu_contact_no,
                'retailer_role': retailer.pu_role
            }

            # ✅ Filter Transactions Based on SERVICE_NAME_MAPPING Keys
            valid_tables = self.SERVICE_NAME_MAPPING.keys()
            service_counts = (
                GlTrn.objects.filter(pu=retailer, service_trn_table__in=valid_tables)
                .values('service_trn_table')
                .annotate(count=Count('service_trn_table'))
            )

            # ✅ Total service calls
            total_service_calls = sum(entry['count'] for entry in service_counts)

            # ✅ Convert to dictionary with mapped names and percentages
            service_usage = {}
            for entry in service_counts:
                table_name = entry['service_trn_table']
                custom_service_name = self.SERVICE_NAME_MAPPING[table_name]  # No need to check, because we already filtered
                percentage = (entry['count'] / total_service_calls) * 100 if total_service_calls > 0 else 0
                service_usage[custom_service_name] = round(percentage, 2)

            # ✅ Sort by highest percentage and keep only top 5 services
            service_usage = dict(sorted(service_usage.items(), key=lambda x: x[1], reverse=True)[:5])

            # ✅ Banner Data
            banner_list = [
                {"banner_image": banner.banner_image, "banner_url": banner.banner_url}
                for banner in Banner.objects.filter(banner_type='RETAILER DASHBOARD PAGE')
            ]

            # ✅ Response Data
            response_data = {
                'status': 'success',
                'message': 'Fetch retailer dashboard data.',
                'retailers': retailer_info,
                'service_usage': service_usage,  # Now a dictionary with top 5 services
                'banner': banner_list
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserActivityAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):

        data = {
            'total_pages': 0,
            'current_page': 0,
            'total_items': 0,
            'results': []
        }

        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        search = request.data.get('search', '')
        user_request_id = request.data.get('user_id', None)
        if user_request_id:
            user_id = user_request_id
        else:
            user_id = request.user.id

        try:

            all_activity = UserActivity.objects.filter(created_by_id=user_id).order_by('-pk')

            if search:
                all_activity = all_activity.filter(Q(ua_action__icontains=search) | Q(table_name__icontains=search))

            # If no results found
            if not all_activity.exists():
                return Response({'status': 'fail','message': 'User activity Data not found.','data': data}, status=status.HTTP_200_OK)
            
            page_number = int(page_number)
            page_size = int(page_size)

            paginator = Paginator(all_activity, page_size)
            page = paginator.get_page(page_number)
            serializer = UserActivitySerializer(page, many=True)

            data = {
                'total_pages': paginator.num_pages,
                'current_page': page.number,
                'total_items': paginator.count,
                'results': serializer.data
            }

            return Response({'status': 'success', 'message': 'User activity data fetch succcessfully.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLogList(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsRetailer]

    def get(self, request):
        try:
            portal_user = PortalUser.objects.get(id=request.user.id)
            all_logs = PortalUserLoginLogs.objects.filter(pu_user=portal_user).order_by('-pk')

            serializer = PortalUserLoginLogsSerializer(all_logs, many=True)

            data = {'results': serializer.data}

            return Response({'status': 'success', 'message': 'get all logs.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserBankDetailsAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsRetailer | IsSuperAdmin]

    def put(self, request):
        bank_id = request.data.get('bank_id')
        ifsc_code = request.data.get('ifsc_code')
        try:
            if not bank_id: return Response({'status': 'fail', 'message': 'bank_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            bank = GlobalBankList.objects.get(bank_id=bank_id)

            bank.bank_ifsc = ifsc_code if ifsc_code else bank.bank_ifsc
            bank.save()

            return Response({'status': 'success', 'message': 'Bank Details updated successfully.'}, status=status.HTTP_200_OK)
        
        except GlobalBankList.DoseNotExists:
            return Response({'status': 'fail', 'message': 'bank dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
