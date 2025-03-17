from django.db import transaction
from rest_framework.response import Response
from .views import *
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import status
import requests
import json
import hashlib
import hmac
import uuid
import time
from .commission_calculations import *
from .utilies import *
from rest_framework.exceptions import ValidationError
from .charges_calculation import *
from django.utils.timezone import localtime, make_aware
from datetime import datetime, timedelta

def create_razorpay_pg_order(request, data):
    name = data.get('name')
    email = data.get('email')
    contact_no = data.get('contact_no')
    amount = data.get('amount')
    currency = "INR"

    api_key = "rzp_test_rEAW6ojdmqFEbn"
    secret_key = "mPPJMnQtFd0o5Q1hKTXTgZSe"

    try:
        admin_wallet = check_admin_wallet(request, amount)
        order_payload = {
            "amount": float(amount)*100,
            "currency": currency
        }

        # scheme = "https" if request.is_secure() else "http"
        callback_url = "admin_hub/payment-gateway/razorpay/"

        details = {
            "api_key": api_key,
            "name": name,
            "email": email,
            "contact_no": contact_no,
            "callback_url": callback_url
        }

        url = "https://api.razorpay.com/v1/orders"

        new_order_response = requests.post(url, auth=(api_key, secret_key), json=order_payload)

        if new_order_response.status_code == 200:
            details['order'] = json.loads(new_order_response.text)
            response = {'status': 'success', 'data': details}

        else:
            details['order'] = json.loads(new_order_response.text)
            response = {'status': 'fail', 'data': details}

        return response
    except Exception as e:
        response = {'status': 'error', 'message': str(e)}

        return response


class RazorpayAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer] 

    def post(self, request):
        try:
            if 'contact_no' in request.data and 'code' in request.data:
                return self.verify_contact_no_otp(request)
            if 'contact_no' in request.data:
                return self.verify_contact_no(request)
            elif 'aadhaar_card' in request.data:
                return self.verify_aadhaar_card(request)
            elif 'aadhaar_otp' in request.data and 'ref_id' in request.data:
                return self.verify_aadhaar_otp(request)
            elif 'email' in request.data and 'amount' in request.data:
                return self.create_pg_order(request)
            elif 'razorpay_order_id' in request.data and 'razorpay_payment_id' in request.data and 'razorpay_signature' in request.data:
                return self.verify_razorpay_payment_gateway(request)
            elif 'page_number' in request.data or 'page_size' in request.data:
                return self.fetch_razorpay_pg_transaction(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def verify_contact_no(self, request):
        contact_no = request.data.get('contact_no')
        sp_id = request.data.get('sp_id')
        try:
            if not contact_no: return Response({"status": "fail", "message": "Contact number is required"}, status=status.HTTP_400_BAD_REQUEST)

            if validate_mobile_number(contact_no) == False: return Response({'status': 'fail','message': 'Invalid contact number.'}, status=status.HTTP_400_BAD_REQUEST)

            pg_customer_id = get_random_string(length=9)
            create_transaction = PgServiceTrn(pg_customer_contact_no=contact_no, pg_customer_id=f"RPG_{pg_customer_id}", sp_id=sp_id, created_by=request.user.id, pg_trn_status="pending")
            code = get_random_string(length=6, allowed_chars='0123456789')

            create_transaction.pg_contact_verify_code = code
            create_transaction.pg_verify_code_expire_at = timezone.now() + timedelta(minutes=10)
            create_transaction.save()

            response = mobicomm_submit_sms(contact_no, code)

            # Check the SMS API response status
            if response.status_code == 200:
                response_data = {
                    'status': 'success',
                    'message': 'OTP has been sent via SMS.',
                    'data': {
                        'code': code, 
                        'pg_customer_id': create_transaction.pg_customer_id
                    }
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
                'message': f'Internal server error occurred: {str(e)}',
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_contact_no_otp(self, request):
        pg_customer_id = request.data.get("pg_customer_id")
        contact_no = request.data.get('contact_no')
        code = request.data.get('code')

        try:
            if not contact_no: return Response({"status": "fail", "message": "Contact number is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not code: return Response({"status": "fail", "message": "OTP code is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not pg_customer_id: return Response({"status": "fail", "message": "pg_customer_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            if validate_mobile_number(contact_no) == False: return Response({'status': 'fail','message': 'Invalid contact number.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(code) == False: return Response({"status": "fail",'message': 'OTP code contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if len(code) != 6: return Response({"status": "fail",'message': 'OTP code must contain 6 digits value.'}, status=status.HTTP_400_BAD_REQUEST)

            pg_service_transaction = PgServiceTrn.objects.get(pg_customer_id=pg_customer_id)

            if pg_service_transaction.pg_contact_verify_code == code and pg_service_transaction.pg_verify_code_expire_at > timezone.now():
                # pg_service_transaction.pg_contact_verify_code = None
                # pg_service_transaction.pg_verify_code_expire_at = None

                response_data = {
                    'status': 'success',
                    'message': 'Code verified successfully.',
                    'data': {'pg_customer_id': pg_service_transaction.pg_customer_id}
                }

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    'status': 'error',
                    'message': 'Invalid or expired verification code.',
                    'data': {'pg_customer_id': pg_service_transaction.pg_customer_id}
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except PgServiceTrn.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'Transaction id does not exist.'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_aadhaar_card(self, request):
        aadhaar_card = request.data.get('aadhaar_card')
        pg_customer_id = request.data.get("pg_customer_id")

        try:
            if not pg_customer_id: return Response({"status": "fail", "message": "pg_customer_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not aadhaar_card: return Response({"status": "fail", "message": "aadhaar_card is required"}, status=status.HTTP_400_BAD_REQUEST)

            pg_service_transaction = PgServiceTrn.objects.get(pg_customer_id=pg_customer_id)
            pg_service_transaction.pg_customer_aadhaar_no = aadhaar_card
            pg_service_transaction.save()
            aadhar_response = aadhaar_verify(aadhaar_card)

            aadhar_response['data']['pg_customer_id'] = pg_service_transaction.pg_customer_id
            
            return Response(aadhar_response.get('data'), status=aadhar_response['status'])
        
        except PgServiceTrn.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'Transaction id does not exist.'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_aadhaar_otp(self, request):
        ref_id = request.data.get('ref_id')
        aadhaar_otp = request.data.get('aadhaar_otp')
        fwdp = request.data.get('fwdp')
        codeVerifier = request.data.get('codeVerifier')
        pg_customer_id = request.data.get("pg_customer_id")

        try:
            if not pg_customer_id: return Response({"status": "fail", "message": "pg_customer_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not aadhaar_otp: return Response({"status": "fail", "message": "aadhaar_otp is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not ref_id: return Response({"status": "fail", "message": "ref_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            pg_service_transaction = PgServiceTrn.objects.get(pg_customer_id=pg_customer_id)

            aadhaar_otp_response = aadhaar_otp_verify(aadhaar_otp, ref_id, fwdp, codeVerifier)
            customer_name = aadhaar_otp_response.get('data').get("aadhaar_data").get('name') if aadhaar_otp_response.get('data').get("aadhaar_data") else 'customer'

            pg_service_transaction.pg_customer_name = customer_name
            pg_service_transaction.pg_aadhaar_response = aadhaar_otp_response.get('data').get("aadhaar_data") if aadhaar_otp_response.get('data').get("aadhaar_data") else aadhaar_otp_response.get('data')
            pg_service_transaction.save()

            aadhaar_otp_response['data']['pg_customer_id'] = pg_service_transaction.pg_customer_id
            return Response(aadhaar_otp_response.get('data'), status=aadhaar_otp_response['status'])
        
        except PgServiceTrn.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'Transaction id does not exist.'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_pg_order(self, request):
        pg_customer_id = request.data.get("pg_customer_id")
        email = request.data.get('email')
        amount = request.data.get('amount')
        sp_id = request.data.get('sp_id')
        currency = "INR"

        # api_key = "rzp_test_rEAW6ojdmqFEbn"
        # secret_key = "mPPJMnQtFd0o5Q1hKTXTgZSe"
        api_key = ""
        secret_key = ""

        try:
            # admin_wallet = check_admin_wallet(request, amount)
            # retailer_wallet = check_retailer_wallet(request, amount, request.user.id)
            if not pg_customer_id: return Response({"status": "fail", "message": "pg_customer_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not email: return Response({"status": "fail", "message": "email is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not amount: return Response({"status": "fail", "message": "amount is required"}, status=status.HTTP_400_BAD_REQUEST)

            pg_service_transaction = PgServiceTrn.objects.get(pg_customer_id=pg_customer_id)
            
            pg_service_transaction.pg_customer_email = email
            pg_service_transaction.pg_trn_amount = float(amount)
            pg_service_transaction.save()

            name = pg_service_transaction.pg_customer_name
            contact_no = pg_service_transaction.pg_customer_contact_no

            order_payload = {
                "amount": float(amount)*100,
                "currency": currency
            }

            # scheme = "https" if request.is_secure() else "http"
            callback_url = "admin_hub/payment-gateway/razorpay/"

            details = {
                "api_key": api_key,
                "name": name,
                "email": email,
                "contact_no": contact_no,
                "callback_url": callback_url
            }

            url = "https://api.razorpay.com/v1/orders"

            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                api_key = sp.credentials_json.get('api_key')
                secret_key = sp.credentials_json.get('secret_key')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                api_key = service_provider.credentials_json.get('api_key')
                secret_key = service_provider.credentials_json.get('secret_key')
            print('api_key, secret_key', api_key, secret_key)
            new_order_response = requests.post(url, auth=(api_key, secret_key), json=order_payload)
            print('new_order_response', new_order_response.text)
            if new_order_response.status_code == 200:
                details['order'] = json.loads(new_order_response.text)
                response = {'status': 'success','pg_customer_id': pg_service_transaction.pg_customer_id, 'data': details}

            else:
                details['order'] = json.loads(new_order_response.text)
                response = {'status': 'fail', 'pg_customer_id': pg_service_transaction.pg_customer_id, 'data': details}

            return Response(response, status=new_order_response.status_code)
        except PortalUser.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'Portal user dose not exists.'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        
        except PortalUserWallet.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'Portal user wallet dose not exists.'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        
        except PgServiceTrn.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'Transaction id does not exist.'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except ValidationError as e:
            message = str(e)
            if "ErrorDetail" in message:
                message = message.split("string='")[1].split("', code=")[0]  
            return Response({'status': 'fail', 'message': message}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_razorpay_payment_gateway(self, request):
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        pg_customer_id = request.data.get("pg_customer_id")
        sp_id = request.data.get('sp_id')

        method = request.method
        timestamp = int(time.time() * 1000)  # Current timestamp in milliseconds

        # api_key = "rzp_test_rEAW6ojdmqFEbn"
        # secret_key = "mPPJMnQtFd0o5Q1hKTXTgZSe"
        api_key = ""
        secret_key = ""
        trn_unique_id = f"rpg_{timestamp}"

        try:
            with transaction.atomic():
                if method == "POST":
                    if not pg_customer_id: return Response({"status": "fail", "message": "pg_customer_id is required"}, status=status.HTTP_400_BAD_REQUEST)
                    if not sp_id: return Response({"status": "fail", "message": "sp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
                    if 'razorpay_order_id' not in request.data or 'razorpay_payment_id' not in request.data or 'razorpay_signature' not in request.data:
                        return Response(
                                {'status': 'fail', 'message': 'razorpay_order_id, razorpay_payment_id and razorpay_signature are required'},
                                status=status.HTTP_400_BAD_REQUEST
                            )

                    pg_service_transaction = PgServiceTrn.objects.get(pg_customer_id=pg_customer_id)

                    if int(sp_id) != int(pg_service_transaction.sp.pk):
                        return Response({
                            'status': 'fail', 
                            'message': 'The provided service transaction SP ID does not match the requested SP ID. Please verify and try again.'
                        }, status=status.HTTP_400_BAD_REQUEST)

                    service_provider = AdServiceProvider.objects.get(sp_id=sp_id)

                    if service_provider.is_self_config == True:
                        api_key = service_provider.credentials_json.get('api_key')
                        secret_key = service_provider.credentials_json.get('secret_key')
                    else:
                        sa_service_provider = ServiceProvider.objects.get(sp_id=service_provider.sp_id)
                        api_key = sa_service_provider.credentials_json.get('api_key')
                        secret_key = sa_service_provider.credentials_json.get('secret_key')

                    gst_rate = service_provider.hsn_sac.tax_rate

                    message = f"{razorpay_order_id}|{razorpay_payment_id}"
                    generated_signature = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
                    print('===========', generated_signature)
                    if generated_signature == razorpay_signature:

                        url = f"https://api.razorpay.com/v1/payments/{razorpay_payment_id}"

                        payment_response = requests.get(url, auth=(api_key, secret_key))

                        if payment_response.status_code == 200:
                            payment_response_json = payment_response.json()

                            pg_service_transaction.sp = service_provider
                            pg_service_transaction.pg_trn_unique_id = trn_unique_id
                            pg_service_transaction.pg_trn_status = "SUCCESS"
                            pg_service_transaction.pg_trn_response = payment_response_json
                            pg_service_transaction.save()
                            admin_charges = None 
                            # fetch admin charges
                            admin_charge_queryset = AdCharges.objects.filter(service_provider_id=sp_id)

                            if admin_charge_queryset.exists():  # Ensure queryset is not empty
                                for charge in admin_charge_queryset:
                                    if charge.minimum <= float(pg_service_transaction.pg_trn_amount) <= charge.maximum:
                                        admin_charges = charge  # Assign matching charge
                                        break  # Exit loop early if a match is found

                                # If no specific charge matched, assign the first one
                                if admin_charges is None:
                                    admin_charges = admin_charge_queryset.first()

                            # Ensure admin_charges is valid before accessing attributes
                            if admin_charges:
                                admin_rate = admin_charges.rate
                                admin_rate_type = admin_charges.rate_type
                                admin_charges_type = admin_charges.charges_type
                            else:
                                admin_rate = 0  # Set default values to avoid errors
                                admin_rate_type = None
                                admin_charges_type = None

                            char_comm_amt = pg_service_transaction.pg_trn_amount * (admin_rate / 100) if admin_rate_type == 'is_percent' else admin_rate
                            admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))

                            portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)

                            data = {
                                "service_id": pg_service_transaction.pk,
                                "amount": pg_service_transaction.pg_trn_amount,
                                "table_name": "ad_pg_service_transaction",
                                "wl_label": f"RazorpayPg_by_{portal_user_details.pud_unique_id}_of_amount_{pg_service_transaction.pg_trn_amount}_with_tx_id_{pg_service_transaction.pg_service_trn_id}",
                                "gst_rate": gst_rate,
                                "admin_tax_amt": admin_tax_amt,
                                "char_comm_amt": char_comm_amt,
                                "admin_charges_type": admin_charges_type,
                                "sp_id": sp_id,
                                "contact_number": pg_service_transaction.pg_customer_contact_no,
                                "name": pg_service_transaction.pg_customer_name,
                                "response_data": payment_response_json,
                                "label": service_provider.label,
                                "category": None,
                                "is_self_config": service_provider.is_self_config
                            }
                            print('data', data)
                            charges_calculation_function(request, data)

                            # for retailer
                            # rt_gl = GlTrn.objects.create(
                            #     service_trn_id=pg_service_transaction.pk,
                            #     pu_id=request.user.id,
                            #     gl_trn_amt=pg_service_transaction.pg_trn_amount,
                            #     effectvie_wallet='pg_wallet',
                            #     effectvie_amt=pg_service_transaction.pg_trn_amount,
                            #     service_trn_table='ad_pg_service_trnasaction',
                            #     effective_type='CR',
                            #     gl_trn_dt=now(),
                            # )

                            # WalletTrn.objects.create(
                            #     action_id=rt_gl.pk,
                            #     action_type='Order',
                            #     pu_id=request.user.id,
                            #     wl_label=f"RazorpayPg_by_{portal_user_details.pud_unique_id}_of_amount_{pg_service_transaction.pg_trn_amount}_with_tx_id_{pg_service_transaction.pg_service_trn_id}",
                            #     effectvie_wallet='pg_wallet',
                            #     effectvie_amt=pg_service_transaction.pg_trn_amount,
                            #     effective_type='CR',
                            #     wl_trn_dt=now()
                            # )

                            # rtl_wallet = PortalUserWallet.objects.get(pu_id=request.user.id)
                            # rtl_wallet.pg_wallet = float(rtl_wallet.pg_wallet) + float(pg_service_transaction.pg_trn_amount)
                            # rtl_wallet.updated_at = now()
                            # rtl_wallet.save()

                            # # for admin
                            # if service_provider.is_self_config==True:
                            #     service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
                            #     plateform_fee = service_provider.plateform_fee
                            #     plateform_fee_type = service_provider.plateform_fee_type
                            #     tax_rate = service_provider.hsn_sac.tax_rate
                            #     rate_amount = pg_service_transaction.pg_trn_amount * (plateform_fee / 100) if plateform_fee_type == 'is_percent' else plateform_fee                      
                            #     gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(tax_rate)/100)))

                            #     admin_amount = rate_amount
                            # else:
                            #     admin_amount=pg_service_transaction.pg_trn_amount
                            # admin_gl = GlTrn.objects.create(
                            #     service_trn_id=pg_service_transaction.pk,
                            #     pu_id=1,
                            #     gl_tax_rate=tax_rate if tax_rate else None,
                            #     gl_tax_amt=gst_amount if tax_rate else None,
                            #     gl_trn_amt=admin_amount,
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=admin_amount,
                            #     service_trn_table='ad_pg_service_trnasaction',
                            #     effective_type='CR',
                            #     gl_trn_dt=now(),
                            # )

                            # WalletTrn.objects.create(
                            #     action_id=admin_gl.pk,
                            #     action_type='Order',
                            #     pu_id=1,
                            #     wl_label=f"RazorpayPg_by_{portal_user_details.pud_unique_id}_of_amount_{admin_amount}_with_tx_id_{pg_service_transaction.pg_service_trn_id}",
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=admin_amount,
                            #     effective_type='CR',
                            #     wl_trn_dt=now()
                            # )
                            
                            # admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                            # admin_wallet.main_wallet = float(admin_wallet.main_wallet) + float(admin_amount)
                            # admin_wallet.updated_at = now()
                            # admin_wallet.save()
                            
                            # if service_provider.is_self_config == False:
                            #     admin_gl = GlTrn.objects.create(
                            #         service_trn_id=pg_service_transaction.pk,
                            #         pu_id=1,
                            #         gl_tax_rate=gst_rate,
                            #         gl_tax_amt=admin_tax_amt,
                            #         gl_trn_amt=pg_service_transaction.pg_trn_amount,
                            #         effectvie_wallet='main_wallet',
                            #         effectvie_amt=char_comm_amt,
                            #         service_trn_table='ad_pg_service_trnasaction',
                            #         effective_type=admin_charges_type,
                            #         gl_trn_dt=now(),
                            #     )

                            #     WalletTrn.objects.create(
                            #         action_id=pg_service_transaction.pk,
                            #         action_type='Order',
                            #         pu_id=1,
                            #         wl_label=f"RazorpayPg_by_{portal_user_details.pud_unique_id}_of_amount_{pg_service_transaction.pg_trn_amount}_with_tx_id_{pg_service_transaction.pg_service_trn_id}",
                            #         effectvie_wallet='main_wallet',
                            #         effectvie_amt=char_comm_amt,
                            #         effective_type=admin_charges_type,
                            #         wl_trn_dt=now()
                            #     )

                            #     admin_wallet_ch = PortalUserWallet.objects.get(pu_id=1)

                            #     if admin_charges_type == 'CR':
                            #         admin_wallet_ch.main_wallet = float(admin_wallet_ch.main_wallet) + float(char_comm_amt)
                            #     else:
                            #         admin_wallet_ch.main_wallet = float(admin_wallet_ch.main_wallet) - float(char_comm_amt)
                            #     admin_wallet_ch.updated_at = now()
                            #     admin_wallet_ch.save()

                            # data = {
                            #     'order_amount': pg_service_transaction.pg_trn_amount,
                            #     'id': request.user.id,
                            #     'sp_id': sp_id,
                            #     'customer_contact_no': pg_service_transaction.pg_customer_contact_no,
                            #     'customer_name': pg_service_transaction.pg_customer_name,
                            #     'trn_response': payment_response_json,
                            #     'service_trn': pg_service_transaction.pk,
                            #     'label': service_provider.label,
                            #     'category': None,
                            #     'table_name': 'ad_pg_service_trnasaction'
                            # }
                            # after_tx_cal(request, data)

                            response_details = {
                                "transaction_date": pg_service_transaction.pg_service_trn_dt,
                                "customer_contact_no": pg_service_transaction.pg_customer_contact_no,
                                "customer_name": pg_service_transaction.pg_customer_name,
                                "transaction_id": pg_service_transaction.pg_service_trn_id,
                                "transaction_status": pg_service_transaction.pg_trn_status,
                                "amount": pg_service_transaction.pg_trn_amount,
                                "payment_response": payment_response_json
                            }

                            return Response({'status': 'success', 'message': 'Payment is successful', 'data': response_details}, status=status.HTTP_200_OK)

                        else:
                            payment_response_json = payment_response.json()
                            pg_service_transaction.sp = service_provider
                            pg_service_transaction.pg_trn_unique_id = trn_unique_id
                            pg_service_transaction.pg_trn_status = payment_response_json.get('status')
                            pg_service_transaction.pg_trn_response = payment_response_json
                            pg_service_transaction.save()

                            response_details = {
                                "transaction_date": pg_service_transaction.pg_service_trn_dt,
                                "customer_contact_no": pg_service_transaction.pg_customer_contact_no,
                                "customer_name": pg_service_transaction.pg_customer_name,
                                "transaction_id": pg_service_transaction.pg_service_trn_id,
                                "transaction_status": pg_service_transaction.pg_trn_status,
                                "amount": pg_service_transaction.pg_trn_amount,
                                "payment_response": payment_response_json
                            }

                            return Response({'status': 'fail', 'data': response_details}, status=payment_response.status_code)

                    else:
                        return Response({'status': 'fail', 'message': 'Signature verification failed'}, status=status.HTTP_404_NOT_FOUND)
                else:
                    return Response({'status': 'fail', 'message': 'Payment is failed'}, status=status.HTTP_404_NOT_FOUND)

        

        except Exception as e:
            return Response(
                    {'status': 'error', 'message': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    def fetch_razorpay_pg_transaction(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size')
        search = request.data.get('search', '')
        transaction_status = request.data.get('transaction_status', '')
        date_filter = request.data.get('date_filter', '')  # today, weekly, monthly, yearly, custom
        start_date = request.data.get('start_date', '')
        end_date = request.data.get('end_date', '')
        try:
            if not page_size: return Response({'status': 'fail','message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(page_size) == False: return Response({'status': 'fail','message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if page_number:
                if isnumber(page_number) == False: return Response({'status': 'fail','message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            queryset = PgServiceTrn.objects.exclude(pg_trn_status='PENDING', created_by=request.user.id).order_by('-pk')

            if search != '':
                queryset = queryset.filter(Q(pg_trn_unique_id__icontains=search) | Q(pg_customer_contact_no__icontains=search))

            if transaction_status != '':
                queryset = queryset.filter(pg_trn_status=transaction_status)

            # Apply Date Filters
            if date_filter or start_date and end_date:
                # Ensure timezone-aware date
                today = localtime().date()
                now = localtime()
                if date_filter.strip() == 'today':
                    start_datetime = make_aware(datetime.combine(today, datetime.min.time()))
                    end_datetime = make_aware(datetime.combine(today + timedelta(days=1), datetime.min.time()))
                    queryset = queryset.filter(created_at__gte=start_datetime, created_at__lt=end_datetime)

                elif date_filter == 'weekly':
                    start_of_week = today - timedelta(days=today.weekday())  # Start of the week (Monday)
                    start_datetime = make_aware(datetime.combine(start_of_week, datetime.min.time()))
                    queryset = queryset.filter(created_at__gte=start_datetime)

                elif date_filter == 'monthly':
                    start_of_month = today.replace(day=1)  # First day of the current month
                    start_datetime = make_aware(datetime.combine(start_of_month, datetime.min.time()))
                    queryset = queryset.filter(created_at__gte=start_datetime)

                elif date_filter == 'yearly':
                    start_of_year = today.replace(month=1, day=1)  # First day of the current year
                    start_datetime = make_aware(datetime.combine(start_of_year, datetime.min.time()))
                    queryset = queryset.filter(created_at__gte=start_datetime)

                elif date_filter == 'custom' and start_date and end_date:
                    try:
                        start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
                        end_date = make_aware(datetime.strptime(end_date, "%Y-%m-%d")) + timedelta(days=1)  # Include end date
                        queryset = queryset.filter(created_at__gte=start_date, created_at__lt=end_date)
                    except ValueError:
                        return Response({'status': 'fail', 'message': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)


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
                        'message': 'Payment Gateway Transaction Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                    
                serializer = PgServiceTrnSerializer(page_obj.object_list, many=True).data
                for trn in serializer:
                    if trn['sp'] != None:
                        sp_obj = AdServiceProvider.objects.get(sp_id=trn['sp'])
                        trn['label'] = sp_obj.label
                    else:
                        trn['label'] = 'Razorpay PG'
                    # Convert to datetime if it's a string
                    if isinstance(trn['pg_service_trn_dt'], str):
                        trn['pg_service_trn_dt'] = datetime.strptime(trn['pg_service_trn_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")

                    trn['pg_service_trn_dt'] = trn['pg_service_trn_dt'].strftime("%d-%m-%Y %I:%M %p")


                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer
                }
                return Response({
                    'status': 'success',
                    'message': 'Payment Gateway Transaction data',
                    'data': paginated_response_data
                }, status=status.HTTP_200_OK)
            serializer = PgServiceTrnSerializer(queryset, many=True, context={'request': request}).data
            for trn in serializer:

                if trn['sp'] != None:
                    sp_obj = AdServiceProvider.objects.get(sp_id=trn['sp'])
                    trn['label'] = sp_obj.label
                else:
                    trn['label'] = 'Razorpay PG'
                # Convert to datetime if it's a string
                if isinstance(trn['pg_service_trn_dt'], str):
                    trn['pg_service_trn_dt'] = datetime.strptime(trn['pg_service_trn_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")

                trn['pg_service_trn_dt'] = trn['pg_service_trn_dt'].strftime("%d-%m-%Y %I:%M %p")

            response_data = {
                'status': 'success',
                'message': 'Payment Gateway Transaction data',
                'data': serializer
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'status': 'fail',
                'message': str(e),
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)
