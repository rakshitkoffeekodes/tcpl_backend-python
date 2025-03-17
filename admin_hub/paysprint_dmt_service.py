from datetime import datetime
from django.shortcuts import get_object_or_404  # If you want to raise 404 in a view
from .views import *
from .commission_calculations import *
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from cryptography.hazmat.backends import default_backend
import base64
import jwt
import time
import random
import xmltodict
import json
from base64 import b64encode
from validation.custom_validation import *
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .charges_calculation import *
from dateutil import parser
from .utilies import *
from django.utils.timezone import localtime, make_aware
from datetime import datetime, timedelta


def get_random():
    return round(random.random() * 1000000000)

def get_timestamp():
    return int(time.time())

def get_token():
# def get_token(secret_key, partnerId):
    random = get_random()
    timestamp = get_timestamp()
    secret_key = b"UFMwMDU3NjM0YzRhYWExMGQ5ZTIwYWEwNGE5MTdkYTg5MzhiY2IyODE3MzM5MDEwOTQ="
    # Ensure secret_key is in bytes
    # if isinstance(secret_key, str):
    #     secret_key = secret_key.encode()  # Convert string to bytes
    token = jwt.encode({
        "timestamp": timestamp,
        "partnerId": "PS005763",
        # "partnerId": partnerId,
        "reqid": random
    }, secret_key, algorithm="HS256", headers={"typ": "JWT", "alg": "HS256"})
    
    return token



def xml_to_json_convert(xml_data):
    # Convert XML to Python dictionary
    xml_dict = xmltodict.parse(xml_data)

    # Convert dictionary to JSON
    json_data = json.dumps(xml_dict, indent=4)

    return json_data


def  generate_encrypt_pid_data(pid_data):
    
    # Replace with your 16-byte AES key and IV
    key = b"26d097cd9b18349e"
    iv = b"e8c461ec1fa93f51"
    
    f_string = f"{pid_data}"

    # Convert f-string to bytes
    bytes_data = f_string.encode('utf-8')
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext_raw = cipher.encrypt(pad(bytes_data, AES.block_size))

    # Base64 encode the ciphertext
    enctoken = b64encode(ciphertext_raw).decode('utf-8')
    return enctoken


class PaysPrintDmtAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request):
        try:
            if 'contact_number' in request.data and 'first_name' in request.data and 'last_name' in request.data and 'zip_code' in request.data:
                return self.get_paysprint_customer_details(request)
            elif 'contact_number' in request.data and 'aadhaar_no' in request.data and 'pid_data' in request.data:
                return self.verify_aadhaar_ekyc(request)
            elif 'contact_number' in request.data and 'referenceid' in request.data and 'amount' in request.data and 'stateresp' in request.data and 'otp' in request.data :
                return self.dmt_transaction(request)
            elif 'contact_number' in request.data and 'otp' in request.data and 'stateresp' in request.data:
                return self.verify_aadhaar_otp(request)
            elif 'contact_number' in request.data and 'txntype' in request.data and 'amount' in request.data and 'bene_id' in request.data:
                return self.create_dmt_transaction(request)
            elif 'contact_number' in request.data:
                return self.get_paysprint_with_mobile(request)
            elif 'referenceids' in request.data:
                return self.dmt_transaction_status(request)
            elif 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_all_dmt_transaction(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get_paysprint_with_mobile(self, request):
        try:
            contact_number = request.data.get('contact_number')
            sp_id = request.data.get('sp_id')
            print('contact_number', contact_number, 'sp_id', sp_id)
            secret_key = ''
            partnerId = ''
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            print('step1')
            mobile_number_validation = validate_mobile_number(contact_number)
            if mobile_number_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid contact number format.'}, status=status.HTTP_400_BAD_REQUEST)
            print('step2')
            url = "https://api.paysprint.in/api/v1/service/dmt/kyc/remitter/queryremitter"
            print('step3')
            try:
                paysprint_dmt_query = ''
                get_pspdmt_customer = PaysPrintDmtCustomer.objects.get(customer_contact_no=contact_number)
                pspdmt_customer_serializer = PaysPrintDmtCustomerSerializer(get_pspdmt_customer)
                print('get_pspdmt_customer', get_pspdmt_customer)
                sp = AdServiceProvider.objects.get(sp_id=sp_id)
                if sp.is_self_config == True:
                    secret_key = sp.credentials_json.get('secret_key')
                    partnerId = sp.credentials_json.get('partnerId')
                else:
                    sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
                    secret_key = sp.credentials_json.get('secret_key')
                    partnerId = sp.credentials_json.get('partnerId')
                print('secret_key', secret_key, 'partnerId', partnerId)
                headers = {
                    "accept": "application/json",
                    "Token": get_token(),
                    # "Token": get_token(secret_key, partnerId),
                    # "Authorisedkey": AuthorisedKey,
                    "Content-Type": "application/json"
                }
                print('headers', headers)
                payload = {"mobile": contact_number}
                print('payload', payload)

                try:
                    response = requests.post(url, json=payload, headers=headers)
                    print('response', response)
                    if response.status_code == 200:
                        response_data = response.json()

                        data = response_data.get("data", {})
                        customer_amount_limit = data.get("limit")
                        get_pspdmt_customer.customer_amount_limit=customer_amount_limit
                        get_pspdmt_customer.save()
                        response_details = {
                            "status": "success",
                            "message": response_data.get("message"),
                            "pspdmt_unique_id": get_pspdmt_customer.pspdmt_unique_id,
                            "customer_details": pspdmt_customer_serializer.data,
                            "response": response_data,
                            "is_aadhar_verified": get_pspdmt_customer.is_aadhar_verified,
                            "is_registered": get_pspdmt_customer.is_registered
                        }

                        return Response(response_details, status=status.HTTP_200_OK if response.status_code == 200 else response.status_code)
                    elif response.status_code == 500:
                        return Response({'status': 'error', 'message': response.text}, status=response.status_code)
                    else:
                        response_data = response.json()
                        response_details = {
                            "status": "fail",
                            "message": response_data.get("message"),
                            "pspdmt_unique_id": get_pspdmt_customer.pspdmt_unique_id,
                            "customer_details": pspdmt_customer_serializer.data,
                            "response": response_data,
                            "is_aadhar_verified": get_pspdmt_customer.is_aadhar_verified,
                            "is_registered": get_pspdmt_customer.is_registered
                        }

                        return Response(response_details, status=response.status_code)

                except requests.RequestException as e:
                    return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            except PaysPrintDmtCustomer.DoesNotExist:
                sp = AdServiceProvider.objects.get(sp_id=sp_id)
                if sp.is_self_config == True:
                    secret_key = sp.credentials_json.get('secret_key')
                    partnerId = sp.credentials_json.get('partnerId')
                else:
                    sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
                    secret_key = sp.credentials_json.get('secret_key')
                    partnerId = sp.credentials_json.get('partnerId')
                headers = {
                    "accept": "application/json",
                    "Token": get_token(),
                    # "Token": get_token(secret_key, partnerId),
                    # "Authorisedkey": AuthorisedKey,
                    "Content-Type": "application/json"
                }
                
                payload = {"mobile": contact_number}
                
                try:
                    response = requests.post(url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        data = response_data.get("data", {})
                        customer_amount_limit = data.get("limit")
                        aadhaar_verified = True if response_data.get("message") == "Remitter account details fetched." else False
                        registered_verified = True if response_data.get("message") == "Remitter account details fetched." else False
                        pspdmt_customer_id_string = get_random_string(length=6)
                        paysprint_dmt_query = PaysPrintDmtCustomer.objects.create(
                            customer_contact_no=contact_number,
                            pspdmt_unique_id=f"PSPDMT_{pspdmt_customer_id_string}",
                            customer_amount_limit=customer_amount_limit,
                            is_aadhar_verified = aadhaar_verified,
                            is_registered = registered_verified
                        )

                        response_details = {
                            "status": "success",
                            "message": response_data.get("message"),
                            "pspdmt_unique_id": paysprint_dmt_query.pspdmt_unique_id,
                            "response": response_data,
                            "is_aadhar_verified": paysprint_dmt_query.is_aadhar_verified,
                            "is_registered": paysprint_dmt_query.is_registered
                        }
                        user_activity = {
                            "table_id": paysprint_dmt_query.pk,
                            "table_name": 'ad_paysprint_dmt_customer',
                            "ua_action": 'Create',  # Action performed
                            "ua_description": 'Customer details Create successfully.',  # Action description
                            "created_by": request.user,  # Current user performing the action
                            "request_data": dict(request.data),  # Request data
                            "response_data": model_to_dict(paysprint_dmt_query)
                        }

                        add_user_activity(user_activity)

                        return Response(response_details, status=status.HTTP_200_OK if response.status_code == 200 else response.status_code)
                    elif response.status_code == 500:
                        return Response({'status': 'error', 'message': response.text}, status=response.status_code)
                    else:
                        response_data = response.json()
                        response_details = {
                            "status": "fail",
                            "message": response_data.get("message"),
                            "response": response_data,
                            "is_aadhar_verified": paysprint_dmt_query.is_aadhar_verified,
                            "is_registered": paysprint_dmt_query.is_registered
                        }
                        return Response(response_details, status=response.status_code)

                except requests.RequestException as e:
                    return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def verify_aadhaar_ekyc(self, request):
        pspdmt_unique_id = request.data.get("pspdmt_unique_id")
        contact_number = request.data.get('contact_number')
        aadhaar_no = request.data.get('aadhaar_no')
        pid_data = request.data.get('pid_data')
        sp_id = request.data.get('sp_id')
        secret_key = ''
        partnerId = ''
        try:
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not aadhaar_no: return Response({"status": "fail", "message": "aadhaar_no is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not pid_data: return Response({"status": "fail", "message": "pid_data is required"}, status=status.HTTP_400_BAD_REQUEST)

            mobile_number_validation = validate_mobile_number(contact_number)
            if not mobile_number_validation:
                return Response({'status': 'fail', 'message': 'Invalid contact number format.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # pid_json = xml_to_json_convert(pid_data)
            # pid_value = pid_json.get('PidData')
            json_data = json.loads(pid_data)

            encrypt_pid_token = generate_encrypt_pid_data(json_data.get('data'))

            url = "https://api.paysprint.in/api/v1/service/dmt/kyc/remitter/queryremitter/kyc"
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            else:
                sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            headers = {
                'Token': get_token(),
                # "Token": get_token(secret_key, partnerId),
                'accept': 'application/json',
                'content-type': 'application/json',
                # 'authorisedkey': AuthorisedKey
            }
            payload = {
                "mobile": contact_number,
                "lat": "28.123456",
                "long": "78.123456",
                "aadhaar_number": aadhaar_no,
                "data": encrypt_pid_token
            }
            get_pspdmt_customer = PaysPrintDmtCustomer.objects.get(pspdmt_unique_id=pspdmt_unique_id, customer_contact_no=contact_number)

            if get_pspdmt_customer.customer_aadhaar_no is None:
                get_pspdmt_customer.customer_aadhaar_no = aadhaar_no
                get_pspdmt_customer.is_aadhar_verified = True
                get_pspdmt_customer.save()
            
            try:
                other_charges = get_object_or_404(OtherCharges, oc_name='dmt_kyc')

                admin = PortalUser.objects.get(id=1)
                retailer = PortalUser.objects.get(id=request.user.id)
                retailer_wallet = PortalUserWallet.objects.get(pu=retailer)
                admin_wallet = PortalUserWallet.objects.get(pu=admin)
                
                charge_type = other_charges.charge_type
                tax_rate = AdHSNSAC.objects.get(hsnsac_id=other_charges.hsn_sac_id).tax_rate
                actual_amount = float(other_charges.charge) if charge_type == 'is_flat' else float(other_charges.charge / 100)

                tax_amount = float(actual_amount) - (float(actual_amount)/(1+(float(tax_rate)/100)))
                
                # **Check if the retailer has enough balance**
                if actual_amount > retailer_wallet.main_wallet:
                    return Response({'status': 'fail', 'message': 'Insufficient balance in retailer wallet.'},status=status.HTTP_400_BAD_REQUEST)

                # **Check if the admin has enough balance**
                if actual_amount > admin_wallet.main_wallet:
                    return Response({'status': 'fail', 'message': 'Insufficient balance in admin wallet.'},status=status.HTTP_400_BAD_REQUEST)

                response = requests.post(url, json=payload, headers=headers)
                print('response', response)
                if response.status_code == 200:
                    response_data = response.json()
                    print('response_data', response_data)
                    if response_data.get('response_code') == 0 or response_data.get('response_code') == 1:
                        retailer_wallet.main_wallet = float(retailer_wallet.main_wallet) - float(actual_amount)
                        retailer_wallet.save()

                        admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(actual_amount)
                        admin_wallet.save()

                        admin_global_transaction = GlTrn.objects.create(
                            pu=admin,
                            gl_trn_amt=actual_amount,
                            gl_tax_rate=tax_rate,
                            gl_tax_amt=tax_amount,
                            effectvie_wallet="main_wallet", 
                            effectvie_amt=actual_amount, 
                            effective_type="DR",
                            gl_trn_dt=timezone.now()
                        )

                        retailer_gltrn = GlTrn.objects.create(
                            pu=retailer,
                            gl_trn_amt=actual_amount,
                            gl_tax_rate=tax_rate,
                            gl_tax_amt=tax_amount,
                            effectvie_wallet="main_wallet", 
                            effectvie_amt=actual_amount, 
                            effective_type="DR",
                            gl_trn_dt=timezone.now()
                        )

                        admin_wallet_trn = WalletTrn.objects.create(
                            pu=admin,
                            wl_label=f'DMT KYC Charge of ₹{actual_amount} Deducted from Admin({admin.pu_name}) Main Wallet',
                            effectvie_wallet='main_wallet',
                            effectvie_amt=actual_amount,  
                            effective_type='DR',
                            current_balance=admin_wallet.main_wallet,
                            wl_trn_des=f"{admin.pu_name} kyc charge by DMT",
                            wl_trn_dt=timezone.now()
                        )
                        retailer_wallet_trn = WalletTrn.objects.create(
                            pu=retailer,
                            wl_label=f'DMT KYC Charge of ₹{actual_amount} Deducted from Retailer({retailer.pu_name}) Main Wallet',
                            effectvie_wallet='main_wallet',
                            effectvie_amt=actual_amount,  
                            effective_type='DR',
                            current_balance=retailer_wallet.main_wallet,
                            wl_trn_des=f"{retailer.pu_name} kyc charge by DMT",
                            wl_trn_dt=timezone.now()
                        )
                        
                        get_pspdmt_customer.is_aadhar_verified = True
                        get_pspdmt_customer.save()
                        response_details = { 
                            "status": "success",
                            "message": response_data.get('message'),
                            "response": response_data,
                            "is_aadhar_verified": get_pspdmt_customer.is_aadhar_verified
                        }

                        return Response(response_details, status=status.HTTP_200_OK)
                    elif response_data.get('response_code') == 2:
                        return Response({'status': 'fail', 'message': response_data.get('message')}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        response_details = {
                            "status": "success",
                            "message": "Finger Fetch not done. Please Try Again",
                            "response": response_data,
                            "is_aadhar_verified": get_pspdmt_customer.is_aadhar_verified
                        }
                        return Response(response_details, status=status.HTTP_200_OK if response.status_code == 200 else response.status_code)
                elif response.status_code == 500:
                    return Response({'status': 'error', 'message': response.text}, status=response.status_code)
                else:
                    response_data = response.json()
                    response_details = {
                        "status": "fail",
                        "message": response_data.get('message'),
                        "pspdmt_unique_id": get_pspdmt_customer.pspdmt_unique_id,
                        "response": response_data,
                        "is_aadhar_verified": get_pspdmt_customer.is_aadhar_verified
                    }
                    return Response(response_details, status=response.status_code)

            except requests.RequestException as e:
                return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except PaysPrintDmtCustomer.DoesNotExist:
                return Response({'status': 'fail', 'message': "customer does not exist."}, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def verify_aadhaar_otp(self, request):
        # pspdmt_unique_id = request.data.get("pspdmt_unique_id")
        contact_number = request.data.get('contact_number')
        otp = request.data.get('otp')
        stateresp = request.data.get('stateresp')
        ekyc_id = request.data.get('ekyc_id')
        sp_id = request.data.get('sp_id')

        try:
            url = "https://api.paysprint.in/api/v1/service/dmt/kyc/remitter/registerremitter"
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            else:
                sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            headers = {
                'Token': get_token(),
                # "Token": get_token(secret_key, partnerId),
                'accept': 'application/json',
                'content-type': 'application/json',
                # 'authorisedkey': AuthorisedKey
            }
            
            payload = {
                "mobile": contact_number,
                "otp": otp,
                "stateresp": stateresp,
                "ekyc_id": ekyc_id
            }
            get_pspdmt_customer = PaysPrintDmtCustomer.objects.get(customer_contact_no=contact_number)
            get_pspdmt_customer.save()
            try:
                response = requests.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get('response_code') == 1:
                        get_pspdmt_customer.customer_amount_limit = int(float(response_data.get('data').get('limit')))
                        get_pspdmt_customer.is_registered = True
                        get_pspdmt_customer.save()
                        response_details = {
                            "status": "success",
                            "message": "OTP verified successfully",
                            "is_generated": get_pspdmt_customer.is_generated,
                            "response": response_data,
                            "is_registered": get_pspdmt_customer.is_registered
                        }
                        return Response(response_details, status=status.HTTP_200_OK)
                    else:
                        response_details = {
                            "status": "fail",
                            "message": response_data.get('message'),
                            "is_generated": get_pspdmt_customer.is_generated,
                            "response": response_data,
                            "is_registered": get_pspdmt_customer.is_registered
                        }
                        return Response(response_details, status=status.HTTP_200_OK if response.status_code == 200 else response.status_code)
                        
                elif response.status_code == 500:
                    return Response({'status': 'error', 'message': response.text}, status=response.status_code)
                else:
                    response_data = response.json()
                    response_details = {
                        "status": "fail",
                        "message": response_data.get('message'),
                        "is_generated": get_pspdmt_customer.is_generated,
                        "response": response_data,
                        "is_registered": get_pspdmt_customer.is_registered
                    }
                    return Response(response_details, status=response.status_code)

            except requests.RequestException as e:
                return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_paysprint_customer_details(self, request):
        try:
            pspdmt_unique_id = request.data.get("pspdmt_unique_id")
            contact_number = request.data.get('contact_number')
            first_name = request.data.get('first_name')
            last_name = request.data.get('last_name')
            address = request.data.get('address', None)
            zip_code = request.data.get('zip_code')
            if not contact_number:
                return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not first_name:
                return Response({'status': 'fail', 'message': 'first name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not last_name:
                return Response({'status': 'fail', 'message': 'last name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
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

            get_paysprint_customer = PaysPrintDmtCustomer.objects.get(pspdmt_unique_id=pspdmt_unique_id)
            get_paysprint_customer.customer_first_name=first_name
            get_paysprint_customer.customer_last_name=last_name
            get_paysprint_customer.customer_address=address if address else None
            get_paysprint_customer.customer_zip_code=zip_code
            get_paysprint_customer.is_generated = True
            get_paysprint_customer.save()

            data ={
                "data": {"mobile": get_paysprint_customer.customer_contact_no}
            }

            return Response({"status": "success", "message": "customer details added successfully", "response": data}, status=status.HTTP_200_OK)

        except PaysPrintDmtCustomer.DoesNotExist:
            return Response({'status': 'fail', 'message': 'customer dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_dmt_transaction(self,request):
        contact_numbner = request.data.get('contact_number')
        txntype = request.data.get('txntype')
        amount = request.data.get('amount')
        gst_state = request.data.get('gst_state', "07")
        dob = request.data.get('dob', "1990-03-02")
        address = request.data.get('address', "New delhi")
        pincode = request.data.get('pincode', "110001")
        bene_id = request.data.get('bene_id')
        sp_id = request.data.get('sp_id')
        secret_key = ''
        partnerId = ''

        if not contact_numbner: return Response({'status': 'fail', 'message': 'contact number is requried.'}, status=status.HTTP_400_BAD_REQUEST)
        if not txntype: return Response({'status': 'fail', 'message': 'txntype is requried.'}, status=status.HTTP_400_BAD_REQUEST)
        if not amount: return Response({'status': 'fail', 'message': 'amount is requried.'}, status=status.HTTP_400_BAD_REQUEST)
        if not bene_id: return Response({'status': 'fail', 'message': 'beneId is requried.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            admin_wallet = check_admin_wallet(request, amount)
            retailer_wallet = check_retailer_wallet(request, amount, request.user.id)
            label = get_random_string(length=7, allowed_chars="1234567890")
            referenceid = "DMTTRN_" + label
            print('referenceid', referenceid)

            # Token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJQQVlTUFJJTlQiLCJ0aW1lc3RhbXAiOjE2MTAwMjYzMzgsInBhcnRuZXJJZCI6IlBTMDAxIiwicHJvZHVjdCI6IldBTExFVCIsInJlcWlkIjoxNjEwMDI2MzM4fQ.buzD40O8X_41RmJ0PCYbBYx3IBlsmNb9iVmrVH9Ix64"
            # AuthorisedKey = "MzNkYzllOGJmZGVhNWRkZTc1YTgzM2Y5ZDFlY2EyZTQ="
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            else:
                sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            header = {
                "Token": get_token(),
                # "Token": get_token(secret_key, partnerId),
                # "Authorisedkey": AuthorisedKey,
                "Content-Type": "application/json",
                "accept": "application/json"
            }

            payload = {
                "mobile": contact_numbner,
                "txntype": txntype,
                "amount": amount,
                "pincode": "110001",
                "address": "New delhi",
                "dob": "1990-03-02",
                "gst_state": "07",
                # "lat": lat,
                # "long": long,
                "referenceid": referenceid,
                "bene_id": bene_id
            }
            print('=======', payload)
            url = "https://api.paysprint.in/api/v1/service/dmt/kyc/transact/transact/send_otp"
            

            transaction_response = requests.post(url, json=payload, headers=header)
            print('transaction_response', transaction_response.json())
            if transaction_response.status_code == 200:
                transaction_response_json = transaction_response.json()

                data = {'response': transaction_response_json, 'referenceid': referenceid}
                return Response({'status': 'success', 'message': transaction_response_json.get("message"), 'data': data}, status=status.HTTP_200_OK)

            elif transaction_response.status_code == 500:
                return Response({'status': 'fail', 'message': transaction_response.text}, status=transaction_response.status_code)

            else:
                transaction_response_json = transaction_response.json()
                data = {'response': transaction_response_json, 'referenceid': referenceid}
                return Response({'status': 'fail', 'message': transaction_response_json.get("message"), 'data': data}, status=transaction_response.status_code)

        except ValidationError as e:
            message = str(e)
            if "ErrorDetail" in message:
                message = message.split("string='")[1].split("', code=")[0]  
            return Response({'status': 'fail', 'message': message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def dmt_transaction(self,request):
        contact_numbner = request.data.get('contact_number')
        referenceid = request.data.get('referenceid')
        bene_id = request.data.get('bene_id')
        txntype = request.data.get('txntype')
        amount = request.data.get('amount')
        stateresp = request.data.get('stateresp')
        otp = request.data.get('otp')
        sp_id = request.data.get('sp_id') 
        response_json = {}
        secret_key = ''
        partnerId = ''

        if not contact_numbner: return Response({'status': 'fail', 'message': 'contact number is requried.'}, status=status.HTTP_400_BAD_REQUEST)
        if not txntype: return Response({'status': 'fail', 'message': 'txntype is requried.'}, status=status.HTTP_400_BAD_REQUEST)
        if not amount: return Response({'status': 'fail', 'message': 'amount is requried.'}, status=status.HTTP_400_BAD_REQUEST)
        if not stateresp: return Response({'status': 'fail', 'message': 'stateresp is requried.'}, status=status.HTTP_400_BAD_REQUEST)
        if not otp: return Response({'status': 'fail', 'message': 'otp is requried.'}, status=status.HTTP_400_BAD_REQUEST)
        if not referenceid: return Response({'status': 'fail', 'message': 'referenceId is requried.'}, status=status.HTTP_400_BAD_REQUEST)
        if not bene_id: return Response({'status': 'fail', 'message': 'beneId is requried.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            else:
                sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            header = {
                "Token": get_token(),
                # "Token": get_token(secret_key, partnerId),
                # "Authorisedkey": AuthorisedKey,
                "Content-Type": "application/json",
                "accept": "application/json"
            }

            payload = {
                "mobile": contact_numbner,
                "referenceid": referenceid,
                "pincode": "110001",
                "address": "New delhi",
                "dob": "1990-03-02",
                "gst_state": "07",
                "bene_id": bene_id,
                "txntype": txntype,
                "amount": amount, 
                "stateresp": stateresp,
                "otp": otp
            }

            url = "https://api.paysprint.in/api/v1/service/dmt/kyc/transact/transact"
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            customer_contact_details = PaysPrintDmtCustomer.objects.get(customer_contact_no=contact_numbner)
            bank_id = PaysPrintDmtBankAccount.objects.get(customer_contact__contains=[{contact_numbner: bene_id}])
            print(bank_id, 'bank_id')
            if sp.service.service_name != "DMT":
                return Response({'status': 'fail', 'message': 'Invalid service provider. Please use Direct Money Transfer service provider.'}, status=status.HTTP_400_BAD_REQUEST)

            response = requests.post(url, json=payload, headers=header)
            print(response.json(), 'dmt transaction response', payload)
            if response.status_code == 200:
                response_json = response.json()
                print('response_json', response_json)
                if response_json.get("response_code") == 1:
                    dmt_trn = DMTTransaction.objects.create(
                        dmt_customer_contact_number = customer_contact_details.customer_contact_no,
                        dmt_customer_name = f"{customer_contact_details.customer_first_name} {customer_contact_details.customer_last_name}",
                        dmt_refrence_id = referenceid,
                        dmt_bene_id = bank_id,
                        dmt_txntype = txntype,
                        dmt_txn_amount = amount,
                        dmt_resposne = response_json,
                        dmt_txn_status = "SUCCESS",
                        dmt_sp_id = sp,
                        created_by = request.user.id
                    )
                    customer_contact_details.customer_amount_limit -= int(amount)
                    customer_contact_details.save()
                    admin_charges = None 
                    admin_charge_queryset = AdCharges.objects.filter(service_provider_id=sp_id)
                    service_provider = AdServiceProvider.objects.get(sp_id=sp_id)

                    gst_rate = service_provider.hsn_sac.tax_rate
                    if admin_charge_queryset.exists():  # Ensure queryset is not empty
                        for charge in admin_charge_queryset:
                            if charge.minimum <= float(dmt_trn.dmt_txn_amount) <= charge.maximum:
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

                    char_comm_amt = float(dmt_trn.dmt_txn_amount) * (float(admin_rate) / 100) if admin_rate_type == 'is_percent' else float(admin_rate)
                    admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))

                    portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)
                    data = {
                        "service_id": dmt_trn.pk,
                        "amount": dmt_trn.dmt_txn_amount,
                        "table_name": "ad_dmt_transaction",
                        "wl_label": f"DMT_by_{portal_user_details.pud_unique_id}_of_amount_{dmt_trn.dmt_txn_amount}_with_tx_id_{dmt_trn.dmt_trn_id}",
                        "gst_rate": gst_rate,
                        "admin_tax_amt": admin_tax_amt,
                        "char_comm_amt": char_comm_amt,
                        "admin_charges_type": admin_charges_type,
                        "sp_id": sp_id,
                        "contact_number": contact_numbner,
                        "name": f"{customer_contact_details.customer_first_name} {customer_contact_details.customer_last_name}",
                        "response_data": response_json,
                        "label": service_provider.label,
                        "category": None,
                        "is_self_config": service_provider.is_self_config
                    }
                    print('data', data)
                    charges_calculation_function(request, data)

                    user_activity = {
                        "table_id": dmt_trn.pk,
                        "table_name": 'ad_dmt_transaction',
                        "ua_action": 'Create',  # Action performed
                        "ua_description": 'DMT transaction successfully.',  # Action description
                        "created_by": request.user,  # Current user performing the action
                        "request_data": dict(request.data),  # Request data
                        "response_data": model_to_dict(dmt_trn)
                    }

                    add_user_activity(user_activity)
                    # for retailer
                    # rt_gl = GlTrn.objects.create(
                    #     service_trn_id=dmt_trn.pk,
                    #     pu_id=request.user.id,
                    #     gl_trn_amt=dmt_trn.dmt_txn_amount,
                    #     effectvie_wallet='pg_wallet',
                    #     effectvie_amt=dmt_trn.dmt_txn_amount,
                    #     service_trn_table='ad_dmt_transaction',
                    #     effective_type='CR',
                    #     gl_trn_dt=now(),
                    # )

                    # WalletTrn.objects.create(
                    #     action_id=rt_gl.pk,
                    #     action_type='Order',
                    #     pu_id=request.user.id,
                    #     wl_label=f"DMT_by_{portal_user_details.pud_unique_id}_of_amount_{dmt_trn.dmt_txn_amount}_with_tx_id_{dmt_trn.dmt_trn_id}",
                    #     effectvie_wallet='pg_wallet',
                    #     effectvie_amt=dmt_trn.dmt_txn_amount,
                    #     effective_type='CR',
                    #     wl_trn_dt=now()
                    # )

                    # rtl_wallet = PortalUserWallet.objects.get(pu_id=request.user.id)
                    # rtl_wallet.pg_wallet = float(rtl_wallet.pg_wallet) + float(dmt_trn.dmt_txn_amount)
                    # rtl_wallet.updated_at = now()
                    # rtl_wallet.save()

                    # # for admin
                            
                    # admin_gl = GlTrn.objects.create(
                    #     service_trn_id=dmt_trn.pk,
                    #     pu_id=1,
                    #     gl_trn_amt=dmt_trn.dmt_txn_amount,
                    #     effectvie_wallet='main_wallet',
                    #     effectvie_amt=dmt_trn.dmt_txn_amount,
                    #     service_trn_table='ad_dmt_transaction',
                    #     effective_type='CR',
                    #     gl_trn_dt=now(),
                    # )

                    # WalletTrn.objects.create(
                    #     action_id=admin_gl.pk,
                    #     action_type='Order',
                    #     pu_id=1,
                    #     wl_label=f"DMT_by_{portal_user_details.pud_unique_id}_of_amount_{dmt_trn.dmt_txn_amount}_with_tx_id_{dmt_trn.dmt_trn_id}",
                    #     effectvie_wallet='main_wallet',
                    #     effectvie_amt=dmt_trn.dmt_txn_amount,
                    #     effective_type='CR',
                    #     wl_trn_dt=now()
                    # )
                    
                    # admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                    # admin_wallet.main_wallet = float(admin_wallet.main_wallet) + float(dmt_trn.dmt_txn_amount)
                    # admin_wallet.updated_at = now()
                    # admin_wallet.save()

                    # admin_gl = GlTrn.objects.create(
                    #     service_trn_id=dmt_trn.pk,
                    #     pu_id=1,
                    #     gl_tax_rate=gst_rate,
                    #     gl_tax_amt=admin_tax_amt,
                    #     gl_trn_amt=dmt_trn.dmt_txn_amount,
                    #     effectvie_wallet='main_wallet',
                    #     effectvie_amt=char_comm_amt,
                    #     service_trn_table='ad_dmt_transaction',
                    #     effective_type=admin_charges_type,
                    #     gl_trn_dt=now(),
                    # )

                    # WalletTrn.objects.create(
                    #     action_id=dmt_trn.pk,
                    #     action_type='Order',
                    #     pu_id=1,
                    #     wl_label=f"DMT_by_{portal_user_details.pud_unique_id}_of_amount_{dmt_trn.dmt_txn_amount}_with_tx_id_{dmt_trn.dmt_trn_id}",
                    #     effectvie_wallet='main_wallet',
                    #     effectvie_amt=char_comm_amt,
                    #     effective_type=admin_charges_type,
                    #     wl_trn_dt=now()
                    # )

                    # admin_wallet_ch = PortalUserWallet.objects.get(pu_id=1)

                    # if admin_charges_type == 'CR':
                    #     admin_wallet_ch.main_wallet = float(admin_wallet_ch.main_wallet) + float(char_comm_amt)
                    # else:
                    #     admin_wallet_ch.main_wallet = float(admin_wallet_ch.main_wallet) - float(char_comm_amt)
                    # admin_wallet_ch.updated_at = now()
                    # admin_wallet_ch.save()

                    # data = {
                    #     'order_amount': dmt_trn.dmt_txn_amount,
                    #     'id': request.user.id,
                    #     'sp_id': sp_id,
                    #     'customer_contact_no': dmt_trn.dmt_customer_contact_number,
                    #     'customer_name': dmt_trn.dmt_customer_name,
                    #     'trn_response': response_json,
                    #     'service_trn': dmt_trn.pk,
                    #     'label': service_provider.label,
                    #     'category': None,
                    #     'table_name': 'ad_dmt_transaction'
                    # }
                    # after_tx_cal(request, data)

                    return Response({'status': 'success', 'message': 'Transaction successfully.', 'data': response_json}, status=status.HTTP_200_OK)

                else:
                    dmt_trn = DMTTransaction.objects.create(
                        dmt_customer_contact_number = customer_contact_details.customer_contact_no,
                        dmt_customer_name = f"{customer_contact_details.customer_first_name} {customer_contact_details.customer_last_name}",
                        dmt_refrence_id = referenceid,
                        dmt_bene_id = bank_id,
                        dmt_txntype = txntype,
                        dmt_txn_amount = amount,
                        dmt_resposne = response_json,
                        dmt_txn_status = "PENDING",
                        dmt_sp_id = sp,
                        created_by = request.user.id
                    )
                    user_activity = {
                        "table_id": dmt_trn.pk,
                        "table_name": 'ad_dmt_transaction',
                        "ua_action": 'Create',  # Action performed
                        "ua_description": response_json.get("message"),  # Action description
                        "created_by": request.user,  # Current user performing the action
                        "request_data": dict(request.data),  # Request data
                        "response_data": model_to_dict(dmt_trn)
                    }

                    add_user_activity(user_activity)
                    return Response({'status': 'fail', 'message': response_json.get("message"), 'data': response_json}, status=status.HTTP_400_BAD_REQUEST)

            elif response.status_code == 500:
                return Response({'status': 'fail', 'message': response.text}, status=response.status_code)

            else:
                dmt_trn = DMTTransaction.objects.create(
                    dmt_customer_contact_number = customer_contact_details.customer_contact_no,
                    dmt_customer_name = f"{customer_contact_details.customer_first_name} {customer_contact_details.customer_last_name}",
                    dmt_refrence_id = referenceid,
                    dmt_bene_id = bank_id,
                    dmt_txntype = txntype,
                    dmt_txn_amount = amount,
                    dmt_resposne = response_json,
                    dmt_txn_status = "FAILED",
                    dmt_sp_id = sp,
                    created_by = request.user.id
                )
                user_activity = {
                    "table_id": dmt_trn.pk,
                    "table_name": 'ad_dmt_transaction',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'DMT Transaction Failed.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(dmt_trn)
                }

                add_user_activity(user_activity)
                return Response({'status': 'fail', 'message': "Transaction Failed", 'data': response_json}, status=status.HTTP_400_BAD_REQUEST)

        except PaysPrintDmtBankAccount.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Bank account details dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)
        except PaysPrintDmtCustomer.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Customer details dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)
        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service Provider dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)
        except DMTTransaction.DoesNotExist:
            return Response({'status': 'fail', 'message': 'DMT Transaction dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def dmt_transaction_status(self, request):
        string_referenceids = request.data.get('referenceids')  # Extract multiple reference IDs as a string
        # sp_id = request.data.get('sp_id')
        secret_key = ''
        partnerId = ''

        if string_referenceids:
            # Remove spaces and square brackets, then split by comma
            string_referenceids = string_referenceids.replace(' ', '').replace('[', '').replace(']', '')
            split_referenceids = string_referenceids.split(',')
        else:
            split_referenceids = []

        # Now, split_referenceids will contain the list without square brackets

        if not string_referenceids:
            return Response({'status': 'fail', 'message': 'At least one referenceId is required.'}, status=status.HTTP_400_BAD_REQUEST)

        results = []

        try:
            for referenceid in split_referenceids:
                payload = {"referenceid": referenceid}
                url = "https://api.paysprint.in/api/v1/service/dmt/kyc/transact/transact/querytransact"
                # sp = AdServiceProvider.objects.get(sp_id=sp_id)
                # if sp.is_self_config == True:
                #     secret_key = sp.credentials_json.get('secret_key')
                #     partnerId = sp.credentials_json.get('partnerId')
                # else:
                #     sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
                #     secret_key = sp.credentials_json.get('secret_key')
                #     partnerId = sp.credentials_json.get('partnerId')
                header = {
                    "Token": get_token(),
                    # "Token": get_token(secret_key, partnerId),
                    # "Authorisedkey": AuthorisedKey,
                    "Content-Type": "application/json",
                    "accept": "application/json"
                }
                
                response = requests.post(url, json=payload, headers=header)
                response_json = response.json()
                print('response_json', response_json)
                if response_json.get("status") == True:
                    try:
                        transaction_data = DMTTransaction.objects.get(dmt_refrence_id=referenceid)
                        retailer_data = PortalUser.objects.get(id=transaction_data.created_by)
                        formatted_date = transaction_data.dmt_service_trn_dt.strftime("%d %B %Y %H:%M")

                        results.append({
                            "retailer_name": retailer_data.pu_name,
                            "retailer_contact_no": retailer_data.pu_contact_no,
                            "customer_mobile_number": transaction_data.dmt_customer_contact_number,
                            "customer_name": transaction_data.dmt_customer_name,
                            "beneficiary_name": transaction_data.dmt_bene_id.pspdmt_beneficiary_name,
                            "beneficiary_bank": transaction_data.dmt_bene_id.pspdmt_bank_name,
                            "beneficiary_account_no": transaction_data.dmt_bene_id.bnk_acc_no,
                            "bank_ifsc_code": transaction_data.dmt_bene_id.bnk_ifsc,
                            "urt_rrn": response_json.get('utr'),
                            "transaction_status": transaction_data.dmt_txn_status,
                            "transaction_id": transaction_data.dmt_refrence_id,
                            "transaction_date": formatted_date,
                            "payment": "Cash",
                            "transfer_mode": transaction_data.dmt_txntype,
                            "transaction_amount": transaction_data.dmt_txn_amount,
                        })
                    except DMTTransaction.DoesNotExist:
                        results.append({
                            "referenceid": referenceid,
                            "status": "fail",
                            "message": "DMT Transaction does not exist."
                        })
                else:
                    results.append({
                        "referenceid": referenceid,
                        "status": "fail",
                        "message": response_json.get("message"),
                        "response": response_json
                    })

            return Response({'status': 'success', 'message': 'Transaction details fetched.', 'data': {"results": results}}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def fetch_all_dmt_transaction(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size')
        search = request.data.get('search', '')
        trn_status = request.data.get('transaction_status', '')
        date_filter = request.data.get('date_filter', '')  # today, weekly, monthly, yearly, custom
        start_date = request.data.get('start_date', '')
        end_date = request.data.get('end_date', '')

        try:
            if not page_size: return Response({'status': 'fail','message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(page_size) == False: return Response({'status': 'fail','message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if page_number:
                if isnumber(page_number) == False: return Response({'status': 'fail','message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            queryset = DMTTransaction.objects.filter(created_by=request.user.id).order_by('-pk')

            if search != '':
                queryset = queryset.filter(Q(dmt_customer_contact_number__icontains=search) | Q(dmt_refrence_id__icontains=search) | Q(dmt_bene_id__bnk_acc_no__icontains=search) | Q(dmt_bene_id__pspdmt_beneficiary_name__icontains=search))

            if trn_status != '':
                queryset = queryset.filter(dmt_txn_status=trn_status)

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
            print('queryset', queryset)
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
                        'message': 'DMT Transaction Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                serializer = PaySprintDmtTrnSerializer(page_obj.object_list, many=True).data

                for trn in serializer:
                    sp_obj = AdServiceProvider.objects.get(sp_id=trn['dmt_sp_id'])
                    trn['label'] = sp_obj.label
                    # Convert to datetime if it's a string
                    if isinstance(trn['dmt_service_trn_dt'], str):
                        trn['dmt_service_trn_dt'] = datetime.strptime(trn['dmt_service_trn_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")

                    trn['dmt_service_trn_dt'] = trn['dmt_service_trn_dt'].strftime("%d-%m-%Y %I:%M %p")  

                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer
                }
                return Response({
                    'status': 'success',
                    'message': 'DMT Transaction data',
                    'data': paginated_response_data
                }, status=status.HTTP_200_OK)

            serializer = PaySprintDmtTrnSerializer(queryset, many=True, context={'request': request}).data

            for trn in serializer:
                sp_obj = AdServiceProvider.objects.get(sp_id=trn['dmt_sp_id'])
                trn['label'] = sp_obj.label
                # Convert to datetime if it's a string
                if isinstance(trn['dmt_service_trn_dt'], str):
                    trn['dmt_service_trn_dt'] = datetime.strptime(trn['dmt_service_trn_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")

                trn['dmt_service_trn_dt'] = trn['dmt_service_trn_dt'].strftime("%d-%m-%Y %I:%M %p")    
                
            response_data = {
                'status': 'success',
                'message': 'DMT Transaction data',
                'data': serializer
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'fail',
                'message': str(e),
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        contact_number = request.data.get('contact_number')
        first_name = request.data.get('first_name', None)
        last_name = request.data.get('last_name', None)
        aadress = request.data.get('address', None)
        zip_code = request.data.get('zip_code', None)
        # aadhaar_card = request.data.get('aadhaar_card', None)

        try:

            mobile_number_validation = validate_mobile_number(contact_number)
            if mobile_number_validation == False: return Response({'status': 'fail', 'message': 'Invalid contact number format.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if first_name:
                first_name_validation = isstring(first_name)
                if first_name_validation == False: return Response({'status': 'fail', 'message': 'Invalid first name format.'}, status=status.HTTP_400_BAD_REQUEST)

            if last_name:
                last_name_validation = isstring(last_name)
                if last_name_validation == False: return Response({'status': 'fail', 'message': 'Invalid last name format.'}, status=status.HTTP_400_BAD_REQUEST)

            if zip_code:
                zip_code_validation = isnumber(zip_code)
                if zip_code_validation == False: return Response({'status': 'fail', 'message': 'Invalid zip code format.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # if aadhaar_card:
            #     aadhaar_card_validation = isnumber(aadhaar_card)
            #     if aadhaar_card_validation == False: return Response({'status': 'fail', 'message': 'Invalid aadhaar card format.'}, status=status.HTTP_400_BAD_REQUEST)

            customer_contact_details = PaysPrintDmtCustomer.objects.filter(customer_contact_no=contact_number).first()
            if not customer_contact_details: return Response({'status': 'fail', 'message': 'Customer details not found.'}, status=status.HTTP_400_BAD_REQUEST)

            customer_contact_details.customer_first_name = first_name
            customer_contact_details.customer_last_name = last_name
            customer_contact_details.customer_address = aadress
            customer_contact_details.customer_zip_code = zip_code
            # customer_contact_details.customer_aadhaar_no = aadhaar_card
            customer_contact_details.save()
            user_activity = {
                "table_id": customer_contact_details.pk,
                "table_name": 'ad_paysprint_dmt_customer',
                "ua_action": 'Update',  # Action performed
                "ua_description": 'Customer details updated successfully.',  # Action description
                "created_by": request.user,  # Current user performing the action
                "request_data": dict(request.data),  # Request data
                "response_data": model_to_dict(customer_contact_details)
            }

            add_user_activity(user_activity)
            return Response({'status': 'success', 'message': 'Customer details updated successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaysPrintDmtBeneficiaryAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication] 
    permission_classes = [IsRetailer]

    def post(self, request):
        try:
            if 'penny_drop' in request.data and 'contact_number' in request.data and 'account_number' in request.data and 'bank_id' in request.data and 'bene_name' in request.data and 'bene_id' in request.data:
                return self.veirfy_bank_account(request)
            if 'digitap' in request.data and 'account_number' in request.data and 'bank_id' in request.data:
                return self.digitap_veirfy_bank_account(request)
            elif 'beneficiary_name' in request.data and 'account_number' in request.data and 'ifsc_code' in request.data and 'contact_number' in request.data:
                return self.add_customer_paysprint_dmt_bank_account(request)
            elif 'fetch_beneficiary' in request.data and 'contact_number' in request.data:
                return self.fetch_beneficiary_data(request)
            elif 'page_size' in request.data or 'page_number' in request.data:
                return self.fatch_customer_paysprint_dmt_bank_account(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def add_customer_paysprint_dmt_bank_account(self, request):
        print('add_customer_paysprint_dmt_bank_account')
        try:
            # bank_name = request.data.get('bank_name')
            beneficiary_name = request.data.get('beneficiary_name')
            account_number = request.data.get('account_number')
            ifsc_code = request.data.get('ifsc_code')
            contact_number = request.data.get('contact_number')
            bank_id = request.data.get('bank_id')
            gst_state = request.data.get('gst_state', "07")
            dob = request.data.get('dob', "1990-03-02")
            address = request.data.get('address', "New delhi")
            pincode = request.data.get('pincode', "110001")
            # sp_id = request.data.get('sp_id')
            secret_key=''
            partnerId=''

            # if not bank_name: return Response({'status': 'fail', 'message': 'bank name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not beneficiary_name: return Response({'status': 'fail', 'message': 'beneficiary name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not account_number: return Response({'status': 'fail', 'message': 'account number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not ifsc_code: return Response({'status': 'fail', 'message': 'IFSC code is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            get_bank_name = GlobalBankList.objects.get(bank_id=bank_id)
            bank_name = get_bank_name.bank_name

            url = "https://api.paysprint.in/api/v1/service/dmt/kyc/beneficiary/registerbeneficiary"
            # sp = AdServiceProvider.objects.get(sp_id=sp_id)
            # if sp.is_self_config == True:
            #     secret_key = sp.credentials_json.get('secret_key')
            #     partnerId = sp.credentials_json.get('partnerId')
            # else:
            #     sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
            #     secret_key = sp.credentials_json.get('secret_key')
            #     partnerId = sp.credentials_json.get('partnerId')
            headers = {
                'Token': get_token(),
                # "Token": get_token(secret_key, partnerId),
                'accept': 'application/json', 
                'content-type': 'application/json',
                # 'authorisedkey': AuthorisedKey
            }
            
            payload = {
                "mobile": contact_number,
                "benename": bank_name,
                "bankid": bank_id,
                "accno": account_number,
                "ifsccode": ifsc_code,
                "verified": 0,
                "gst_state": gst_state,
                "dob": dob,
                "address": address,
                "pincode": pincode
            }
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()
            existing_account = PaysPrintDmtBankAccount.objects.filter(pspdmt_bank_name=bank_name, bnk_acc_no=account_number, bnk_ifsc=ifsc_code).first()
            print('existing_account', existing_account)
            if existing_account:
                print('step1')
                if contact_number in existing_account.customer_contact:
                    return Response({'status': 'fail', 'message': 'This bank account with the provided contact number already exists.'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    print('step2')
                    existing_account.customer_contact.append({contact_number: str(response_data.get('data').get('bene_id'))})
                    existing_account.save()
                    return Response({'status': 'success', 'message': 'Contact number added to existing DMT bank account.'}, status=status.HTTP_200_OK)

            else:
                print('step3')
                existing_account_number = PaysPrintDmtBankAccount.objects.filter(bnk_acc_no=account_number).first()
                if existing_account_number and int(account_number) == existing_account_number.bnk_acc_no:
                    return Response({'status': 'fail', 'message': 'Account number already existing DMT bank account.'}, status=status.HTTP_400_BAD_REQUEST)

                print('add bene response', response.json())
                if response.status_code == 200:
                    
                    if response_data.get('response_code') == 1:
                        if response_data.get('data').get('verified') == "0":
                            referenceid= get_random_string(length=9, allowed_chars='0123456789')
                            url = "https://api.paysprint.in/api/v1/service/dmt/kyc/beneficiary/registerbeneficiary/benenameverify"

                            headers = {
                                'Token': get_token(),
                                # "Token": get_token(secret_key, partnerId),
                                'accept': 'application/json', 
                                'content-type': 'application/json',
                            }

                            payload = {
                                "mobile": contact_number,
                                "accno": account_number,
                                "bankid": bank_id,
                                "benename": bank_name,
                                "referenceid": referenceid,
                                "pincode": pincode,
                                "address": address,
                                "dob": dob,
                                "gst_state": gst_state,
                                "bene_id":response_data.get('data').get('bene_id'),
                            }
                            response_penny_drop = requests.post(url, json=payload, headers=headers)

                            if response_penny_drop.status_code == 200:
                                response_data = response_penny_drop.json()
                                if response_data.get('response_code') == 1:
                                    response_details = {
                                        "status": "success",
                                        "message": "DMT bank benificiary added successfully.",
                                        "response": response_data
                                    }
                                else:
                                    response_details = {
                                        "status": "fail",
                                        "message": response_data.get("message"),
                                        "response": response_data
                                    }
                                return Response(response_details, status=response_penny_drop.status_code)
                            else:
                                return Response({'status': 'error','message': "PaySprint api service down.", 'data': response_penny_drop.text}, status=response_penny_drop.status_code)

                        beneficiary_prefix = "DMT_"
                        beneficiary_code= get_random_string(length=8, allowed_chars='qwertyuiopasdfghjklzxcvbnm0123456789')
                        paysprint_dmt_queryset = PaysPrintDmtBankAccount.objects.create(
                            pspdmt_beneficiary_id=f'{beneficiary_prefix}{beneficiary_code}',
                            pspdmt_beneficiary_name=beneficiary_name,
                            pspdmt_bank_name=bank_name,
                            bnk_acc_no=account_number,
                            bnk_ifsc=ifsc_code,
                            gst_state_code=gst_state,
                            dob=dob,
                            address=address,
                            pincode=pincode,
                            is_added=True,
                            customer_contact=[{contact_number: str(response_data.get('data').get('bene_id'))}]
                        )

                        paysprint_dmt_queryset.pspdmt_bene_id = response_data.get('data').get('bene_id') if response_data.get('data') else None
                        paysprint_dmt_queryset.save()

                        response_details = {
                            "status": "success",
                            "message": "DMT bank benificiary added successfully.",
                            "response": response_data
                        }
                    elif response_data.get('response_code') == 2:
                        response_details = {
                            "status": "success",
                            "message": "Unable to create beneficiary details.",
                            "response": response_data
                        }
                    else:
                        response_details = {
                            "status": "success",
                            "message": "Remitter accounts not found.",
                            "response": response_data
                        }

                    return Response(response_details, status=status.HTTP_200_OK if response.status_code == 200 else response.status_code)
                elif response.status_code == 500:
                    return Response({'status': 'error','message': "PaySprint api service down.", 'data': response.text}, status=response.status_code)
                else:
                    response_data = response.json()
                    response_details = {
                        "status": "fail",
                        "message": response_data.get("message"),
                        "response": response_data
                    }
                    return Response(response_data, status=response.status_code)

        except requests.RequestException as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except GlobalBankList.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Bank Does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def digitap_veirfy_bank_account(self, request):
        print('digitap_veirfy_bank_account')
        bank_name = request.data.get('bank_name')
        account_number = request.data.get('account_number')
        ifsc_code = request.data.get('ifsc_code')
        bank_id = request.data.get('bank_id')

        client_id = 76034597
        client_secret = "jIzkvvBkEFvIYjde8O7lini65ghUk5Yo"
        callback_url = "https://api.digitap.ai/penny-drop/v2/check-valid"

        if not bank_name: return Response({'status': 'fail', 'message': 'bank name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not account_number: return Response({'status': 'fail', 'message': 'account number is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ifsc_code: return Response({'status': 'fail', 'message': 'IFSC code is required.'}, status=status.HTTP_400_BAD_REQUEST)

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

        try:
            get_bank_name = GlobalBankList.objects.get(bank_id=bank_id)
            bank_name = get_bank_name.bank_name

            auth_string = f"{client_id}:{client_secret}"

            encode_auth_string = base64.b64encode(bytes(auth_string, 'utf-8'))

            payload = {
                "accNo": account_number,
                "ifsc": ifsc_code,
            }
            headers = {
                "ent_authorization": encode_auth_string,
                "Content-Type": "application/json"
            }

            verify_bank_response = requests.post(callback_url, headers=headers, json=payload)
            verify_bank_response_json = verify_bank_response.json()
            print('verify_bank_response_json', verify_bank_response_json)
            print('verify_bank_response_json.get("model").get("beneficiaryName")', verify_bank_response_json.get("model").get("beneficiaryName"))
            existing_account_number = PaysPrintDmtBankAccount.objects.filter(bnk_acc_no=account_number, bnk_ifsc=ifsc_code).first()
            if verify_bank_response_json.get("model").get("status") == "SUCCESS":

                service_provider = AdServiceProvider.objects.get(sp_id=6)
                charges = PortalUserCharges.objects.get(sp=service_provider, dh__isnull=True)
                charge_rate = charges.puc_charges[0].get('rate')
                retailer = PortalUser.objects.get(id=request.user.id)
                admin = PortalUser.objects.get(id=1)
                retailer_wallet = PortalUserWallet.objects.get(pu=retailer)
                admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                pud_unique_id = PortalUserDetails.objects.get(pu=retailer).pud_unique_id
                charge_tax_rate = service_provider.hsn_sac.tax_rate
                gst_charge_amt = float(charge_rate) - (float(charge_rate)/(1+(float(charge_tax_rate)/100)))

                retailer_wallet.main_wallet = float(retailer_wallet.main_wallet) - float(charge_rate)
                retailer_wallet.updated_at = now()
                retailer_wallet.save()
                admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(charge_rate)
                admin_wallet.updated_at = now()
                admin_wallet.save()

                retailer_global_transaction = GlTrn.objects.create(
                    service_trn_id=retailer_wallet.pk,
                    gl_trn_amt=charge_rate,
                    gl_tax_rate=charge_tax_rate,
                    gl_tax_amt=gst_charge_amt,
                    effectvie_wallet="main_wallet",
                    effectvie_amt=charge_rate,
                    effective_type="DR",
                    pu=retailer,
                    service_trn_table="ad_portal_user_wallet",
                    gl_trn_dt=timezone.now()
                )

                WalletTrn.objects.create(
                    action_id=retailer_global_transaction.pk,
                    action_type=f"digitap_verify_by_{pud_unique_id}",
                    wl_label=f"Charges by {retailer.pu_name}",
                    effectvie_wallet="main_wallet",
                    effectvie_amt=charge_rate,
                    effective_type="DR",
                    pu=retailer,
                    current_balance=retailer_wallet.main_wallet,
                    wl_trn_dt=timezone.now()
                )

                admin_global_transaction = GlTrn.objects.create(
                    service_trn_id=admin_wallet.pk,
                    gl_trn_amt=charge_rate,
                    gl_tax_rate=charge_tax_rate,
                    gl_tax_amt=gst_charge_amt,
                    effectvie_wallet="main_wallet",
                    effectvie_amt=charge_rate,
                    effective_type="DR",
                    pu=admin,
                    service_trn_table="ad_portal_user_wallet",
                    gl_trn_dt=timezone.now()
                )

                WalletTrn.objects.create(
                    action_id=admin_global_transaction.pk,
                    action_type=f"digitap_verify_by_admin",
                    wl_label=f"Charges by {admin.pu_name}",
                    effectvie_wallet="main_wallet",
                    effectvie_amt=charge_rate,
                    effective_type="DR",
                    pu=admin,
                    current_balance=admin_wallet.main_wallet,
                    wl_trn_dt=timezone.now()
                )

                
                print('existing_account_number', existing_account_number)
                if existing_account_number and int(account_number) == existing_account_number.bnk_acc_no:
                    print('step1')
                    if existing_account_number.is_verified_1 == True:
                        print('step2')
                        return Response({'status': 'success', 'message': 'This bank account already verified.'}, status=status.HTTP_200_OK)
                    else:
                        print('step3')
                        existing_account_number.is_verified_1 = True
                        existing_account_number.pspdmt_beneficiary_name = verify_bank_response_json.get("model").get("beneficiaryName")
                        existing_account_number.save()
                        print('step4')
                        return Response({'status': 'success', 'message': 'Bank verification completed successfully.', "data": {'pspdmt_beneficiary_name': verify_bank_response_json.get("model").get("beneficiaryName")}}, status=status.HTTP_400_BAD_REQUEST)
                beneficiary_prefix = "DMT_"
                beneficiary_code= get_random_string(length=8, allowed_chars='qwertyuiopasdfghjklzxcvbnm0123456789')
                paysprint_dmt_queryset = PaysPrintDmtBankAccount.objects.create(
                    pspdmt_beneficiary_id=f'{beneficiary_prefix}{beneficiary_code}',
                    pspdmt_beneficiary_name=verify_bank_response_json.get("model").get("beneficiaryName"),
                    pspdmt_bank_name=bank_name,
                    bnk_acc_no=account_number,
                    bnk_ifsc=ifsc_code,
                    is_added=True,
                    is_verified_1=True,
                    customer_contact=[]
                )
                return Response({"status": "success", "message": "Bank verification completed successfully.", "data": {'verify_bank_response_json': verify_bank_response_json, 'pspdmt_beneficiary_name': verify_bank_response_json.get("model").get("beneficiaryName")}}, status=status.HTTP_200_OK)
            if verify_bank_response_json.get("model").get("status") == "PENDING":
                return Response({"status": "pending", "message": "Bank verification is currently pending. Please check back later.", "data": verify_bank_response_json}, status=status.HTTP_200_OK)
            else:
                existing_account_number.is_verified_1 = True
                existing_account_number.save()
                return Response({"status": "fail", "message": verify_bank_response_json.get('model').get('desc'), "data": verify_bank_response_json}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def veirfy_bank_account(self, request):
        print('veirfy_bank_account')
        beneficiary_name = request.data.get('beneficiary_name')
        bene_name = request.data.get('bene_name')
        ifsc_code = request.data.get('ifsc_code')
        account_number = request.data.get('account_number')
        contact_number = request.data.get('contact_number')
        bank_id = request.data.get('bank_id')
        bene_id = request.data.get('bene_id')
        gst_state = request.data.get('gst_state', "07")
        dob = request.data.get('dob', "1990-03-02")
        address = request.data.get('address', "New delhi")
        pincode = request.data.get('pincode', "110001")
        sp_id = request.data.get('sp_id')
        partnerId = ''
        secret_key = ''

        try:
            if not bene_name: return Response({'status': 'fail', 'message': 'beneficiary name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not account_number: return Response({'status': 'fail', 'message': 'account number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not bank_id: return Response({'status': 'fail', 'message': 'bank id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not bene_id: return Response({'status': 'fail', 'message': 'bene id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not beneficiary_name: return Response({'status': 'fail', 'message': 'beneficiary name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not ifsc_code: return Response({'status': 'fail', 'message': 'ifsc code is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if isstring(bene_name) == False: return Response({'status': 'fail', 'message': 'beneficiary name must be a valid string.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(account_number) == False: return Response({'status': 'fail', 'message': 'account number must be a valid number.'}, status=status.HTTP_400_BAD_REQUEST)
            if validate_account_number(account_number) == False: return Response({'status': 'fail', 'message': 'account number must be a valid account number.'}, status=status.HTTP_400_BAD_REQUEST)
            if validate_mobile_number(contact_number) == False: return Response({'status': 'fail', 'message': 'contact number must be a valid mobile number.'}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(bank_id) == False: return Response({'status': 'fail', 'message': "bank Id must be a valid number"}, status=status.HTTP_400_BAD_REQUEST)
            if isnumber(bene_id) == False: return Response({'status': 'fail', 'message': 'bene Id must be a valid number'}, status=status.HTTP_400_BAD_REQUEST)


            get_bank_name = GlobalBankList.objects.get(bank_id=bank_id)
            bank_name = get_bank_name.bank_name

            beneficiary_prefix = "DMT_"
            beneficiary_code= get_random_string(length=8, allowed_chars='qwertyuiopasdfghjklzxcvbnm0123456789')

            url = "https://api.paysprint.in/api/v1/service/dmt/kyc/beneficiary/registerbeneficiary/benenameverify"
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            else:
                sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
                secret_key = sp.credentials_json.get('secret_key')
                partnerId = sp.credentials_json.get('partnerId')
            headers = {
                'Token': get_token(),
                # "Token": get_token(secret_key, partnerId),
                'accept': 'application/json',
                'content-type': 'application/json', 
                # 'authorisedkey': AuthorisedKey
            }
            
            payload = {
                "mobile": contact_number,
                "accno": account_number,
                "bankid": bank_id,
                "benename": bene_name,
                "referenceid": f"{beneficiary_prefix}{beneficiary_code}",
                "pincode": pincode,
                "address": address,
                "dob": dob,
                "gst_state": gst_state,
                "bene_id": bene_id
            }
            
            try:
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    response_data = response.json()
                    print('response_data', response_data)
                    if response_data.get('response_code') == 1:
                        existing_bank = PaysPrintDmtBankAccount.objects.filter(bnk_acc_no=account_number, pspdmt_bene_id=bene_id, bnk_ifsc=ifsc_code).first()
                        if existing_bank:
                            existing_bank.is_verified_2 = True
                            existing_bank.pspdmt_beneficiary_name = response_data.get('benename')
                            existing_bank.save()
                            return Response({
                                "status": "success",
                                "message": "DMT bank benificiary verify successfully.",
                                "results": {'response_data': response_data, 'pspdmt_beneficiary_name': existing_bank.pspdmt_beneficiary_name}
                            }, status=status.HTTP_200_OK)
                        else:
                            paysprint_dmt_queryset = PaysPrintDmtBankAccount.objects.create(
                                pspdmt_beneficiary_id=f'{beneficiary_prefix}{beneficiary_code}',
                                pspdmt_beneficiary_name=response_data.get('benename'),
                                pspdmt_bank_name=bank_name,
                                bnk_acc_no=account_number,
                                bnk_ifsc=ifsc_code,
                                gst_state_code=gst_state,
                                dob=dob,
                                address=address,
                                pincode=pincode,
                                is_added=True,
                                is_verified_2=True,
                                customer_contact=[]
                            )
                            paysprint_dmt_queryset.pspdmt_bene_id = response_data.get('data').get('bene_id') if response_data.get('data') else None
                            paysprint_dmt_queryset.save()

                            response_details = {
                                "status": "success",
                                "message": "DMT bank benificiary verify successfully.",
                                "results": {'response_data': response_data, 'pspdmt_beneficiary_name': existing_bank.pspdmt_beneficiary_name}
                            }
                    elif response_data.get('response_code') == 2:
                        response_details = {
                            "status": "success",
                            "message": "Account verification is not allowed in this pipe.",
                            "response": response_data
                        }
                    else:
                        response_details = {
                            "status": "success",
                            "message": "Remitter accounts not found.",
                            "response": response_data
                        }

                    return Response(response_details, status=status.HTTP_200_OK if response.status_code == 200 else response.status_code)
                elif response.status_code == 500:
                    return Response({'status': 'error','message': "PaySprint api service down.", 'data': response.text}, status=response.status_code)
                else:
                    response_data = response.json()
                    response_details = {
                        "status": "fail",
                        "message": response_data.get("message"),
                        "response": response_data
                    }
                    return Response(response_data, status=response.status_code)

            except requests.RequestException as e:
                return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except GlobalBankList.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Bank Does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)   

    def fatch_customer_paysprint_dmt_bank_account(self, request):
        print('fatch_customer_paysprint_dmt_bank_account')
        try:
            page_number = int(request.data.get('page_number', 1))
            page_size = int(request.data.get('page_size', 10))
            mobile_number = request.data.get('contact_number', None)
            account_number = request.data.get('account_number', None)
            search = request.data.get('search', "").lower()

            if page_size <= 0:
                return Response({'status': 'fail', 'message': 'page_size must be a positive integer.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if page_number <= 0:
                return Response({'status': 'fail', 'message': 'page_number must be a positive integer.'},
                                status=status.HTTP_400_BAD_REQUEST)

            queryset = PaysPrintDmtBankAccount.objects.filter(is_deleted=False)

            if account_number:
                queryset = queryset.filter(bnk_acc_no=account_number)
                if not queryset.exists():
                    return Response({'status': 'fail', 'message': 'No records found for the given account number.'},
                                    status=status.HTTP_404_NOT_FOUND)

            customer_data = []
            if account_number:
                for contact in queryset.first().customer_contact:
                    customer = PaysPrintDmtCustomer.objects.filter(customer_contact_no=contact).first()
                    if customer:
                        customer_data.append(customer)
                if customer_data:
                    customer_serializer = PaysPrintDmtCustomerSerializer(customer_data, many=True)
                    customer_serializer_data = customer_serializer.data
                    if search:
                        filtered_customers = [
                            customer for customer in customer_serializer_data
                            if (customer.get('customer_contact_no') and search in customer['customer_contact_no'].lower()) or
                            (customer.get('customer_first_name') and search in customer['customer_first_name'].lower()) or
                            (customer.get('customer_last_name') and search in customer['customer_last_name'].lower())
                        ]
                    else:
                        filtered_customers = customer_serializer_data
                else:
                    filtered_customers = []
 
            if mobile_number:
                queryset = queryset.filter(customer_contact__contains=[mobile_number])

            if search and not account_number:
                queryset = queryset.filter(pspdmt_bank_name__icontains=search)

            if not account_number:
                paginator = Paginator(queryset, page_size)
                try:
                    page_obj = paginator.page(page_number)
                except EmptyPage:
                    return Response({'status': 'fail', 'message': 'Page not found.'}, status=status.HTTP_404_NOT_FOUND)
                bank_account_serializer = PaysPrintDmtBankSerializer(page_obj, many=True)
            else:
                bank_account_serializer = PaysPrintDmtBankSerializer(queryset, many=True)

            customer_details = {}
            if mobile_number and not account_number:
                try:
                    pspdmt_customer = PaysPrintDmtCustomer.objects.get(customer_contact_no=mobile_number)
                    customer_details = PaysPrintDmtCustomerSerializer(pspdmt_customer).data
                except PaysPrintDmtCustomer.DoesNotExist:
                    customer_details = {}

            data = {
                "customer_details": filtered_customers if account_number else customer_details,
                "results": bank_account_serializer.data,
                "digitap_pennydrop": True,
                "paysprint_pennydrop": False,
                "digitap_label": "verify 1",
                "paysprint_label": "verify 2"
            }
            return Response({
            'status': 'success',
            'total_pages': paginator.num_pages if not account_number else 1,
            'current_page': page_number if not account_number else 1,
            'data': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_beneficiary_data(self, request):
        print('fetch_beneficiary_data')
        contact_no = request.data.get('contact_number')
        fetch_beneficiary = request.data.get('fetch_beneficiary')
        page_number = int(request.data.get('page_number', 1))
        page_size = int(request.data.get('page_size', 10))
        # sp_id = request.data.get('sp_id')
        partnerId = ''
        secret_key = ''
        try:
            if not contact_no:
                return Response({'status': 'fail', 'message': 'Contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not validate_mobile_number(contact_no):
                return Response({'status': 'fail', 'message': 'Invalid contact number format.'}, status=status.HTTP_400_BAD_REQUEST)

            customer_contact_details = PaysPrintDmtCustomer.objects.filter(customer_contact_no=contact_no).first()
            if not customer_contact_details:
                return Response({'status': 'fail', 'message': 'Customer details not found.'}, status=status.HTTP_404_NOT_FOUND)

            if fetch_beneficiary:
                url = "https://api.paysprint.in/api/v1/service/dmt/kyc/beneficiary/registerbeneficiary/fetchbeneficiary"
                # sp = AdServiceProvider.objects.get(sp_id=sp_id)
                # if sp.is_self_config == True:
                #     secret_key = sp.credentials_json.get('secret_key')
                #     partnerId = sp.credentials_json.get('partnerId')
                # else:
                #     sp = ServiceProvider.objects.get(sp_id=sp.sp_id)
                #     secret_key = sp.credentials_json.get('secret_key')
                #     partnerId = sp.credentials_json.get('partnerId')
                headers = {
                    'Token': get_token(),
                    # "Token": get_token(secret_key, partnerId),
                    'accept': 'application/json',
                    'content-type': 'application/json',
                }

                payload = {"mobile": contact_no}
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    json_response = response.json()
                    beneficiaries = json_response.get('data', [])
                    queryset = []
                    if beneficiaries:
                        for json_data in beneficiaries:
                            existing_bank_details = PaysPrintDmtBankAccount.objects.filter(bnk_acc_no=json_data.get('accno'), bnk_ifsc=json_data.get('ifsc'), is_deleted=False).first()
                            # existing_bank_details = PaysPrintDmtBankAccount.objects.filter(
                            #     customer_contact__contains=[{contact_no: str(json_data.get('bene_id'))}], is_deleted=False
                            # ).first()
                            print('existing_bank_details', existing_bank_details)

                            if not existing_bank_details:
                                existing_bank_details = PaysPrintDmtBankAccount.objects.create(
                                    pspdmt_bene_id=json_data.get('bene_id'),
                                    pspdmt_beneficiary_id=str(json_data.get('bene_id')),
                                    pspdmt_beneficiary_name=json_data.get('name'),
                                    pspdmt_bank_name=json_data.get('bankname'),
                                    bnk_acc_no=json_data.get('accno'),
                                    bnk_ifsc=json_data.get('ifsc'),
                                    customer_contact=[{contact_no: str(json_data.get('bene_id'))}],
                                )
                            else:
                                # Ensure contact_no is in customer_contact
                                customer_contacts = existing_bank_details.customer_contact  # List of dicts
                                if not any(contact_no in contact for contact in customer_contacts):
                                    customer_contacts.append({contact_no: str(json_data.get('bene_id'))})
                                    existing_bank_details.customer_contact = customer_contacts
                                    existing_bank_details.save()

                            queryset.append(existing_bank_details)
                        
                    paginator = Paginator(queryset, page_size)
                    try:
                        page_obj = paginator.page(page_number)
                    except EmptyPage:
                        return Response({'status': 'fail', 'message': 'Page not found.'}, status=status.HTTP_404_NOT_FOUND)
                    bank_account_serializer = PaysPrintDmtBankSerializer(page_obj, many=True)
                    for data in bank_account_serializer.data:
                        for bene in data.get("customer_contact", []): 
                             for contact_number, bene_id in bene.items():
                                if contact_no == contact_number:
                                    data["pspdmt_bene_id"] = bene_id
                                    data["customer_contact"] = [contact_number]

                    customer_details = {}
                    if contact_no:
                        try:
                            pspdmt_customer = PaysPrintDmtCustomer.objects.get(customer_contact_no=contact_no)
                            customer_details = PaysPrintDmtCustomerSerializer(pspdmt_customer).data
                        except PaysPrintDmtCustomer.DoesNotExist:
                            customer_details = {}

                    data_dict = {
                        
                    }

                    data = {
                        'total_pages': paginator.num_pages,
                        'current_page': page_number,
                        'total_items': paginator.count,
                        "customer_details": customer_details,
                        "results": bank_account_serializer.data,
                        "digitap_pennydrop": True,
                        "paysprint_pennydrop": False,
                        "digitap_label": "verify 1",
                        "paysprint_label": "verify 2"
                    }

                    return Response({'status': 'success', 'message': 'Beneficiary details fetched successfully.', 'data': data}, status=status.HTTP_200_OK)

                elif response.status_code == 500:
                    return Response({'status': 'error', 'message': "PaySprint API service is down.", 'data': response.text}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                else:
                    response_data = response.json()
                    return Response({'status': 'fail', 'message': response_data.get("message", "Unknown error"), 'response': response_data}, status=response.status_code)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        try:
            if 'contact_number' in request.data and 'bene_id' in request.data and 'code' in request.data:
                return self.bene_delete(request)
            elif 'contact_number' in request.data and 'bene_id' in request.data:
                return self.verify_contact_otp(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def verify_contact_otp(self, request):
        contact_number = request.data.get('contact_number')
        bene_id = request.data.get('bene_id')

        try:
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is requried.'}, status=status.HTTP_400_BAD_REQUEST)
            if not bene_id: return Response({'status': 'fail', 'message': 'bene id is requried.'}, status=status.HTTP_400_BAD_REQUEST)

            existing_bank_details = PaysPrintDmtBankAccount.objects.filter(
                customer_contact__contains=[{contact_number: bene_id}], is_deleted=False
            ).first()
            print('existing_bank_details', existing_bank_details)

            code = get_random_string(length=6, allowed_chars='0123456789')

            existing_bank_details.verify_code = code
            existing_bank_details.verify_code_expire_at = timezone.now() + timedelta(minutes=10)
            existing_bank_details.save()

            response = mobicomm_submit_sms(contact_number, code)
            # Check the SMS API response status
            if response.status_code == 200:
                response_data = {
                    'status': 'success',
                    'message': 'OTP has been sent via SMS.',
                    'data': {'code': code}
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
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    def bene_delete(self, request):
        contact_number = request.data.get('contact_number')
        bene_id = request.data.get('bene_id')
        code = request.data.get('code')

        try:
            # Validate input
            if not contact_number:
                return Response({'status': 'fail', 'message': 'Contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not bene_id:
                return Response({'status': 'fail', 'message': 'Beneficiary ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch existing bank details
            existing_bank_details = PaysPrintDmtBankAccount.objects.filter(
                customer_contact__contains=[{contact_number: bene_id}],
                is_deleted=False
            ).first()

            if not existing_bank_details:
                return Response({'status': 'fail', 'message': 'Bank details not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Validate verification code
            if existing_bank_details.verify_code != code or existing_bank_details.verify_code_expire_at <= timezone.now():
                return Response({'status': 'fail', 'message': 'Invalid or expired verification code.'}, status=status.HTTP_400_BAD_REQUEST)

            # API call to delete beneficiary
            url = "https://api.paysprint.in/api/v1/service/dmt/kyc/beneficiary/registerbeneficiary/deletebeneficiary"
            headers = {
                'Token': get_token(),
                'accept': 'application/json',
                'content-type': 'application/json',
            }
            payload = {
                "mobile": contact_number,
                "bene_id": bene_id
            }
            print('payload', payload)
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()
            print('response_data', response_data)
            if response.status_code == 200:
                if response_data.get('response_code') == 1:
                    # Handle customer contact deletion from list of dicts
                    customer_contacts = existing_bank_details.customer_contact  # List of dicts

                    if isinstance(customer_contacts, list):
                        # Remove the dictionary that contains contact_number and bene_id
                        updated_contacts = [contact for contact in customer_contacts if contact.get(contact_number) != bene_id]
                        print('updated_contact', updated_contacts)
                        if not updated_contacts:  # If the list is empty after removal, delete the entire record
                            existing_bank_details.delete()
                            message = "Bank details deleted as only one contact was associated."
                        else:
                            existing_bank_details.customer_contact = updated_contacts  # Save the updated list
                            existing_bank_details.save()
                            message = f"Contact number {contact_number} removed from beneficiary record."
                    else:
                        message = "Invalid customer contact format."


                    return Response({"status": "success", "message": message, "response": response_data}, status=status.HTTP_200_OK)

                elif response_data.get('response_code') == 11:
                    return Response({"status": "fail", "message": "Authentication failed.", "response": response_data}, status=status.HTTP_401_UNAUTHORIZED)

                else:
                    return Response({"status": "fail", "message": "Remitter accounts not found.", "response": response_data}, status=status.HTTP_404_NOT_FOUND)

            elif response.status_code == 500:
                return Response({'status': 'error', 'message': "PaySprint API service down.", 'data': response.text}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            else:
                response_data = response.json()
                return Response({"status": "fail", "message": response_data.get("message", "Unknown error"), "response": response_data}, status=response.status_code)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaysPrintGlobalBankListAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsDistributor | IsRetailer]

    def post(self, request):
        try:
            page_number = int(request.data.get('page_number', 1))
            page_size = int(request.data.get('page_size', 10))
            search = request.data.get('search')

            queryset = GlobalBankList.objects.all().order_by('-pk')
            if search:
                queryset = queryset.filter(bank_name__icontains=search)

            if not queryset.exists():
                return Response({
                    'status': 'fail',
                    'message': 'No records found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            paginator = Paginator(queryset, page_size)
            total_items = paginator.count
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)

            dmt_bank_list_serializer = PaysPrintGlobalBankListSerializer(page_obj, many=True)
            
            data = {
                "results": dmt_bank_list_serializer.data,
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': total_items
            }

            return Response({
                'status': 'success',
                'data': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)