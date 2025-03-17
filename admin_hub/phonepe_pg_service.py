from .views import *
from .models import *
from .utilies import *
import json
import base64
import hashlib
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import uuid
import datetime
from datetime import timedelta
from django.shortcuts import redirect
from .charges_calculation import *
from dateutil import parser
from django.utils.timezone import localtime, make_aware


class PhonePeAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request):
        print('requst.data', request.data)
        try:
            if 'amount' in request.data and 'sp_id' in request.data:
                return self.create_transaction(request)
            elif 'merchantTransactionid' in request.data:
                return self.status_transaction(request)
            elif 'is_get_charges' in request.data:
                return self.fetch_charges(request)
            elif 'page_number' in request.data or 'page_size' in request.data:
                return self.get_all_transaction(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid request.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_transaction(self, request):
        amount = request.data.get('amount')
        sp_id = request.data.get('sp_id')
        # merchantId = "TAPIPEONLINE"
        # saltkey = "93880238-12c3-495e-8bdc-688187572c00"
        merchantId = ''
        saltkey = ''
        try:
            service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
            if service_provider.is_self_config == True:
                merchantId = service_provider.credentials_json.get('merchantId')
                saltkey = service_provider.credentials_json.get('saltkey')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=service_provider.sp_id)
                merchantId = service_provider.credentials_json.get('merchantId')
                saltkey = service_provider.credentials_json.get('saltkey')

            contact_number = PortalUser.objects.get(id=request.user.id).pu_contact_no
            merchantUserId = PortalUserDetails.objects.get(pu_id=request.user.id).pud_unique_id

            merchantTransactionid = f"MT{uuid.uuid4().int}"[:20]
            data = {
                "merchantId": merchantId,
                "merchantTransactionId": merchantTransactionid,
                "merchantUserId": merchantUserId,
                "amount": amount,
                "redirectUrl": "https://api.tapipe.in/admin_hub/phonepe/response/",
                "redirectMode": "POST",
                "callbackUrl": f"https://partner.tapipe.in/retailer-phonepepg/{merchantTransactionid}",
                "mobileNumber": contact_number,
                "paymentInstrument": {
                    "type": "PAY_PAGE"
                }
            }

            index = "1"
            endpoint = "/pg/v1/pay"
            saltkey = saltkey

            json_data = json.dumps(data)
            data_bytes = json_data.encode('utf-8')
            sha256val = base64.b64encode(data_bytes).decode('utf-8')

            print(f"Base64 Encoded Data: {sha256val}")

            main_string = sha256val + endpoint + saltkey
            hash_data = hashlib.sha256(main_string.encode('utf-8')).hexdigest()
            check_sum = f"{hash_data}###{index}"

            print(f"Generated Checksum: {check_sum}")

            url = "https://api.phonepe.com/apis/hermes/pg/v1/pay"
            payload = {"request": sha256val}
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "X-VERIFY": check_sum
            }

            response = requests.post(url, json=payload, headers=headers)
            print(f"Response Status Code: {response.status_code}") 
            print(f"Raw Response Content: {response.text}")

            if response.status_code == 200:
                try:
                    json_response = response.json()
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON response from PhonePe API.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                effective_amt = int(amount) / 100
                phonepe_trnasaction = PhonePeTransaction.objects.create(
                    pp_marchant_trn_id=merchantTransactionid,
                    pp_amount=effective_amt,
                    pp_contact_no=contact_number,
                    pp_pay_response=json_response,
                    sp=service_provider,
                    created_by=request.user.id
                )
                user_activity = {
                    "table_id": phonepe_trnasaction.pk,
                    "table_name": 'ad_phonepe_service_transaction',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'Phonepe Payment Getway Transaction successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(phonepe_trnasaction)
                }

                add_user_activity(user_activity)
                return Response({'status': 'success', 'message': 'Service Transaction successfully.', 'data': json_response}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': f'PhonePe API error: {response.status_code}', 'data': response.text}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except requests.RequestException as e:
            return Response({'status': 'error', 'message': f'API request failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def status_transaction(self, request):
        merchantTransactionid = request.data.get('merchantTransactionid')
        sp_id = request.data.get('sp_id')
        # merchantId = "TAPIPEONLINE"
        merchantId = ''
        # saltkey = "93880238-12c3-495e-8bdc-688187572c00"
        saltkey = ''
        try:
            if not merchantTransactionid: return Response({'status': 'fail', 'message': 'merchantTransactionid is required.'}, status=status.HTTP_400_BAD_REQUEST)
            service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
            if service_provider.is_self_config == True:
                merchantId = service_provider.credentials_json.get('merchantId')
                saltkey = service_provider.credentials_json.get('saltkey')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                merchantId = service_provider.credentials_json.get('merchantId')
                saltkey = service_provider.credentials_json.get('saltkey')

            transaction_data = PhonePeTransaction.objects.get(pp_marchant_trn_id=merchantTransactionid)
            print('============', transaction_data)
            merchantId = merchantId
            merchantTransactionId = merchantTransactionid

            index = "1"
            saltkey = saltkey

            # Generate checksum
            main_string = f"/pg/v1/status/{merchantId}/{merchantTransactionId}{saltkey}"
            hash_data = hashlib.sha256(main_string.encode('utf-8')).hexdigest()
            check_sum = f"{hash_data}###{index}"

            print("Checksum:", check_sum)

            url = f"https://api.phonepe.com/apis/hermes/pg/v1/status/{merchantId}/{merchantTransactionId}"

            headers = {
                "Content-Type": "application/json",
                "X-VERIFY": check_sum,
                "X-MERCHANT-ID": merchantId,
                "accept": "application/json"
            }

            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                try:
                    json_response = response.json()
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON response from PhonePe API.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                print("json_response.get('code')", json_response.get('code'))
                transaction_data.pp_trn_response=json_response
                transaction_data.pp_status='SUCCESS' if json_response.get('code') == 'PAYMENT_SUCCESS' else 'FAILED'
                transaction_data.save()
                service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
                gst_rate = service_provider.hsn_sac.tax_rate
                admin_charges = None 
                # fetch admin charges
                admin_charge_queryset = AdCharges.objects.filter(service_provider_id=sp_id)

                if admin_charge_queryset.exists():  # Ensure queryset is not empty
                    for charge in admin_charge_queryset:
                        if charge.minimum <= float(transaction_data.pp_amount) <= charge.maximum:
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

                char_comm_amt = transaction_data.pp_amount * (admin_rate / 100) if admin_rate_type == 'is_percent' else admin_rate
                admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))

                portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)

                if transaction_data.pp_trn_response.get('data').get('paymentInstrument').get('type') == 'UPI':
                    configed = PhonePeConfiged.objects.get(payment_method="UPI")
                elif transaction_data.pp_trn_response.get('data').get('paymentInstrument').get('type') == 'CARD':
                    card_type = transaction_data.pp_trn_response.get('data').get('paymentInstrument').get('cardType')
                    configed = PhonePeConfiged.objects.get(payment_method='CARD', card_type=card_type)
                else:
                    configed = PhonePeConfiged.objects.get(payment_method="OTHERS")

                data = {
                    "service_id": transaction_data.pk,
                    "amount": transaction_data.pp_amount,
                    "table_name": "ad_mobile_recharge",
                    "wl_label": f"Phonepe_pg_by_{portal_user_details.pud_unique_id}_of_amount_{transaction_data.pp_amount}_with_tx_id_{transaction_data.pp_marchant_trn_id}",
                    "gst_rate": gst_rate,
                    "admin_tax_amt": admin_tax_amt,
                    "char_comm_amt": char_comm_amt,
                    "admin_charges_type": admin_charges_type,
                    "sp_id": transaction_data.sp.sp_id,
                    "contact_number": transaction_data.pp_contact_no,
                    "name": None,
                    "response_data": json_response,
                    "label": service_provider.label,
                    "category": configed.ss_id,
                    "is_self_config": service_provider.is_self_config
                }
                print('data', data)
                charges_calculation_function(request, data)
                user_activity = {
                    "table_id": transaction_data.pk,
                    "table_name": 'ad_phonepe_service_transaction',
                    "ua_action": 'Sattel Transaction',  # Action performed
                    "ua_description": 'Phonepe Payment Getway Transaction settle successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(transaction_data)
                }

                add_user_activity(user_activity)
                
                return Response({'status': 'success', 'message': 'Service Transaction successfully.'}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': f'PhonePe API error: {response.status_code}', 'response': response.text}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except PhonePeTransaction.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Trnasaction ID dose not exsits.'}, status=status.HTTP_404_NOT_FOUND)

        except requests.exceptions.RequestException as e:
            return Response({'status': 'fail', 'message': str(e)}, status=500)

    def get_all_transaction(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        search = request.data.get('search', '')
        transaction_status = request.data.get('transaction_status', '')
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
            transactions = PhonePeTransaction.objects.filter(created_by=request.user.id).order_by('-pk')

            if search != '':
                transactions = transactions.filter(Q(pp_marchant_trn_id__icontains=search) | Q(pp_contact_no__icontains=search))

            if transaction_status != '':
                transactions = transactions.filter(pp_status=transaction_status)

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
            serializer = PhonePeSerializer(page, many=True)
            
            # Convert datetime fields in the serialized data
            for trn in serializer.data:
                if 'cf_pg_service_trn_dt' in trn and isinstance(trn['cf_pg_service_trn_dt'], str):
                    parsed_date = parser.parse(trn['cf_pg_service_trn_dt'])  # Auto-detect format
                    trn['cf_pg_service_trn_dt'] = parsed_date.strftime("%d-%m-%Y %I:%M %p")

            data = {
                'total_pages': paginator.num_pages,
                'current_page': page.number,
                'total_items': paginator.count,
                'results': serializer.data
            }

            return Response({'status': 'success', 'message': 'Get all transactions.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_charges(self, request):
        is_get_charges = request.data.get('is_get_charges')

        try:
            if not is_get_charges: return Response({'status': 'fail', 'message': 'is_get_charges is required.'}, status=status.HTTP_400_BAD_REQUEST)
            results = {'results': []}
            if is_get_charges == 'True':
                phone_pe_configed = PhonePeConfiged.objects.filter(is_deactive=False, is_deleted=False, sa_provided=True)
                print('=============', phone_pe_configed)
                if phone_pe_configed:
                    serializer = PhonePeConfigedSerializer(phone_pe_configed, many=True)
                    results = {'results': serializer.data}
                    return Response({'status': 'success', 'message': 'Phonepe Configed data fetch successfully.', 'data': results}, status=status.HTTP_200_OK)
                else:
                    return Response({'status': 'success', 'message': 'Phonepe Configed dose not exists.', 'data': results}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': 'is_get_charges is not True.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PhonePeResponse(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        merchantTransactionid = request.data.get('merchantOrderId')
        phone_pe_trn = PhonePeTransaction.objects.get(pp_marchant_trn_id=merchantTransactionid)
        
        phone_pe_trn.pp_pay_response = request.data
        # phone_pe_trn.pp_status = 'SUCCESS'
        phone_pe_trn.save()
        code = 0
        if request.data.get('code') == 'PAYMENT_SUCCESS':
            code = 0
        else:
            code = 1
        frontend_url = f"https://partner.tapipe.in/retailer-phonepepg/{merchantTransactionid}/{code}"
        return redirect(frontend_url)



