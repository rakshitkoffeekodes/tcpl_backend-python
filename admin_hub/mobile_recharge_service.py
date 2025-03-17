from .views import *
from validation.custom_validation import *
from .utilies import *
from rest_framework.exceptions import ValidationError
from .charges_calculation import *
from control_panel.models import *
from datetime import datetime, timedelta
from django.utils.timezone import localtime, make_aware

class MobileRechargeAPIView(APIView):

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]    

    def post(self, request):
        if 'contact_number' in request.data and 'amount' in request.data and 'opid' in request.data and 'sp_id' in request.data:
            return self.create_recharge_order(request)
        elif 'reftxnid' in request.data:
            return self.check_recharge_status(request)
        elif 'recharge_type' in request.data:
            return self.get_recharge_oprator(request)
        elif 'ss_name' in request.data and 'is_fetch_plan' in request.data:
            return self.get_fetch_plan(request)
        elif 'page_number' in request.data or 'page_size' in request.data:
            return self.get_recharge_transaction(request)
        else:
            return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)
          
    def create_recharge_order(self, request):
        contact_number = request.data.get('contact_number')
        amount = request.data.get('amount')
        opid = request.data.get('opid')
        sp_id = request.data.get('sp_id')
        response_data = {}
        trn_id = get_random_string(length=6, allowed_chars='0123456789')
        reftxnid = f'SkPMR_{trn_id}'
        ApiToken=""

        if not contact_number: return Response({'status': 'fail', 'message': 'contact_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not amount: return Response({'status': 'fail', 'message': 'amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not opid: return Response({'status': 'fail', 'message': 'opid is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not sp_id: return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not validate_mobile_number(contact_number): return Response({'status': 'fail', 'message': 'Invalid mobile number format.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isnumber(amount): return Response({'status': 'fail', 'message': 'Amount must be a number.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isnumber(opid): return Response({'status': 'fail', 'message': 'Opid must be a number.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isnumber(sp_id): return Response({'status': 'fail', 'message': 'Sp_id must be a number.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            admin_wallet = check_admin_wallet(request, amount)
            retailer_wallet = check_retailer_wallet(request, amount, request.user.id)

            if sp.is_self_config == True:
                ApiToken = sp.credentials_json.get('ApiToken')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                ApiToken = service_provider.credentials_json.get('ApiToken')
            
            oprator_id = Oprators.objects.get(ss_id=opid)
            oprator_code = oprator_id.operator_code
            # ApiToken="68f9d0d9-59b8-46a8-bda7-d6f98ae1c277"
            url = f"https://sankalppe.com/Api/Service/Recharge2?ApiToken={ApiToken}&MobileNo={contact_number}&Amount={amount}&OpId={oprator_code}&RefTxnId={reftxnid}"

            response = requests.get(url, timeout=3)
            
            response_data = response.json()
            if response_data['STATUS'] == 1:
                mobile_recharge = MobileRecharge.objects.create(mr_mobile_no=contact_number,
                                                                mr_request_txnid=reftxnid,
                                                                mr_amount=amount,
                                                                mr_operator=opid,
                                                                mr_sp = sp,
                                                                mr_response=response_data,
                                                                mr_optxnid=response_data['OPTXNID'],
                                                                mr_txnno = response_data['TXNNO'],
                                                                mr_status='SUCCESS',
                                                                created_by=request.user.id)

                oprator = Oprators.objects.filter(ss_id=opid).first()
                service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
                gst_rate = service_provider.hsn_sac.tax_rate
                admin_rate = float(oprator.to_us_charges.get('rate_value'))

                admin_rate_type = oprator.to_us_charges.get('rate_type')

                admin_charges_type = oprator.to_us_charges.get('charge_type')

                
                char_comm_amt = float(amount) * (admin_rate / 100) if admin_rate_type == 'is_percent' else admin_rate
                admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))

                portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)

                data = {
                    "service_id": mobile_recharge.pk,
                    "amount": mobile_recharge.mr_amount,
                    "table_name": "ad_mobile_recharge",
                    "wl_label": f"Recharge_by_{portal_user_details.pud_unique_id}_of_amount_{amount}_with_tx_id_{mobile_recharge.mr_request_txnid}",
                    "gst_rate": gst_rate,
                    "admin_tax_amt": admin_tax_amt,
                    "char_comm_amt": char_comm_amt,
                    "admin_charges_type": admin_charges_type,
                    "sp_id": sp_id,
                    "contact_number": contact_number,
                    "name": None,
                    "response_data": response_data,
                    "label": service_provider.label,
                    "category": oprator.ss_id
                }
                
                charges_calculation_function(data, request)


                user_activity = {
                    "table_id": mobile_recharge.pk,
                    "table_name": 'ad_mobile_recharge',
                    "ua_action": 'Create',  # Action performed
                    "ua_description": 'Mobile Recharge successfully.',  # Action description
                    "created_by": request.user,  # Current user performing the action
                    "request_data": dict(request.data),  # Request data
                    "response_data": model_to_dict(mobile_recharge)
                }

                add_user_activity(user_activity)

                return Response({'status': 'success', 'message': 'Recharge  order created successfully.', 'data': response_data}, status=status.HTTP_200_OK)
            
            else:
                mobile_recharge = MobileRecharge.objects.create(mr_mobile_no=contact_number,
                                                                mr_response=response_data,
                                                                created_by=request.user.id,
                                                                mr_request_txnid=reftxnid,
                                                                mr_amount=amount,
                                                                mr_operator=opid,
                                                                mr_status='FAILED')

                return Response({'status': 'fail', 'message': 'Service Unavailable. Please try again later'}, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.Timeout:
            mobile_recharge = MobileRecharge.objects.create(mr_mobile_no=contact_number,
                                                            mr_response=response_data,
                                                            created_by=request.user.id,
                                                            mr_request_txnid=reftxnid,
                                                            mr_amount=amount,
                                                            mr_operator=opid,
                                                            mr_sp=sp,
                                                            mr_status='PENDING')

            return Response({'status': 'success', 'message': 'Your recharge is currently pending. Please check the status again after 5 minutes.', 'is_pending': True}, status=status.HTTP_200_OK)
        

        except ValidationError as e:
            message = str(e)
            if "ErrorDetail" in message:
                message = message.split("string='")[1].split("', code=")[0]  
            return Response({'status': 'fail', 'message': message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'fail', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def check_recharge_status(self, request):
        reftxnid = request.data.get('reftxnid')
        sp_id = request.data.get('sp_id')
        ApiToken = ''
        try:
            if not reftxnid: return Response({'status': 'fail', 'message': 'reftxnid is required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                mobile_recharge = MobileRecharge.objects.get(mr_request_txnid=reftxnid)
            except MobileRecharge.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Mobile recharge order not found.'}, status=status.HTTP_404_NOT_FOUND)

            # sp = AdServiceProvider.objects.get(sp_id=sp_id)
            # if sp.is_self_config == True:
            #     ApiToken = sp.credentials_json.get('ApiToken')
            # else:
            #     service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
            #     ApiToken = service_provider.credentials_json.get('ApiToken')

            oprator_name = Oprators.objects.get(ss_id=mobile_recharge.mr_operator)
            ApiToken="68f9d0d9-59b8-46a8-bda7-d6f98ae1c277"
            url = f"https://sankalppe.com/Api/service/statuscheck?ApiToken={ApiToken}&RefTxnId={reftxnid}"
            response = requests.get(url)
            response_data = response.json()
            print('response_data', response_data)
            if response_data['STATUS'] == 1:
                mobile_recharge.mr_response = response_data
                mobile_recharge.mr_circle = response_data['CIRCLE']
                mobile_recharge.mr_optxnid = response_data['OPTXNID']
                mobile_recharge.mr_txnno = response_data['TXNNO']
                mobile_recharge.mr_response = response_data
                print('mobile_recharge.mr_status', mobile_recharge.mr_status)
                if mobile_recharge.mr_status == "PENDING":
                    print('------------------')
                    oprator = Oprators.objects.filter(ss_id=mobile_recharge.mr_operator).first()
                    service_provider = AdServiceProvider.objects.get(sp_id=mobile_recharge.mr_sp.sp_id)
                    gst_rate = service_provider.hsn_sac.tax_rate

                    admin_rate = float(oprator.to_us_charges.get('rate_value'))

                    admin_rate_type = oprator.to_us_charges.get('rate_type')

                    admin_charges_type = oprator.to_us_charges.get('charge_type')

                    admin_wallet = check_admin_wallet(request, mobile_recharge.mr_amount)
                    retailer_wallet = check_retailer_wallet(request, mobile_recharge.mr_amount, request.user.id)
                    char_comm_amt = float(mobile_recharge.mr_amount) * (admin_rate / 100) if admin_rate_type == 'is_percent' else admin_rate
                    admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))

                    portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)

                    data = {
                        "service_id": mobile_recharge.pk,
                        "amount": mobile_recharge.mr_amount,
                        "table_name": "ad_mobile_recharge",
                        "wl_label": f"Recharge_by_{portal_user_details.pud_unique_id}_of_amount_{mobile_recharge.mr_amount}_with_tx_id_{mobile_recharge.mr_request_txnid}",
                        "gst_rate": gst_rate,
                        "admin_tax_amt": admin_tax_amt,
                        "char_comm_amt": char_comm_amt,
                        "admin_charges_type": admin_charges_type,
                        "sp_id": mobile_recharge.mr_sp.sp_id,
                        "contact_number": mobile_recharge.mr_mobile_no,
                        "name": None,
                        "response_data": response_data,
                        "label": service_provider.label,
                        "category": oprator.ss_id,
                        "is_self_config": service_provider.is_self_config
                    }
                    print('data', data)
                    charges_calculation_function(request, data)
 
                    user_activity = {
                        "table_id": mobile_recharge.pk,
                        "table_name": 'ad_mobile_recharge',
                        "ua_action": 'Create',  # Action performed
                        "ua_description": 'Mobile Recharge successfully.',  # Action description
                        "created_by": request.user,  # Current user performing the action
                        "request_data": dict(request.data),  # Request data
                        "response_data": model_to_dict(mobile_recharge)
                    }

                    add_user_activity(user_activity)
                mobile_recharge.mr_status = "SUCCESS"
                mobile_recharge.save()
                recipt_data = {
                    "Service Provider": oprator_name.ss_name,
                    "Service Number": mobile_recharge.mr_mobile_no,
                    "Trnasaction ID": mobile_recharge.mr_request_txnid,
                    "Time": mobile_recharge.mr_dt.strftime("%d/%m/%Y %I:%M %p"),
                    "Recharge Amount": f"Rs. {mobile_recharge.mr_amount}",
                    "Surcharge": "Rs. 0.00",
                    "Net Amount": f"Rs. {mobile_recharge.mr_amount}",
                }

                return Response({'status': 'success', 'message': 'Mobile recharge order status.', 'data': {"results":recipt_data}}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': 'Mobile recharge order status.', 'data': {"results":response_data}}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'fail', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # def get_recharge_oprator(self, request):
    #     recharge_type = request.data.get('recharge_type')
    #     if not recharge_type: return Response({'status': 'fail', 'message': 'Type is required.'}, status=status.HTTP_400_BAD_REQUEST)

    #     if recharge_type not in ['Mobile Recharge', 'DTH Recharge', 'Electricity Bill', 'Broadband/Landline', 'Piped Gas', 'Insurance Payment', 'Water', 'Other', 'FASTag', 'Financial Service', 'Credit Card Home']:
    #         return Response({'status': 'fail', 'message': 'Invalid type. Please enter a valid type for Mobile Recharge, DTH Recharge, Electricity Bill, Broadband/Landline, Piped Gas, Insurance Payment, Water, Other, FASTag, Financial Service, Credit Card Home.'}, status=status.HTTP_400_BAD_REQUEST)

    #     try:
    #         all_oprators = Oprators.objects.filter(operator_type=recharge_type).exclude(sd_charges__isnull=True, md_charges__isnull=True, dt_charges__isnull=True, rt_charges__isnull=True,)

    #         data ={
    #             'results': AdOperatorSerializer(all_oprators, many=True).data
    #         }
    #         return Response({'status': 'success', 'message': 'All operators.', 'data': data}, status=status.HTTP_200_OK)

    #     except Exception as e:
    #         return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_recharge_oprator(self, request):
        print('request', request.data)
        recharge_type = request.data.get('recharge_type', '')
        if not recharge_type: return Response({'status': 'fail', 'message': 'Type is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if recharge_type not in ['POSTPAID', 'PREPAID', 'DTH']:
            return Response({'status': 'fail', 'message': 'Invalid type. Please enter a valid type for PostPaid, PrePaid, DTH.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            all_oprators = Oprators.objects.filter(recharge_type=recharge_type).exclude(sd_charges__isnull=True, md_charges__isnull=True, dt_charges__isnull=True, rt_charges__isnull=True,)

            data ={
                'results': AdOperatorSerializer(all_oprators, many=True).data
            }
            return Response({'status': 'success', 'message': 'All operators.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_recharge_transaction(self, request):
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

            if not isnumber(page_number):
                return Response({'status': 'fail', 'message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
            fetch_info = MobileRecharge.objects.filter(created_by=request.user.id).order_by('-pk')

            if search != '':
                fetch_info = fetch_info.filter(Q(mr_optxnid__icontains=search) | Q(mr_txnno__icontains=search) | Q(mr_request_txnid__icontains=search) | Q(mr_mobile_no__icontains=search))
            
            if transaction_status != '':
                fetch_info = fetch_info.filter(mr_status=transaction_status)

            # Apply Date Filters
            if date_filter or start_date and end_date:
                # Ensure timezone-aware date
                today = localtime().date()
                now = localtime()
                if date_filter.strip() == 'today':
                    start_datetime = make_aware(datetime.combine(today, datetime.min.time()))
                    end_datetime = make_aware(datetime.combine(today + timedelta(days=1), datetime.min.time()))
                    fetch_info = fetch_info.filter(created_at__gte=start_datetime, created_at__lt=end_datetime)

                elif date_filter == 'weekly':
                    start_of_week = today - timedelta(days=today.weekday())  # Start of the week (Monday)
                    start_datetime = make_aware(datetime.combine(start_of_week, datetime.min.time()))
                    fetch_info = fetch_info.filter(created_at__gte=start_datetime)

                elif date_filter == 'monthly':
                    start_of_month = today.replace(day=1)  # First day of the current month
                    start_datetime = make_aware(datetime.combine(start_of_month, datetime.min.time()))
                    fetch_info = fetch_info.filter(created_at__gte=start_datetime)

                elif date_filter == 'yearly':
                    start_of_year = today.replace(month=1, day=1)  # First day of the current year
                    start_datetime = make_aware(datetime.combine(start_of_year, datetime.min.time()))
                    fetch_info = fetch_info.filter(created_at__gte=start_datetime)

                elif date_filter == 'custom' and start_date and end_date:
                    try:
                        start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
                        end_date = make_aware(datetime.strptime(end_date, "%Y-%m-%d")) + timedelta(days=1)  # Include end date
                        fetch_info = fetch_info.filter(created_at__gte=start_date, created_at__lt=end_date)
                    except ValueError:
                        return Response({'status': 'fail', 'message': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

            paginator = Paginator(fetch_info, page_size)
            page = paginator.get_page(page_number)
            serializer = MobileRechargeSerializer(page, many=True)
            for trn in serializer.data:
                # Convert to datetime if it's a string
                if isinstance(trn['mr_dt'], str):
                    trn['mr_dt'] = datetime.strptime(trn['mr_dt'], "%Y-%m-%dT%H:%M:%S.%f%z")

                trn['mr_dt'] = trn['mr_dt'].strftime("%d-%m-%Y %I:%M %p")

            data = {
                'total_pages': paginator.num_pages,
                'current_page': page.number,
                'total_items': paginator.count,
                'results': serializer.data
            }

            return Response({'status': 'success', 'message': 'Recharge Trnasaction list.', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal Server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_fetch_plan(self, request):
        ss_name = request.data.get('ss_name')
        is_fetch_plan = request.data.get('is_fetch_plan')

        try:
            if not ss_name: return Response({'status': 'fail', 'message': 'ss_name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not is_fetch_plan: return Response({'status': 'fail', 'message': 'is_fetch_plan is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if is_fetch_plan == 'True':
                url = "https://www.mplan.in/api/plans.php?apikey=1ee7537d7d3a290419f31b655a2cadf0&cricle=Gujarat&&operator=Jio"

                response = requests.get(url)
                json_response = response.json()
                if response.status_code == 200:

                    return Response({'status': 'success', 'message': 'plan fetch successfully.', 'data': {'results': json_response}}, status=status.HTTP_200_OK)

                else:
                    return Response({'status': 'fail', 'message': json_response.get('results').get('records').get('msg')}, status=status.HTTP_400_BAD_REQUEST)
            
            else:
                return Response({'status': 'fail', 'message': 'is_fetch_plan is false please enter True.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
