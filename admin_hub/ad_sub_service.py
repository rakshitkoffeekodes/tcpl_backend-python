from .views import *


class UpdateServiceCategoryCharges(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request):
        try:
            if 'sp_id' in request.data and 'page_number' in request.data or 'page_size' in request.data:
                if request.data.get('sp_id') == '8':
                    return self.fetch_bbps_data(request)
                elif request.data.get('sp_id') == '4':
                    return self.fetch_recharge_data(request)
                elif request.data.get('sp_id') == '9':
                    return self.fetch_configed_data(request)
                elif request.data.get('sp_id') == '10':
                    return self.fetch_phonepe_configed_data(request)
                else:
                    return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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

            all_categories = BBPSBillerCategory.objects.filter(is_deleted=False).order_by('-pk')

            if ss_id:
                all_categories = all_categories.filter(ss_id=ss_id).order_by('-pk')

            if search != '':
                all_categories = all_categories.filter(Q(ss_name__icontains=search)).order_by('-pk')

            paginator = Paginator(all_categories, page_size)
            categories = paginator.page(page_number)
            serializer = BBPSBillerCategorySerializer(categories, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data,
                'is_configed': False,
                'sub_service': 'bbps'
            }
            return Response({'status': 'success', 'message': 'BBPS Biller Categories', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_recharge_data(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        ss_id = request.data.get('ss_id', None)
        search = request.data.get('search', '')
        filter_by = request.data.get('filter_by')

        try:
            if not page_number:
                return Response({'status': 'fail', 'message': 'page_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not page_size:
                return Response({'status': 'fail', 'message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not filter_by: return Response({'status': 'fail', 'message': 'filter_by is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(page_number):
                return Response({'status': 'fail', 'message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(page_size):
                return Response({'status': 'fail', 'message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            page_number = int(page_number)
            page_size = int(page_size)

            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)

            all_oprators = Oprators.objects.filter(is_deleted=False, sa_provided=True).order_by('-pk')

            if filter_by != 'ALL':
                all_oprators = all_oprators.filter(recharge_type=filter_by)

            if ss_id:
                all_oprators = all_oprators.filter(ss_id=ss_id).order_by('-pk')
            
            if search != '':
                all_oprators = all_oprators.filter(Q(ss_name__icontains=search) | Q(operator_code__icontains=search) | Q(operator_type__icontains=search)).order_by('-pk')

            paginator = Paginator(all_oprators, page_size)
            oprators = paginator.page(page_number)
            serializer = AdOperatorSerializer(oprators, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data,
                'is_configed': False,
                'sub_service': 'recharge'
            }
            return Response({'status': 'success', 'message': 'Recharge Oprators fetch successfully', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_configed_data(self, request):
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

            all_configeds = AdCfPgConfiged.objects.filter(is_deleted=False).order_by('-pk')

            if ss_id:
                all_configeds = all_configeds.filter(ss_id=ss_id).order_by('-pk')
            
            if search != '':
                all_configeds = all_configeds.filter(Q(card_type__icontains=search) | Q(card_network__icontains=search) | Q(card_sub_type__icontains=search)).order_by('-pk')

            paginator = Paginator(all_configeds, page_size)
            configeds = paginator.page(page_number)
            serializer = AdCfPgConfigedSerializer(configeds, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data,
                'is_configed': True,
                'sub_service': 'cashfree_pg'
            }
            return Response({'status': 'success', 'message': 'Cashfree Payment Getway configed fetch successfully', 'data': data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_phonepe_configed_data(self, request):
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

            all_configeds = PhonePeConfiged.objects.filter(is_deleted=False).order_by('-pk')

            if ss_id:
                all_configeds = all_configeds.filter(ss_id=ss_id).order_by('-pk')
            
            if search != '':
                all_configeds = all_configeds.filter(Q(card_type__icontains=search) | Q(card_network__icontains=search) | Q(card_sub_type__icontains=search)).order_by('-pk')

            paginator = Paginator(all_configeds, page_size)
            configeds = paginator.page(page_number)
            serializer = PhonePeConfigedSerializer(configeds, many=True)
            data = {
                'total_pages': paginator.num_pages,
                'current_page': page_number,
                'total_items': paginator.count,
                'results': serializer.data,
                'is_configed': True,
                'sub_service': 'phonepe_pg'
            }
            return Response({'status': 'success', 'message': 'Phonepe Payment Getway configed fetch successfully', 'data': data}, status=status.HTTP_200_OK)

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
        ss_id = request.data.get('ss_id')
        sp_id = request.data.get('sp_id')
        sd_charges = request.data.get('sd_charges', None)
        md_charges = request.data.get('md_charges', None)
        dt_charges = request.data.get('dt_charges', None)
        rt_charges = request.data.get('rt_charges', None)
        charge_type = request.data.get('charge_type', None)
        rate_type = request.data.get('rate_type', None)
        commission_type = request.data.get('commission_type', None)
        message = 'BBPS Category updated successfully.'

        try:
            if not ss_id:
                return Response({'status': 'fail', 'message': 'ss_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not sp_id:
                return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(ss_id):
                return Response({'status': 'fail', 'message': 'ss_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            service_provider = AdServiceProvider.objects.filter(sp_id=sp_id).first()
            service = AdService.objects.get(service_id=service_provider.service.service_id)
            bbps_category = BBPSBillerCategory.objects.get(ss_id=ss_id)

            if not service.is_global:
                return Response({'status': 'fail', 'message': 'The service is not global.'}, status=status.HTTP_400_BAD_REQUEST)

            if not sd_charges and not md_charges and not dt_charges and not rt_charges:
                if not (bbps_category.sd_charges and bbps_category.md_charges and 
                        bbps_category.dt_charges and bbps_category.rt_charges):
                    return Response({
                        'status': 'fail',
                        'message': 'The service and service provider are active. Please configure charges before proceeding.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not bbps_category.is_deactive:
                    bbps_category.is_deactive = True
                    bbps_category.save()
                    message = 'BBPS category deactivated successfully.'
                else:
                    bbps_category.is_deactive = False
                    bbps_category.save()
                    message = 'BBPS category activated successfully.'
            else:
                def parse_charges(charges, charge_type, rate_type, commission_type):
                    if charges:
                        try:
                            charges = json.loads(charges)
                            if not isinstance(charges, dict):
                                raise ValidationError("Invalid format for charges. Must be a JSON object.")
                            charges.update({
                                'charge_type': charge_type,
                                'is_slab': False,
                                'maximum': 0.0,
                                'minimum': 0.0,
                                'rate_type': rate_type,
                                'commission_type': commission_type,
                                'effective_wallet': 'commission_wallet'
                            })
                            return charges
                        except json.JSONDecodeError:
                            raise ValidationError("Invalid JSON format for charges.")
                    return None

                sd_charges = parse_charges(sd_charges, charge_type, rate_type, commission_type)
                md_charges = parse_charges(md_charges, charge_type, rate_type, commission_type)
                dt_charges = parse_charges(dt_charges, charge_type, rate_type, commission_type)
                rt_charges = parse_charges(rt_charges, charge_type, rate_type, commission_type)

                if not bbps_category.sd_charges and not bbps_category.md_charges and \
                not bbps_category.dt_charges and not bbps_category.rt_charges:
                    message = 'BBPS Category added successfully.'

                bbps_category.sd_charges = [sd_charges] if sd_charges else bbps_category.sd_charges
                bbps_category.md_charges = [md_charges] if md_charges else bbps_category.md_charges
                bbps_category.dt_charges = [dt_charges] if dt_charges else bbps_category.dt_charges
                bbps_category.rt_charges = [rt_charges] if rt_charges else bbps_category.rt_charges
                bbps_category.save()

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def update_recharge_category(self, request):
        ss_id = request.data.get('ss_id')
        sp_id = request.data.get('sp_id')
        sd_charges = request.data.get('sd_charges', None)
        md_charges = request.data.get('md_charges', None)
        dt_charges = request.data.get('dt_charges', None)
        rt_charges = request.data.get('rt_charges', None)
        charge_type = request.data.get('charge_type', None)
        rate_type = request.data.get('rate_type', None)
        commission_type = request.data.get('commission_type', None)
        message = 'Recharge Operator updated successfully.'

        try:
            if not ss_id:
                return Response({'status': 'fail', 'message': 'ss_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not sp_id:
                return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(ss_id):
                return Response({'status': 'fail', 'message': 'ss_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            service_provider = AdServiceProvider.objects.filter(sp_id=sp_id).first()
            service = AdService.objects.get(service_id=service_provider.service.service_id)
            operators = Oprators.objects.get(ss_id=ss_id)

            if not service.is_global:
                return Response({'status': 'fail', 'message': 'The service is not global.'}, status=status.HTTP_400_BAD_REQUEST)

            if not sd_charges and not md_charges and not dt_charges and not rt_charges:
                if not (operators.sd_charges and operators.md_charges and 
                        operators.dt_charges and operators.rt_charges):
                    return Response({
                        'status': 'fail',
                        'message': 'The service and service provider are active. Please configure charges before proceeding.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not operators.is_deactive:
                    operators.is_deactive = True
                    operators.save()
                    message = 'Recharge Operator deactivated successfully.'
                else:
                    operators.is_deactive = False
                    operators.save()
                    message = 'Recharge Operator activated successfully.'
            else:
                def parse_charges(charges, charge_type, rate_type, commission_type):
                    if charges:
                        try:
                            charges = json.loads(charges)
                            if not isinstance(charges, dict):
                                raise ValidationError("Invalid format for charges. Must be a JSON object.")
                            charges.update({
                                'charge_type': charge_type,
                                'is_slab': False,
                                'maximum': 0.0,
                                'minimum': 0.0,
                                'rate_type': rate_type,
                                'commission_type': commission_type,
                                'effective_wallet': 'commission_wallet'
                            })
                            return charges
                        except json.JSONDecodeError:
                            raise ValidationError("Invalid JSON format for charges.")
                    return None

                sd_charges = parse_charges(sd_charges, charge_type, rate_type, commission_type)
                md_charges = parse_charges(md_charges, charge_type, rate_type, commission_type)
                dt_charges = parse_charges(dt_charges, charge_type, rate_type, commission_type)
                rt_charges = parse_charges(rt_charges, charge_type, rate_type, commission_type)

                if not operators.sd_charges and not operators.md_charges and \
                not operators.dt_charges and not operators.rt_charges:
                    message = 'Recharge Operator added successfully.'

                operators.sd_charges = [sd_charges] if sd_charges else operators.sd_charges
                operators.md_charges = [md_charges] if md_charges else operators.md_charges
                operators.dt_charges = [dt_charges] if dt_charges else operators.dt_charges
                operators.rt_charges = [rt_charges] if rt_charges else operators.rt_charges
                operators.save()

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_cf_pg_configed(self, request):
        ss_id = request.data.get('ss_id')
        sp_id = request.data.get('sp_id')
        sd_charges = request.data.get('sd_charges', None)
        md_charges = request.data.get('md_charges', None)
        dt_charges = request.data.get('dt_charges', None)
        rt_charges = request.data.get('rt_charges', None)
        charge_type = request.data.get('charge_type', None)
        rate_type = request.data.get('rate_type', None)
        holding_hours = request.data.get('holding_hours', None)
        commission_type = request.data.get('commission_type', None)
        message = 'Cashfree Payment Getway configed updated successfully.'

        try:
            if not ss_id:
                return Response({'status': 'fail', 'message': 'ss_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not sp_id:
                return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(ss_id):
                return Response({'status': 'fail', 'message': 'ss_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            service_provider = AdServiceProvider.objects.filter(sp_id=sp_id).first()
            service = AdService.objects.get(service_id=service_provider.service.service_id)
            configeds = AdCfPgConfiged.objects.get(ss_id=ss_id)

            if not service.is_global:
                return Response({'status': 'fail', 'message': 'The service is not global.'}, status=status.HTTP_400_BAD_REQUEST)

            if not sd_charges and not md_charges and not dt_charges and not rt_charges:
                if not (configeds.sd_charges and configeds.md_charges and 
                        configeds.dt_charges and configeds.rt_charges):
                    return Response({
                        'status': 'fail',
                        'message': 'The service and service provider are active. Please configure charges before proceeding.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not configeds.is_deactive:
                    configeds.is_deactive = True
                    configeds.save()
                    message = 'Cashfree Payment Getway configed deactivated successfully.'
                else:
                    configeds.is_deactive = False
                    configeds.save()
                    message = 'Cashfree Payment Getway configed activated successfully.'
            else:
                def parse_charges(charges, charge_type, rate_type, commission_type):
                    if charges:
                        try:
                            charges = json.loads(charges)
                            if not isinstance(charges, dict):
                                raise ValidationError("Invalid format for charges. Must be a JSON object.")
                            charges.update({
                                'charge_type': charge_type,
                                'is_slab': False,
                                'maximum': 0.0,
                                'minimum': 0.0,
                                'rate_type': rate_type,
                                'commission_type': commission_type,
                                'effective_wallet': 'commission_wallet',
                                'holding_hours': holding_hours
                            })
                            return charges
                        except json.JSONDecodeError:
                            raise ValidationError("Invalid JSON format for charges.")
                    return None

                sd_charges = parse_charges(sd_charges, charge_type, rate_type, commission_type)
                md_charges = parse_charges(md_charges, charge_type, rate_type, commission_type)
                dt_charges = parse_charges(dt_charges, charge_type, rate_type, commission_type)
                rt_charges = parse_charges(rt_charges, charge_type, rate_type, commission_type)

                if not configeds.sd_charges and not configeds.md_charges and \
                not configeds.dt_charges and not configeds.rt_charges:
                    message = 'Cashfree Payment Getway configed added successfully.'

                configeds.sd_charges = [sd_charges] if sd_charges else configeds.sd_charges
                configeds.md_charges = [md_charges] if md_charges else configeds.md_charges
                configeds.dt_charges = [dt_charges] if dt_charges else configeds.dt_charges
                configeds.rt_charges = [rt_charges] if rt_charges else configeds.rt_charges
                configeds.save()

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_phonepe_pg_configed(self, request):
        ss_id = request.data.get('ss_id')
        sp_id = request.data.get('sp_id')
        sd_charges = request.data.get('sd_charges', None)
        md_charges = request.data.get('md_charges', None)
        dt_charges = request.data.get('dt_charges', None)
        rt_charges = request.data.get('rt_charges', None)
        charge_type = request.data.get('charge_type', None)
        rate_type = request.data.get('rate_type', None)
        commission_type = request.data.get('commission_type', None)
        message = 'Phonepe Payment Getway configed updated successfully.'

        try:
            if not ss_id:
                return Response({'status': 'fail', 'message': 'ss_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not sp_id:
                return Response({'status': 'fail', 'message': 'sp_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(ss_id):
                return Response({'status': 'fail', 'message': 'ss_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            service_provider = AdServiceProvider.objects.filter(sp_id=sp_id).first()
            service = AdService.objects.get(service_id=service_provider.service.service_id)
            configeds = PhonePeConfiged.objects.get(ss_id=ss_id)

            if not service.is_global:
                return Response({'status': 'fail', 'message': 'The service is not global.'}, status=status.HTTP_400_BAD_REQUEST)

            if not sd_charges and not md_charges and not dt_charges and not rt_charges:
                if not (configeds.sd_charges and configeds.md_charges and 
                        configeds.dt_charges and configeds.rt_charges):
                    return Response({
                        'status': 'fail',
                        'message': 'The service and service provider are active. Please configure charges before proceeding.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if not configeds.is_deactive:
                    configeds.is_deactive = True
                    configeds.save()
                    message = 'Phonepe Payment Getway configed deactivated successfully.'
                else:
                    configeds.is_deactive = False
                    configeds.save()
                    message = 'Phonepe Payment Getway configed activated successfully.'
            else:
                def parse_charges(charges, charge_type, rate_type, commission_type):
                    if charges:
                        try:
                            charges = json.loads(charges)
                            if not isinstance(charges, dict):
                                raise ValidationError("Invalid format for charges. Must be a JSON object.")
                            charges.update({
                                'charge_type': charge_type,
                                'is_slab': False,
                                'maximum': 0.0,
                                'minimum': 0.0,
                                'rate_type': rate_type,
                                'commission_type': commission_type,
                                'effective_wallet': 'commission_wallet'
                            })
                            return charges
                        except json.JSONDecodeError:
                            raise ValidationError("Invalid JSON format for charges.")
                    return None

                sd_charges = parse_charges(sd_charges, charge_type, rate_type, commission_type)
                md_charges = parse_charges(md_charges, charge_type, rate_type, commission_type)
                dt_charges = parse_charges(dt_charges, charge_type, rate_type, commission_type)
                rt_charges = parse_charges(rt_charges, charge_type, rate_type, commission_type)

                if not configeds.sd_charges and not configeds.md_charges and \
                not configeds.dt_charges and not configeds.rt_charges:
                    message = 'Phonepe Payment Getway configed added successfully.'

                configeds.sd_charges = [sd_charges] if sd_charges else configeds.sd_charges
                configeds.md_charges = [md_charges] if md_charges else configeds.md_charges
                configeds.dt_charges = [dt_charges] if dt_charges else configeds.dt_charges
                configeds.rt_charges = [rt_charges] if rt_charges else configeds.rt_charges
                configeds.save()

            return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)

        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service provider does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)