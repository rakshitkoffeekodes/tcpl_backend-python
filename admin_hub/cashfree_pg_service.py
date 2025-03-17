from .views import *
from .models import *
from .utilies import *
from validation.custom_validation import *
import random
import string
import requests
from datetime import datetime, timedelta
from django.utils.timezone import localtime, make_aware
import json
from .charges_calculation import *
import pytz
from .utilies import add_user_activity

def save_file(file, directory):
    print('file', file)
    file_extension = file.name.split('.')[-1].lower()
    if file_extension not in ['png', 'jpg', 'jpeg']:
        return None

    sanitized_file_name = file.name.replace(' ', '').replace('(', '').replace(')', '')
    file_path = os.path.join(directory, sanitized_file_name)

    with open(file_path, "wb") as f:
        f.write(file.read())

    return f'{directory}{sanitized_file_name}'

class CashfreePaymentAPIView(APIView):
    """
    API view to handle the cashfree payment gateway.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request):
        try:
            if 'contact_number' in request.data and 'front_aadhaar_card' in request.data and 'back_aadhaar_card' in request.data and 'pan_card' in request.data and 'pan_card_number' in request.data:
                return self.ekyc_document(request)
            elif 'contact_number' in request.data and 'amount' in request.data and 'orderId' in request.data:
                print('========')
                return self.create_trnasaction(request)
            elif 'contact_number' in request.data and 'amount' in request.data and 'sp_id' in request.data:
                return self.add_amount(request)
            elif 'is_settle' in request.data and 'contact_number' in request.data and 'orderId' in request.data:
                return self.settel_calculation(request)
            elif 'is_rate_fetch' in request.data and 'contact_number' in request.data and 'orderId' in request.data:
                return self.fetch_rate(request)
            elif 'contact_number' in request.data and 'code' in request.data:
                return self.register_ekyc(request)
            elif 'contact_number' in request.data:
                return self.check_mobile_number(request)
            elif 'page_number' in request.data or 'page_size' in request.data:
                return self.get_all_transaction(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid Request.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def check_mobile_number(self, request):
        contact_number = request.data.get('contact_number')
        service_provider = None
        try:
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if validate_mobile_number(contact_number) == False:
                return Response({'status': 'fail', 'message': 'invalid contact number formate.'}, status=status.HTTP_400_BAD_REQUEST)
            
            register_contact_number = CfPgCustomer.objects.get(cf_pg_customer_contact_no=contact_number)
            results = {
                'contact_number': register_contact_number.cf_pg_customer_contact_no,
                'cf_pg_is_kyc': register_contact_number.cf_pg_is_kyc
            }

            return Response({'status': 'success', 'message': 'contact number register successfully.', 'data': {'results': results}})
        
        except CfPgCustomer.DoesNotExist:
            register_contact_number = CfPgCustomer.objects.create(
                cf_pg_customer_contact_no=contact_number,
                created_by=request.user.id
            )
            results = {
                'contact_number': register_contact_number.cf_pg_customer_contact_no,
                'cf_pg_is_kyc': register_contact_number.cf_pg_is_kyc
            }
            return Response({'status': 'success', 'message': 'contact number register successfully.', 'data': {'results': results}})

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def ekyc_document(self, request):
        contact_number = request.data.get('contact_number')
        pan_card_number = request.data.get('pan_card_number')
        required_files ={
            "front_aadhaar_image": request.FILES.get('front_aadhaar_card'),
            "back_aadhaar_image": request.FILES.get('back_aadhaar_card'),
            "pan_card_image": request.FILES.get('pan_card'),
        }

        try:
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not pan_card_number: return Response({'status': 'fail', 'message': 'pan card number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            register_contact_number = CfPgCustomer.objects.get(cf_pg_customer_contact_no=contact_number)
        
            max_file_size = 10 * 1024 * 1024 

            folder_name = f'KYC_DOC_NO_{contact_number}'
            user_directory = f'media/CashFreePG/Kyc/{folder_name}/'
            os.makedirs(user_directory, exist_ok=True)

            ekyc_doc_urls_dict = {}
            for key, file in required_files.items():
                file_url = save_file(file, user_directory)
                if not file_url:
                    return Response({'status': 'fail', 'message': f'Invalid file format for {key}. Only PNG, JPG, and JPEG are allowed.'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                if file.size > max_file_size:
                    return Response(
                        {'status': 'fail', 'message': f'{key.replace("_", " ").capitalize()} exceeds the 10 MB size limit.'}, status=status.HTTP_400_BAD_REQUEST)
                ekyc_doc_urls_dict[key] = file_url

            code = get_random_string(length=6, allowed_chars='0123456789')

            register_contact_number.cf_pg_contact_verify_code = code
            register_contact_number.cf_pg_verify_code_expire_at = timezone.now() + timedelta(minutes=10)
            register_contact_number.cf_pg_ekyc_document=ekyc_doc_urls_dict
            register_contact_number.cf_pg_customer_pan_no=pan_card_number
            register_contact_number.save()
            response = mobicomm_submit_sms(contact_number, code)

            # Check the SMS API response status
            if response.status_code == 200:
                response_data = {
                    'status': 'success',
                    'message': 'OTP has been sent via SMS.',
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data = {
                    'status': 'error',
                    'message': 'Failed to send the OTP via SMS.',
                    'details': response.text  # Include the response for debugging
                }
                return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except CfPgServiceTrn.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Contact number is dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def register_ekyc(self, request):
        contact_number = request.data.get('contact_number')
        code = request.data.get('code')

        try:
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not code: return Response({'status': 'fail', 'message': 'code is required.'}, status=status.HTTP_400_BAD_REQUEST)

            register_contact_number = CfPgCustomer.objects.get(cf_pg_customer_contact_no=contact_number)

            if register_contact_number.cf_pg_contact_verify_code == code and register_contact_number.cf_pg_verify_code_expire_at > timezone.now():
                register_contact_number.cf_pg_contact_verify_code = None
                register_contact_number.cf_pg_verify_code_expire_at = None
                register_contact_number.cf_pg_is_kyc = True
                register_contact_number.save()
                return Response({'status': 'success', 'message': 'E-Kyc completed successfully.'}, status=status.HTTP_200_OK)

            else:
                response_data = {
                    'status': 'fail',
                    'message': 'Invalid or expired verification code.'}
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
        except CfPgCustomer.DoesNotExist:
            return Response({'status': 'fail', 'message': 'contact number dose not exists.'}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_amount(self, request):
        print('=================')
        contact_number = request.data.get('contact_number')
        amount = request.data.get('amount')
        sp_id = request.data.get('sp_id')

        try:
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not amount: return Response({'status': 'fail', 'message': 'amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not sp_id: return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            part1 = str(random.randint(1000, 9999)) 
            part2 = ''.join(random.choices(string.ascii_uppercase, k=3))
            part3 = str(random.randint(100000, 999999))
            cf_pg_customer_id = part1 + part2 + part3
            print("cf_pg_customer_id", cf_pg_customer_id)
            date_part = timezone.now().strftime("%Y-%m-%d")

            number_part = str(random.randint(1000000, 9999999))
            random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
            order_id = f"CFPG_{number_part}st{random_part}"
            print('======----------')
            register_contact_number = CfPgCustomer.objects.get(cf_pg_customer_contact_no=contact_number)
            service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
            print('service_provider', service_provider)
            url = "https://api.cashfree.com/pg/orders"
            payload = {
                "order_id": order_id,
                "order_currency": "INR",
                "order_amount": float(amount),
                "customer_details": {
                    "customer_id": cf_pg_customer_id,
                    "customer_phone": contact_number
                },
                "order_meta": {"return_url": "https://www.cashfree.com/devstudio/thankyou","payment_methods": "cc,dc,upi"}
            }
            print('==========================--------------------')
            if service_provider.is_self_config == True:
                Client_id = service_provider.credentials_json.get('Client_id')
                Client_secret = service_provider.credentials_json.get('Client_secret')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                Client_id = service_provider.credentials_json.get('Client_id')
                Client_secret = service_provider.credentials_json.get('Client_secret')

            headers = {
                "x-api-version": "2025-01-01",
                # "x-client-id": "4497774aa0cd30fea81656c14c777944",
                "x-client-id": Client_id,
                # "x-client-secret": "cfsk_ma_prod_082349799c0b18c3fbeba11efdcbe58f_30f3f209",
                "x-client-secret": Client_secret,
                "Content-Type": "application/json"
            }

            response = requests.request("POST", url, json=payload, headers=headers)
            print('response', response)
            json_response = response.json()
            print('josn_response', json_response)
            register_contact_number.cf_pg_trn_unique_id=order_id
            register_contact_number.save()
            if response.status_code == 200:
                trnasactions = CfPgServiceTrn.objects.create(
                    cf_pg_trn_amount=amount,
                    customer=register_contact_number,
                    cf_pg_trn_unique_id=order_id,
                    cf_pg_customer_contact_no=contact_number,
                    sp=service_provider,
                    created_by=request.user.id
                )
                results = {
                    "payment_session_id": json_response.get("payment_session_id"),
                    "return_url": json_response.get("order_meta").get("return_url"),
                    "payment_methods": json_response.get("order_meta").get("payment_methods"),
                    "order_id": json_response.get("order_id")
                }

                user_activity = {
                    "table_id": trnasactions.pk,
                    "table_name": 'ad_cashfree_pg_service_transaction',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'Cashfree Payment Getway add amount successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(trnasactions)
                }

                add_user_activity(user_activity)

                return Response({'status': 'success', 'message': 'success', 'data': {'results': results}}, status=status.HTTP_200_OK)

            else:
                return Response({'status': 'fail', 'message': json_response.get('message')}, status=status.HTTP_400_BAD_REQUEST)
        
        except CfPgCustomer.DoesNotExist:
            return Response({'status': 'fail', 'message': 'contact number dose not exists.'}, status=status.HTTP_404_NOT_FOUND)
        
        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'service provider dose not exists.'}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_trnasaction(self, request):
        contact_number = request.data.get('contact_number')
        amount = request.data.get('amount')
        order_id = request.data.get('orderId')
        sp_id = request.data.get('sp_id')
        print('-----------------')

        try:
            print('contact_number', contact_number)
            print('order_id', order_id)
            trnasaction_data = CfPgServiceTrn.objects.get(cf_pg_customer_contact_no=contact_number, cf_pg_trn_unique_id=order_id)
            print('step 1-------------', trnasaction_data)
            url = f"https://api.cashfree.com/pg/orders/{order_id}/payments"

            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                Client_id = sp.credentials_json.get('Client_id')
                Client_secret = sp.credentials_json.get('Client_secret')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                Client_id = service_provider.credentials_json.get('Client_id')
                Client_secret = service_provider.credentials_json.get('Client_secret')

            headers = {
                "x-api-version": "2025-01-01",
                "x-client-id": Client_id,
                "x-client-secret": Client_secret,
                # "x-client-id": "4497774aa0cd30fea81656c14c777944",
                # "x-client-secret": "cfsk_ma_prod_082349799c0b18c3fbeba11efdcbe58f_30f3f209",
                "Content-Type": "application/json"
            }
            response = requests.request("GET", url, headers=headers)
            json_response = response.json()
            print('step 4', json_response)
            if response.status_code == 200:
                trnasaction_data.cf_pg_trn_response = json_response
                trnasaction_data.cf_pg_trn_status = "SUCCESS"
                trnasaction_data.save()
                user_activity = {
                    "table_id": trnasaction_data.pk,
                    "table_name": 'ad_cashfree_pg_service_transaction',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'Cashfree Payment Getway Create Transaction successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(trnasaction_data)
                }

                add_user_activity(user_activity)
                return Response({'status': 'success', 'message': 'Transaction successfully.'}, status=status.HTTP_200_OK)

            else:
                trnasaction_data.cf_pg_trn_response = json_response
                trnasaction_data.cf_pg_trn_status = "FAILED"
                trnasaction_data.cf_pg_settle_status = "FAILED"
                trnasaction_data.save()
                return Response({'status': 'fail','message': json_response.get('message')}, status=status.HTTP_400_BAD_REQUEST)

        except CfPgServiceTrn.DoesNotExist:
            return Response({'status': 'fail', 'message': 'contact number dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_rate(self, request):
        contact_number = request.data.get('contact_number')
        order_id = request.data.get('orderId', '0')
        try:
            if order_id != '0':
                transaction_data = CfPgServiceTrn.objects.get(cf_pg_customer_contact_no=contact_number, cf_pg_trn_unique_id=order_id)
                if transaction_data.cf_pg_trn_status != 'SUCCESS':
                    return Response(
                        {'status': 'fail', 'message': 'Transaction cannot be settled because it was not successful.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                payment_method = transaction_data.cf_pg_trn_response[0].get('payment_method', '')
                if "upi" in payment_method:
                    configed = AdCfPgConfiged.objects.get(payment_method="UPI")
                elif "card" in payment_method:
                    card_info = payment_method.get("card", {})
                    card_type = card_info.get("card_type", "")
                    card_network = card_info.get("card_network", "")
                    card_sub_type = card_info.get("card_sub_type", "")
                    configed = AdCfPgConfiged.objects.get(
                        payment_method="CARD", 
                        card_type=card_type, 
                        card_network=card_network, 
                        card_sub_type=card_sub_type
                    )
                else:
                    configed = AdCfPgConfiged.objects.get(payment_method="OTHERS")

                # Ensure `transaction_data.cf_pg_service_trn_dt` is timezone-aware
                if transaction_data.cf_pg_service_trn_dt is None:
                    transaction_datetime = transaction_data.cf_pg_service_trn_dt
                else:
                    transaction_datetime = transaction_data.cf_pg_service_trn_dt

                # Convert `holding_hours` to integer
                holding_hours = int(configed.rt_charges[0].get('holding_hours', 0))  
                
                # Get the current datetime in UTC
                current_time = timezone.now()

                # Calculate time difference in hours
                time_difference = (current_time - transaction_datetime).total_seconds() / 3600  # Convert seconds to hours

                rate = 0.00
                rate_type = ''

                # Calculate remaining time
                remaining_time = max(holding_hours - time_difference, 0)  # Remaining time should not be negative
                remaining_hours = int(remaining_time)
                remaining_minutes = int((remaining_time - remaining_hours) * 60)

                # Check if the time difference is greater than holding hours
                if time_difference > holding_hours:
                    rate = float(configed.rt_charges[0].get('regular_rate', 0.00))
                    rate_type = 'regular_rate'
                else:
                    rate = float(configed.rt_charges[0].get('premium_rate', 0.00))
                    rate_type = 'premium_rate'

                amount = float(transaction_data.cf_pg_trn_amount)
                amt = amount * rate / 100
                effective_amt = amount - amt

                data = {
                    'results': {
                        'rate': rate, 
                        'amount': amount, 
                        'effective_amt': effective_amt, 
                        'holding_hours': holding_hours,
                        'rate_type': rate_type,
                        'remaining_time': f"{remaining_hours} hours {remaining_minutes} minutes"
                    }
                }
                return Response({'status': 'success', 'message': 'Rate fetched successfully.', 'data': data}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'success', 'message': 'Rate not found.'}, status=status.HTTP_200_OK)
        except CfPgServiceTrn.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Order ID does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except AdCfPgConfiged.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Payment configuration not found.'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'status': 'error', 'message': 'Invalid data type for holding hours.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def settel_calculation(self, request):
        contact_number = request.data.get('contact_number')
        order_id = request.data.get('orderId')
        is_settle = request.data.get('is_settle')
        sp_id = request.data.get('sp_id')

        try:
            transaction_data = CfPgServiceTrn.objects.get(cf_pg_customer_contact_no=contact_number, cf_pg_trn_unique_id=order_id) 
            if transaction_data.cf_pg_settle_status == 'SUCCESS':
                return Response({'status': 'success', 'message': 'This transaction is already settled.'}, status=status.HTTP_200_OK)
            
            payment_method = transaction_data.cf_pg_trn_response[0].get('payment_method', '')
            if "upi" in transaction_data.cf_pg_trn_response[0].get('payment_method'):
                configed = AdCfPgConfiged.objects.get(payment_method="UPI")
            elif "card" in transaction_data.cf_pg_trn_response[0].get('payment_method'):
                card_type = payment_method["card"].get("card_type")
                card_network = payment_method["card"].get("card_network")
                card_sub_type = payment_method["card"].get("card_sub_type")
                configed = AdCfPgConfiged.objects.get(payment_method="CARD", card_type=card_type, card_network=card_network, card_sub_type=card_sub_type)
            else:
                configed = AdCfPgConfiged.objects.get(payment_method="OTHERS")

            # Ensure `transaction_data.cf_pg_service_trn_dt` is timezone-aware
            if transaction_data.cf_pg_service_trn_dt is None:
                transaction_datetime = transaction_data.cf_pg_service_trn_dt
            else:
                transaction_datetime = transaction_data.cf_pg_service_trn_dt

            # Convert `holding_hours` to integer
            holding_hours = int(configed.rt_charges[0].get('holding_hours', 0))
            # Get the current datetime in UTC
            current_time = timezone.now()

            # Calculate time difference in hours
            time_difference = (current_time - transaction_datetime).total_seconds() / 3600  # Convert seconds to hours
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if is_settle == 'true':
            # if time_difference > holding_hours and is_settle == 'true':
                # transaction_data.cf_pg_trn_status = 'SETTLED'
                transaction_data.cf_pg_settle_status = 'SUCCESS'
                transaction_data.updated_at = timezone.now()
                transaction_data.save()

                amount = transaction_data.cf_pg_trn_amount
                gst_rate = sp.hsn_sac.tax_rate
                portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)
                # fetch admin charges
                admin_charge_queryset = AdCharges.objects.filter(service_provider_id=sp_id)
                admin_charges = None
                if admin_charge_queryset.exists():  # Ensure queryset is not empty
                    for charge in admin_charge_queryset:
                        if charge.minimum <= float(amount) <= charge.maximum:
                            admin_charges = charge  # Assign matching charge
                            break  # Exit loop early if a match is found

                    # If no specific charge matched, assign the first one
                    if admin_charges is None:
                        admin_charges = admin_charge_queryset.first()
                print('admin_charges-1111111111111111', admin_charges)

                # Ensure admin_charges is valid before accessing attributes
                if admin_charges:
                    print('if ============>')
                    admin_rate = admin_charges.rate
                    admin_rate_type = admin_charges.rate_type
                    admin_charges_type = admin_charges.charges_type
                else:
                    print('else ============>')
                    admin_rate = 0  # Set default values to avoid errors
                    admin_rate_type = None
                    admin_charges_type = None

                char_comm_amt = float(amount) * (float(admin_rate) / 100) if admin_rate_type == 'is_percent' else float(admin_rate)
                admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))
                print('char_comm_amt', char_comm_amt, 'admin_tax_amt', admin_tax_amt)
                data = {
                    "service_id": transaction_data.pk,
                    "amount": amount,
                    "table_name": "ad_cashfree_pg_service_transaction",
                    "wl_label": f"CashfreePg_by_{portal_user_details.pud_unique_id}_of_amount_{amount}_with_tx_id_{transaction_data.cf_pg_trn_unique_id}",
                    "gst_rate": gst_rate,
                    "admin_tax_amt": admin_tax_amt,
                    "char_comm_amt": char_comm_amt,
                    "admin_charges_type": admin_charges_type,
                    "sp_id": sp_id,
                    "contact_number": transaction_data.cf_pg_customer_contact_no,
                    "name": None,
                    "response_data": transaction_data.cf_pg_trn_response,
                    "label": sp.label,
                    "category": configed.ss_id,
                    "is_self_config": sp.is_self_config,
                    "charge_level": 'PREMIUM' if time_difference < holding_hours else 'REGULAR'
                }
                print('data', data)
                charges_calculation_function(request, data)

                user_activity = {
                    "table_id": transaction_data.pk,
                    "table_name": 'ad_cashfree_pg_service_transaction',
                    "ua_action": 'Settel Calculation',  # Action performed
                    "ua_description": 'Cashfree Payment Getway settle calculation successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(transaction_data)
                }

                add_user_activity(user_activity)

                return Response({'status': 'success', 'message': 'Transaction settle successfully.'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': 'settelment time is lessthen current time so still settlement premium charge.'}, status=status.HTTP_400_BAD_REQUEST)
        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'service provider dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except CfPgServiceTrn.DoesNotExist:
            return Response({'status': 'fail', 'message': 'order id dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_all_transaction(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        search = request.data.get('search', '')
        trn_transaction_status = request.data.get('trn_transaction_status', '')
        settle_transaction_status = request.data.get('settle_transaction_status', '')
        date_filter = request.data.get('date_filter', '')  # today, weekly, monthly, yearly, custom
        start_date = request.data.get('start_date', '')
        end_date = request.data.get('end_date', '')

        try:
            if not page_number:
                return Response({'status': 'fail', 'message': 'page_number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not str(page_number).isdigit():
                return Response({'status': 'fail', 'message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch transactions for the logged-in user
            transactions = CfPgServiceTrn.objects.filter(created_by=request.user.id).order_by('-pk')

            if search != '':
                transactions = transactions.filter(Q(cf_pg_trn_unique_id__icontains=search) | Q(cf_pg_customer_contact_no__icontains=search))

            if trn_transaction_status != '':
                transactions = transactions.filter(cf_pg_trn_status=trn_transaction_status)

            if settle_transaction_status != '':
                transactions = transactions.filter(cf_pg_settle_status=settle_transaction_status)

            # Apply Date Filters
            if date_filter or start_date and end_date:
                # Ensure timezone-aware date
                today = localtime().date()
                now = localtime()
                if date_filter.strip() == 'today':
                    start_datetime = make_aware(datetime.combine(today, datetime.min.time()))
                    end_datetime = make_aware(datetime.combine(today + timedelta(days=1), datetime.min.time()))
                    transactions = transactions.filter(created_at__gte=start_datetime, created_at__lt=end_datetime)

                elif date_filter == 'weekly':
                    start_of_week = today - timedelta(days=today.weekday())  # Start of the week (Monday)
                    start_datetime = make_aware(datetime.combine(start_of_week, datetime.min.time()))
                    transactions = transactions.filter(created_at__gte=start_datetime)

                elif date_filter == 'monthly':
                    start_of_month = today.replace(day=1)  # First day of the current month
                    start_datetime = make_aware(datetime.combine(start_of_month, datetime.min.time()))
                    transactions = transactions.filter(created_at__gte=start_datetime)

                elif date_filter == 'yearly':
                    start_of_year = today.replace(month=1, day=1)  # First day of the current year
                    start_datetime = make_aware(datetime.combine(start_of_year, datetime.min.time()))
                    transactions = transactions.filter(created_at__gte=start_datetime)

                elif date_filter == 'custom' and start_date and end_date:
                    try:
                        start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
                        end_date = make_aware(datetime.strptime(end_date, "%Y-%m-%d")) + timedelta(days=1)  # Include end date
                        transactions = transactions.filter(created_at__gte=start_date, created_at__lt=end_date)
                    except ValueError:
                        return Response({'status': 'fail', 'message': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

            paginator = Paginator(transactions, page_size)
            page = paginator.get_page(page_number)
            serializer = CfPgServiceTrnSerializer(page, many=True)
            for trn in serializer.data:
                # Convert datetime fields in the serialized data
                if 'cf_pg_service_trn_dt' in trn and isinstance(trn['cf_pg_service_trn_dt'], str):
                    trn['cf_pg_service_trn_dt'] = datetime.strptime(trn['cf_pg_service_trn_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")

                trn['cf_pg_service_trn_dt'] = trn['cf_pg_service_trn_dt'].strftime("%d-%m-%Y %I:%M %p")

                if 'updated_at' in trn and trn['updated_at'] != None and isinstance(trn['updated_at'], str):
                    trn['updated_at'] = datetime.strptime(trn['updated_at'], "%Y-%m-%dT%H:%M:%S.%f%z")

                trn['updated_at'] = trn['updated_at'].strftime("%d-%m-%Y %I:%M %p") if trn['updated_at'] != None else None

            data = {
                'total_pages': paginator.num_pages,
                'current_page': page.number,
                'total_items': paginator.count,
                'results': serializer.data
            }

            return Response({'status': 'success', 'message': 'Get all transactions.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

