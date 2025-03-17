from .views import *
from .utilies import *
from validation.custom_validation import *
from .commission_calculations import *
from rest_framework.exceptions import ValidationError
from .charges_calculation import *


class CfPayOutAPIView(APIView):
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
            elif 'account_number' in request.data:
                return self.get_payout_with_account(request)
            elif 'beneficiary_id' in request.data and 'py_trn_amount' in request.data and 'transaction_mode' in request.data:
                return self.create_payout_transaction(request)
            elif 'page_number' in request.data or 'page_size' in request.data:
                return self.fetch_payout_transaction(request)
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
                return Response({'status': 'success', 'message': 'Customer with this contact number already exists'}, status=status.HTTP_200_OK)

        except PyOtCustomer.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Payout customer dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def check_mobile_number(self, request):
        try:
            contact_number = request.data.get('contact_number')
            search = request.data.get('search', '').lower()  

            if not contact_number:
                return Response({'status': 'fail', 'message': 'Contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate the contact number format
            if not validate_mobile_number(contact_number):
                return Response({'status': 'fail', 'message': 'Invalid contact number format.'}, status=status.HTTP_400_BAD_REQUEST)
            
            exists_mobile_number = PyOtCustomer.objects.get(customer_contact_no=contact_number)

            if exists_mobile_number.is_verify:
                banks_list = []

                payout_banks = PyOtBankAccount.objects.all()
                for bank in payout_banks:
                    if contact_number in bank.customer_contact:
                        banks_list.append(bank)


                if search:
                    banks_list = PyOtBankSerializer(banks_list, many=True).data
                    filtered_customers = [
                        bank for bank in banks_list
                        if (bank.get('pyot_bank_name') and search in str(bank['pyot_bank_name']).lower()) or
                        (bank.get('bnk_acc_no') and search in str(bank['bnk_acc_no']).lower()) or
                        (bank.get('bnk_ifsc') and search in str(bank['bnk_ifsc']).lower())
                    ]
                    banks_list = filtered_customers

                banks_list = PyOtBankSerializer(banks_list, many=True).data

                data = {
                    'results': banks_list,
                    'customer_contact_no': exists_mobile_number.customer_contact_no,
                    'customer_first_name': exists_mobile_number.customer_first_name,
                    'customer_last_name': exists_mobile_number.customer_last_name,
                    'customer_address': exists_mobile_number.customer_address,
                    'customer_zip_code': exists_mobile_number.customer_zip_code,
                    'pyot_unique_id': exists_mobile_number.pyot_unique_id,
                    "digitap_pennydrop": True,
                    "digitap_label": "verify 1"
                }

                return Response({'status': 'success', 'message': 'Get Banks Account Details.', 'data': data}, status=status.HTTP_200_OK)
            
            else:
                # Generate OTP and send verification SMS
                code = get_random_string(length=6, allowed_chars='0123456789')
                exists_mobile_number.verify_code = code
                exists_mobile_number.verify_code_expire_at = timezone.now() + timedelta(minutes=15)
                exists_mobile_number.save()

                response = mobicomm_submit_sms(contact_number, code)

                # Check the SMS API response status
                if response.status_code == 200:
                    return Response(
                        {'status': 'success', 'message': 'A verification code has been sent to the mobile number.', 'verify_code': code, 'expiry_time': '15 minutes'},
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {'status': 'error', 'message': 'Failed to send the OTP via SMS.', 'details': response.text},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

        except PyOtCustomer.DoesNotExist:
            # Create a new customer and send verification SMS
            code = get_random_string(length=6, allowed_chars='0123456789')
            PyOtCustomer.objects.create(
                customer_contact_no=contact_number,
                verify_code=code,
                verify_code_expire_at=timezone.now() + timedelta(minutes=15),
            )
            response = mobicomm_submit_sms(contact_number, code)
            return Response(
                {'status': 'success', 'message': 'A verification code has been sent to the mobile number.', 'verify_code': code, 'expiry_time': '15 minutes'},
                status=status.HTTP_200_OK
            )

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
            search = request.data.get('search', '').lower()
            if not account_number:
                return Response({'status': 'fail', 'message': 'Account number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(account_number):
                return Response({'status': 'fail', 'message': 'Account number must be a number.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                get_payout_account = PyOtBankAccount.objects.get(bnk_acc_no=account_number)
            except PyOtBankAccount.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Account number does not exist.'}, status=status.HTTP_404_NOT_FOUND)

            customer_data = []
            for contact in get_payout_account.customer_contact:
                customer = PyOtCustomer.objects.filter(customer_contact_no=contact).first()
                if customer:
                    customer_data.append(customer)

            if customer_data:
                customer_serializer = PyOtCustomerSerializer(customer_data, many=True)
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

            bank_serializer = PyOtBankSerializer(get_payout_account)

            data = {
                'status': 'success',
                'message': 'Retrieved all contact numbers successfully.',
                'results': {
                    'bank_details': bank_serializer.data,
                    'customer_details': filtered_customers,
                    "digitap_pennydrop": True,
                    "digitap_label": "verify 1"
                }
            }
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_payout_transaction(self, request):
        customer_contact_no = request.data.get('customer_contact_no')
        beneficiary_id = request.data.get('beneficiary_id')
        sp_id = request.data.get('sp_id')
        py_trn_amount = request.data.get('py_trn_amount')
        transaction_mode = request.data.get('transaction_mode')
        Client_id ,Client_secret, beneficiary_email, beneficiary_phone = "", "", "", ""
        # add_beneficiary_url = "https://sandbox.cashfree.com/payout/beneficiary"
        # payout_transfer_url = "https://sandbox.cashfree.com/payout/transfers"
        add_beneficiary_url = "https://api.cashfree.com/payout/beneficiary"
        payout_transfer_url = "https://api.cashfree.com/payout/transfers"

        sp = AdServiceProvider.objects.get(sp_id=sp_id)
        print('sp.is_self_config', sp.is_self_config)
        if sp.is_self_config == True:
            Client_id = sp.credentials_json.get('Client_id')
            Client_secret = sp.credentials_json.get('Client_secret')
            beneficiary_phone = sp.credentials_json.get('beneficiary_phone')
            beneficiary_email = sp.credentials_json.get('beneficiary_email')
        else:
            service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
            print('service_provider.credentials_json', service_provider.credentials_json)
            Client_id = service_provider.credentials_json.get('Client_id')    
            Client_secret = service_provider.credentials_json.get('Client_secret')    
            beneficiary_phone = service_provider.credentials_json.get('beneficiary_phone')    
            beneficiary_email = service_provider.credentials_json.get('beneficiary_email') 

        print('client_id ,client_secret, beneficiary_email, beneficiary_phone', Client_id ,Client_secret, beneficiary_email, beneficiary_phone)   

        headers = {
            "accept": "application/json",
            "x-api-version": "2024-01-01",
            "content-type": "application/json",
            # "x-client-id": "CF449777CRQG8U0O577S73AHL800",
            # "x-client-secret": "cfsk_ma_prod_cc00245b0b0baa6a900984e8ecaab99f_9f28681b",
            "x-client-id": Client_id,
            "x-client-secret": Client_secret,
            # "x-client-id": "CF379597CR4QJ3VPU07S7391HLIG",
            # "x-client-secret": "cfsk_ma_test_579d140d50ce6d479c922805f91c1f9a_747f96ec"
        }

        admin_wallet = check_admin_wallet(request, py_trn_amount)
        retailer_wallet = check_retailer_wallet(request, py_trn_amount, request.user.id)
        try:
            with transaction.atomic():
                pyot_bnk_obj = PyOtBankAccount.objects.get(pyot_beneficiary_id=beneficiary_id)
                
                pyot_cus_obj = PyOtCustomer.objects.get(customer_contact_no=customer_contact_no)
                try:
                    puw_obj = PortalUserWallet.objects.get(pu_id=request.user.id)
                except PortalUserWallet.DoesNotExist:
                    return Response({'status': 'fail', 'message': 'User Wallet Does Not Exist'}, status=status.HTTP_404_NOT_FOUND)

                main_wallet = float(puw_obj.main_wallet)

                if float(py_trn_amount) >= float(main_wallet):
                    return Response({'status': 'fail', 'message': 'User have insufficient balance.'}, status=status.HTTP_404_NOT_FOUND)
                
                if not pyot_bnk_obj.is_added:
                    add_beneficiary_payload = {
                        "beneficiary_instrument_details": {
                            "bank_account_number": str(pyot_bnk_obj.bnk_acc_no),
                            "bank_ifsc": str(pyot_bnk_obj.bnk_ifsc)
                        },
                        "beneficiary_id": str(pyot_bnk_obj.pyot_beneficiary_id),
                        "beneficiary_name": str(pyot_bnk_obj.pyot_beneficiary_name),
                        "beneficiary_contact_details": {
                            # "beneficiary_email": "mr9537858000@gmail.com",
                            # "beneficiary_phone": "9537858000"
                            "beneficiary_email": beneficiary_email,
                            "beneficiary_phone": beneficiary_phone
                        }
                    }
                    
                    beneficiary_response = requests.post(
                        add_beneficiary_url, json=add_beneficiary_payload, headers=headers)
                    
                    bene_response = beneficiary_response.json()
                    if beneficiary_response.status_code == 201:
                        transfer_payload = {
                            "beneficiary_details": {"beneficiary_id": beneficiary_id},
                            "transfer_id": get_random_string(length=12),
                            "transfer_amount": py_trn_amount,
                            "transfer_currency": "INR",
                            "transfer_mode": transaction_mode,
                            "fundsource_id": "CASHFREE_55010"
                            # "fundsource_id": "YES_CONNECTED_55010_091bf6b"
                        }
                        
                        payout_response = requests.post(payout_transfer_url, json=transfer_payload, headers=headers)
                        py_response = payout_response.json()
                        if payout_response.status_code == 200:
                            # Create PyOtServiceTrn entry
                            sp = AdServiceProvider.objects.get(sp_id=sp_id)
                            gst_rate = sp.hsn_sac.tax_rate
                            service_trn = PyOtServiceTrn.objects.create(
                                sp_id=sp_id,
                                trn_unique_id=f"CashFreePayout_TXN_{uuid.uuid4().hex[:8]}_{time.time() * 1000}",
                                trn_amount=py_trn_amount,
                                trn_response=py_response,  
                                customer_name=f"{pyot_cus_obj.customer_first_name} {pyot_cus_obj.customer_last_name}",
                                customer_contact_no=customer_contact_no,
                                trn_status='COMPLETED' if py_response.get('status') == 'RECEIVED' else py_response.get('status'),
                                created_by=request.user.id
                            )
                            admin_charges = None
                            # fetch admin charges
                            admin_charge_queryset = AdCharges.objects.filter(service_provider_id=sp_id)
                            if admin_charge_queryset.exists():  # Ensure queryset is not empty
                                for charge in admin_charge_queryset:
                                    if charge.minimum <= float(py_trn_amount) <= charge.maximum:
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

                            char_comm_amt = float(service_trn.trn_amount) * (float(admin_rate) / 100) if admin_rate_type == 'is_percent' else float(admin_rate)
                            admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))

                            portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)

                            data = {
                                "service_id": service_trn.pk,
                                "amount": service_trn.trn_amount,
                                "table_name": "ad_payout_service_trnasaction",
                                "wl_label": f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{service_trn.trn_amount}_with_tx_id_{service_trn.service_trn_id}",
                                "gst_rate": gst_rate,
                                "admin_tax_amt": admin_tax_amt,
                                "char_comm_amt": char_comm_amt,
                                "admin_charges_type": admin_charges_type,
                                "sp_id": sp_id,
                                "contact_number": customer_contact_no,
                                "name": f"{pyot_cus_obj.customer_first_name} {pyot_cus_obj.customer_last_name}",
                                "response_data": py_response,
                                "label": sp.label,
                                "category": None,
                                "is_self_config": sp.is_self_config
                            }
                            print('data', data)
                            charges_calculation_function(request, data)

                            # for retailer
                            # rt_gl = GlTrn.objects.create(
                            #     service_trn_id=service_trn.pk,
                            #     pu_id=request.user.id,
                            #     gl_trn_amt=service_trn.trn_amount,
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=service_trn.trn_amount,
                            #     service_trn_table='ad_payout_service_trnasaction',
                            #     effective_type='DR',
                            #     gl_trn_dt=now(),
                            # )

                            # WalletTrn.objects.create(
                            #     action_id=rt_gl.pk,
                            #     action_type='Order',
                            #     pu_id=request.user.id,
                            #     wl_label=f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{service_trn.trn_amount}_with_tx_id_{service_trn.service_trn_id}",
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=service_trn.trn_amount,
                            #     effective_type='DR',
                            #     wl_trn_dt=now()
                            # )

                            # rtl_wallet = PortalUserWallet.objects.get(pu_id=request.user.id)
                            # rtl_wallet.main_wallet = float(rtl_wallet.main_wallet) - float(service_trn.trn_amount)
                            # rtl_wallet.updated_at = now()
                            # rtl_wallet.save()

                            # # for admin
                            # if sp.is_self_config==True:
                            #     service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
                            #     plateform_fee = service_provider.plateform_fee
                            #     plateform_fee_type = service_provider.plateform_fee_type
                            #     tax_rate = service_provider.hsn_sac.tax_rate
                            #     rate_amount = py_trn_amount * (plateform_fee / 100) if plateform_fee_type == 'is_percent' else plateform_fee                      
                            #     gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(tax_rate)/100)))

                            #     admin_amount = rate_amount
                            # else:
                            #     admin_amount=py_trn_amount

                            # admin_gl = GlTrn.objects.create(
                            #     service_trn_id=service_trn.pk,
                            #     pu_id=1,
                            #     gl_tax_rate=tax_rate if tax_rate else None,
                            #     gl_tax_amt=gst_amount if tax_rate else None,
                            #     gl_trn_amt=admin_amount,
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=admin_amount,
                            #     service_trn_table='ad_payout_service_trnasaction',
                            #     effective_type='DR',
                            #     gl_trn_dt=now(),
                            # )

                            # WalletTrn.objects.create(
                            #     action_id=admin_gl.pk,
                            #     action_type='Order',
                            #     pu_id=1,
                            #     wl_label=f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{admin_amount}_with_tx_id_{service_trn.service_trn_id}",
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=admin_amount,
                            #     effective_type='DR',
                            #     wl_trn_dt=now()
                            # )
                            
                            # admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                            # admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(admin_amount)
                            # admin_wallet.updated_at = now()
                            # admin_wallet.save()
                            # if sp.is_self_config == False:
                            #     admin_gl = GlTrn.objects.create(
                            #         service_trn_id=service_trn.pk,
                            #         pu_id=1,
                            #         gl_tax_rate=gst_rate,
                            #         gl_tax_amt=admin_tax_amt,
                            #         gl_trn_amt=service_trn.trn_amount,
                            #         effectvie_wallet='main_wallet',
                            #         effectvie_amt=char_comm_amt,
                            #         service_trn_table='ad_payout_service_trnasaction',
                            #         effective_type=admin_charges_type,
                            #         gl_trn_dt=now(),
                            #     )

                            #     WalletTrn.objects.create(
                            #         action_id=service_trn.pk,
                            #         action_type='Order',
                            #         pu_id=1,
                            #         wl_label=f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{service_trn.trn_amount}_with_tx_id_{service_trn.service_trn_id}",
                            #         effectvie_wallet='main_wallet',
                            #         effectvie_amt=char_comm_amt,
                            #         effective_type=admin_charges_type,
                            #         wl_trn_dt=now()
                            #     )

                            #     admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                            #     if admin_charges_type == 'CR':
                            #         admin_wallet.main_wallet = float(admin_wallet.main_wallet) + float(char_comm_amt)
                            #     else:
                            #         admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(char_comm_amt)
                            #     admin_wallet.updated_at = now()
                            #     admin_wallet.save()

                            # data = {
                            #     'order_amount': py_trn_amount,
                            #     'id': request.user.id,
                            #     'sp_id': sp_id,
                            #     'customer_contact_no': customer_contact_no,
                            #     'customer_name': f"{pyot_cus_obj.customer_first_name} {pyot_cus_obj.customer_last_name}",
                            #     'trn_response': py_response,
                            #     'service_trn': service_trn.pk,
                            #     'label': sp.label,
                            #     'category': None,
                            #     'table_name': 'ad_payout_service_trnasaction'
                            # }

                            # after_tx_cal(request, data)

                            return Response({'status': 'success', 'message': "Payout Transfer done successfully"}, status=payout_response.status_code)
                        else:
                            return Response({'status': 'fail', 'message': py_response["message"]}, status=payout_response.status_code)
                    else:
                        transfer_payload = {
                            "beneficiary_details": {"beneficiary_id": beneficiary_id},
                            "transfer_id": get_random_string(length=12),
                            "transfer_amount": py_trn_amount,
                            "transfer_currency": "INR",
                            "transfer_mode": transaction_mode,
                            "fundsource_id": "CASHFREE_55010"
                            # "fundsource_id": "YES_CONNECTED_55010_091bf6b"
                        }
                        payout_response = requests.post(payout_transfer_url, json=transfer_payload, headers=headers)
                        py_response = payout_response.json()
                        if payout_response.status_code == 200:
                            sp = AdServiceProvider.objects.get(sp_id=sp_id)
                            gst_rate = sp.hsn_sac.tax_rate
                            service_trn = PyOtServiceTrn.objects.create(
                                sp_id=sp_id,
                                trn_unique_id=f"CashFreePayout_TXN_{uuid.uuid4().hex[:8]}_{time.time() * 1000}",
                                trn_amount=py_trn_amount,
                                trn_response=py_response,  
                                customer_name=f"{pyot_cus_obj.customer_first_name} {pyot_cus_obj.customer_last_name}",
                                customer_contact_no=customer_contact_no,
                                trn_status='COMPLETED' if py_response.get('status') == 'RECEIVED' else py_response.get('status'),
                                created_by=request.user.id
                            )
                            admin_charges = None
                            # fetch admin charges
                            admin_charge_queryset = AdCharges.objects.filter(service_provider_id=sp_id)
                            if admin_charge_queryset.exists():  # Ensure queryset is not empty
                                for charge in admin_charge_queryset:
                                    if charge.minimum <= float(py_trn_amount) <= charge.maximum:
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

                            char_comm_amt = float(service_trn.trn_amount) * (float(admin_rate) / 100) if admin_rate_type == 'is_percent' else float(admin_rate)
                            admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))

                            portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)

                            data = {
                                "service_id": service_trn.pk,
                                "amount": service_trn.trn_amount,
                                "table_name": "ad_payout_service_trnasaction",
                                "wl_label": f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{service_trn.trn_amount}_with_tx_id_{service_trn.service_trn_id}",
                                "gst_rate": gst_rate,
                                "admin_tax_amt": admin_tax_amt,
                                "char_comm_amt": char_comm_amt,
                                "admin_charges_type": admin_charges_type,
                                "sp_id": sp_id,
                                "contact_number": customer_contact_no,
                                "name": f"{pyot_cus_obj.customer_first_name} {pyot_cus_obj.customer_last_name}",
                                "response_data": py_response,
                                "label": sp.label,
                                "category": None,
                                "is_self_config": sp.is_self_config
                            }
                            print('data', data)
                            charges_calculation_function(request, data)

                            # for retailer
                            # rt_gl = GlTrn.objects.create(
                            #     service_trn_id=service_trn.pk,
                            #     pu_id=request.user.id,
                            #     gl_trn_amt=service_trn.trn_amount,
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=service_trn.trn_amount,
                            #     service_trn_table='ad_payout_service_trnasaction',
                            #     effective_type='DR',
                            #     gl_trn_dt=now(),
                            # )
                            # WalletTrn.objects.create(
                            #     action_id=rt_gl.pk,
                            #     action_type='Order',
                            #     pu_id=request.user.id,
                            #     wl_label=f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{service_trn.trn_amount}_with_tx_id_{service_trn.service_trn_id}",
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=service_trn.trn_amount,
                            #     effective_type='DR',
                            #     wl_trn_dt=now()
                            # )

                            # rtl_wallet = PortalUserWallet.objects.get(pu_id=request.user.id)
                            # rtl_wallet.main_wallet = float(rtl_wallet.main_wallet) - float(service_trn.trn_amount)
                            # rtl_wallet.updated_at = now()
                            # rtl_wallet.save()

                            # # for admin
                            # if sp.is_self_config==True:
                            #     service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
                            #     plateform_fee = service_provider.plateform_fee
                            #     plateform_fee_type = service_provider.plateform_fee_type
                            #     tax_rate = service_provider.hsn_sac.tax_rate
                            #     rate_amount = py_trn_amount * (plateform_fee / 100) if plateform_fee_type == 'is_percent' else plateform_fee                      
                            #     gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(tax_rate)/100)))

                            #     admin_amount = rate_amount
                            # else:
                            #     admin_amount=py_trn_amount
                            # admin_gl = GlTrn.objects.create(
                            #     service_trn_id=service_trn.pk,
                            #     pu_id=1,
                            #     gl_tax_rate=tax_rate if tax_rate else None,
                            #     gl_tax_amt=gst_amount if tax_rate else None,
                            #     gl_trn_amt=admin_amount,
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=admin_amount,
                            #     service_trn_table='ad_payout_service_trnasaction',
                            #     effective_type='DR',
                            #     gl_trn_dt=now(),
                            # )

                            # WalletTrn.objects.create(
                            #     action_id=admin_gl.pk,
                            #     action_type='Order',
                            #     pu_id=1,
                            #     wl_label=f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{admin_amount}_with_tx_id_{service_trn.service_trn_id}",
                            #     effectvie_wallet='main_wallet',
                            #     effectvie_amt=admin_amount,
                            #     effective_type='DR',
                            #     wl_trn_dt=now()
                            # )
                            
                            # admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                            # admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(admin_amount)
                            # admin_wallet.updated_at = now()
                            # admin_wallet.save()
                            
                            # if sp.is_self_config == False:
                            #     admin_gl = GlTrn.objects.create(
                            #         service_trn_id=service_trn.pk,
                            #         pu_id=1,
                            #         gl_tax_rate=gst_rate,
                            #         gl_tax_amt=admin_tax_amt,
                            #         gl_trn_amt=service_trn.trn_amount,
                            #         effectvie_wallet='main_wallet',
                            #         effectvie_amt=char_comm_amt,
                            #         service_trn_table='ad_payout_service_trnasaction',
                            #         effective_type=admin_charges_type,
                            #         gl_trn_dt=now(),
                            #     )

                            #     WalletTrn.objects.create(
                            #         action_id=service_trn.pk,
                            #         action_type='Order',
                            #         pu_id=1,
                            #         wl_label=f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{service_trn.trn_amount}_with_tx_id_{service_trn.service_trn_id}",
                            #         effectvie_wallet='main_wallet',
                            #         effectvie_amt=char_comm_amt,
                            #         effective_type=admin_charges_type,
                            #         wl_trn_dt=now()
                            #     )

                            #     admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                            #     if admin_charges_type == 'CR':
                            #         admin_wallet.main_wallet = float(admin_wallet.main_wallet) + float(char_comm_amt)
                            #     else:
                            #         admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(char_comm_amt)
                            #     admin_wallet.updated_at = now()
                            #     admin_wallet.save()

                            # data = {
                            #     'order_amount': py_trn_amount,
                            #     'id': request.user.id,
                            #     'sp_id': sp_id,
                            #     'customer_contact_no': customer_contact_no,
                            #     'customer_name': f"{pyot_cus_obj.customer_first_name} {pyot_cus_obj.customer_last_name}",
                            #     'trn_response': py_response,
                            #     'service_trn': service_trn.pk,
                            #     'label': sp.label,
                            #     'category': None,
                            #     'table_name': 'ad_payout_service_trnasaction'
                            # }
                            # after_tx_cal(request, data)
    
                            return Response({'status': "success", 'message': "Payout Transfer done successfully"}, status=payout_response.status_code)
                        else:
                            return Response({'status': 'fail', 'message': py_response["message"]}, status=payout_response.status_code)
                else:
                    transfer_payload = {
                        "beneficiary_details": {"beneficiary_id": beneficiary_id},
                        "transfer_id": get_random_string(length=12),
                        "transfer_amount": py_trn_amount,
                        "transfer_currency": "INR",
                        "transfer_mode": transaction_mode,
                        "fundsource_id": "CASHFREE_55010"
                        # "fundsource_id": "YES_CONNECTED_55010_091bf6b"
                    }
                    payout_response = requests.post(payout_transfer_url, json=transfer_payload, headers=headers)
                    py_response = payout_response.json()
                    if payout_response.status_code == 200:
                        sp = AdServiceProvider.objects.get(sp_id=sp_id)
                        gst_rate = sp.hsn_sac.tax_rate
                        service_trn = PyOtServiceTrn.objects.create(
                            sp_id=sp_id,
                            trn_unique_id=f"CashFreePayout_TXN_{uuid.uuid4().hex[:8]}_{time.time() * 1000}",
                            trn_amount=py_trn_amount,
                            trn_response=py_response,  
                            customer_name=f"{pyot_cus_obj.customer_first_name} {pyot_cus_obj.customer_last_name}",
                            customer_contact_no=customer_contact_no,
                            trn_status='COMPLETED' if py_response.get('status') == 'RECEIVED' else py_response.get('status'),
                            created_by=request.user.id
                        )
                        admin_charges = None
                        # fetch admin charges
                        admin_charge_queryset = AdCharges.objects.filter(service_provider_id=sp_id)
                        if admin_charge_queryset.exists():  # Ensure queryset is not empty
                            for charge in admin_charge_queryset:
                                if charge.minimum <= float(py_trn_amount) <= charge.maximum:
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

                        admin_rate = admin_charges.rate
                        admin_rate_type = admin_charges.rate_type
                        admin_charges_type = admin_charges.charges_type

                        char_comm_amt = float(service_trn.trn_amount) * (float(admin_rate) / 100) if admin_rate_type == 'is_percent' else float(admin_rate)
                        admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))

                        portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)

                        data = {
                            "service_id": service_trn.pk,
                            "amount": service_trn.trn_amount,
                            "table_name": "ad_payout_service_trnasaction",
                            "wl_label": f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{service_trn.trn_amount}_with_tx_id_{service_trn.service_trn_id}",
                            "gst_rate": gst_rate,
                            "admin_tax_amt": admin_tax_amt,
                            "char_comm_amt": char_comm_amt,
                            "admin_charges_type": admin_charges_type,
                            "sp_id": sp_id,
                            "contact_number": customer_contact_no,
                            "name": f"{pyot_cus_obj.customer_first_name} {pyot_cus_obj.customer_last_name}",
                            "response_data": py_response,
                            "label": sp.label,
                            "category": None,
                            "is_self_config": sp.is_self_config
                        }
                        print('data', data)
                        charges_calculation_function(request, data)

                        # for retailer
                        # rt_gl = GlTrn.objects.create(
                        #     service_trn_id=service_trn.pk,
                        #     pu_id=request.user.id,
                        #     gl_trn_amt=service_trn.trn_amount,
                        #     effectvie_wallet='main_wallet',
                        #     effectvie_amt=service_trn.trn_amount,
                        #     service_trn_table='ad_payout_service_trnasaction',
                        #     effective_type='DR',
                        #     gl_trn_dt=now(),
                        # )

                        # WalletTrn.objects.create(
                        #     action_id=rt_gl.pk,
                        #     action_type='Order',
                        #     pu_id=request.user.id,
                        #     wl_label=f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{service_trn.trn_amount}_with_tx_id_{service_trn.service_trn_id}",
                        #     effectvie_wallet='main_wallet',
                        #     effectvie_amt=service_trn.trn_amount,
                        #     effective_type='DR',
                        #     wl_trn_dt=now()
                        # )

                        # rtl_wallet = PortalUserWallet.objects.get(pu_id=request.user.id)
                        # rtl_wallet.main_wallet = float(rtl_wallet.main_wallet) - float(service_trn.trn_amount)
                        # rtl_wallet.updated_at = now()
                        # rtl_wallet.save()

                        # # for admin
                        # if sp.is_self_config==True:
                        #     service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
                        #     plateform_fee = service_provider.plateform_fee
                        #     plateform_fee_type = service_provider.plateform_fee_type
                        #     tax_rate = service_provider.hsn_sac.tax_rate
                        #     rate_amount = py_trn_amount * (plateform_fee / 100) if plateform_fee_type == 'is_percent' else plateform_fee                      
                        #     gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(tax_rate)/100)))

                        #     admin_amount = rate_amount
                        # else:
                        #     admin_amount=py_trn_amount
                        # admin_gl = GlTrn.objects.create(
                        #     service_trn_id=service_trn.pk,
                        #     pu_id=1,
                        #     gl_tax_rate=tax_rate if tax_rate else None,
                        #     gl_tax_amt=gst_amount if tax_rate else None,
                        #     gl_trn_amt=admin_amount,
                        #     effectvie_wallet='main_wallet',
                        #     effectvie_amt=admin_amount,
                        #     service_trn_table='ad_payout_service_trnasaction',
                        #     effective_type='DR',
                        #     gl_trn_dt=now(),
                        # )

                        # WalletTrn.objects.create(
                        #     action_id=admin_gl.pk,
                        #     action_type='Order',
                        #     pu_id=1,
                        #     wl_label=f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{admin_amount}_with_tx_id_{service_trn.service_trn_id}",
                        #     effectvie_wallet='main_wallet',
                        #     effectvie_amt=admin_amount,
                        #     effective_type='DR',
                        #     wl_trn_dt=now()
                        # )
                        
                        # admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                        # admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(admin_amount)
                        # admin_wallet.updated_at = now()
                        # admin_wallet.save()
                        # if sp.is_self_config == False:
                        #     admin_gl = GlTrn.objects.create(
                        #         service_trn_id=service_trn.pk,
                        #         pu_id=1,
                        #         gl_tax_rate=gst_rate,
                        #         gl_tax_amt=admin_tax_amt,
                        #         gl_trn_amt=service_trn.trn_amount,
                        #         effectvie_wallet='main_wallet',
                        #         effectvie_amt=char_comm_amt,
                        #         service_trn_table='ad_payout_service_trnasaction',
                        #         effective_type=admin_charges_type,
                        #         gl_trn_dt=now(),
                        #     )

                        #     WalletTrn.objects.create(
                        #         action_id=service_trn.pk,
                        #         action_type='Order',
                        #         pu_id=1,
                        #         wl_label=f"CashFreePayout_by_{portal_user_details.pud_unique_id}_of_amount_{service_trn.trn_amount}_with_tx_id_{service_trn.service_trn_id}",
                        #         effectvie_wallet='main_wallet',
                        #         effectvie_amt=char_comm_amt,
                        #         effective_type=admin_charges_type,
                        #         wl_trn_dt=now()
                        #     )

                        #     admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                        #     if admin_charges_type == 'CR':
                        #         admin_wallet.main_wallet = float(admin_wallet.main_wallet) + float(char_comm_amt)
                        #     else:
                        #         admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(char_comm_amt)
                        #     admin_wallet.updated_at = now()
                        #     admin_wallet.save()

                        # data = {
                        #     'order_amount': py_trn_amount,
                        #     'id': request.user.id,
                        #     'sp_id': sp_id,
                        #     'customer_contact_no': customer_contact_no,
                        #     'customer_name': f"{pyot_cus_obj.customer_first_name} {pyot_cus_obj.customer_last_name}",
                        #     'trn_response': py_response,
                        #     'service_trn': service_trn.pk,
                        #     'label': sp.label,
                        #     'category': None,
                        #     'table_name': 'ad_payout_service_trnasaction'
                        # }
                        # after_tx_cal(request, data)
                        
                        return Response({'status': 'success', 'message': "Payout Transfer done successfully"}, status=status.HTTP_200_OK)
                    else:
                        return Response({'status': 'fail', 'message': py_response["message"]}, status=payout_response.status_code)
        except PyOtCustomer.DoesNotExist:
            response_data = {
                'status': 'error',
                'message': 'Customer with this contact number does not exist.'
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as e:
            message = str(e)
            print('message', message)
            if "ErrorDetail" in message:
                message = message.split("string='")[1].split("', code=")[0]  
            return Response({'status': 'fail', 'message': message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_payout_transaction(self, request):
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

            queryset = PyOtServiceTrn.objects.filter(created_by=request.user.id).order_by('-pk')

            if search != '':
                queryset = queryset.filter(Q(trn_unique_id__icontains=search) | Q(customer_contact_no__icontains=search))

            if transaction_status != '':
                queryset = queryset.filter(trn_status=transaction_status)

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
                        'message': 'Payout Transaction Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                serializer = PyOtServiceTrnSerializer(page_obj.object_list, many=True).data
                for trn in serializer:
                    sp_obj = AdServiceProvider.objects.get(sp_id=trn['sp'])
                    trn['label'] = sp_obj.label
                    # Convert to datetime if it's a string
                    if isinstance(trn['service_trn_dt'], str):
                        trn['service_trn_dt'] = datetime.strptime(trn['service_trn_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")

                    trn['service_trn_dt'] = trn['service_trn_dt'].strftime("%d-%m-%Y %I:%M %p")
                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer
                }
                return Response({
                    'status': 'success',
                    'message': 'Payout Transaction data',
                    'data': paginated_response_data
                }, status=status.HTTP_200_OK)

            serializer = PyOtServiceTrnSerializer(queryset, many=True, context={'request': request}).data

            for trn in serializer:
                sp_obj = AdServiceProvider.objects.get(sp_id=trn['sp'])
                trn['label'] = sp_obj.label
                # Convert to datetime if it's a string
                if isinstance(trn['service_trn_dt'], str):
                    trn['service_trn_dt'] = datetime.strptime(trn['service_trn_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")

                trn['service_trn_dt'] = trn['service_trn_dt'].strftime("%d-%m-%Y %I:%M %p")

            response_data = {
                'status': 'success',
                'message': 'Payout Transaction data',
                'data': serializer
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'fail',
                'message': str(e),
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)


class CfPayoutBeneficiaryAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request):
        try:
            if 'bank_name' in request.data and 'beneficiary_name' in request.data and 'account_number' in request.data and 'ifsc_code' in request.data and 'contact_number' in request.data:
                return self.add_customer_payout_bank_account(request)
            elif 'bank_name' in request.data and 'beneficiary_name' in request.data and 'account_number' in request.data and 'ifsc_code' in request.data:
                return self.verify_customer_payout_bank_account(request)
            elif 'page_size' in request.data or 'page_number' in request.data or 'account_number' in request.data:
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
            ifsc_code = request.data.get('ifsc_code')
            contact_number = request.data.get('contact_number')

            if not bank_name: return Response({'status': 'fail', 'message': 'bank name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not beneficiary_name: return Response({'status': 'fail', 'message': 'beneficiary name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not account_number: return Response({'status': 'fail', 'message': 'account number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not ifsc_code: return Response({'status': 'fail', 'message': 'IFSC code is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not contact_number: return Response({'status': 'fail', 'message': 'contact number is required.'}, status=status.HTTP_400_BAD_REQUEST)

            existing_account = PyOtBankAccount.objects.filter(pyot_bank_name=bank_name, pyot_beneficiary_name=beneficiary_name, bnk_acc_no=account_number, bnk_ifsc=ifsc_code).first()

            if existing_account:
                if existing_account.customer_contact is None:
                    existing_account.customer_contact = []
                    existing_account.save()
                if contact_number in existing_account.customer_contact:
                    return Response({'status': 'success', 'message': 'This bank account with the provided contact number already exists.'}, status=status.HTTP_200_OK)
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

    def verify_customer_payout_bank_account(self, request):
        bank_name = request.data.get('bank_name')
        beneficiary_name = request.data.get('beneficiary_name')
        account_number = request.data.get('account_number')
        ifsc_code = request.data.get('ifsc_code')

        client_id = 76034597
        client_secret = "jIzkvvBkEFvIYjde8O7lini65ghUk5Yo"
        callback_url = "https://api.digitap.ai/penny-drop/v2/check-valid"

        if not bank_name: return Response({'status': 'fail', 'message': 'bank name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not beneficiary_name: return Response({'status': 'fail', 'message': 'beneficiary name is required.'}, status=status.HTTP_400_BAD_REQUEST)
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
            if verify_bank_response_json.get("model").get("status") == "SUCCESS":
                existing_account_number = PyOtBankAccount.objects.filter(bnk_acc_no=account_number).first()
                if existing_account_number and int(account_number) == existing_account_number.bnk_acc_no:
                    if existing_account_number.is_verified == True:
                        return Response({'status': 'success', 'message': 'This bank account already verified.'}, status=status.HTTP_200_OK)
                    else:
                        existing_account_number.is_verified = True
                        existing_account_number.save()
                        return Response({'status': 'success', 'message': 'Bank verification completed successfully.'}, status=status.HTTP_400_BAD_REQUEST)
                beneficiary_prefix = "CF_"
                beneficiary_code= get_random_string(length=9, allowed_chars='qwertyuiopasdfghjklzxcvbnm0123456789')

                PyOtBankAccount.objects.create(
                    pyot_beneficiary_id=f'{beneficiary_prefix}{beneficiary_code}',
                    pyot_beneficiary_name=beneficiary_name,
                    pyot_bank_name=bank_name,
                    bnk_acc_no=account_number,
                    bnk_ifsc=ifsc_code,
                    is_verified=True
                )
                return Response({"status": "success", "message": "Bank verification completed successfully.", "data": verify_bank_response_json}, status=status.HTTP_200_OK)
            if verify_bank_response_json.get("model").get("status") == "PENDING":
                return Response({"status": "pending", "message": "Bank verification is currently pending. Please check back later.", "data": verify_bank_response_json}, status=status.HTTP_200_OK)
            else:
                return Response({"status": "fail", "message": "Bank verification failed. Please verify the details and try again.", "data": verify_bank_response_json}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fatch_customer_payout_bank_account(self, request):
        try:
            page_number = int(request.data.get('page_number', 1))
            page_size = int(request.data.get('page_size', 10))
            mobile_number = request.data.get('mobile_number', None)
            account_number = request.data.get('account_number', None)

            if not account_number:

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
                    "results": bank_account_serializer.data,
                    "digitap_pennydrop": True,
                    "digitap_label": "verify 1"
                }

                return Response({
                    'status': 'success',
                    'data': data,
                    'total_pages': paginator.num_pages,
                    'current_page': page_number,
                })
            
            else:
                existing_account = PyOtBankAccount.objects.filter(bnk_acc_no=account_number).first()
                if existing_account:
                    bank_account_serializer = PyOtBankSerializer(existing_account)
                    data = {
                        "results": bank_account_serializer.data,
                        "digitap_pennydrop": True,
                        "digitap_label": "verify 1"
                    }

                    return Response({
                        'status': 'success',
                        'message': 'bank account fetched successfully.',
                        'data': data
                    })
                else:
                    return Response({'status': 'fail', 'message': 'Payout bank account not found.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)