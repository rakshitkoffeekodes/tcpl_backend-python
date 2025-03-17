from .views import *


class AdminCategoryAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            if 'sp_id' and 'page_number' in request.data or 'page_size' in request.data:
                if  request.data.get('sp_id') == '3':
                    return self.fetch_bbps_data(request)
                elif request.data.get('sp_id') == '4':
                    return self.fetch_recharge_data(request)
                elif request.data.get('sp_id') == '6':
                    return self.fetch_cf_pg_configed_data(request)
                elif request.data.get('sp_id') == '7':
                    return self.fetch_phonepe_pg_configed_data(request)
                else:
                    return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def fetch_recharge_data(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        ss_id = request.data.get('ss_id', None)
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

            all_operator = SaOprators.objects.filter(is_deleted=False).order_by('-pk')

            if ss_id:
                all_operator = all_operator.filter(ss_id=ss_id).order_by('-pk')

            if search != '':
                all_operator = all_operator.filter(Q(ss_name__icontains=search) | Q(operator_code__icontains=search) | Q(operator_type__icontains=search)).order_by('-pk')

            paginator = Paginator(all_operator, page_size)
            operator = paginator.page(page_number)
            serializer = RechargeOperatorSerializer(operator, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data,
                'is_configed': False
            }
            return Response({'status': 'success', 'message': 'Recharge Operator data fetched successfully', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def fetch_bbps_data(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        ss_id = request.data.get('ss_id', None)
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

            all_categories = SaBBPSBillerCategory.objects.filter(is_deleted=False).order_by('-pk')

            if ss_id:
                all_categories = all_categories.filter(ss_id=ss_id).order_by('-pk')

            if search != '':
                all_categories = all_categories.filter(ss_name__icontains=search).order_by('-pk')

            paginator = Paginator(all_categories, page_size)
            categories = paginator.page(page_number)
            serializer = BBPSBillerCategorySerializer(categories, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data,
                'is_configed': False
            }
            return Response({'status': 'success', 'message': 'BBPS Biller Categories', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_cf_pg_configed_data(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        ss_id = request.data.get('ss_id', None)
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

            all_configed = SaPgConfiged.objects.filter(is_deleted=False).order_by('-pk')

            if ss_id:
                all_configed = all_configed.filter(ss_id=ss_id).order_by('-pk')

            if search != '':
                all_configed = all_configed.filter(Q(card_type__icontains=search) | Q(card_network__icontains=search) | Q(card_sub_type__icontains=search)).order_by('-pk')

            paginator = Paginator(all_configed, page_size)
            configeds = paginator.page(page_number)
            serializer = CfPgConfigedSerializer(configeds, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data,
                'is_configed': True
            }
            return Response({'status': 'success', 'message': 'Cashfree payment getway configed', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_phonepe_pg_configed_data(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        ss_id = request.data.get('ss_id', None)
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

            all_configed = SaPhonePePgConfiged.objects.filter(is_deleted=False).order_by('-pk')

            if ss_id:
                all_configed = all_configed.filter(ss_id=ss_id).order_by('-pk')

            if search != '':
                all_configed = all_configed.filter(Q(card_type__icontains=search) | Q(card_network__icontains=search) | Q(card_sub_type__icontains=search)).order_by('-pk')

            paginator = Paginator(all_configed, page_size)
            configeds = paginator.page(page_number)
            serializer = PhonePePgConfigedSerializer(configeds, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data,
                'is_configed': True
            }
            return Response({'status': 'success', 'message': 'PhonePe payment getway configed', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        sp_id = request.data.get('sp_id')
        try:
            if sp_id == '8':
                return self.update_bbps_category(request)
            elif sp_id == '4':
                return self.update_recharge_category(request)
            elif sp_id == '9':
                return self.update_cf_pg_configed(request)
            elif sp_id == '10':
                return self.update_phonepe_pg_configed(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update_bbps_category(self, request):
        # Extract request data
        ss_id = request.data.get('ss_id')
        sp_id = request.data.get('sp_id')
        to_us_charges = request.data.get('to_us_charges')
        to_provide_charges = request.data.get('to_provide_charges')
        charge_type = request.data.get('charge_type')
        message = 'BBPS Category updated successfully.'

        # Validate required fields
        if not ss_id:
            return Response({'status': 'fail', 'message': 'ss_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not sp_id:
            return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ss_id.isdigit():
            return Response({'status': 'fail', 'message': 'ss_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve service and related objects
            service_provider = ServiceProvider.objects.filter(sp_id=sp_id).first()
            service = SaService.objects.get(service_id=service_provider.service_id.service_id)
            bbps_category = SaBBPSBillerCategory.objects.get(ss_id=ss_id)

            # Ensure service is global
            if not service.is_global:
                return Response({'status': 'fail', 'message': 'The service is not global.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Handle charges and category activation/deactivation
            if not to_us_charges and not to_provide_charges:
                # Handle case when charges are not provided
                if not bbps_category.to_us_charges or not bbps_category.to_provide_charges:
                    return Response({
                        'status': 'fail',
                        'message': 'Charges data is required before activating sub service.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Handle category deactivation
                if bbps_category.is_deactive == False:
                    bbps_category.is_deactive = True
                    bbps_category.save()
                    
                    # Deactivate all related admin categories
                    admin_bbps_categories = BBPSBillerCategory.objects.filter(is_deleted=False, ss_name=bbps_category.ss_name)
                    for category in admin_bbps_categories:
                        category.sa_provided = False
                        category.is_deactive = True
                        category.save()
                    
                    message = 'BBPS category deactivated successfully.'
                else:
                    # Handle category activation
                    if service_provider.is_deactive == False and service.is_deactive == False:
                        if not BBPSBillerCategory.objects.filter(ss_name=bbps_category.ss_name):
                            BBPSBillerCategory.objects.create(
                                ss_name=bbps_category.ss_name,
                                to_us_charges=bbps_category.to_provide_charges
                            )
                            message = 'BBPS category activated successfully.'
                            
                        else:
                            category_data = BBPSBillerCategory.objects.filter(ss_name=bbps_category.ss_name)
                            for data in category_data:
                                data.to_us_charges=bbps_category.to_provide_charges
                                data.sa_provided = True
                                data.save()
                            bbps_category.is_deactive = False
                            bbps_category.save()
                            
                            message = 'BBPS category activated successfully.'

                    else:
                        bbps_category.is_deactive = False
                        bbps_category.save()
                        
                        message = 'BBPS category activated successfully.'
            else:
                # Handle case when charges are provided
                
                try:
                    to_us_charges = json.loads(to_us_charges)
                    to_us_charges['charge_type'] = charge_type
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON format for to_us_charges.'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    to_provide_charges = json.loads(to_provide_charges)
                    to_provide_charges['charge_type'] = charge_type
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON format for to_provide_charges.'}, status=status.HTTP_400_BAD_REQUEST)

                # Update category charges
                
                bbps_category.to_us_charges = to_us_charges
                bbps_category.to_provide_charges = to_provide_charges
                bbps_category.save()

                admin_bbps_categories = BBPSBillerCategory.objects.filter(is_deleted=False, ss_name=bbps_category.ss_name)
                if admin_bbps_categories:
                    for data in admin_bbps_categories:
                        data.to_us_charges=bbps_category.to_provide_charges
                        data.save()

            # Return success response
            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except SaService.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except ServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except SaBBPSBillerCategory.DoesNotExist:
            return Response({'status': 'fail', 'message': 'BBPS category does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def update_recharge_category(self, request):
        # Extract request data
        ss_id = request.data.get('ss_id')
        sp_id = request.data.get('sp_id')
        to_us_charges = request.data.get('to_us_charges')
        to_provide_charges = request.data.get('to_provide_charges')
        charge_type = request.data.get('charge_type')
        message = 'Recharge Operator updated successfully.'

        # Validate required fields
        if not ss_id:
            return Response({'status': 'fail', 'message': 'ss_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not sp_id:
            return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ss_id.isdigit():
            return Response({'status': 'fail', 'message': 'ss_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve service and related objects
            service_provider = ServiceProvider.objects.filter(sp_id=sp_id).first()
            service = SaService.objects.get(service_id=service_provider.service_id.service_id)
            recharge_opertator = SaOprators.objects.get(ss_id=ss_id)

            # Ensure service is global
            if not service.is_global:
                return Response({'status': 'fail', 'message': 'The service is not global.'}, status=status.HTTP_400_BAD_REQUEST)

            # Handle charges and category activation/deactivation
            if not to_us_charges and not to_provide_charges:
                # Handle case when charges are not provided
                if service_provider.is_deactive and service.is_deactive:
                    if not recharge_opertator.to_us_charges or not recharge_opertator.to_provide_charges:
                        return Response({
                            'status': 'fail',
                            'message': 'The service and service provider are currently active. Please configure charges before proceeding.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    if not recharge_opertator.to_us_charges or not recharge_opertator.to_provide_charges:
                        return Response({
                            'status': 'fail',
                            'message': 'The service and service provider are currently active. Please configure charges before proceeding.'
                        }, status=status.HTTP_400_BAD_REQUEST)

                # Handle category deactivation
                if recharge_opertator.is_deactive == False:
                    recharge_opertator.is_deactive = True
                    recharge_opertator.save()
                    # Deactivate all related admin categories
                    admin_recharge_oprators = Oprators.objects.filter(is_deleted=False, ss_name=recharge_opertator.ss_name)
                    for oprators in admin_recharge_oprators:
                        oprators.is_deactive = True
                        oprators.sa_provided = False
                        oprators.save()
                    message = 'Recharge Operator deactivated successfully.'
                else:
                    # Handle category activation
                    if service_provider.is_deactive == False and service.is_deactive == False:
                        if not Oprators.objects.filter(ss_name=recharge_opertator.ss_name):
                            Oprators.objects.create(
                                ss_name=recharge_opertator.ss_name,
                                to_us_charges=recharge_opertator.to_provide_charges
                            )
                            message = 'Recharge Operator activated successfully.'
                        else:
                            category_data = Oprators.objects.filter(ss_name=recharge_opertator.ss_name)
                            for data in category_data:
                                data.to_us_charges=recharge_opertator.to_provide_charges
                                data.sa_provided = True
                                data.save()
                            recharge_opertator.is_deactive = False
                            recharge_opertator.save()
                            message = 'Recharge Operator activated successfully.'

                    else:
                        recharge_opertator.is_deactive = False
                        recharge_opertator.save()
                        message = 'Recharge Operator activated successfully.'
            else:
                # Handle case when charges are provided
                try:
                    to_us_charges = json.loads(to_us_charges)
                    to_us_charges['charge_type'] = charge_type
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON format for to_us_charges.'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    to_provide_charges = json.loads(to_provide_charges)
                    to_provide_charges['charge_type'] = charge_type
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON format for to_provide_charges.'}, status=status.HTTP_400_BAD_REQUEST)

                # Update category charges
                recharge_opertator.to_us_charges = to_us_charges
                recharge_opertator.to_provide_charges = to_provide_charges
                recharge_opertator.save()

                admin_recharge_oprators = Oprators.objects.filter(is_deleted=False, ss_name=recharge_opertator.ss_name)
                if admin_recharge_oprators:
                    for data in admin_recharge_oprators:
                        data.to_us_charges=recharge_opertator.to_provide_charges
                        data.save()

            # Return success response
            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except SaService.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except ServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except SaOprators.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Recharge Operator does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_cf_pg_configed(self, request):
        # Extract request data
        ss_id = request.data.get('ss_id')
        sp_id = request.data.get('sp_id')
        to_us_charges = request.data.get('to_us_charges')
        to_provide_charges = request.data.get('to_provide_charges')
        charge_type = request.data.get('charge_type')
        message = 'Cashfree Payment getway configed updated successfully.'

        # Validate required fields
        if not ss_id:
            return Response({'status': 'fail', 'message': 'ss_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not sp_id:
            return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ss_id.isdigit():
            return Response({'status': 'fail', 'message': 'ss_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve service and related objects
            service_provider = ServiceProvider.objects.filter(sp_id=sp_id).first()
            service = SaService.objects.get(service_id=service_provider.service_id.service_id)
            configed = SaPgConfiged.objects.get(ss_id=ss_id)
            print('configed', configed)
            # Ensure service is global
            if not service.is_global:
                return Response({'status': 'fail', 'message': 'The service is not global.'}, status=status.HTTP_400_BAD_REQUEST)

            # Handle charges and category activation/deactivation
            if not to_us_charges and not to_provide_charges:
                # Handle case when charges are not provided
                if service_provider.is_deactive and service.is_deactive:
                    if not configed.to_us_charges or not configed.to_provide_charges:
                        return Response({
                            'status': 'fail',
                            'message': 'The service and service provider are currently active. Please configure charges before proceeding.'
                        }, status=status.HTTP_400_BAD_REQUEST)

                # Handle category deactivation
                if configed.is_deactive == False:
                    configed.is_deactive = True
                    configed.save()
                    # Deactivate all related admin categories
                    admin_configed = AdCfPgConfiged.objects.filter(is_deleted=False, card_type=configed.card_type, card_network=configed.card_network, card_sub_type=configed.card_sub_type)
                    print('admin_configed', admin_configed)
                    for confi in admin_configed:
                        confi.is_deactive = True
                        confi.sa_provided = False
                        confi.save()
                    message = 'Cashfree Payment Getway configed deactivated successfully.'
                else:
                    # Handle category activation
                    if service_provider.is_deactive == False and service.is_deactive == False:
                        if not AdCfPgConfiged.objects.filter(card_type=configed.card_type, card_network=configed.card_network, card_sub_type=configed.card_sub_type):
                            AdCfPgConfiged.objects.create(
                                card_type=configed.card_type, 
                                card_network=configed.card_network, 
                                card_sub_type=configed.card_sub_type,
                                payment_method=configed.payment_method,
                                to_us_charges=configed.to_provide_charges,
                                sa_provided=True
                            )
                            message = 'Cashfree Payment Getway configed activated successfully.'
                        else:
                            configed_data = AdCfPgConfiged.objects.filter(card_type=configed.card_type, card_network=configed.card_network, card_sub_type=configed.card_sub_type)
                            for data in configed_data:
                                data.is_deactive = False
                                data.sa_provided=True
                                data.save()
                            configed.is_deactive = False
                            configed.save()
                            message = 'Cashfree Payment Getway configed activated successfully.'

                    else:
                        if not AdCfPgConfiged.objects.filter(card_type=configed.card_type, card_network=configed.card_network, card_sub_type=configed.card_sub_type):
                            AdCfPgConfiged.objects.create(
                                card_type=configed.card_type, 
                                card_network=configed.card_network, 
                                card_sub_type=configed.card_sub_type,
                                payment_method=configed.payment_method,
                                to_us_charges=configed.to_provide_charges,
                                sa_provided=True
                            )
                        configed.is_deactive = False
                        configed.save()
                        message = 'Cashfree Payment Getway configed activated successfully.'
            else:
                # Handle case when charges are provided
                try:
                    to_us_charges = json.loads(to_us_charges)
                    to_us_charges['charge_type'] = charge_type
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON format for to_us_charges.'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    to_provide_charges = json.loads(to_provide_charges)
                    to_provide_charges['charge_type'] = charge_type
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON format for to_provide_charges.'}, status=status.HTTP_400_BAD_REQUEST)

                # Update category charges
                configed.to_us_charges = to_us_charges
                configed.to_provide_charges = to_provide_charges
                configed.save()

                admin_configed = AdCfPgConfiged.objects.filter(is_deleted=False, card_type=configed.card_type, card_network=configed.card_network, card_sub_type=configed.card_sub_type)
                if admin_configed:
                    for data in admin_configed:
                        data. to_us_charges=configed.to_provide_charges
                        data.save()

            # Return success response
            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except SaService.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except ServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except SaPgConfiged.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Cashfree Payment Getway configed does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_phonepe_pg_configed(self, request):
        # Extract request data
        ss_id = request.data.get('ss_id')
        sp_id = request.data.get('sp_id')
        to_us_charges = request.data.get('to_us_charges')
        to_provide_charges = request.data.get('to_provide_charges')
        charge_type = request.data.get('charge_type')
        message = 'Phonepe Payment getway configed updated successfully.'

        # Validate required fields
        if not ss_id:
            return Response({'status': 'fail', 'message': 'ss_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not sp_id:
            return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ss_id.isdigit():
            return Response({'status': 'fail', 'message': 'ss_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve service and related objects
            service_provider = ServiceProvider.objects.filter(sp_id=sp_id).first()
            service = SaService.objects.get(service_id=service_provider.service_id.service_id)
            configed = SaPhonePePgConfiged.objects.get(ss_id=ss_id)
            print('configed', configed)
            # Ensure service is global
            if not service.is_global:
                return Response({'status': 'fail', 'message': 'The service is not global.'}, status=status.HTTP_400_BAD_REQUEST)

            # Handle charges and category activation/deactivation
            if not to_us_charges and not to_provide_charges:
                # Handle case when charges are not provided
                if service_provider.is_deactive and service.is_deactive:
                    if not configed.to_us_charges or not configed.to_provide_charges:
                        return Response({
                            'status': 'fail',
                            'message': 'The service and service provider are currently active. Please configure charges before proceeding.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    if not configed.to_us_charges or not configed.to_provide_charges:
                        return Response({
                            'status': 'fail',
                            'message': 'The service and service provider are currently active. Please configure charges before proceeding.'
                        }, status=status.HTTP_400_BAD_REQUEST)

                # Handle category deactivation
                if configed.is_deactive == False:
                    configed.is_deactive = True
                    configed.save()
                    # Deactivate all related admin categories
                    admin_configed = PhonePeConfiged.objects.filter(is_deleted=False, card_type=configed.card_type, payment_method=configed.payment_method)
                    print('admin_configed', admin_configed)
                    for confi in admin_configed:
                        confi.is_deactive = True
                        confi.sa_provided = False
                        confi.save()
                    message = 'Phonepe Payment Getway configed deactivated successfully.'
                else:
                    # Handle category activation
                    if service_provider.is_deactive == False and service.is_deactive == False:
                        if not PhonePeConfiged.objects.filter(card_type=configed.card_type, payment_method=configed.payment_method):
                            PhonePeConfiged.objects.create(
                                card_type=configed.card_type, 
                                card_network=configed.card_network, 
                                card_sub_type=configed.card_sub_type,
                                payment_method=configed.payment_method,
                                to_us_charges=configed.to_provide_charges,
                                sa_provided=True
                            )
                            message = 'Phonepe Payment Getway configed activated successfully.'
                        else:
                            configed_data = PhonePeConfiged.objects.filter(card_type=configed.card_type, payment_method=configed.payment_method)
                            for data in configed_data:
                                data.to_us_charges=configed.to_provide_charges
                                data.sa_provided=True
                                data.save()
                            configed.is_deactive = False
                            configed.save()
                            message = 'Phonepe Payment Getway configed activated successfully.'

                    else:
                        if not PhonePeConfiged.objects.filter(card_type=configed.card_type, payment_method=configed.payment_method):
                            PhonePeConfiged.objects.create(
                                card_type=configed.card_type, 
                                card_network=configed.card_network, 
                                card_sub_type=configed.card_sub_type,
                                payment_method=configed.payment_method,
                                to_us_charges=configed.to_provide_charges,
                                sa_provided=True
                            )
                        configed.is_deactive = False
                        configed.save()
                        message = 'Phonepe Payment Getway configed activated successfully.'
            else:
                # Handle case when charges are provided
                try:
                    to_us_charges = json.loads(to_us_charges)
                    to_us_charges['charge_type'] = charge_type
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON format for to_us_charges.'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    to_provide_charges = json.loads(to_provide_charges)
                    to_provide_charges['charge_type'] = charge_type
                except json.JSONDecodeError:
                    return Response({'status': 'fail', 'message': 'Invalid JSON format for to_provide_charges.'}, status=status.HTTP_400_BAD_REQUEST)

                # Update category charges
                configed.to_us_charges = to_us_charges
                configed.to_provide_charges = to_provide_charges
                configed.save()

                admin_configed = PhonePeConfiged.objects.filter(is_deleted=False, card_type=configed.card_type, payment_method=configed.payment_method)
                if admin_configed:
                    for data in admin_configed:
                        data.to_us_charges=configed.to_provide_charges
                        data.save()

            # Return success response
            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except SaService.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except ServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except SaPhonePePgConfiged.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Phonepe Payment Getway configed does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)