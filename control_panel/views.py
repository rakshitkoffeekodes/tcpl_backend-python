from datetime import datetime, timedelta
from email import header
import json
import os
from pydoc import doc
from xml.dom.minidom import Document
from django.forms import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg import openapi
from django.db import transaction
from django.utils.dateparse import parse_date
from tcpl_backend import settings
# from tcpl_backend.web_portal import admin
from .pdf_gerate import merge_files_from_urls
from web_portal.models import SaUserActivity
from admin_hub.models import PortalUser, AdService, AdCharges, AdHSNSAC, AdServiceProvider, PortalUserCharges, PortalUserDetails,PortalUserWallet, DistributorHierarchy, PortalUserLoginLogs, BBPSBillerCategory, Oprators, GlTrn, WalletTrn, AdCfPgConfiged, PhonePeConfiged
from .models import HSNSAC, Admin, AdminAgreement, AdminService, Charges, FeesType, Product, ProductCategory, SaService, ServiceProvider, expense,RequiredDocumentList, CustomUser, AdminBankDetails,AdminFundRequest , BankDetails, SaBBPSBillerCategory, SaOprators, SaPgConfiged, SaPhonePePgConfiged, SaOtherCharges
from .serializers import AdminAgreementSerializer, AdminSerializer, AdminServiceSerializer, ChargesSerializer, CitySerializer,  ExpenseSerializer, FeesTypeSerializer, HSNSACSerializer, ProductCategorySerializer, ProductSerializer, SaServiceSerializer, ServiceProviderSerializer, AdminFundRequestSerializer,DocumentListSerializer, StateSerializer, BBPSBillerCategorySerializer, RechargeOperatorSerializer, CfPgConfigedSerializer, PhonePePgConfigedSerializer, SaOtherChargesSerializer
from tcpl_backend.custom_jwt_auth import get_tokens_for_user, IsAdmin, IsSuperAdmin, IsRetailer, IsDistributor, CustomJWTAuthentication
from rest_framework.pagination import PageNumberPagination  # Importing pagination support.
from django.db.models import Q 
from django.core.paginator import Paginator,EmptyPage
# from django.template.loader import render_to_string
from django.http import HttpResponse
from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa
import requests
from rest_framework.response import Response
from django.http import JsonResponse
import uuid
from .models import State,City
from rest_framework.permissions import IsAuthenticated, AllowAny
from validation.custom_validation import isboolean, isfloat, isnumber 
import csv
from io import StringIO
import json
from django.utils import timezone
from django.forms.models import model_to_dict
from validation.custom_validation import *
import base64
from decimal import Decimal
from .admin_provided_data import *
from dotenv import set_key, load_dotenv
from admin_hub.utilies import add_user_activity
# from tcpl_backend.settings import x_client_id,x_client_secret

# from django.template.loader import render_to_string


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


class FeesTypeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_data(request)
            elif 'ft_name' in request.data and 'ft_type' in request.data:
                return self.create_fee_type(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_fee_type(self, request):
        try:
            with transaction.atomic():
                serializer = FeesTypeSerializer(data=request.data)
                if serializer.is_valid():
                    fee_type = serializer.save(created_by=request.user)
                    action =  'create'
                    description =  f'Created new AboutUs with ID {fee_type.pk}'
                    # Log the activity
                    activity = SaUserActivity(
                        table_id=fee_type.pk,  # ID of the AboutUs entry
                        table_name='FeesType',  # Name of the table
                        ua_action=action,  # Action performed
                        ua_description=description,  # Action description
                        created_by=request.user  # Current user performing the action
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Fee Type Created Successfully'
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
            fees_type_id = request.data.get('fees_type_id', None)
            if fees_type_id:
                try:
                    fee_type = FeesType.objects.get(ft_id=fees_type_id,is_deleted=False)
                    serializer = FeesTypeSerializer(fee_type, context={'request': request})
                    response_data = {
                        'status': 'success',
                        'message': 'Fee Type Data',
                        'data': serializer.data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                except FeesType.DoesNotExist:
                    response_data = {
                        'status': 'fail',
                        'message': "Fee Type not found.",
                        'data': {}
                    }
                    return Response(response_data, status=status.HTTP_404_NOT_FOUND)
            else:
                page_size = request.data.get('page_size')
                page = request.data.get('page_number')
                filter_field = request.data.get('filter_field', None)
                filter_value = request.data.get('filter_value', None)
                order_by = request.data.get('order_by',"ascending")
                start_date = request.data.get('start_date',None)
                end_date = request.data.get('end_date',None)
                

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

                paginator = PageNumberPagination()
                paginator.page_size = int(page_size)
                paginator.page_size_query_param = 'page_size'
                paginator.max_page_size = 100

                queryset = FeesType.objects.filter(is_deleted=False).order_by('-ft_id')
                if start_date and end_date:
                            start_date_parsed = parse_date(start_date)
                            end_date_parsed = parse_date(end_date)
                            queryset = queryset.filter(created_at__range=[start_date_parsed, end_date_parsed + timedelta(days=1)])
                if filter_field:
                        queryset = queryset.order_by(f'{filter_field}')
                        
                        
                        if order_by == "descending":
                            queryset = queryset.order_by(f'-{filter_field}')
                        if filter_value:
                            filter_kwargs = {filter_field: filter_value}
                            queryset = queryset.filter(**filter_kwargs)
                search_query = request.data.get('search', None)
                if search_query:
                    queryset = queryset.filter(
                        Q(name__icontains=search_query) |
                        Q(type__icontains=search_query)
                    )

                result_page = paginator.paginate_queryset(queryset, request)
                if result_page is not None:
                    serializer = FeesTypeSerializer(result_page, many=True, context={'request': request})
                    paginated_response_data = {
                        'total_pages': paginator.page.paginator.num_pages,
                        'current_page': paginator.page.number,
                        'total_items': paginator.page.paginator.count,
                        'results': serializer.data
                    }
                    response_data = {
                        'status': 'success',
                        'message': 'Fee Type Data',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                serializer = FeesTypeSerializer(queryset, many=True, context={'request': request})
                response_data = {
                    'status': 'success',
                    'message': 'Fee Type Data',
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
        fees_type_id = request.data.get("fees_type_id")
        ft_type = request.data.get("ft_type")

        if not fees_type_id or not ft_type:
            response_data = {
                'status': 'fail',
                'message': "fees_type_id and ft_type are required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            fee_type = FeesType.objects.get(ft_id=fees_type_id,is_deleted=False)
            fee_type.ft_type = ft_type
            fee_type.updated_at = datetime.now()
            fee_type.save()
            action =  'update'
            description =   f'Updated AboutUs with ID {fee_type.pk}'
            # Log the activity
            activity = SaUserActivity(
                table_id=fee_type.pk,  # ID of the AboutUs entry
                table_name='FeesType',  # Name of the table
                ua_action=action,  # Action performed
                ua_description=description,  # Action description
                created_by=request.user  # Current user performing the action
            )
            activity.save()

            response_data = {
                'status': 'success',
                'message': 'Fee Type Updated Successfully'
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except FeesType.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': "Fee Type not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    def delete(self, request):
        fees_type_id = request.data.get("fees_type_id")
        if not fees_type_id:
            response_data = {
                'status': 'fail',
                'message': "fees_type_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            fee_type = FeesType.objects.get(ft_id=fees_type_id,is_deleted=False)
            fee_type.is_deleted =True
            fee_type.save()
            response_data = {
                'status': 'success',
                'message': 'Fee Type Deleted Successfully'
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except FeesType.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': "Fee Type not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SaServiceAPIView(APIView):
    
    permission_classes = [IsAuthenticated]
            
    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_service(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
        
    def fetch_service(self, request):
        try:
            page_size = request.data.get('page_size', 10)  # Number of items per page
            page = request.data.get('page_number', 1)  # Default to page 1 if not provided
            
            service_id = request.data.get('service_id', None)
            search_query = request.data.get('search', None)
            
            queryset = SaService.objects.filter(is_deleted=False).order_by('-pk')
            
            if service_id:
                queryset = queryset.filter(service_id=service_id)
            
            if search_query:
                queryset = queryset.filter(
                    Q(service_name__icontains=search_query) |
                    Q(description__icontains=search_query)
                    # Add more filters based on your requirements
                )
            
            paginator = Paginator(queryset, page_size)
            if not queryset.exists():
                paginated_response_data = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }
                response_data = {
                    'status': 'fail',
                    'message': 'Service Data not found.',
                    'data': paginated_response_data
                }
                return Response(response_data, status=status.HTTP_200_OK)
            
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = SaServiceSerializer(page_obj.object_list, many=True, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted","updated_by", "created_by"]})
            
            response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': serializer.data
            }
            
            response_data = {
                'status': 'success',
                'message': 'Service Data',
                'data': response_data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except SaService.DoesNotExist as e:
            response_error = {
                'status': 'fail',
                'message': str(e),
                'data': {}
            }
            return Response(response_error, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            response_error = {
                'status': 'error',
                'message': 'Internal server error',
                'data': str(e)
            }
            return Response(response_error, status=status.HTTP_500_INTERNAL_SERVER_ERROR)   

    def put(self, request):
        service_id = request.data.get('service_id')
        description = request.data.get('description', None)

        try:
            if not service_id:
                return Response({'status': 'fail', 'message': 'Service ID is required'}, status=status.HTTP_400_BAD_REQUEST)

            service = SaService.objects.get(service_id=service_id)

            if not description and description is not None:
                return Response({'status': 'fail', 'message': 'Description is required'}, status=status.HTTP_400_BAD_REQUEST)

            if not description:
                if service.is_global == True:
                    if service.service_name == 'BBPS':
                        category = SaBBPSBillerCategory.objects.filter(is_deactive=False)
                        if not category.exists():
                            return Response({'status': 'fail', 'message': 'Please update the category before deactivating the service.'}, status=status.HTTP_400_BAD_REQUEST)
                if service.is_deactive:
                    # Activate service
                    service.is_deactive = False
                    service.updated_at = datetime.now()
                    service_provider = ServiceProvider.objects.filter(service_id=service.service_id)
                    for provider in service_provider:
                        if provider:
                            provider.is_deactive = False
                            provider.save()

                    portal_user_service = AdService.objects.filter(service_name=service.service_name).first()
                    if portal_user_service:
                        portal_user_service.is_deactive = False
                        portal_user_service.updated_at = datetime.now()
                        portal_user_service.save()

                    portal_user_service_provider = AdServiceProvider.objects.filter(service=portal_user_service)
                    for provider in portal_user_service_provider:
                        if provider:
                            provider.is_deactive = False
                            provider.save()

                        all_portal_user_charges = PortalUserCharges.objects.filter(sp=provider)
                        for portal_user_charge in all_portal_user_charges:
                            portal_user_charge.is_deactive = False
                            portal_user_charge.updated_at = datetime.now()
                            portal_user_charge.save()

                    service.save()
                    return Response({'status': 'success', 'message': 'Service Activated Successfully.'}, status=status.HTTP_200_OK)

                elif not service.is_deleted:
                    # Deactivate service
                    service.is_deactive = True
                    service.updated_at = datetime.now()
                    service_provider = ServiceProvider.objects.filter(service_id=service)
                    for provider in service_provider:
                        if provider:
                            provider.is_deactive = True
                            provider.save()

                    portal_user_service = AdService.objects.filter(service_name=service.service_name).first()
                    if portal_user_service:
                        portal_user_service.is_deactive = True
                        portal_user_service.updated_at = datetime.now()
                        portal_user_service.save()

                    portal_user_service_provider = AdServiceProvider.objects.filter(service=portal_user_service)
                    for provider in portal_user_service_provider:
                        if provider:
                            provider.is_deactive = True
                            provider.save()

                        all_portal_user_charges = PortalUserCharges.objects.filter(sp=provider)
                        for portal_user_charge in all_portal_user_charges:
                            portal_user_charge.is_deactive = True
                            portal_user_charge.updated_at = datetime.now()
                            portal_user_charge.save()

                    service.save()
                    return Response({'status': 'success', 'message': 'Service Deactivated Successfully.'}, status=status.HTTP_200_OK)

            # Update service description
            service.description = description if description else service.description
            service.updated_at = datetime.now()
            service.updated_by = request.user
            service.save()

            activity = SaUserActivity(
                table_id=service.pk,
                table_name='SaService',
                ua_action='update',
                ua_description=f'Updated Service "{service.service_name}"',
                created_by=request.user,
                request_data=request.data,
            )
            activity.save()

            return Response({'status': 'success', 'message': 'Service Updated Successfully'}, status=status.HTTP_200_OK)

        except SaService.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
   
    def delete(self, request):
        try:
            with transaction.atomic():
                savepoint = transaction.savepoint()
                service_id = request.data.get('service_id')
                if not service_id:
                    response_data = {
                        'status': 'fail',
                        'message': 'ID is required'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                service_data = SaService.objects.get(service_id=service_id)
                if service_data.is_deleted:
                    response_data = {
                        'status': 'success',
                        'message': 'Already, this service has been Deleted'
                    }
                else:
                    service_data.is_deleted = True
                    service_data.is_deactive = True
                    service_data.save()

                    # Log the deletion activity if needed
                    activity = SaUserActivity(
                        table_id=service_data.pk,
                        table_name='SaService',
                        ua_action='delete',
                        ua_description=f'deleted Service "{service_data.service_name}"',
                        created_by=request.user,
                        request_data=request.data,  # Request data
                    )
                    activity.save()
                    transaction.savepoint_commit(savepoint)
                    response_data = {
                        'status': 'success',
                        'message': 'Service Deleted Successfully'
                    }
                return Response(response_data, status=status.HTTP_200_OK)

        except SaService.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': 'Service not found'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    
class ServiceProviderAPIView(APIView):

    permission_classes = [IsAuthenticated]

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
                
            queryset = ServiceProvider.objects.filter(is_deleted=False)

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
            for provider in page_obj:
                # Fetch related charges (assuming 'to_provide' charges category)
                to_us_charges = Charges.objects.filter(service_provider=provider)
                if len(to_us_charges) > 0:
                    charge_serializer = ChargesSerializer(to_us_charges, many=True, context={'request': request})
                    charge_type = to_us_charges.first().charges_type if to_us_charges.exists() else None
                    charge_serializer_update = charge_serializer.data
                    for charge in charge_serializer_update:
                        charge.pop("created_at")
                        charge.pop("updated_at")
                        charge.pop("is_deactive")
                        charge.pop("is_deleted")

                        if charge.get("minimum") == "0.00" and charge.get("maximum") == "0.00":
                            charge.update({"is_slab": False})
                        else:
                            charge.update({"is_slab": True})
                else:
                    charge_serializer_update = []
                    charge_type = None
                service_name = SaService.objects.get(service_id=provider.service_id.service_id)
                service_provider_data.append({
                    'sp_id': provider.sp_id,
                    'service_id': service_name.service_id,
                    'service_name': service_name.service_name,
                    'service_nature': provider.service_nature,
                    'is_global': service_name.is_global,
                    'sp_name': provider.sp_name,
                    'label': provider.label,
                    'tds_rate': provider.tds_rate,
                    'tds_type': provider.tds_type,
                    'hsn_sac': provider.hsn_sac.hsnsac_id if provider.hsn_sac else None,
                    'hsn_sac_code': provider.hsn_sac.hsnsac_code if provider.hsn_sac else None,
                    'tax_rate': provider.hsn_sac.tax_rate if provider.hsn_sac else None,
                    'charge_type': charge_type,
                    'is_deactive': provider.is_deactive,
                    'charges_data': charge_serializer_update,
                    'is_table_config': provider.is_table_config,
                    'config_table_name': provider.config_table_name,
                    'credentials_json': provider.credentials_json,
                    'plateform_fee': provider.plateform_fee,
                    'plateform_fee_type': provider.plateform_fee_type,
                    'required_key': provider.required_key
                }) 
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
 
    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_service_provider(request)
            elif 'label' in request.data and 'sp_name' in request.data:
                return self.create_service_provider(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  
       
    def put(self, request):
        sp_id = request.data.get('sp_id')
        charges_type = request.data.get('charges_type', None)
        tds_rate = request.data.get('tds_rate', None)
        tds_type = request.data.get('tds_type', None)

        try:
            if not sp_id:
                return Response({'status': 'fail', 'message': 'Service ID is required'}, status=status.HTTP_400_BAD_REQUEST)

            service_provider = ServiceProvider.objects.get(sp_id=sp_id, is_deleted=False)

            if not charges_type and charges_type is not None:
                return Response({'status': 'fail', 'message': 'charges type is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not tds_rate and tds_rate is not None:
                return Response({'status': 'fail', 'message': 'tds rate is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not tds_type and tds_type is not None:
                return Response({'status': 'fail', 'message': 'tds type is required'}, status=status.HTTP_400_BAD_REQUEST)

            if not charges_type and not tds_rate and not tds_type:
                serivce_data = SaService.objects.get(service_id=service_provider.service_id.service_id)
                if serivce_data.is_global == True:
                    if serivce_data.service_name == 'BBPS':
                        category = SaBBPSBillerCategory.objects.filter(is_deactive=False)
                        if not category.exists():
                            return Response({'status': 'fail', 'message': 'Please update the category rate before activating the service provider.'}, status=status.HTTP_400_BAD_REQUEST)
                    elif serivce_data.service_name == 'Recharge':
                        category = SaOprators.objects.filter(is_deactive=False)
                        if not category.exists():
                            return Response({'status': 'fail', 'message': 'Please update the category rate before activating the service provider.'}, status=status.HTTP_400_BAD_REQUEST)
                else:    
                    # Check if AdCharges exists for the given sp_id
                    if not Charges.objects.filter(service_provider_id=sp_id).exists():
                        return Response(
                            {'status': 'fail', 'message': 'Charges data is required before activating the service provider.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                if service_provider.is_deactive:
                    service_provider.is_deactive = False
                    service_provider.updated_at = datetime.now()

                    admin_service = SaService.objects.filter(service_id=service_provider.service_id.service_id).first()
                    if admin_service:
                        admin_service.is_deactive = False
                        admin_service.save()

                    service_provider.save()
                    return Response({'status': 'success', 'message': 'Service Activated Successfully.'}, status=status.HTTP_200_OK)

                else:
                    # Deactivate service
                    service_provider.is_deactive = True
                    service_provider.updated_at = datetime.now()

                    portal_user_service = AdService.objects.get(service_id=service_provider.service_id.service_id)
                    if portal_user_service:
                        portal_user_service.is_deactive = True
                        portal_user_service.updated_at = datetime.now()
                        portal_user_service.save()

                    if portal_user_service.is_global and portal_user_service.service_name == 'BBPS':
                        # Deactivate all BBPSBillerCategory entries
                        BBPSBillerCategory.objects.filter(is_deactive=False, sa_provided=True).update(is_deactive=True, sa_provided=False, updated_at=datetime.now())

                    if portal_user_service.is_global and portal_user_service.service_name == 'Recharge':
                        # Deactivate all BBPSBillerCategory entries
                        Oprators.objects.filter(is_deactive=False, sa_provided=True).update(is_deactive=True, sa_provided=False, updated_at=datetime.now())

                    portal_user_service_provider = AdServiceProvider.objects.filter(sp_id=sp_id)  # sp_id changes done by divya
                    for provider in portal_user_service_provider:
                        if provider:
                            provider.is_deactive = True
                            provider.sa_provided=False
                            provider.save()

                        all_portal_user_charges = PortalUserCharges.objects.filter(sp=provider)
                        for portal_user_charge in all_portal_user_charges:
                            portal_user_charge.is_deactive = True
                            portal_user_charge.updated_at = datetime.now()
                            portal_user_charge.save()

                    service_provider.save()
                    return Response({'status': 'success', 'message': 'Service Deactivated Successfully.'}, status=status.HTTP_200_OK)
            else:
                if tds_rate:
                    tds_rate = float(tds_rate)
                if tds_rate and tds_rate < 0: return Response({'status': 'fail', 'message': 'TDS rate must be a positive number.'}, status=status.HTTP_400_BAD_REQUEST)
                if tds_rate and tds_rate > 100: return Response({'status': 'fail', 'message': 'TDS rate must be between 0 and 100.'}, status=status.HTTP_400_BAD_REQUEST)
                if tds_type and tds_type not in ['WITH TDS', 'WITHOUT TDS']: return Response({'status': 'fail', 'message': "tds type must be either 'WITH TDS' or 'WITHOUT TDS'"}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    service_provider = ServiceProvider.objects.get(sp_id=sp_id, is_deleted=False)
                except ServiceProvider.DoesNotExist:
                    return Response({
                        'status': 'fail',
                        'message': 'Service Provider not found'
                    }, status=status.HTTP_404_NOT_FOUND)
                serializer = ServiceProviderSerializer(service_provider, data=request.data, partial=True, context={'request': request})
                if serializer.is_valid():
                    service_provider_instance = serializer.save(updated_at=datetime.now(), tds_rate=tds_rate, tds_type=tds_type, updated_by=request.user)
                    # Log the update activity
                    activity = SaUserActivity(
                        table_id=service_provider.pk,
                        table_name='Service',
                        ua_action='Update',
                        ua_description=f'Update Service "{service_provider.pk}"',
                        created_by=request.user,
                        request_data=request.data,  # Request data
                        response_data=serializer.data  # Serialized response data
                    )
                    activity.save()
                    sa_service_data = SaService.objects.get(service_id=service_provider.service_id.service_id)
                    if sa_service_data.is_global == False or service_provider.is_table_config == False:
                        # Process 'to_us_charges'
                        to_us_charges_str = request.data.get('to_us_charges', '[]')
                        self.process_charges(to_us_charges_str, service_provider_instance, request, 'to_us', charges_type)

                        # Process 'to_provide_charges'
                        to_provide_charges_str = request.data.get('to_provide_charges', '[]')
                        self.process_charges(to_provide_charges_str, service_provider_instance, request, 'to_provide', charges_type)
                    else:
                        pass

                return Response({'status': 'success', 'message': 'Service Updated Successfully'}, status=status.HTTP_200_OK)

        except SaService.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)   

    @transaction.atomic
    def process_charges(self, charges_str, service_provider_instance, request, charge_category, charges_type):
        try:
            charges = json.loads(charges_str)
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format for charges")

        # Fetch existing charges for the given service provider and category
        existing_charges = Charges.objects.filter(
            service_provider=service_provider_instance,
            charge_category=charge_category,
            is_deleted=False
        )

        # Convert existing charges to a set for easy comparison
        existing_charges_dict = {
            (charge.minimum, charge.maximum, charge.rate_type, charge.charges_type): charge
            for charge in existing_charges
        }

        # Track new charges and update existing ones
        received_charges_keys = set()
        with transaction.atomic():
            for charge in charges:
                charge_data = {
                    "minimum": Decimal(charge["minimum"]),
                    "maximum": Decimal(charge["maximum"]),
                    "rate_type": charge["rate_type"],
                    "charges_type": charges_type,
                    "charge_category": charge_category,
                    "service_provider": service_provider_instance,
                }
                charge_key = (
                    charge_data["minimum"],
                    charge_data["maximum"],
                    charge_data["rate_type"],
                    charge_data["charges_type"],
                )
                received_charges_keys.add(charge_key)

                existing_charge = existing_charges_dict.get(charge_key)

                if existing_charge:
                    # Update existing charge if rate has changed
                    if existing_charge.rate != Decimal(charge["rate"]):
                        existing_charge.rate = Decimal(charge["rate"])
                        existing_charge.updated_at = datetime.now()
                        existing_charge.updated_by = request.user
                        existing_charge.save()
                        self.update_related_models(existing_charge, service_provider_instance)
                else:
                    # Create new charge if it doesn't exist
                    charge_data["rate"] = Decimal(charge["rate"])
                    new_charge = Charges.objects.create(**charge_data)

        # Delete charges that are in DB but not in the request payload
        for charge_key, charge_instance in existing_charges_dict.items():
            if charge_key not in received_charges_keys:
                charge_instance.is_deleted = True
                charge_instance.updated_at = datetime.now()
                charge_instance.updated_by = request.user
                charge_instance.save()
                self.delete_related_models(charge_instance, service_provider_instance)

    @transaction.atomic
    def delete_related_models(self, charge_instance, service_provider_instance):
        """
        Delete related records (AdCharges and AdminService charges) when a charge is deleted.
        """
        Charges.objects.filter(
            service_provider=service_provider_instance,
            minimum=charge_instance.minimum,
            maximum=charge_instance.maximum,
            rate_type=charge_instance.rate_type,
            charges_type=charge_instance.charges_type,
        ).delete()

        ad_sp_instance = AdServiceProvider.objects.get(sp_id=service_provider_instance.pk)
        # Delete from AdCharges
        AdCharges.objects.filter(
            service_provider=ad_sp_instance,
            minimum=charge_instance.minimum,
            maximum=charge_instance.maximum,
            rate_type=charge_instance.rate_type,
            charges_type=charge_instance.charges_type,
        ).delete()

        # Remove from AdminService charges JSON
        admin_services = AdminService.objects.filter(service_provider=service_provider_instance)
        for admin_service in admin_services:
            admin_service.charges = [
                charge for charge in admin_service.charges
                if not (
                    Decimal(charge["minimum"]) == charge_instance.minimum
                    and Decimal(charge["maximum"]) == charge_instance.maximum
                    and charge["rate_type"] == charge_instance.rate_type
                    and charge["charge_type"] == charge_instance.charges_type
                )
            ]
            admin_service.save()

    @transaction.atomic
    def update_related_models(self, charge_instance, service_provider_instance):
        """
        Update related models (AdminService and AdCharges) when a charge is updated.
        """
        ad_sp_instance = AdServiceProvider.objects.get(sp_id=service_provider_instance.pk)
        if charge_instance.charge_category == "to_provide":
            # Update AdminService
            admin_services = AdminService.objects.filter(service_provider=service_provider_instance)
            for admin_service in admin_services:
                updated = False
                new_rate = None
                for admin_charge in admin_service.charges:
                    if (
                        Decimal(admin_charge["minimum"]) == charge_instance.minimum
                        and Decimal(admin_charge["maximum"]) == charge_instance.maximum
                        and admin_charge["rate_type"] == charge_instance.rate_type
                        and admin_charge["charge_type"] == charge_instance.charges_type
                    ):
                        if Decimal(admin_charge["rate"]) != charge_instance.rate:
                            admin_charge["rate"] = float(charge_instance.rate)  # Convert to float for JSON compatibility
                            new_rate = float(charge_instance.rate)
                            updated = True
                if updated:
                    if not new_rate == None:
                        admin_service.rate = new_rate
                    admin_service.save()

            # Update AdCharges
            ad_charges = AdCharges.objects.filter(service_provider=ad_sp_instance)
            for ad_charge in ad_charges:
                if (
                    ad_charge.minimum == charge_instance.minimum
                    and ad_charge.maximum == charge_instance.maximum
                    and ad_charge.rate_type == charge_instance.rate_type
                    and ad_charge.charges_type == charge_instance.charges_type
                ):
                    if ad_charge.rate != charge_instance.rate:
                        ad_charge.rate = charge_instance.rate
                        ad_charge.save()

    def delete(self, request):
        try:
            sp_id = request.data.get('sp_id')
            if not sp_id:
                return Response({
                    'status': 'fail',
                    'message': 'Service Provider ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                with transaction.atomic():
                    service_provider = ServiceProvider.objects.get(sp_id=sp_id, is_deleted=False)
                    service_provider.hsn_sac = None
                    service_provider.is_deactive =True
                    service_provider.is_deleted = True
                    charges = Charges.objects.filter(service_provider=service_provider.pk,is_deleted=False)
                    if charges.exists():
                        try:
                            charges.update(is_deleted=True)
                            # Log the deletion activity for charges
                            for charge in charges:
                                activity = SaUserActivity(
                                    table_id=charge.pk,
                                    table_name='charges',
                                    ua_action='delete',
                                    ua_description='Charge deleted successfully',
                                    created_by=request.user,
                                    request_data=request.data,
                                )
                                activity.save()
                        except Charges.DoesNotExist:
                            return Response({'status': 'error','message': 'Charges not found'}, status=status.HTTP_404_NOT_FOUND)
                        except Exception as e:
                            return Response({'status': 'error','message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    service_provider.save()

                    # Log the deletion activity
                    activity = SaUserActivity(
                        table_id=service_provider.pk,
                        table_name='service_provider',
                        ua_action='delete',
                        ua_description=f'Deleted Service Provider "{service_provider.pk}"',
                        created_by=request.user
                    )
                    activity.save()

                    return Response({
                        'status': 'success',
                        'message': 'Service Provider Deleted Successfully'
                    }, status=status.HTTP_200_OK)

            except ServiceProvider.DoesNotExist:
                return Response({
                    'status': 'fail',
                    'message': 'Service Provider not found'
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChargesView(APIView):
    permission_classes = [IsAuthenticated]

    
    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_charges(request)
            elif 'charges_type' in request.data:
                return self.create_charges(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_charges(self, request):
        try:
            serializer = ChargesSerializer(data=request.data,context={'request': request})
            if serializer.is_valid():
                with transaction.atomic():
                    charges = serializer.save()
                    activity = SaUserActivity(
                        table_id=charges.pk,  # ID of the created banner
                        table_name='charges',  # Name of the model
                        ua_action='create',  # Action performed
                        ua_description='charges create successfully',  # Action description
                        created_by=request.user,  # Current user performing the action
                        request_data=request.data,  # Request data
                        response_data=serializer.data  # Serialized response data
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Charges Created Successfully'
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                response_data = {
                'status': 'error',
                'message': serializer.errors
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_charges(self, request):
        try:
            page_size = request.data.get('page_size', 10)  # Number of items per page
            page = request.data.get('page_number', 1)  # Default to page 1 if not provided
            
            sp_id = request.data.get('sp_id')
            search_query = request.data.get('search')
            
            queryset = Charges.objects.filter(is_deleted=False).order_by('-pk')
            
            if sp_id:
                queryset = queryset.filter(service_provider=sp_id)
            
            if search_query:
                queryset = queryset.filter(
                    Q(charges_type__icontains=search_query) |
                    Q(rate_type__icontains=search_query)
                    # Add more filters based on your requirements
                )
            
            paginator = Paginator(queryset, page_size)
            if not queryset.exists():
                paginated_response_data = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }
                response_data = {
                    'status': 'fail',
                    'message': 'Charges Data not found.',
                    'data': paginated_response_data
                }
                return Response(response_data, status=status.HTTP_200_OK)
            
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ChargesSerializer(page_obj.object_list, many=True)
            
            response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': serializer.data
            }
            
            response_data = {
                'status': 'success',
                'message': 'Charges Data',
                'data': response_data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Charges.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': 'Charges not found'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def put(self, request):
        charges_id = request.data.get('charges_id')
        if not charges_id:
            return Response({'status': 'error','message': 'charges_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            charges = Charges.objects.get(pk=charges_id)
            serializer = ChargesSerializer(charges, data=request.data, partial=True,context={'request': request})
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save(updated_by=request.user,updated_at=datetime.now())
                    activity = SaUserActivity(
                        table_id=serializer.instance.pk,  # ID of the created banner
                        table_name='charges',  # Name of the model
                        ua_action='update',  # Action performed
                        ua_description='charges a updated successfully',  # Action description
                        created_by=request.user,  # Current user performing the action
                        request_data=request.data,  # Request data
                        response_data=serializer.data  # Serialized response data
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Charges Updated Successfully'
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Charges.DoesNotExist:
            return Response({'status': 'error','message': 'Charges not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error','message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def delete(self, request):
        charges_id = request.data.get('charges_id')
        if not charges_id:
            return Response({'status': 'error','message': 'charges_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            charges = Charges.objects.get(pk=charges_id,is_deleted=False)
            charges.is_deleted= True
            charges.save()
            activity = SaUserActivity(
                        table_id=charges.pk,  # ID of the created banner
                        table_name='charges',  # Name of the model
                        ua_action='delete',  # Action performed
                        ua_description='charges deleted successfully',  # Action description
                        created_by=request.user,  # Current user performing the action
                        request_data=request.data,  # Request data
                    )
            activity.save()
            response_data = {
                'status': 'success',
                'message': 'Charges Deleted Successfully'
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Charges.DoesNotExist:
            return Response({'status': 'error','message': 'Charges not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error','message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ProductCategoryApiView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_category(request)
            elif 'category_name' in request.data:
                return self.create_category(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_category(self, request):
        try:
            serializer = ProductCategorySerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                with transaction.atomic():
                    category = serializer.save(created_by=request.user)
                    activity = SaUserActivity(
                        table_id=category.pk,  # ID of the created category
                        table_name='product_category',  # Name of the model
                        ua_action='create',  # Action performed
                        ua_description='Product Category created successfully',  # Action description
                        created_by=request.user,  # Current user performing the action
                        request_data=request.data,  # Request data
                        response_data=serializer.data  # Serialized response data
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Product Category Created Successfully',
                        # 'data': serializer.data
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                response_data = {
                    'status': 'error',
                    'message': serializer.errors
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_category(self, request):
        try:
            page_size = request.data.get('page_size', 10)  # Number of items per page
            page = request.data.get('page_number', 1)  # Default to page 1 if not provided
            is_deactive = request.data.get('is_deactive', None)
            product_category_id = request.data.get('product_category_id')
            search_query = request.data.get('search')

            queryset = ProductCategory.objects.filter(is_deleted=False).order_by('-pk')

            if is_deactive is not None:
                queryset = queryset.filter(is_deactive=is_deactive)

            if product_category_id:
                queryset = queryset.filter(product_category_id=product_category_id)

            if search_query:
                queryset = queryset.filter(
                    Q(category_name__icontains=search_query) |
                    Q(category_description__icontains=search_query)
                )
            if page_size != "0":
                paginator = Paginator(queryset, page_size)
                if not queryset.exists():
                    paginated_response_data = {
                        'total_pages': 0,
                        'current_page': 0,
                        'total_items': 0,
                        'results': []
                    }
                    response_data = {
                        'status': 'fail',
                        'message': 'Product Category Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                try:
                    page_obj = paginator.page(page)
                except EmptyPage:
                    return Response({
                        'status': 'fail',
                        'message': 'Page not found.',
                        'data': {}
                    }, status=status.HTTP_404_NOT_FOUND)

                serializer = ProductCategorySerializer(page_obj.object_list, many=True,context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted","updated_by", "created_by"]})

                response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }
            else:
                serializer = ProductCategorySerializer(queryset, many=True,context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted","updated_by", "created_by"]})
                response_data = {
                    'total_pages': 1,
                    'current_page': 1,
                    'total_items': queryset.count(),
                    'results': serializer.data
                }

            response_data = {
                'status': 'success',
                'message': 'Product Category Data Retrieved',
                'data': response_data
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except ProductCategory.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': 'Product Category not found'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def put(self,request):
        product_category_id = request.data.get('product_category_id')
        if not product_category_id:
            return Response({'status': 'error','message': 'product_category_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product_category = ProductCategory.objects.get(pk=product_category_id)
            serializer = ProductCategorySerializer(product_category, data=request.data, partial=True,context={'request': request})
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save(updated_by=request.user,updated_at=datetime.now())
                    activity = SaUserActivity(
                        table_id=serializer.instance.pk,  # ID of the created banner
                        table_name='product_category',  # Name of the model
                        ua_action='update',  # Action performed
                        ua_description='Product Category a updated successfully.',  # Action description
                        created_by=request.user,  # Current user performing the action
                        request_data=request.data,  # Request data
                        response_data=serializer.data  # Serialized response data
                    )
                    activity.save()
                    
                    is_deactive = 'is_deactive' in request.data
                    if ('category_name' in request.data or 'category_description' in request.data or 'parent_category_id' in request.data) and is_deactive:
                        response_data = {
                            'status': 'success',
                            'message': 'Product Category Updated Successfully',
                        }
                    elif is_deactive:
                        response_data = {
                            'status': 'success',
                            'message': 'Product Category Deactivate Successfully' if serializer.instance.is_deactive else 'Product Category Activate Successfully',
                        }
                    else:
                        response_data = {
                            'status': 'success',
                            'message': 'Product Category Updated Successfully'
                        }
                    
                    # response_data = {
                    #     'status': 'success',
                    #     'message': 'Product Category Updated Successfully'
                    # }
                    return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Charges.DoesNotExist:
            return Response({'status': 'error','message': 'Product Category not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error','message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        product_category_id = request.data.get('product_category_id')
        if not product_category_id:
            return Response({'status': 'error','message': 'product_category_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            Product_Category = ProductCategory.objects.get(pk=product_category_id,is_deleted=False)
            Product_Category.is_deleted= True
            Product_Category.is_deactive = True
            Product_Category.save()
            activity = SaUserActivity(
                        table_id=Product_Category.pk,  # ID of the created banner
                        table_name='ProductCategory',  # Name of the model
                        ua_action='delete',  # Action performed
                        ua_description='ProductCategory deleted successfully',  # Action description
                        created_by=request.user,  # Current user performing the action
                        request_data=request.data,  # Request data
                    )
            activity.save()
            response_data = {
                'status': 'success',
                'message': 'ProductCategory Deleted Successfully'
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Charges.DoesNotExist:
            return Response({'status': 'error','message': 'ProductCategory not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error','message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ExpenseApiView(APIView):
    permission_classes = [IsAuthenticated]

    
    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_expense(request)
            elif 'expense_date' in request.data:
                return self.create_expense(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_expense(self, request):
        try:
            with transaction.atomic():
                
                # Initialize the serializer with the data from the request
                # files = request.data.getlist('expense_attachment')
                request_data = request.data.copy()
                file_paths = []
                for key, value in request_data.items():
                    if key.startswith('expense_attachment'):
                       
                        file = value
                        # Validate file size
                        if file.size > 10 * 1024 * 1024 :
                            raise ValidationError("Expense attachment must be less than 10 MB.")
                        # Construct the relative file path
                        relative_file_path = os.path.join('expense/attachments', file.name)
                        file_paths.append(relative_file_path)

                        # Save the file to the media directory
                        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directories if they don't exist

                        with open(file_path, 'wb+') as destination:
                            for chunk in file.chunks():
                                destination.write(chunk)

                expense_attachment = file_paths
                
                # request_data['expense_attachment'] = {}
                serializer = ExpenseSerializer(data=request_data, context={'request': request})
                
                # Check if the provided data is valid
                if serializer.is_valid(raise_exception=True):
                    # Save the expense with the created_by field set to the authenticated user
                    expense_instance = serializer.save(created_by=request.user)
                    expense_instance.expense_attachment = expense_attachment
                    expense_instance.save()
                    # Log the activity
                    activity = SaUserActivity(
                        table_id=expense_instance.pk,  # ID of the created expense
                        table_name='expense',  # Name of the model
                        ua_action='create',  # Action performed
                        ua_description='Created a new expense',  # Action description
                        created_by=request.user,  # Current user performing the action
                        request_data=request_data,  # Request data
                        response_data=serializer.data,  # Serialized response data
                    )
                    activity.save()

                    response_data = {
                        'status': 'success',
                        'message': 'Expense Created Successfully'
                    }
                    # Return a success response with status code 201 (Created)
                    return Response(response_data, status=status.HTTP_201_CREATED)
                
                # If data is invalid, return the error messages
                response_data = {
                    'status': 'fail',
                    'message': serializer.errors
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
        except ValidationError as e:
            response_data = {
                'status': 'fail',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def fetch_expense(self, request):
        try:
            page_size = request.data.get('page_size', 10)  # Number of items per page
            page = request.data.get('page_number', 1)  # Default to page 1 if not provided
            
            expense_id = request.data.get('expense_id')
            search_query = request.data.get('search')
            
            queryset = expense.objects.filter(is_deleted=False).order_by('-pk')
            
            if expense_id:
                queryset = queryset.filter(expense_id=expense_id)
            
            if search_query:
                queryset = queryset.filter(
                    Q(expense_amount__icontains=search_query) |
                    Q(expense_payment_type__icontains=search_query) |
                    Q(expense_type__icontains=search_query) |
                    Q(expense_description__icontains=search_query)


                    # Add more filters based on your requirements
                )
            
            paginator = Paginator(queryset, page_size)
            if not queryset.exists():
                paginated_response_data = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }
                response_data = {
                    'status': 'fail',
                    'message': 'Expense Data not found.',
                    'data': paginated_response_data
                }
                return Response(response_data, status=status.HTTP_200_OK)
            
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                return Response({
                    'status': 'fail',
                    'message': 'Page not found.',
                    'data': {}
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ExpenseSerializer(page_obj.object_list, many=True, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted","updated_by", "created_by"]})
            
            response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': serializer.data
            }
            
            response_data = {
                'status': 'success',
                'message': 'Expense Data',
                'data': response_data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except expense.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': 'Expense not found'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        expense_id = request.data.get("expense_id")
        
        if not expense_id:
            return Response({'status': 'fail', 'message': "expense_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                try:
                    request_data = request.data.copy()
                    # Retrieve the expense object by ID
                    expense_instance = expense.objects.get(expense_id=expense_id, is_deleted=False)
                    
                    if any(key.startswith('expense_attachment') for key in request_data.keys()):
                        # Initialize the serializer with the data from the request
                        # files = request.data.getlist('expense_attachment')
                        file_paths = []
                        for key, value in request_data.items():
                            if key.startswith('expense_attachment'):
                            
                                file = value
                                # Validate file size
                                if file.size > 10 * 1024 * 1024 :
                                    raise ValidationError("Expense attachment must be less than 10 MB.")
                                # Construct the relative file path
                                relative_file_path = os.path.join('expense/attachments', file.name)
                                file_paths.append(relative_file_path)

                                # Save the file to the media directory
                                file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                                os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directories if they don't exist

                                with open(file_path, 'wb+') as destination:
                                    for chunk in file.chunks():
                                        destination.write(chunk)

                        expense_attachment =  file_paths
                        
                        request_data['expense_attachment'] = {}

                    serializer = ExpenseSerializer(expense_instance, data=request_data, partial=True, context={'request': request})
                    if serializer.is_valid():
                        serializer.save(updated_at=datetime.now(), updated_by=request.user)
                        if any(key.startswith('expense_attachment') for key in request_data.keys()):
                            expense_instance.expense_attachment = expense_attachment
                            expense_instance.save()

                        message = 'Expense Updated Successfully'
                    else:
                        return Response({'status': 'fail', 'message': f'{serializer.errors}'}, status=status.HTTP_400_BAD_REQUEST)

                    # Log the activity
                    activity = SaUserActivity(
                        table_id=expense_instance.pk,
                        table_name='Expense',
                        ua_action='Update',
                        ua_description=f'Updated expense with ID {expense_instance.pk}',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=serializer.data
                    )
                    activity.save()
                    
                    return Response({'status': 'success', 'message': message}, status=status.HTTP_200_OK)
                
                except expense.DoesNotExist:
                    return Response({'status': 'fail', 'message': "Expense not found."}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        expense_id = request.data.get("expense_id")
        
        # Check if expense_id is provided
        if not expense_id:
            response_data = {
                'status': 'fail',
                'message': "expense_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Retrieve the expense object by ID
                expense_obj = expense.objects.get(expense_id=expense_id, is_deleted=False)
                # Mark the expense object as deleted
                expense_obj.is_deleted = True
                expense_obj.save()
                
                # Log the activity
                activity = SaUserActivity(
                    table_id=expense_obj.pk,  # ID of the expense
                    table_name='expense',  # Name of the model
                    ua_action='Delete',  # Action performed
                    ua_description=f'Deleted expense with ID {expense_obj.pk}',  # Action description
                    created_by=request.user,  # Current user performing the action
                    request_data=request.data  # Request data
                )
                activity.save()
                
                response_data = {
                    'status': 'success',
                    'message': 'Expense Deleted Successfully'
                }
                # Return a success response
                return Response(response_data, status=status.HTTP_200_OK)
        except expense.DoesNotExist:
            # Handle case where expense is not found
            response_data = {
                'status': 'fail',
                'message': "Expense not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
import ast
def get_error_message(errors):
    error_messages = []
    for field, error_list in errors.items():
        for error in error_list:
            error_messages.append(f"{field}: {error}")
    return " ".join(error_messages)

class AdminAPIView(APIView):
    permission_classes = [IsAuthenticated]

      
    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_admin(request)
            elif 'name' in request.data and 'contact_no' in request.data :
                return self.create_admin(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create_admin(self, request):
        try:
            with transaction.atomic():
                request_data = request.data.copy()
                name = request_data.get('name')
                contact_no = request_data.get('contact_no')
                email = request_data.get('email')

                required_docs_obj = RequiredDocumentList.objects.filter(is_required=True, is_deleted=False)
                required_docs = [doc.document_slug for doc in required_docs_obj]

                # if not any(key in required_docs for key in request_data.keys()):
                #     raise ValidationError("One of the required documents is missing.")

                def process_files(file, dir_name, max_size=10 * 1024 * 1024):
                    if file is None:
                        raise ValidationError("File is missing.")
                    if file.size > max_size:
                        raise ValidationError(f"File size must be less than {max_size / (1024 * 1024)} MB.")

                    file_key = file.name.split('.')[0]
                    now = datetime.now().strftime("%Y%m%d%H%M%S")
                    relative_file_path = os.path.join(dir_name, f"{file_key}{now}.{file.name.split('.')[-1]}")
                    file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    with open(file_path, 'wb+') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)
                    
                    return relative_file_path

                kyc_docs_file_paths = {
                    key: process_files(request_data[key], 'docs_file') for key in required_docs if key in request_data
                }

                # stamp_ids = ast.literal_eval(request_data.get('stamp_id', '[]'))
                # stamp_docs = [
                #     {
                #         "stamp_id": i,
                #         "stamp_file": process_files(request_data.get(f"stamp_file{stamp_ids.index(i)}"), 'Stamp_file')
                #     }
                #     for i in stamp_ids
                # ]

                serializer = AdminSerializer(data=request_data, context={'request': request})
                if serializer.is_valid():
                    admin_obj = serializer.save(created_by=request.user)
                    admin_obj.docs_files = kyc_docs_file_paths
                    # admin_obj.stamp_docs = stamp_docs
                    admin_obj.charges = list(Charges.objects.filter(charge_category="to_provide").values_list('pk', flat=True))
                    admin_obj.save()

                    request_data["admin_id"] = admin_obj.pk
                    agreement_serializer = AdminAgreementSerializer(data=request_data, context={'request': request})
                    pdf_file_paths = list(serializer.data["docs_files"].values())
                    if agreement_serializer.is_valid():
                        agreement_serializer.save(created_by=request.user)
                        SaUserActivity.objects.create(
                            table_id=agreement_serializer.instance.pk,
                            table_name='sa_admin_agreement',
                            ua_action='create',
                            ua_description=f'Created Admin Agreement "{agreement_serializer.instance.pk}"',
                            created_by=request.user,
                            request_data=request.data,
                            response_data=agreement_serializer.data,
                        )

                    # Log admin creation activity
                    SaUserActivity.objects.create(
                        table_id=serializer.instance.pk,
                        table_name='sa_admin',
                        ua_action='create',
                        ua_description=f'Created Admin "{serializer.instance.name}"',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=serializer.data,
                    )

                    # Synchronize data with the second database
                    pu_user = PortalUser.objects.using('tcpl_admin_db').create(
                        pu_name=name, pu_contact_no=contact_no, pu_email=email, pu_role='ADMIN'
                    )

                    PortalUserDetails.objects.using('tcpl_admin_db').create(
                        pu=pu_user,
                        aadhaar_card = admin_obj.aadhaar_card_number,
                        pan_card = admin_obj.pan_card_number,
                        doc_images = pdf_file_paths,
                        state_id = admin_obj.state.state_id,
                        city_id = admin_obj.city.city_id,
                        zip_code = admin_obj.pincode,
                    )
                    PortalUserWallet.objects.using('tcpl_admin_db').create(
                        pu=pu_user,
                        main_wallet = 0.00
                    )
                    provided_data(request)
                    return Response({
                        'status': 'success',
                        'message': 'Admin Created Successfully',
                        'admin_id': serializer.instance.pk,
                    }, status=status.HTTP_201_CREATED)
                else:
                    raise ValidationError(serializer.errors)

        except ValidationError as e:
            return Response({'status': 'fail', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_admin_agreement(self,request):
        try:
            with transaction.atomic():
                request_data = request.data.copy()
                admin_id = request.data.get("admin_id")
                if admin_id:
                    if AdminAgreement.objects.filter(admin_id = admin_id).exists():
                        raise ValidationError("this admin Agreement is already added.")
                else:
                    raise ValidationError("admin id is required.")
                agreement_serializer = AdminAgreementSerializer(data=request_data, context={'request': request})
                if agreement_serializer.is_valid():
                    agreement_serializer.save(created_by=request.user)
                    activity = SaUserActivity(
                        table_id=agreement_serializer.instance.pk,
                        table_name='sa_admin_agreement',
                        ua_action='create',
                        ua_description=f'Created Admin "{agreement_serializer.instance.pk}"',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=agreement_serializer.data,
                    )
                    activity.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Admin Agreement Created Successfully',
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)
                else:
                    raise ValidationError(agreement_serializer.errors)
        
        except ValidationError as e:
            response_data = {
                'status': 'fail',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # def put(self, request):
    #     """
    #     Handles PUT requests to update `Admin` objects.

    #     This endpoint requires authentication with JWT token (`@permission_classes([IsAuthenticated])` and `@authentication_classes([JWTAuthentication])`).

    #     Upon receiving a PUT request:
    #     - Retrieves the `admin_id` from the request data (`request.data.get('admin_id')`). If not provided, returns a `400 Bad Request` response indicating that the ID is required.
    #     - Attempts to fetch the `Admin` object with the provided `admin_id`.
    #     - If the `Admin` object does not exist or is soft deleted (`is_deleted=True`), returns a `404 Not Found` response indicating that the admin with the specified ID does not exist.
    #     - Serializes the incoming request data using `AdminSerializer` with `partial=True` to allow for partial updates.
    #     - If the serialized data is valid:
    #         - Saves the updated `Admin` object.
    #         - Logs the update activity using `UserActivity` model.
    #         - Returns a `200 OK` response with a success message.
    #     - If the serialized data is not valid:
    #         - Returns a `400 Bad Request` response with validation errors.
    #     - Handles any exceptions that occur during the process and returns a `500 Internal Server Error` response with the exception message.

    #     ### Parameters
    #     - `admin_id` (in form data, required): ID of the admin to update.
    #     - `name` (in form data, optional): Updated name of the admin.
    #     - `contact_no` (in form data, optional): Updated contact number of the admin.
    #     - `email` (in form data, optional): Updated email of the admin.
    #     - `kyc_docs_id` (in form data, optional): Updated KYC documents ID.
    #     - `kyc_docs` (in form data, optional): Updated KYC documents.
    #     - `company_name` (in form data, optional): Updated company name.
    #     - `gst_number` (in form data, optional): Updated GST number.
    #     - `gst_type` (in form data, optional): Updated GST type.
    #     - `state` (in form data, optional): Updated state.
    #     - `city` (in form data, optional): Updated city.
    #     - `pincode` (in form data, optional): Updated pincode.
    #     - `is_deactive` (in form data, optional): Updated deactivation status.
    #     - `business_docs_id` (in form data, optional): Updated business documents ID.
    #     - `business_docs` (in form data, optional): Updated business documents.

    #     ### Responses
    #     - **Success**:
    #         - `200 OK`: Returns a success message indicating that the admin was updated successfully.
    #         - `200 OK`: Returns a success message indicating that the admin was deactivated or activated successfully if the `is_deactive` status was updated.

    #     - **Error Handling**:
    #         - `400 Bad Request`: Returns a fail response with validation errors if there's an issue with the data provided.
    #         - `404 Not Found`: Returns a fail response if the admin with the specified `admin_id` does not exist or is soft deleted.
    #         - `500 Internal Server Error`: Returns an error message for any server-side issues during processing.

    #     ### Usage
    #     - Send a PUT request to update an `Admin` object identified by `admin_id`.
    #     - Include valid authentication credentials (`Bearer` token) in the request header.
    #     - Provide the `admin_id` and any fields (`name`, `contact_no`, `email`, `kyc_docs_id`, `kyc_docs`, `company_name`, `gst_number`, `gst_type`, `state`, `city`, `pincode`, `is_deactive`, `business_docs_id`, `business_docs`) to update in the request body.
    #     - Handle responses based on the returned status (`'status': 'success'`, `'status': 'fail'`, or `'status': 'error'`) and access the updated data or error message as required.
    #     """
    #     try:
    #         with transaction.atomic():
    #             request_data = request.data.copy()

    #             # Process KYC documents if present
    #             required_docs_obj = RequiredDocumentList.objects.filter(is_required=True, is_deleted=False)
    #             required_docs = [x.document_slug for x in required_docs_obj]
    #             if any(key in required_docs for key in request_data.keys()):
    #                 kyc_docs_file_paths = {}
    #                 for key, value in request_data.items():
    #                     if key in required_docs:
    #                         file = value
    #                         if file.size > 10 * 1024 * 1024:
    #                             raise ValidationError("docs_file must be less than 10 MB.")
    #                         file_key = file.name.split('.')[0]
    #                         relative_file_path = os.path.join('docs_file', file_key + str(datetime.now().strftime("%Y%m%d%H%M%S")) + '.' + file.name.split('.')[-1])
    #                         file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
    #                         os.makedirs(os.path.dirname(file_path), exist_ok=True)
    #                         with open(file_path, 'wb+') as destination:
    #                             for chunk in file.chunks():
    #                                 destination.write(chunk)
    #                         kyc_docs_file_paths[key] = relative_file_path
    #                 request_data['docs_file'] = json.dumps(kyc_docs_file_paths)
    #             else:
    #                 request_data.pop('docs_file', None)

    #             if "stamp_id" in request.data:
    #                 stamp_ids = ast.literal_eval(request.data.get('stamp_id'))
    #                 stamp_docs = []
    #                 for i in stamp_ids:
    #                     file = request.data.get(f"stamp_file{stamp_ids.index(i)}")
    #                     if i != file.name.split('.')[0]:
    #                         raise ValidationError("Stamp file name and stamp file id must be same.")
    #                     if file.size > 10 * 1024 * 1024:
    #                         raise ValidationError("docs_file must be less than 10 MB.")
    #                     now = datetime.now().strftime("%Y%m%d%H%M%S")
    #                     file_key = f"{file.name.split('.')[0]}{str(now)}"
    #                     relative_file_path = os.path.join('Stamp_file', file_key + '.' + file.name.split('.')[-1])
    #                     file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
    #                     os.makedirs(os.path.dirname(file_path), exist_ok=True)
    #                     with open(file_path, 'wb+') as destination:
    #                         for chunk in file.chunks():
    #                             destination.write(chunk)
    #                     stamp_docs.append({"stamp_id": i, "stamp_file": relative_file_path})
    #                 request_data['stamp_docs'] = json.dumps(stamp_docs)

    #             admin_id = request_data.get('admin_id')
    #             if not admin_id:
    #                 return Response({'status': 'fail', 'message': 'ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    #             try:
    #                 admin = Admin.objects.get(admin_id=admin_id)
    #             except Admin.DoesNotExist:
    #                 return Response({'status': 'fail', 'message': 'Admin not found'}, status=status.HTTP_404_NOT_FOUND)

    #             if admin.is_deleted:
    #                 return Response({'status': 'fail', 'message': 'Admin is deleted'}, status=status.HTTP_404_NOT_FOUND)

    #             fields_to_check = ['name', 'contact_no', 'email', 'kyc_docs_id', 'kyc_docs', 'gst_number', 'gst_type', 'state', 'city', 'pincode', 'company_name', 'business_docs_id', 'business_docs']
    #             is_deactive = 'is_deactive' in request_data

    #             serializer = AdminSerializer(admin, data=request_data, partial=True, context={'request': request})
    #             if serializer.is_valid():
    #                 admin_obj = serializer.save(updated_at=datetime.now())
    #                 charges_ids =[x.pk for x in  Charges.objects.filter(charge_category="to_provide").order_by("pk")]
    #                 admin_obj.charges = charges_ids
    #                 admin_obj.save()
    #                 if any(key in required_docs for key in request_data.keys()):
    #                     admin_obj.docs_files = kyc_docs_file_paths
    #                     admin_obj.save()
    #                 if "stamp_id" in request.data:
    #                     admin_obj.stamp_docs = stamp_docs
    #                     admin_obj.save()
    #                 agreement_field = ["aa_amount", "gst_amount", "agreement_document", "aa_status"]
    #                 if any(key in agreement_field for key in request_data.keys()):
    #                     admin_agreement_id = request_data.get("aa_id")
    #                     if not admin_agreement_id:
    #                         raise ValidationError("aa_id is required for update Agreement detail.")
                        
    #                     try:
    #                         agreement_obj = AdminAgreement.objects.get(aa_id=admin_agreement_id, is_deleted=False,admin_id=admin_obj.pk)
    #                     except AdminAgreement.DoesNotExist:
    #                         return Response({'status': 'fail', 'message': 'Admin Agreement not found'}, status=status.HTTP_404_NOT_FOUND)
                            
    #                     agreement_serializer = AdminAgreementSerializer(agreement_obj, data=request_data, partial=True, context={'request': request})
    #                     if agreement_serializer.is_valid():
    #                         agreement_serializer.save(updated_at=datetime.now())
    #                     else:
    #                         raise ValidationError(agreement_serializer.errors)

    #                 activity = UserActivity(
    #                     table_id=serializer.instance.pk,
    #                     table_name='sa_admin',
    #                     ua_action='update',
    #                     ua_description=f'Updated Admin "{serializer.instance.name}"',
    #                     created_by=request.user,
    #                     request_data=request_data,
    #                     response_data=serializer.data,
    #                 )
    #                 activity.save()

    #                 if any(field in request.data for field in fields_to_check) and is_deactive:
    #                     response_data = {'status': 'success', 'message': 'Admin Deactivated Successfully' if serializer.instance.is_deactive else 'Admin Activated Successfully'}
    #                 elif serializer.instance.is_deactive:
    #                     response_data = {'status': 'success', 'message': 'Admin Activated Successfully'}
    #                 else:
    #                     response_data = {'status': 'success', 'message': 'Admin Update Successfully'}

    #                 return Response(response_data, status=status.HTTP_200_OK)

    #             return Response({'status': 'fail', 'message': 'Failed to update admin', 'data': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    #     except Exception as e:
    #         return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            if 'admin_id' in request.data and 'admin_status' in request.data:
                return self.update_admin_status(request)
            elif 'admin_id' in request.data and 'service_provider_name' not in request.data:
                return self.update_admin_profile(request)
            elif 'name' in request.data and 'email' in request.data and 'service_provider_name' in request.data:
                return self.update_admin_service_and_charges(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def update_admin_status(self, request):
        admin_id = request.data.get('admin_id')
        admin_status = request.data.get('admin_status')
        status_reason = request.data.get('status_reason', None)
        try:
            admin = PortalUser.objects.filter(id=admin_id, is_deleted=False).first()
            
            if admin.pu_status in ['APROVE', 'REJECT']:
                return Response({'status': 'fail', 'message': 'status is already updated.'}, status=status.HTTP_400_BAD_REQUEST)
            
            admin.pu_status = admin_status
            admin.pu_reason = status_reason if status_reason else None
            admin.save()
            sa_admin = Admin.objects.get(admin_id=admin_id)
            sa_admin.admin_status = admin_status
            sa_admin.reason = status_reason if status_reason else None
            sa_admin.save()
            return Response({'status': 'success', 'message': 'Admin status updated successfully.'}, status=status.HTTP_200_OK)
        
        except PortalUser.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Admin not found.'}, status=status.HTTP_404_NOT_FOUND)

        except Admin.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Admin not found.'}, status=status.HTTP_404_NOT_FOUND)    

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_admin_profile(self, request):
        try:
            with transaction.atomic():
                request_data = request.data.copy()

                # Process KYC documents if present
                required_docs_obj = RequiredDocumentList.objects.filter(is_required=True, is_deleted=False)
                required_docs = [x.document_slug for x in required_docs_obj]
                if any(key in required_docs for key in request_data.keys()):
                    kyc_docs_file_paths = {}
                    for key, value in request_data.items():
                        if key in required_docs:
                            file = value
                            if file.size > 10 * 1024 * 1024:
                                raise ValidationError("docs_file must be less than 10 MB.")
                            file_key = file.name.split('.')[0]
                            relative_file_path = os.path.join('docs_file', file_key + str(datetime.now().strftime("%Y%m%d%H%M%S")) + '.' + file.name.split('.')[-1])
                            file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                            os.makedirs(os.path.dirname(file_path), exist_ok=True)
                            with open(file_path, 'wb+') as destination:
                                for chunk in file.chunks():
                                    destination.write(chunk)
                            kyc_docs_file_paths[key] = relative_file_path
                    request_data['docs_file'] = json.dumps(kyc_docs_file_paths)
                else:
                    request_data.pop('docs_file', None)

                # if "stamp_id" in request.data:
                #     stamp_ids = ast.literal_eval(request.data.get('stamp_id'))
                #     stamp_docs = []
                #     for i in stamp_ids:
                #         file = request.data.get(f"stamp_file{stamp_ids.index(i)}")
                #         if i != file.name.split('.')[0]:
                #             raise ValidationError("Stamp file name and stamp file id must be same.")
                #         if file.size > 10 * 1024 * 1024:
                #             raise ValidationError("docs_file must be less than 10 MB.")
                #         now = datetime.now().strftime("%Y%m%d%H%M%S")
                #         file_key = f"{file.name.split('.')[0]}{str(now)}"
                #         relative_file_path = os.path.join('Stamp_file', file_key + '.' + file.name.split('.')[-1])
                #         file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                #         os.makedirs(os.path.dirname(file_path), exist_ok=True)
                #         with open(file_path, 'wb+') as destination:
                #             for chunk in file.chunks():
                #                 destination.write(chunk)
                #         stamp_docs.append({"stamp_id": i, "stamp_file": relative_file_path})
                #     request_data['stamp_docs'] = json.dumps(stamp_docs)

                admin_id = request_data.get('admin_id')
                if not admin_id:
                    return Response({'status': 'fail', 'message': 'ID is required'}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    admin = Admin.objects.get(admin_id=admin_id)
                except Admin.DoesNotExist:
                    return Response({'status': 'fail', 'message': 'Admin not found'}, status=status.HTTP_404_NOT_FOUND)

                if admin.is_deleted:
                    return Response({'status': 'fail', 'message': 'Admin is deleted'}, status=status.HTTP_404_NOT_FOUND)

                fields_to_check = ['name', 'contact_no', 'email', 'kyc_docs_id', 'kyc_docs', 'gst_number', 'gst_type', 'state', 'city', 'pincode', 'company_name', 'business_docs_id', 'business_docs']
                is_deactive = 'is_deactive' in request_data

                serializer = AdminSerializer(admin, data=request_data, partial=True, context={'request': request})
                if serializer.is_valid():
                    admin_obj = serializer.save(updated_at=datetime.now())
                    charges_ids =[x.pk for x in  Charges.objects.filter(charge_category="to_provide").order_by("pk")]
                    admin_obj.charges = charges_ids
                    admin_obj.save()
                    if any(key in required_docs for key in request_data.keys()):
                        admin_obj.docs_files = kyc_docs_file_paths
                        admin_obj.save()
                    # if "stamp_id" in request.data:
                    #     admin_obj.stamp_docs = stamp_docs
                    #     admin_obj.save()
                    agreement_field = ["aa_amount", "gst_amount", "agreement_document", "aa_status"]
                    if any(key in agreement_field for key in request_data.keys()):
                        admin_agreement_id = request_data.get("aa_id")
                        if not admin_agreement_id:
                            raise ValidationError("aa_id is required for update Agreement detail.")
                        
                        try:
                            agreement_obj = AdminAgreement.objects.get(aa_id=admin_agreement_id, is_deleted=False,admin_id=admin_obj.pk)
                        except AdminAgreement.DoesNotExist:
                            return Response({'status': 'fail', 'message': 'Admin Agreement not found'}, status=status.HTTP_404_NOT_FOUND)
                            
                        agreement_serializer = AdminAgreementSerializer(agreement_obj, data=request_data, partial=True, context={'request': request})
                        if agreement_serializer.is_valid():
                            agreement_serializer.save(updated_at=datetime.now())
                        else:
                            raise ValidationError(agreement_serializer.errors)

                    activity = SaUserActivity(
                        table_id=serializer.instance.pk,
                        table_name='sa_admin',
                        ua_action='update',
                        ua_description=f'Updated Admin "{serializer.instance.name}"',
                        created_by=request.user,
                        request_data=request_data,
                        response_data=serializer.data,
                    )
                    activity.save()

                    if any(field in request.data for field in fields_to_check) and is_deactive:
                        response_data = {'status': 'success', 'message': 'Admin Deactivated Successfully' if serializer.instance.is_deactive else 'Admin Activated Successfully'}
                    elif serializer.instance.is_deactive:
                        response_data = {'status': 'success', 'message': 'Admin Activated Successfully'}
                    else:
                        response_data = {'status': 'success', 'message': 'Admin Update Successfully'}

                    return Response(response_data, status=status.HTTP_200_OK)

                return Response({'status': 'fail', 'message': 'Failed to update admin', 'data': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update_admin_service_and_charges(self, request):
        try:
            request_data = request.data.copy()
            name = request.data.get('name')
            email = request.data.get('email')
            service_provider_name = request.data.get('service_provider_name')
            markup_rate = request.data.get('markup_rate', None)
            markdown_rate = request.data.get('markdown_rate', None)

            try:
                portal_admin = PortalUser.objects.using('tcpl_admin_db').get(pu_name=name, pu_email=email)
            except PortalUser.DoesNotExist:
                return JsonResponse({'status': 'fail', 'message': 'Portal admin not found'}, status=status.HTTP_404_NOT_FOUND)

            if portal_admin.is_deleted:
                return JsonResponse({'status': 'fail', 'message': 'Admin is deleted'}, status=status.HTTP_404_NOT_FOUND)

            # Fetch the service provider
            try:
                service_provider = AdServiceProvider.objects.using('tcpl_admin_db').get(
                    sp_name=service_provider_name)
            except AdServiceProvider.DoesNotExist:
                return JsonResponse({'status': 'fail', 'message': 'Service provider not found'},
                                status=status.HTTP_404_NOT_FOUND)

            # Fetch the charges related to the admin and service provider
            try:
                admin_charges = AdCharges.objects.using('tcpl_admin_db').get(created_by=portal_admin.pk,
                                                                             service_provider=service_provider.pk)
            except AdCharges.DoesNotExist:
                return JsonResponse({'status': 'fail', 'message': 'Charges not found'},
                                status=status.HTTP_404_NOT_FOUND)

            if markup_rate:
                if admin_charges.rate_type == "is_flat":
                    admin_charge_rate = admin_charges.rate
                    calculate_rate = (float(admin_charge_rate) * float(markup_rate)) / 100
                    admin_charges.rate = float(admin_charge_rate) + float(calculate_rate)

                if admin_charges.rate_type == "is_percent":
                    admin_charge_rate = admin_charges.rate
                    admin_charges.rate = float(admin_charge_rate) + float(markup_rate)

            if markdown_rate:
                if admin_charges.rate_type == "is_flat":
                    admin_charge_rate = admin_charges.rate
                    calculate_rate = (float(admin_charge_rate) * float(markup_rate)) / 100
                    admin_charges.rate = float(admin_charge_rate) - float(calculate_rate)

                if admin_charges.rate_type == "is_percent":
                    admin_charge_rate = admin_charges.rate
                    admin_charges.rate = float(admin_charge_rate) - float(markup_rate)

            admin_charges.save()

            return JsonResponse({"status": "success", "message": "Admin charges update successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return JsonResponse(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_admin(self, request):
        try:
            admin_id = request.data.get('admin_id')
            search_query = request.data.get('search', None)
            filter_field = request.data.get('filter_field', None)
            filter_value = request.data.get('filter_value', None)
            order_by = request.data.get('order_by', "ascending")
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            is_deactive = request.data.get('is_deactive', None)
            page_number = int(request.data.get('page_number', 1))
            page_size = int(request.data.get('page_size', 10))

            # Validate pagination inputs
            if page_size <= 0 or page_number <= 0:
                return Response({
                    'status': 'fail',
                    'message': 'page_size and page_number must be positive integers.',
                    'data': {}
                }, status=status.HTTP_400_BAD_REQUEST)

            # Fetch specific admin by admin_id
            if admin_id:
                try:
                    admin = Admin.objects.get(admin_id=admin_id, is_deleted=False)
                    serializer = AdminSerializer(admin, context={'request': request})

                    # Fetch related service providers and their to_provide charges
                    service_providers = ServiceProvider.objects.all()
                    service_provider_data = []

                    for provider in service_providers:
                        to_provide_charges = Charges.objects.filter(service_provider=provider, charge_category='to_provide')
                        charge_serializer = ChargesSerializer(to_provide_charges, many=True, context={'request': request})

                        # Assuming all charges under the service provider have the same charge_type
                        charge_type = to_provide_charges.first().charges_type if to_provide_charges.exists() else None

                        service_provider_data.append({
                            'sp_id': provider.sp_id,
                            'service_name': provider.service_id.service_name,
                            'provider_name': provider.sp_name,
                            'provider_label': provider.label,
                            # 'hsn_sac_code': provider.hsn_sac.hsnsac_code if provider.hsn_sac.hsnsac_code else None,
                            'charge_type': charge_type,  # Include charge_type as a separate value
                            'is_deactive': False,
                            'to_provide_charges': charge_serializer.data
                        })

                    response_data = {
                        'status': 'success',
                        'message': 'Admin Data with Service Providers and Charges',
                        'data': {
                            'admin': serializer.data,
                            'service_providers': service_provider_data
                        }
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                except Admin.DoesNotExist:
                    return Response({
                        'status': 'fail',
                        'message': 'Admin not found.',
                        'data': {}
                    }, status=status.HTTP_404_NOT_FOUND)

            # Filter and order queryset
            queryset = Admin.objects.filter(is_deleted=False)

            # Apply date range filtering if provided
            if start_date and end_date:
                try:
                    start_date_parsed = parse_date(start_date)
                    end_date_parsed = parse_date(end_date)
                    queryset = queryset.filter(created_at__range=[start_date_parsed, end_date_parsed + timedelta(days=1)])
                except ValueError:
                    return Response({
                        'status': 'fail',
                        'message': 'Invalid date format. Use YYYY-MM-DD.',
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Apply filtering by field
            if filter_field and filter_value:
                filter_kwargs = {filter_field: filter_value}
                queryset = queryset.filter(**filter_kwargs)

            # Apply deactivation filter if provided
            if is_deactive == "true":
                queryset = queryset.filter(is_deactive=True)
            elif is_deactive == "false":
                queryset = queryset.filter(is_deactive=False)

            # Apply search query if provided
            if search_query:
                queryset = queryset.filter(
                    Q(name__icontains=search_query) |
                    Q(email__icontains=search_query) |
                    Q(company_name__icontains=search_query) |
                    Q(gst_number__icontains=search_query) |
                    Q(created_by__username__icontains=search_query)
                )

            # Apply ordering
            if order_by == "descending" and filter_field:
                queryset = queryset.order_by(f'-{filter_field}')
            elif filter_field:
                queryset = queryset.order_by(f'{filter_field}')

            # Pagination logic
            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({
                    'status': 'success',
                    'message': 'No data found for the requested page.',
                    'data': {
                        'total_pages': paginator.num_pages,
                        'current_page': page_number,
                        'total_items': paginator.count,
                        'results': []
                    }
                }, status=status.HTTP_200_OK)

            # Serialize and return paginated data
            serializer = AdminSerializer(page_obj.object_list, many=True, context={'request': request})
            response_data = {
                'status': 'success',
                'message': 'Admin Data',
                'data': {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Internal server error',
                'data': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self,request):
        try:
            with transaction.atomic():
                admin_id = request.data.get('admin_id')
                if not admin_id:
                    response_data = {
                        'status': 'fail',
                        'message': 'ID is required'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                admin_data = Admin.objects.get(admin_id=admin_id)
                if admin_data.is_deactive == False:
                    
                    admin_data.is_deactive = True
                    admin_data.save()

                    portal_users = PortalUser.objects.all()

                    for portal_user in portal_users:
                        portal_user.is_deactive = True
                        portal_user.save()

                    portal_user_login_logs = PortalUserLoginLogs.objects.all()

                    for portal_user in portal_user_login_logs:
                        portal_user.is_expire = True
                        portal_user.save()

                    response_data = {
                        'status': 'success',
                        'message': 'Admin Block Successfully'
                    }
                else:
                    admin_data.is_deactive = False
                    admin_data.save()

                    portal_users = PortalUser.objects.all()

                    for portal_user in portal_users:
                        portal_user.is_deactive = False
                        portal_user.save()

                    portal_user_login_logs = PortalUserLoginLogs.objects.all()

                    for portal_user in portal_user_login_logs:
                        portal_user.is_expire = False
                        portal_user.save()
                    response_data = {
                        'status': 'success',
                        'message': 'Admin Unblock Successfully'
                    }

                # Log the deletion activity
                activity = SaUserActivity(
                    table_id=admin_data.pk,
                    table_name='sa_admin',
                    ua_action='delete',
                    ua_description=f'deleted Admin "{admin_data.name}"',
                    created_by=request.user,
                    request_data=request.data,
                )
                activity.save()

                return Response(response_data, status=status.HTTP_200_OK)

        except Admin.DoesNotExist:
            response_data = {
                'status': 'fail',
                'message': 'Admin not found'
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # permission_classes = [IsAuthenticated]
   
    # def get(self, request):
        
    #     """
    #     API endpoint for retrieving the details of an admin by their ID.

    #     This endpoint requires authentication with a JWT token.

    #     Upon receiving a GET request:
    #     - The endpoint retrieves the `admin_id` parameter from the query parameters.
    #     - It then fetches the details of the specified admin using this ID.
    #     - The admin details are serialized using the `AdminSerializer`.
    #     - The serialized data is returned in the response with a status of `200 OK`.

    #     Fields in the Response:
    #     - `status`: Indicates the success or failure of the request.
    #     - `message`: A descriptive message related to the request outcome.
    #     - `data`: The admin details if the request is successful.

    #     Usage:
    #     - Send a GET request with the `admin_id` as a query parameter.
    #     - Include valid authentication credentials (`Bearer` token) in the request header.
    #     - Handle responses based on the returned status and access the admin data or error message as required.
    #     """
   
    #     admin_id = request.data.get("admin_id")

    #     if not admin_id:
    #         return Response({
    #             'status': 'fail',
    #             'message': 'Admin ID is required.'
    #         }, status=status.HTTP_400_BAD_REQUEST)

    #     try:
    #         admin = Admin.objects.get(admin_id=admin_id)
    #         serializer = AdminSerializer(admin, context={'request': request})

    #         response_data = {
    #             'status': 'success',
    #             'message': 'Admin data retrieved successfully',
    #             'data': serializer.data
    #         }
    #         return Response(response_data, status=status.HTTP_200_OK) 

    #     except Admin.DoesNotExist:
    #         return Response({
    #             'status': 'fail',
    #             'message': f'Admin with ID {admin_id} not found.'
    #         }, status=status.HTTP_404_NOT_FOUND)

    #     except Exception as e:
    #         return Response({
    #             'status': 'error',
    #             'message': 'Internal server error',
    #             'data': str(e)
    #         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def handle_esign_request(self,request):
        # esign_id = request.FILES.get('esign_id')
        document = request.FILES.get('document')
        


                
        # elif document:
        
        if not document:
            return Response(
            {'status': 'fail', 'message': 'Document is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
            
        files = {
            'document': (document.name, document, 'application/pdf')
        }
            # print(files,"---------document---------")

        upload_url = "https://sandbox.cashfree.com/verification/esignature/document"

        headers = {
            'x-client-id': 'CF10200215CQOS9TNPU07S7391HH9G',
            'x-client-secret': 'cfsk_ma_test_b68698459f24796a6d655dd514e9b1b1_5180673a',
                # 'Content-Type': 'multipart/form-data'
            }

        try:
            response = requests.post(upload_url, headers=headers, files=files)
            response_data = response.json()
            # print(response_data["message"])
            
            if response.status_code == 200:
                # response_data['is_gst_verify'] = True
  
                document_id = response_data.get('document_id')
                # document_id = request.data.get('document_id')
                
                
                if not document_id:
                    return Response(
                        {'status': 'fail', 'message': 'Failed to retrieve document_id from upload response.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
                try:
                    
                    admin=Admin.objects.get(verification_id=verification_id)
                    
                except Admin.DoesNotExist:
                    return Response(
                        {'status': 'fail', 'message': 'Admin not found for the given verification_id.'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                    
                signers=[
                    {
                        "name": admin.name,
                        "email": admin.email,
                        "phone":admin.contact_no,
                        "sequence": 1,
                        "aadhaar_last_four_digit":admin.aadhaar_card_number[-4:] if admin.aadhaar_card_number else None,
                        "sign_positions": []
                    }
                ]
                    
                verification_id=request.data.get('verification_id')
                # auth_type = request.data.get('auth_type')
                # expiry_in_days=request.data.get('expiry_in_days')
                # signers=request.data.get('signers')
                redirect_url = request.data.get('redirect_url')
                notification_modes = request.data.get('notification_modes',[])

                payload = {
                    'document_id': document_id,
                    "verification_id": verification_id,
                    "document_id": document_id,
                    "auth_type": 'AADHAAR',
                    "expiry_in_days": '2',
                    "signers": signers,
                    "redirect_url": redirect_url,
                    "notification_modes": notification_modes
                }

                esign_url = "https://your-esign-service.com/create_esign_request"

                headers = {
                    "accept": "application/json",
                    "content-type": "application/json"
                }

                try:
                    esign_response = requests.post(esign_url, headers=headers, data=json.dumps(payload))
                    esign_response_data = esign_response.json()

                    return Response(
                        esign_response_data,
                        status=esign_response.status_code
                    )

                except requests.RequestException as e:
                    return Response(
                        {'status': 'error', 'message': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                return Response(
                    {'status': 'fail', 'message': response_data.get('message', 'Unknown error occurred.')},
                    status=response.status_code
                )
        except requests.RequestException as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminServicesChargesAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Extract request data
            data = request.data
            sp_id = data.get('sp_id', None)
            admin_id = data.get('admin_id')
            service_id = data.get('service_id', None)
            hsn_sac_id = data.get('hsn_sac_id', None)
            search_txt = data.get('search', None)
            start_date = data.get('start_date', None)
            end_date = data.get('end_date', str(datetime.now().date()))
            page_number = data.get('page_number', 1)
            page_size = data.get('page_size', 10)
            # Validate required fields
            if not admin_id or not str(admin_id).isdigit():
                return self._error_response('Valid admin_id is required.')

            if not page_size or not str(page_size).isdigit() or int(page_size) <= 0:
                return self._error_response('Invalid page_size.')

            if not str(page_number).isdigit() or int(page_number) <= 0:
                return self._error_response('Invalid page_number.')

            admin_id = int(admin_id)
            page_number = int(page_number)
            page_size = int(page_size)

            # Validate numeric inputs
            for field, name in [(sp_id, 'sp_id'), (service_id, 'service_id'), (hsn_sac_id, 'hsn_sac_id')]:
                if field and not str(field).isdigit():
                    return self._error_response(f'{name} must contain only digits.')

            # Fetch user and admin details
            try:
                user = PortalUser.objects.get(id=admin_id)
            except PortalUser.DoesNotExist:
                return self._error_response('User not found.')

            try:
                admin_data = Admin.objects.get(admin_id=admin_id)
            except Admin.DoesNotExist:
                return self._error_response('Admin not found.')

            # Filter ServiceProvider queryset
            queryset = self._filter_queryset(start_date, end_date, sp_id, service_id, hsn_sac_id, search_txt)
            
            # Apply pagination
            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({'status': 'fail', 'message': 'Page not found.', 'data': {}}, status=status.HTTP_404_NOT_FOUND)
            
            # Process service provider data
            service_provider_data = self._process_service_providers(page_obj, admin_data, user)

            # Construct paginated response
            paginated_response = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': service_provider_data
            }
            
            return Response({'status': 'success', 'message': 'Service Provider Data with Charges', 'data': paginated_response}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _filter_queryset(self, start_date, end_date, sp_id, service_id, hsn_sac_id, search_txt):
        queryset = ServiceProvider.objects.filter(is_deleted=False, is_deactive=False)
        if start_date:
            queryset = queryset.filter(created_at__date__range=[start_date, end_date])
        if sp_id:
            queryset = queryset.filter(pk=sp_id)
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        if hsn_sac_id:
            queryset = queryset.filter(hsn_sac=hsn_sac_id)
        if search_txt:
            queryset = queryset.filter(
                Q(service_id__service_name__icontains=search_txt) |
                Q(sp_name__icontains=search_txt) |
                Q(label__icontains=search_txt) |
                Q(hsn_sac__hsnsac_code__icontains=search_txt)
            )
        return queryset.order_by('-pk')

    def _process_service_providers(self, page_obj, admin_data, user):
        service_provider_data = []
        sub_service_provider_mapping = {}

        for provider in page_obj:
            
            charges = self._get_charges(provider, admin_data)
            
            service_provider_id = AdServiceProvider.objects.filter(sp_id=provider.sp_id).first()
            
            if service_provider_id:
                if not service_provider_id.is_table_config:
                    # if not service_provider_id.sa_provided and service_provider_id.is_deactive: --- change
                    if not service_provider_id.sa_provided:
                        is_user_service_provider = False
                    else:
                        is_user_service_provider = True
                else:
                    if not service_provider_id.is_deactive:
                        is_user_service_provider = True
                    else:
                        is_user_service_provider = False
            else:
                is_user_service_provider = True
            # is_user_service_provider = not service_provider_id or service_provider_id.is_deactive

            if provider.parent_id is None:
                service_provider_data.append({
                    'parent_id': None,
                    'is_user_service_provider': is_user_service_provider,
                    'sub_service_provider': [],
                    'sp_id': provider.sp_id,
                    'service_name': provider.service_id.service_name if provider.service_id else None,
                    'provider_name': provider.sp_name,
                    'provider_label': provider.label,
                    'tds_rate': provider.tds_rate,
                    'hsn_sac': provider.hsn_sac.hsnsac_id if provider.hsn_sac else None,
                    'hsn_sac_code': provider.hsn_sac.hsnsac_code if provider.hsn_sac else None,
                    'tax_rate': provider.hsn_sac.tax_rate if provider.hsn_sac else None,
                    'tds_type': provider.tds_type,
                    'charges': charges,
                    'is_global': provider.service_id.is_global if provider.service_id else None,
                })
            else:
                if provider.parent_id not in sub_service_provider_mapping:
                    sub_service_provider_mapping[provider.parent_id] = {
                        'parent_id': provider.parent_id,
                        'sub_service_provider': []
                    }
                sub_service_provider_mapping[provider.parent_id]['sub_service_provider'].append({
                    'sp_id': provider.sp_id,
                    'is_user_service_provider': is_user_service_provider,
                    'service_name': provider.service_id.service_name if provider.service_id else None,
                    'provider_name': provider.sp_name,
                    'provider_label': provider.label,
                    'tds_rate': provider.tds_rate,
                    'hsn_sac': provider.hsn_sac.hsnsac_id if provider.hsn_sac else None,
                    'hsn_sac_code': provider.hsn_sac.hsnsac_code if provider.hsn_sac else None,
                    'tax_rate': provider.hsn_sac.tax_rate if provider.hsn_sac else None,
                    'tds_type': provider.tds_type,
                    'charges': charges,
                    'is_global': provider.service_id.is_global if provider.service_id else None,
                })

        for _, data in sub_service_provider_mapping.items():
            service_provider_data.append(data)
        return service_provider_data

    def _get_charges(self, provider, admin_data):
        charges = []
        if provider.sp_id != 3 and provider.sp_id != 4:
            admin_charges = AdminService.objects.filter(admin=admin_data, service_provider=provider)
            if admin_charges.exists():
                defualt_charges = Charges.objects.filter(service_provider=provider, charge_category='to_us')
                for charge_data in admin_charges:
                    for charge in charge_data.charges:
                        charges.append({
                            'charge_type': charge['charge_type'],
                            'minimum': charge['minimum'],
                            'maximum': charge['maximum'],
                            'rate_type': charge['rate_type'],
                            'rate': charge['rate'],
                            'charge_categoy': charge['charge_categoy']
                        })
                for charge_data in defualt_charges:
                    charges.append({
                        'charge_type': charge_data.charges_type,
                        'minimum': charge_data.minimum,
                        'maximum': charge_data.maximum,
                        'rate_type': charge_data.rate_type,
                        'rate': charge_data.rate,
                        'charge_categoy': charge_data.charge_category
                    })
            else:
                # Rakshit start
                default_charges = Charges.objects.filter(service_provider=provider)
                # changes [, charge_category='to_provide']
                # Rakshit end
                for charge in default_charges:
                    charges.append({
                        'charge_type': charge.charges_type,
                        'minimum': charge.minimum,
                        'maximum': charge.maximum,
                        'rate_type': charge.rate_type,
                        'rate': charge.rate,
                        'charge_categoy': charge.charge_category
                    })
        
        return charges

    def _error_response(self, message):
        return Response({'status': 'fail', 'message': message}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        print('request.data', request.data)
        try:
            if 'admin_id' in request.data and 'sp_id' in request.data and 'charges' in request.data:
                return self.update_admin_charges(request)
            elif 'admin_id' in request.data and 'sp_id' in request.data:
                print('-----------1')
                return self.active_deactive_service_charges(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def toggle_activation(self, instance, activate, success_message, deactivate_message, plateform_fee, plateform_fee_type, credentials_json):
        if activate:
            instance.sa_provided = True
            instance.plateform_fee = plateform_fee
            instance.plateform_fee_type = plateform_fee_type
            instance.credentials_json = credentials_json
            instance.save()
            return {'status': 'success', 'message': success_message}
        else:
            instance.sa_provided = False
            instance.save()
            return {'status': 'success', 'message': deactivate_message}

    def setup_hsn_code(self, hsn_code, created_by):
        try:
            return AdHSNSAC.objects.get(hsnsac_code=hsn_code.hsnsac_code)
        except AdHSNSAC.DoesNotExist:
            return AdHSNSAC.objects.create(
                hsnsac_code=hsn_code.hsnsac_code,
                tax_rate=hsn_code.tax_rate,
                description=hsn_code.description,
                created_by=created_by,
            )

    @transaction.atomic
    def active_deactive_service_charges(self, request):
        sp_id = request.data.get('sp_id')
        admin_id = request.data.get('admin_id')
        try:
            # Validate Admin and Service Provider
            portal_user = PortalUser.objects.get(id=admin_id)
            admin_data = Admin.objects.get(admin_id=admin_id)
            if portal_user.pu_status in ['PENDING', 'REJECT']:
                return Response({'status': 'fail', 'message': 'Account not approved. Contact support.'}, status=status.HTTP_400_BAD_REQUEST)
            print('=============')
            service_provider = ServiceProvider.objects.get(sp_id=sp_id)
            service_data = SaService.objects.filter(service_id=service_provider.service_id.service_id).first()
            print('service_data', service_data)
            # Handle Non-Global Services
            if not service_data.is_global or not service_provider.is_table_config:
                hsn_code = HSNSAC.objects.get(hsnsac_id=service_provider.hsn_sac.hsnsac_id)
                ad_hsn = self.setup_hsn_code(hsn_code, portal_user)

                charges = Charges.objects.filter(service_provider_id=sp_id, charge_category='to_provide')
                ad_crg = AdCharges.objects.filter(service_provider_id=sp_id, charge_category='to_us')
                sa_ad_crg = AdminService.objects.filter(service_provider_id=sp_id, admin_id=admin_id)
                for charge in charges:
                    if not ad_crg:
                        AdCharges.objects.create(
                            minimum=charge.minimum,
                            maximum=charge.maximum,
                            charges_type=charge.charges_type,
                            rate_type=charge.rate_type,
                            rate=charge.rate,
                            charge_category='to_us',
                            service_provider_id=sp_id,
                            created_by=portal_user
                        )
                    if not sa_ad_crg:
                        charges_data = [{
                            'charge_type': charge.charges_type,
                            'minimum': float(charge.minimum) if isinstance(charge.minimum, Decimal) else charge.minimum,
                            'maximum': float(charge.maximum) if isinstance(charge.maximum, Decimal) else charge.maximum,
                            'rate_type': charge.rate_type,
                            'rate': float(charge.rate) if isinstance(charge.rate, Decimal) else charge.rate,
                            'charge_categoy': charge.charge_category
                        }]
                        ad_ser = AdminService.objects.create(
                            admin_id=admin_id,
                            service=service_data,
                            charges=charges_data,
                            rate=charge.rate,
                            service_provider_id=sp_id
                        )

                # ad_sp = AdServiceProvider.objects.filter(sp_name=service_provider.sp_name).first() -- change
                ad_sp = AdServiceProvider.objects.filter(sp_id=service_provider.sp_id).first()
                if ad_sp:
                    message = self.toggle_activation(
                        ad_sp, not ad_sp.sa_provided,
                        'Service Provider Activated Successfully.',
                        'Service Provider Deactivated Successfully.',
                        service_provider.plateform_fee, service_provider.plateform_fee_type, service_provider.credentials_json
                    )
                else:
                    message = {'status': 'error', 'message': 'Service Provider not found.'}

                return Response(message, status=status.HTTP_200_OK)

            print('service_provider.sp_id', service_provider.sp_id)
            # Handle BBPS Services
            if service_provider.sp_id == 3:
                ad_sp = AdServiceProvider.objects.filter(sp_id=service_provider.sp_id).first()
                return self.insert_bbps_category(ad_sp, service_provider)
            elif service_provider.sp_id == 4:
                ad_sp = AdServiceProvider.objects.filter(sp_id=service_provider.sp_id).first()
                print('ad_sp', ad_sp)
                return self.insert_recharge_category(ad_sp, service_provider)
            elif service_provider.sp_id == 6:
                ad_sp = AdServiceProvider.objects.filter(sp_id=service_provider.sp_id).first()
                return self.insert_cashfree_pg_configed(ad_sp, service_provider)
            elif service_provider.sp_id == 7:
                ad_sp = AdServiceProvider.objects.filter(sp_id=service_provider.sp_id).first()
                return self.insert_phonepe_pg_configed(ad_sp, service_provider)
            else:
                return Response({'status': 'error', 'message': 'Unsupported service type.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def insert_phonepe_pg_configed(self, ad_sp, service_provider):
        status_message = ''
        try:
            configed = SaPhonePePgConfiged.objects.filter(is_deleted=False, is_deactive=False)
            for conf in configed:
                # Ensure `to_us_charges` exists
                if conf.to_us_charges is None:
                    continue

                # Fetch or create the BBPS category
                pp_pg_configed, created = PhonePeConfiged.objects.get_or_create(
                    payment_method=conf.payment_method,
                    defaults={
                        'to_us_charges': conf.to_us_charges,
                        'is_deactive': False,
                        'sa_provided': True,
                    }
                )

                if not created:  # If category already exists

                    # Update `to_us_charges` if not set
                    if not pp_pg_configed.to_us_charges:
                        pp_pg_configed.to_us_charges = conf.to_us_charges
                        pp_pg_configed.save()

                    # Toggle activation based on `sa_provided`
                    pp_pg_configed.sa_provided = not pp_pg_configed.sa_provided
                    pp_pg_configed.save()

                    ad_sp.sa_provided = pp_pg_configed.sa_provided
                    ad_sp.plateform_fee = service_provider.plateform_fee
                    ad_sp.plateform_fee_type = service_provider.plateform_fee_type
                    ad_sp.credentials_json = service_provider.credentials_json
                    ad_sp.save()
                    status_message = (
                        "Service Provider Activated Successfully."
                        if pp_pg_configed.sa_provided
                        else "Service Provider Deactivated Successfully."
                    )
                else:
                    status_message = "Cashfree Payment Getway Added Successfully."
            return Response({'status': 'success', 'message': status_message}, status=status.HTTP_200_OK)

        except Exception as e:
            error_message = f"Internal server error: {str(e)}"
            return Response({'status': 'error', 'message': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def insert_cashfree_pg_configed(self, ad_sp, service_provider):
        status_message = ''
        try:
            configed = SaPgConfiged.objects.filter(is_deleted=False)

            for conf in configed:
                # Ensure `to_us_charges` exists
                if conf.to_us_charges is None:
                    continue

                # Fetch or create the BBPS category
                cf_pg_configed, created = AdCfPgConfiged.objects.get_or_create(
                    payment_method=conf.payment_method,
                    card_type=conf.card_type,
                    card_network=conf.card_network,
                    card_sub_type=conf.card_sub_type,
                    defaults={
                        'to_us_charges': conf.to_us_charges,
                        'is_deactive': False,
                        'sa_provided': True,
                    }
                )

                if not created:  # If category already exists
                    # Update `to_us_charges` if not set
                    if not cf_pg_configed.to_us_charges:
                        cf_pg_configed.to_us_charges = conf.to_us_charges
                        cf_pg_configed.save()
                    # Toggle activation based on `sa_provided`
                    cf_pg_configed.sa_provided = not cf_pg_configed.sa_provided
                    cf_pg_configed.save()

                    ad_sp.sa_provided = cf_pg_configed.sa_provided
                    ad_sp.plateform_fee = service_provider.plateform_fee
                    ad_sp.plateform_fee_type = service_provider.plateform_fee_type
                    ad_sp.credentials_json = service_provider.credentials_json
                    ad_sp.save()
                    status_message = (
                        "Service Provider Activated Successfully."
                        if cf_pg_configed.sa_provided
                        else "Service Provider Deactivated Successfully."
                    )
                else:
                    status_message = "Cashfree Payment Getway Added Successfully."
            return Response({'status': 'success', 'message': status_message}, status=status.HTTP_200_OK)

        except Exception as e:
            error_message = f"Internal server error: {str(e)}"
            return Response({'status': 'error', 'message': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def insert_bbps_category(self, ad_sp, service_provider):
        try:
            categories = SaBBPSBillerCategory.objects.filter(is_deleted=False, is_deactive=False)
            for category in categories:
                # Ensure `to_us_charges` exists
                if category.to_us_charges is None:
                    continue

                # Fetch or create the BBPS category
                bbps_category, created = BBPSBillerCategory.objects.get_or_create(
                    ss_name=category.ss_name,
                    defaults={
                        'to_us_charges': category.to_us_charges,
                        'is_deactive': False,
                        'sa_provided': True,
                    }
                )

                if not created:  # If category already exists
                    # Update `to_us_charges` if not set
                    if not bbps_category.to_us_charges:
                        bbps_category.to_us_charges = category.to_us_charges
                        bbps_category.save()

                    # Toggle activation based on `sa_provided`
                    bbps_category.sa_provided = not bbps_category.sa_provided
                    bbps_category.save()

                    ad_sp.sa_provided = bbps_category.sa_provided
                    ad_sp.plateform_fee = service_provider.plateform_fee
                    ad_sp.plateform_fee_type = service_provider.plateform_fee_type
                    ad_sp.credentials_json = service_provider.credentials_json
                    ad_sp.save()

                    status_message = (
                        "Service Provider Activated Successfully."
                        if bbps_category.sa_provided
                        else "Service Provider Deactivated Successfully."
                    )
                else:
                    status_message = "Category Added Successfully."
            return Response({'status': 'success', 'message': status_message}, status=status.HTTP_200_OK)

        except Exception as e:
            error_message = f"Internal server error: {str(e)}"
            return Response({'status': 'error', 'message': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def insert_recharge_category(self, ad_sp, service_provider):
        status_message = ''
        try:
            categories = SaOprators.objects.filter(is_deleted=False, is_deactive=False)
            print('categories', categories)
            for category in categories:
                # Ensure `to_us_charges` exists
                if category.to_us_charges is None:
                    continue
                
                # Handle existing or new category
                bbps_category, created = Oprators.objects.get_or_create(
                    ss_name=category.ss_name,
                    operator_code=category.operator_code,
                    operator_type=category.operator_type,
                    defaults={
                        'to_us_charges': category.to_us_charges,
                        'is_deactive': False,
                        'sa_provided': True,
                    }
                )
                print('------->', created)
                if not created:  # If category already exists
                    # Update `to_us_charges` if not set
                    print('------->', bbps_category.to_us_charges)
                    if not bbps_category.to_us_charges:
                        bbps_category.to_us_charges = category.to_us_charges
                        bbps_category.save()
                    print('=====')
                    # Toggle activation based on `sa_provided`
                    bbps_category.sa_provided = not bbps_category.sa_provided
                    bbps_category.save()

                    ad_sp.sa_provided = bbps_category.sa_provided
                    ad_sp.plateform_fee = service_provider.plateform_fee
                    ad_sp.plateform_fee_type = service_provider.plateform_fee_type
                    ad_sp.credentials_json = service_provider.credentials_json
                    ad_sp.save()
                    print('-------->>>>>>>>>')
                    status_message = (
                        "Service Provider Activated Successfully."
                        if bbps_category.sa_provided
                        else "Service Provider Deactivated Successfully."
                    )
                    print('status_message', status_message)
                else:
                    status_message = "Category Added Successfully."
            return Response({'status': 'success', 'message': status_message}, status=status.HTTP_200_OK)

        except Exception as e:
            error_message = f"Internal server error: {str(e)}"
            return Response({'status': 'error', 'message': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def update_admin_charges(self, request):
        sp_id = request.data.get('sp_id')
        admin_id = request.data.get('admin_id')
        charges = request.data.get('charges')
        try:
            # Validate and parse charges
            try:
                charges = json.loads(charges)
                if not isinstance(charges, list) or not charges:
                    raise ValidationError("Charges should be a non-empty list of charge objects.")
            except json.JSONDecodeError:
                return Response({'status': 'error', 'message': "Invalid JSON format for charges."}, status=status.HTTP_400_BAD_REQUEST)

            # Filter charges for "to_provide" category
            to_provide_charges = [charge for charge in charges if charge.get('charge_categoy') == 'to_provide']
            if not to_provide_charges:
                return Response({'status': 'fail', 'message': 'No charges found for category "to_provide".'}, status=status.HTTP_404_NOT_FOUND)

            # Fetch required objects
            try:
                admin_data = Admin.objects.get(admin_id=admin_id)
                portal_user = PortalUser.objects.get(id=admin_id)
                sp_data = ServiceProvider.objects.get(sp_id=sp_id)
            except Admin.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Admin not found.'}, status=status.HTTP_404_NOT_FOUND)
            except PortalUser.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Portal user not found.'}, status=status.HTTP_404_NOT_FOUND)
            except ServiceProvider.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Service provider not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Update AdminService
            admin_services = AdminService.objects.filter(admin=admin_data, service_provider=sp_data)
            if not admin_services.exists():
                return Response({'status': 'fail', 'message': 'Admin services not found.'}, status=status.HTTP_404_NOT_FOUND)

            for admin_service in admin_services:
                updated_charges = []
                charges_updated = False
                new_rate = None

                for charge in admin_service.charges:
                    if charge.get('charge_categoy') == 'to_provide':
                        for new_charge in to_provide_charges:
                            if charge.get('minimum') == new_charge.get('minimum') and charge.get('maximum') == new_charge.get('maximum'):
                                if charge.get('rate') != new_charge.get('rate'):
                                    charge['rate'] = new_charge.get('rate')
                                    charges_updated = True
                                    new_rate = new_charge.get('rate')  # Update rate field with the new rate
                    updated_charges.append(charge)

                if charges_updated:
                    admin_service.charges = updated_charges
                    if new_rate is not None:
                        admin_service.rate = new_rate
                    admin_service.save()

            # Update AdCharges
            admin_service_provider = AdServiceProvider.objects.filter(sp_id=sp_id)
            if not admin_service_provider.exists():
                return Response({'status': 'fail', 'message': 'Admin service providers not found.'}, status=status.HTTP_404_NOT_FOUND)

            admin_charges = AdCharges.objects.filter(service_provider__in=admin_service_provider, created_by=portal_user)
            if not admin_charges.exists():
                return Response({'status': 'fail', 'message': 'Admin charges not found.'}, status=status.HTTP_404_NOT_FOUND)

            for admin_charge in admin_charges:
                for new_charge in to_provide_charges:
                    if admin_charge.minimum == new_charge.get('minimum') and admin_charge.maximum == new_charge.get('maximum'):
                        if admin_charge.rate != new_charge.get('rate'):
                            admin_charge.rate = new_charge.get('rate')
                            admin_charge.save()

            return Response({'status': 'success', 'message': 'Charges updated successfully.'}, status=status.HTTP_200_OK)

        except ValidationError as ve:
            return Response({'status': 'error', 'message': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HSNSACApiView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_data(request)
            elif 'hsnsac_code' in request.data and 'tax_rate' in request.data:
                return self.create_hsnsac(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    
    def create_hsnsac(self, request):
        try:
            with transaction.atomic():
                request_data = request.data.copy()
                
                serializer = HSNSACSerializer(data=request_data, context={'request': request})
                # Check if the provided data is valid
                if serializer.is_valid(raise_exception=True):
                    # Save the HSNSAC entry with the created_by field set to the authenticated user
                    hsnsac = serializer.save(created_by=request.user)

                   
                    activity = SaUserActivity.objects.create(
                        table_id=hsnsac.pk,
                        table_name='HSNSAC',
                        ua_action='create',
                        ua_description='Created a new HSNSAC entry',
                        created_by=request.user
                    )
                    activity.save()

                    response_data = {
                        'status': 'success',
                        'message': 'HSNSAC Entry Created Successfully'
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
            hsnsac_id = request.data.get('hsnsac_id')
            page_size = request.data.get('page_size')
            page_number = request.data.get('page_number', 1)
            order_by = request.data.get('order_by',"descending")
            search_query = request.data.get('search', None)

            # Validate page_size and page_number
            if not page_size or not page_size.isdigit() or int(page_size) <= 0:
                raise ValidationError("page_size parameter is required and must be a positive integer.")

            if not page_number or not page_number.isdigit() or int(page_number) <= 0:
                raise ValidationError("page_number parameter is required and must be a positive integer.")

            queryset = HSNSAC.objects.filter(is_deleted=False).order_by('-pk')

            if hsnsac_id:
                queryset = queryset.filter(pk=hsnsac_id)
            if search_query:
                queryset = queryset.filter(
                    Q(hsnsac_code__icontains=search_query) |
                    Q(tax_rate__icontains=search_query)
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
                        'message': 'HSNSAC Data not found.',
                        'data': paginated_response_data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                serializer = HSNSACSerializer(page_obj.object_list, many=True, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted","updated_by", "created_by"]})
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

            serializer = HSNSACSerializer(queryset, many=True, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted","updated_by", "created_by"]})
            response_data = {
                'status': 'success',
                'message': 'HSNSAC Data',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except (ValueError, Exception) as e:
            return Response({
                'status': 'fail',
                'message': str(e),
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)
        

    def put(self, request):
        hsnsac_id = request.data.get("hsnsac_id")
        
        # Check if hsnsac_id is provided
        if not hsnsac_id:
            response_data = {
                'status': 'fail',
                'message': "hsnsac_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                try:
                    # Retrieve the HSNSAC object by ID
                    hsnsac = HSNSAC.objects.get(hsnsac_id=hsnsac_id, is_deleted=False)
                    
                    # Check if is_deactive flag is provided and handle accordingly
                    if 'is_deactive' in request.data:
                        is_deactive = request.data['is_deactive']
                        is_deactive = True if is_deactive == "true" else False if is_deactive == "false" else None
                        hsnsac.is_deactive = is_deactive
                        hsnsac.updated_at = datetime.now()
                        hsnsac.updated_by = request.user
                        hsnsac.save()
                        
                        if is_deactive:
                            message = 'HSNSAC Entry Deactivated Successfully'
                        else:
                            message = 'HSNSAC Entry Activated Successfully'
                    else:
                        # Initialize the serializer with the existing HSNSAC object and the new data
                        serializer = HSNSACSerializer(hsnsac, data=request.data, partial=True, context={'request': request})
                        
                        # Check if the provided data is valid
                        if serializer.is_valid():
                            # Save the updated HSNSAC with partial data
                            serializer.save(updated_at=datetime.now(), updated_by=request.user)
                            message = 'HSNSAC Entry Updated Successfully'
                        else:
                            # If data is invalid, return the error messages
                            response_data = {
                                'status': 'fail',
                                'message': f'{serializer.errors}'
                            }
                            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Log the activity
                    activity = SaUserActivity(
                        table_id=hsnsac.pk,  # ID of the created HSNSAC entry
                        table_name='HSNSAC',  # Name of the model
                        ua_action='Update',  # Action performed
                        ua_description=f'Updated HSNSAC entry with ID {hsnsac.pk}',  # Action description
                        created_by=request.user  # Current user performing the action
                    )
                    activity.save()
                    
                    # Return a success response with the appropriate message
                    response_data = {
                        'status': 'success',
                        'message': message
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
            
                # Handle case where HSNSAC entry is not found
                except HSNSAC.DoesNotExist:
                    response_data = {
                        'status': 'fail',
                        'message': "HSNSAC entry not found."
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
        """
        Delete an HSNSAC entry.

        This endpoint allows users to delete an HSNSAC entry by providing its ID. The deletion process involves marking the entry as deleted rather than physically removing it from the database.

        - **Authentication**: Requires user authentication (`permission_classes = [IsAuthenticated]`).

        ### Process
        1. **Parameter Validation**:
            - Checks if the `hsnsac_id` is provided in the request. If not, returns a `400 (Bad Request)` response.

        2. **HSNSAC Retrieval**:
            - Retrieves the `HSNSAC` object by its ID if it exists and is not marked as deleted. If the `HSNSAC` with the given ID does not exist or is already deleted, returns a `404 (Not Found)` response.

        3. **HSNSAC Deletion**:
            - Marks the `HSNSAC` object as deleted by setting the `is_deleted` flag to `True` and saves the changes.

        4. **Activity Logging**:
            - Logs the deletion action in the `SaUserActivity` model with details such as the ID of the `HSNSAC`, the action performed, and the user who performed the action.

        5. **Error Handling**:
            - Returns a `500 (Internal Server Error)` response for any unexpected server-side issues during the process.

        ### Swagger Documentation
        - **Operation**: "Delete an HSNSAC entry."
        - **Parameters**:
            - `hsnsac_id`: Required integer parameter in the form for the ID of the HSNSAC entry to delete.
        - **Responses**:
            - `200 (OK)`: Indicates the HSNSAC entry was successfully deleted.
            - `404 (Not Found)`: Indicates that the HSNSAC entry with the given ID was not found.
            - `500 (Internal Server Error)`: Indicates an error occurred on the server while processing the request.
        - **Security**: Bearer token authentication is required.

        ### Usage
        - To delete an HSNSAC entry, send a DELETE request to the endpoint with the `hsnsac_id` parameter included in the form data.

        ### Example
        ```http
        DELETE /hsnsac/
        Content-Type: application/x-www-form-urlencoded
        Authorization: Bearer <your_token_here>

        hsnsac_id=123
        ```

        - **Success Response**:
        ```json
        {
            "status": "success",
            "message": "HSNSAC Deleted Successfully"
        }
        ```

        - **Error Responses**:
            - `400 Bad Request`:
            ```json
            {
                "status": "fail",
                "message": "hsnsac_id is required."
            }
            ```
            - `404 Not Found`:
            ```json
            {
                "status": "fail",
                "message": "HSNSAC not found."
            }
            ```
            - `500 Internal Server Error`:
            ```json
            {
                "status": "error",
                "message": "Error message"
            }
            ```
        """
        hsnsac_id = request.data.get("hsnsac_id")
        
        # Check if hsnsac_id is provided
        if not hsnsac_id:
            response_data = {
                'status': 'fail',
                'message': "hsnsac_id is required."
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Retrieve the HSNSAC object by ID
                hsnsac = HSNSAC.objects.get(hsnsac_id=hsnsac_id, is_deleted=False)
                # Mark the HSNSAC object as deleted
                hsnsac.is_deleted = True
                hsnsac.save()
                # Log the activity
                activity = SaUserActivity(
                    table_id=hsnsac.pk,  # ID of the HSNSAC
                    table_name='HSNSAC',  # Name of the model
                    ua_action='Delete',  # Action performed
                    ua_description=f'Deleted HSNSAC with ID {hsnsac.pk}',  # Action description
                    created_by=request.user  # Current user performing the action
                )
                activity.save()
                
                response_data = {
                    'status': 'success',
                    'message': 'HSNSAC Deleted Successfully'
                }
                # Return a success response
                return Response(response_data, status=status.HTTP_200_OK)
        except HSNSAC.DoesNotExist:
            # Handle case where HSNSAC is not found
            response_data = {
                'status': 'fail',
                'message': "HSNSAC not found."
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Handle any exceptions and return an error response
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RequiredDocumentListAPI(APIView):
    """
    Handles creation, retrieval, and deletion of DocumentGroup objects, and provides pagination and filtering for admin entries.

    This endpoint requires authentication with JWT token.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsAdmin | IsRetailer | IsSuperAdmin]


    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_document_list(request)
            elif 'document_name' in request.data and 'label_name' in request.data:
                return self.create_documentlist(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
    def create_documentlist(self, request):
        try:
            with transaction.atomic():
        
                request_data = request.data

                # Create a serializer instance with the data
                serializer = DocumentListSerializer(data=request_data)

                # Validate and save the data
                if serializer.is_valid():
                    document_group = serializer.save(created_by=request.user)

                    activity = SaUserActivity(
                        table_id=document_group.rdl_id, 
                        table_name='required_document_list',
                        ua_action='create',
                        created_by=request.user,
                        response_data=request_data,
                    )
                    activity.save()

                    response_data = {
                        'status': 'success',
                        'message': 'Required Document List Created Successfully',
                        # 'data': serializer.data
                    }
                    return Response(response_data, status=status.HTTP_201_CREATED)

                
                error_messages = []
                for field, errors in serializer.errors.items():
                    for error in errors:
                        error_messages.append(str(error))

                response_data = {
                    'status': 'fail',
                    'message': ' '.join(error_messages)
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as e:
            response_data = {
                'status': 'fail',
                'message': str(e.detail)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
          
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            with transaction.atomic():
              
                rdl_id = request.data.get('rdl_id')
                required_document = RequiredDocumentList.objects.filter(rdl_id=rdl_id).first()

                if not required_document:
                    return Response({
                        'status': 'fail',
                        'message': 'Document List not found'
                    }, status=status.HTTP_404_NOT_FOUND)

                if required_document.is_deleted:
                    return Response({
                        'status': 'fail',
                        'message': 'Cannot update a deleted record'
                    }, status=status.HTTP_400_BAD_REQUEST)

              
                serializer = DocumentListSerializer(required_document, data=request.data, partial=True, context={'request': request})

                if serializer.is_valid():
                    updated_document = serializer.save(updated_at=datetime.now())

                    activity = SaUserActivity(
                        table_id=updated_document.pk,
                        table_name='required_document_list',
                        ua_action='update',
                        ua_description=f'Updated Document List "{updated_document.label_name}"',
                        created_by=request.user,
                        request_data=request.data,
                        response_data=serializer.data,
                    )
                    activity.save()

                    response_data = {
                        'status': 'success',
                        'message': 'Required Document List Updated Successfully'
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                response_data = {
                    'status': 'fail',
                    'message': next(iter(serializer.errors.values()))[0]
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_document_list(self, request):
        """
        Handles POST requests to search, filter, and retrieve `RequiredDocumentList` objects.

        This endpoint allows clients to search, filter, and retrieve `RequiredDocumentList` objects using various criteria such as search queries, filtering fields, and date ranges. It also supports pagination to manage large datasets.

        **Process**:
        - Retrieves and validates pagination parameters (`page_size`, `page_number`).
        - If an `rdl_id` is provided, it fetches the specific `RequiredDocumentList` object corresponding to that ID.
        - If no `rdl_id` is provided, it filters the queryset based on the provided criteria, such as:
            - Date range (`start_date`, `end_date`).
            - Specific field filtering (`filter_field`, `filter_value`).
            - Search queries (`search`).
        - Orders the queryset based on the `order_by` parameter (either 'ascending' or 'descending').
        - Paginates the queryset based on `page_size` and `page_number`.
        - Serializes the filtered and paginated data and returns it in the response.

        **Request Parameters**:
        - `rdl_id` (optional): The ID of a specific `RequiredDocumentList` to retrieve. If provided, other filters are ignored.
        - `search` (optional): A search query string to filter results based on the `label_name` or `created_by` fields.
        - `filter_field` (optional): The name of the field to apply a filter on (e.g., `label_name`).
        - `filter_value` (optional): The value to filter the `filter_field` by.
        - `order_by` (optional): Determines the order of the results. Accepts 'ascending' or 'descending' (default is 'ascending').
        - `start_date` (optional): Start date for filtering results by the `created_at` field.
        - `end_date` (optional): End date for filtering results by the `created_at` field.
        - `page_size` (optional): The number of results per page (default is 10).
        - `page_number` (optional): The page number to retrieve (default is 1).

        **Response Fields**:
        - `status`: Indicates the success or failure of the request ('success', 'fail', or 'error').
        - `message`: A descriptive message related to the request outcome.
        - `data`: Contains the serialized data if the request is successful, including pagination details like `total_pages`, `current_page`, `total_items`, and the `results` list.

        **Usage**:
        - Send a POST request with the desired search criteria and pagination parameters in the request body.
        - Include valid authentication credentials (`Bearer` token) in the request header.
        - Handle responses based on the returned status and access the filtered and paginated data or error message as required.

        **Example Usage**:
        To search for `RequiredDocumentList` objects created by a user named 'admin' and retrieve results in descending order:
        
        ```
        POST /api/required_document_list/
        {
            "search": "admin",
            "order_by": "descending",
            "page_size": 5,
            "page_number": 2
        }
        ```

        **Error Handling**:
        - Returns a `400 Bad Request` if pagination parameters are invalid (e.g., non-positive integers).
        - Returns a `404 Not Found` if the `rdl_id` does not correspond to any `RequiredDocumentList`.
        - Returns a `200 OK` with an appropriate message if no data matches the search and filtering criteria.

        **Internal Server Error**:
        - Returns a `500 Internal Server Error` if any unexpected exception occurs during processing, with the error details included in the response.

        """

        try:
            # Retrieve request parameters
            rdl_id = request.data.get('rdl_id')
            search_query = request.data.get('search', None)
            filter_field = request.data.get('filter_field', None)
            filter_value = request.data.get('filter_value', None)
            order_by = request.data.get('order_by', "ascending")
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            page_size = request.data.get('page_size', 10)
            page_number = request.data.get('page_number', 1)

            # Validate pagination parameters
            if not str(page_size).isdigit() or int(page_size) <= 0:
                return Response({
                    'status': 'fail',
                    'message': 'page_size parameter is required and must be a positive integer.',
                    'data': {}
                }, status=status.HTTP_400_BAD_REQUEST)

            if not str(page_number).isdigit() or int(page_number) <= 0:
                return Response({
                    'status': 'fail',
                    'message': 'page_number parameter is required and must be a positive integer.',
                    'data': {}
                }, status=status.HTTP_400_BAD_REQUEST)

            # Fetch a specific RequiredDocumentList object if rd_id is provided
            if rdl_id:
                try:
                    document_group = RequiredDocumentList.objects.get(rdl_id=rdl_id, is_deleted=False)
                    serializer = DocumentListSerializer(
                        document_group,
                        context={'request': request, 'exclude_fields': ["created_at", "updated_at", "is_deleted", "updated_by", "created_by"]}
                    )
                    response_data = {
                        'status': 'success',
                        'message': 'Required Document List Data',
                        'data': serializer.data
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                except RequiredDocumentList.DoesNotExist:
                    return Response({
                        'status': 'fail',
                        'message': 'Required Document List not found.',
                        'data': {}
                    }, status=status.HTTP_404_NOT_FOUND)

            # Base queryset
            queryset = RequiredDocumentList.objects.filter(is_deleted=False).order_by('-pk')

            # Filter by date range if provided
            if start_date and end_date:
                start_date_parsed = parse_date(start_date)
                end_date_parsed = parse_date(end_date)
                queryset = queryset.filter(created_at__range=[start_date_parsed, end_date_parsed + timedelta(days=1)])

            # Apply filtering if filter_field and filter_value are provided
            if filter_field and filter_value:
                filter_kwargs = {f"{filter_field}__icontains": filter_value}
                queryset = queryset.filter(**filter_kwargs)

            # Apply search query if provided
            if search_query:
                queryset = queryset.filter(
                    Q(label_name__icontains=search_query) |
                    Q(created_by__username__icontains=search_query)
                )

            # Order the queryset
            if order_by == "descending":
                queryset = queryset.order_by('-pk')
            else:
                queryset = queryset.order_by('pk')

            # Check if the queryset is empty
            if not queryset.exists():
                paginated_response_data = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }
                response_data = {
                    'status': 'fail',
                    'message': 'Required Document List Data not found',
                    'data': paginated_response_data
                }
                return Response(response_data, status=status.HTTP_200_OK)

            # Paginate the queryset
            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_number,
                    'total_items': paginator.count,
                    'results': []
                }
                response_data = {
                    'status': 'success',
                    'message': 'No data found for the requested page.',
                    'data': paginated_response_data
                }
                return Response(response_data, status=status.HTTP_200_OK)

            # Serialize the paginated data
            serializer = DocumentListSerializer(
                page_obj.object_list, many=True,
                context={'request': request, 'exclude_fields': ["created_at", "updated_at", "is_deleted", "updated_by", "created_by"]}
            )
            paginated_response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': serializer.data
            }

            # Construct the success response
            response_data = {
                'status': 'success',
                'message': 'Required Document List Data',
                'data': paginated_response_data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            # Handle unexpected errors
            response_data = {
                'status': 'error',
                'message': 'Internal server error',
                'data': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    def delete(self, request):
        """
        Handles DELETE requests to soft delete a `RequiredDocumentList` object.

        This endpoint allows clients to soft delete a `RequiredDocumentList` object by marking it as deleted.
        The object is not removed from the database but is marked as deleted and thus excluded from future queries.

        **Process**:
        - Retrieves the `rdl_id` from the request data.
        - Validates the presence of the `rdl_id` parameter.
        - Attempts to fetch the `RequiredDocumentList` object corresponding to the provided `rdl_id`.
        - If the object exists and is not already deleted, marks it as deleted.
        - Logs the deletion activity in the `SaUserActivity` model.
        - Returns a success response if the object is successfully marked as deleted.

        **Request Parameters**:
        - `rdl_id` (required): The ID of the `RequiredDocumentList` to be deleted.

        **Response Fields**:
        - `status`: Indicates the success or failure of the request.
        - `message`: Descriptive message related to the request outcome.

        **Usage**:
        - Send a DELETE request with the `rdl_id` included in the request data.
        - Include valid authentication credentials (`Bearer` token) in the request header.
        - Handle responses based on the returned status and access the success or error message as required.
        """
        try:
            with transaction.atomic():
                rdl_id = request.data.get('rdl_id')
                
                if not rdl_id:
                    response_data = {
                        'status': 'fail',
                        'message': 'rdl_id parameter is required.'
                    }
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

                try:
                    document_group_data = RequiredDocumentList.objects.get(rdl_id=rdl_id, is_deleted=False)
                except RequiredDocumentList.DoesNotExist:
                    response_data = {
                        'status': 'fail',
                        'message': 'Required Document List not found.'
                    }
                    return Response(response_data, status=status.HTTP_404_NOT_FOUND)

                document_group_data.is_deleted = True
                document_group_data.save()

                # Log the deletion activity
                activity = SaUserActivity(
                    table_id=document_group_data.pk,
                    table_name='sa_document_group',
                    ua_action='delete',
                    ua_description=f'Deleted DocumentGroup "{document_group_data.label_name}"',
                    created_by=request.user,
                    request_data=request.data,
                )
                activity.save()

                response_data = {
                    'status': 'success',
                    'message': 'Required Document List Deleted Successfully'
                }
                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminServiceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_admin_service(request)
            elif 'admin' in request.data and 'service' in request.data and 'charges' in request.data:
                return self.create_admin_service(request)
            else:
                return Response({'status': 'error','message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            response_data = {
                'status': 'error',
                'message': f'{str(e)}'
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
    def create_admin_service(self, request):
        try:
            with transaction.atomic():
                service_provider_id = request.data.get("service_provider")
                if not service_provider_id:
                    raise ValidationError("service_provider is required.")

                # Initialize an empty list to store charge instances
                charges_list = []
                charges_data = request.data.get('charges', '[]')

                # Parse the JSON string into a Python list
                try:
                    charges = json.loads(charges_data)
                    if not isinstance(charges, list):
                        raise ValidationError("charges should be a list of charge objects.")
                except json.JSONDecodeError:
                    return Response({'status': 'error', 'message': "Invalid JSON format for charges"}, status=status.HTTP_400_BAD_REQUEST)

                # Process each charge in the list
                for charge_obj in charges:
                    if charge_obj.get("charge_category") != "to_provide":
                        raise ValidationError("charge_category field value must be 'to_provide'.")
                    
                    if charge_obj.get("minimum") == "null":
                        charge_obj["minimum"] = None
                    if charge_obj.get("maximum") == "null":
                        charge_obj["maximum"] = None
                    charge_obj["service_provider"] = service_provider_id

                    charges_serializer = ChargesSerializer(data=charge_obj, context={'request': request})
                    if charges_serializer.is_valid():
                        charges_instance = charges_serializer.save()
                        charges_list.append(charges_instance.pk)

                        # Log the creation activity for each charge
                        activity = SaUserActivity(
                            table_id=charges_instance.pk,
                            table_name='charges',
                            ua_action='create',
                            ua_description='charges created successfully',
                            created_by=request.user,
                            request_data=request.data,
                            response_data=charges_serializer.data
                        )
                        activity.save()
                    else:
                        return Response({
                            'status': 'error',
                            'message': charges_serializer.errors
                        }, status=status.HTTP_400_BAD_REQUEST)

                request_data = request.data.copy()
                request_data["charges"] = charges_list
                serializer = AdminServiceSerializer(data=request_data, context={'request': request})

                if serializer.is_valid():
                    admin_service_obj = serializer.save(created_by=request.user)
                    admin_service_obj.charges = charges_list
                    admin_service_obj.save()

                    # Log the activity
                    activity = SaUserActivity(
                        table_id=serializer.instance.admin_service_id,
                        table_name='admin_service',
                        ua_action='create',
                        ua_description=f'Created AdminService "{serializer.instance.admin_service_id}"',
                        created_by=request.user,
                        request_data=request_data,
                        response_data=serializer.data,
                    )
                    activity.save()

                    return Response({'status': 'success', 'message': 'AdminService Created Successfully'}, status=status.HTTP_201_CREATED)

                return Response({'status': 'fail', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    permission_classes = [IsAuthenticated]       
    
 
    def put(self, request):
        try:
            request_data = request.data.copy()
            admin_service_id = request_data.get('admin_service_id')
            if not admin_service_id:
                return Response({'status': 'fail', 'message': 'ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            

            try:
                admin_service = AdminService.objects.get(admin_service_id=admin_service_id)
            except AdminService.DoesNotExist:
                return Response({'status': 'fail', 'message': 'AdminService not found'}, status=status.HTTP_404_NOT_FOUND)

            if admin_service.is_deleted:
                return Response({'status': 'fail', 'message': 'AdminService is deleted'}, status=status.HTTP_404_NOT_FOUND)
            charges_str = request_data.get('charges', [])
            charges_list = admin_service.charges
            service_provider_id = request_data.get("service_provider",None)
            if service_provider_id and not charges_str:
                charges_ids = admin_service.charges
                for i in charges_ids:
                    try:
                        try:
                            sp_id = ServiceProvider.objects.get(pk=service_provider_id)
                        except ServiceProvider.DoesNotExist:
                            raise ValidationError(f"{service_provider_id} this id must be ServiceProvider instance id.")
                        if sp_id:
                            existing_charge_obj = Charges.objects.get(pk=i)
                            existing_charge_obj.service_provider = sp_id
                            existing_charge_obj.save()

                    except Charges.DoesNotExist:
                        return Response({'status': 'error', 'message': 'Charges not found'}, status=status.HTTP_404_NOT_FOUND)

                

            if not service_provider_id:
                service_provider_id = admin_service.service_provider.pk
            if charges_str:
                # Parse the JSON string into a Python list
                try:
                    charges = json.loads(charges_str)
                except json.JSONDecodeError:
                    return Response({'status': 'error', 'message': "Invalid JSON format for charges"}, status=status.HTTP_400_BAD_REQUEST)

                for charge in charges:
                    if charge.get("charge_category") != "to_provide" and charge.get("charge_category"):
                        raise ValidationError("charge_category field value must be 'to_provide'.")
                    if charge["minimum"] == "null":
                        charge["minimum"] = None
                    if charge["maximum"] == "null":
                        charge["maximum"] = None
                    if "charges_id" in charge:
                        charges_id = charge["charges_id"]
                        charge["service_provider"] = service_provider_id
                        if charges_id not in admin_service.charges:
                            raise ValidationError(f"The provided charges ID ({charges_id}) is not associated with the specified admin service (ID: {admin_service.pk}).")
                        try:
                            existing_charge = Charges.objects.get(pk=charges_id)
                            
                            charge_serializer = ChargesSerializer(existing_charge, data=charge, partial=True, context={'request': request})
                            if charge_serializer.is_valid():
                                charge_serializer.save(updated_by=request.user, updated_at=datetime.now())
                                
                                activity = SaUserActivity(
                                    table_id=charge_serializer.instance.pk,
                                    table_name='charges',
                                    ua_action='update',
                                    ua_description='charges updated successfully',
                                    created_by=request.user,
                                    request_data=request_data,
                                    response_data=charge_serializer.data
                                )
                                activity.save()
                            else:
                                raise Exception({'status': 'error', 'message': charge_serializer.errors})
                            
                        except Charges.DoesNotExist:
                            return Response({'status': 'error', 'message': 'Charges not found'}, status=status.HTTP_404_NOT_FOUND)
                        except Exception as e:
                            raise Exception({'status': 'error', 'message': str(e)})
                    else:
                        charge["service_provider"] = service_provider_id
                        charge_serializer = ChargesSerializer(data=charge, context={'request': request})
                        if charge_serializer.is_valid():
                            charge_instance = charge_serializer.save()
                            charges_list.append(charge_instance.pk)
                            activity = SaUserActivity(
                                table_id=charge_instance.pk,
                                table_name='charges',
                                ua_action='create',
                                ua_description='charges created successfully',
                                created_by=request.user,
                                request_data=request_data,
                                response_data=charge_serializer.data
                            )
                            activity.save()
                        else:
                            raise Exception({'status': 'error', 'message': charge_serializer.errors})

            
            if charges_list :
                request_data["charges"] = charges_list
            
            # Partial update
            serializer = AdminServiceSerializer(admin_service, data=request_data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save(updated_at=datetime.now())

                # Logging user activity
                activity = SaUserActivity(
                    table_id=serializer.instance.pk,
                    table_name='admin_service',
                    ua_action='update',
                    ua_description=f'Updated AdminService "{serializer.instance.admin_service_id}"',
                    created_by=request.user,
                    request_data=request_data,
                    response_data=serializer.data,
                )
                activity.save()

                # Determine the appropriate success message
                is_deactive = 'is_deactive' in request.data
                if ('admin' in request.data or 'service' in request.data or 'charges' in request.data or 'rate' in request.data or 'service_provider' in request.data) and is_deactive:
                    response_data = {
                        'status': 'success',
                        'message': 'AdminService Updated Successfully',
                    }
                elif is_deactive:
                    response_data = {
                        'status': 'success',
                        'message': 'AdminService Deactivate Successfully' if serializer.instance.is_deactive else 'AdminService Activate Successfully',
                    }
                else:
                    response_data = {
                        'status': 'success',
                        'message': 'AdminService Updated Successfully',
                    }
                return Response(response_data, status=status.HTTP_200_OK)

            return Response({'status': 'fail', 'message': 'Failed to update AdminService', 'data': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def fetch_admin_service(self, request):
        """
        Handles POST requests to search and retrieve AdminService objects based on various criteria.

        This endpoint is designed to support a wide range of filtering and searching functionalities, allowing clients to 
        efficiently retrieve `AdminService` records. The endpoint requires authentication, typically through a JWT token.

        ### Request
        - **Method**: POST
        - **Authentication**: Requires JWT token.
        
        ### Request Parameters
        - `admin_service_id` (optional): If provided, retrieves the specific `AdminService` object with this ID.
        - `search` (optional): A query string to filter the `AdminService` records based on specific fields (e.g., `created_by` username).
        - `filter_field` (optional): The name of the field to apply a filter on. Can be used in conjunction with `filter_value`.
        - `filter_value` (optional): The value to filter the `filter_field` by. Should be used with `filter_field`.
        - `start_date` (optional): Filter results to include only those created on or after this date.
        - `end_date` (optional): Filter results to include only those created on or before this date.
        - `is_deactive` (optional): Boolean filter to retrieve either deactivated (`true`) or active (`false`) `AdminService` records.
        - `order_by` (optional): Sort the results by the specified field. Accepts "ascending" or "descending" as values.
        - `page_size` (optional, default=10): Number of records to return per page.
        - `page_number` (optional, default=1): Specifies which page of results to return.
        
        ### Processing
        - **Validation**: Ensures that `page_size` and `page_number` are positive integers. Returns a 400 error if validation fails.
        - **AdminService Retrieval**: 
            - If `admin_service_id` is provided, the method retrieves and returns that specific `AdminService` object.
            - If not, the method retrieves a queryset of `AdminService` records, applying filters, search, and pagination as specified by the parameters.
            - The queryset can be filtered by date range, specific fields, search queries, and deactivation status.
        - **Pagination**: The method paginates the filtered queryset according to the specified `page_size` and `page_number`.
        - **Error Handling**: 
            - If the `AdminService` with the provided `admin_service_id` does not exist, returns a 404 error.
            - If an error occurs during processing, returns a 500 error with details.

        ### Responses
        - **200 OK**: Returns the filtered and paginated `AdminService` objects along with pagination details (total pages, current page, total items).
            - `status`: "success"
            - `message`: "AdminService Data"
            - `data`: A dictionary containing pagination info and the list of `AdminService` objects.
        
        - **400 Bad Request**: Returned if there are validation errors in the request parameters.
            - `status`: "fail"
            - `message`: "Validation errors"
        
        - **404 Not Found**: If no `AdminService` object matches the provided `admin_service_id`.
            - `status`: "fail"
            - `message`: "AdminService not found"
        
        - **500 Internal Server Error**: For any server-side issues encountered during the processing of the request.
            - `status`: "error"
            - `message`: "Internal server error"

        ### Usage
        - Clients should send a POST request with appropriate parameters to retrieve `AdminService` records.
        - Use the `admin_service_id` to fetch a specific record, or omit it to apply filters, searches, and pagination on the list of `AdminService` objects.
        - Handle responses based on the `status` field to determine success or failure of the request.
        """
        try:
            # Retrieve parameters from request data
            admin_service_id = request.data.get('admin_service_id')
            search_query = request.data.get('search', None)
            filter_field = request.data.get('filter_field', None)
            filter_value = request.data.get('filter_value', None)
            order_by = request.data.get('order_by', "ascending")
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            is_deactive = request.data.get('is_deactive', None)
            page_size = request.data.get('page_size', 10)
            page_number = request.data.get('page_number', 1)

            if not str(page_size).isdigit() or int(page_size) <= 0:
                return Response({
                    'status': 'fail',
                    'message': 'page_size parameter is required and must be a positive integer.',
                    'data': {}
                }, status=status.HTTP_400_BAD_REQUEST)

            if not str(page_number).isdigit() or int(page_number) <= 0:
                return Response({
                    'status': 'fail',
                    'message': 'page_number parameter is required and must be a positive integer.',
                    'data': {}
                }, status=status.HTTP_400_BAD_REQUEST)

            if admin_service_id:
                try:
                    admin_service = AdminService.objects.get(admin_service_id=admin_service_id, is_deleted=False)
                    serializer = AdminServiceSerializer(admin_service, context={
                        'request': request,
                        'exclude_fields': ["created_at", "updated_at", "is_deleted", "created_by"]
                    })
                    response_data = {
                        'status': 'success',
                        'message': 'AdminService Data',
                        'data': {
                            'total_pages': 1,
                            'current_page': 1,
                            'total_items': 1,
                            'results': [serializer.data]
                        }
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                except AdminService.DoesNotExist:
                    return Response({
                        'status': 'fail',
                        'message': 'AdminService not found.',
                        'data': {}
                    }, status=status.HTTP_404_NOT_FOUND)

            queryset = AdminService.objects.filter(is_deleted=False).order_by('-pk')

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

            if is_deactive == "true":
                queryset = queryset.filter(is_deactive=True)
            elif is_deactive == "false":
                queryset = queryset.filter(is_deactive=False)

            if search_query:
                queryset = queryset.filter(
                    Q(created_by__username__icontains=search_query)
                )

            if not queryset.exists():
                paginated_response_data = {
                    'total_pages': 0,
                    'current_page': 0,
                    'total_items': 0,
                    'results': []
                }
                response_data = {
                    'status': 'fail',
                    'message': 'AdminService Data not found',
                    'data': paginated_response_data
                }
                return Response(response_data, status=status.HTTP_200_OK)

            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_number,
                    'total_items': paginator.count,
                    'results': []
                }
                response_data = {
                    'status': 'success',
                    'message': 'No data found for the requested page.',
                    'data': paginated_response_data
                }
                return Response(response_data, status=status.HTTP_200_OK)

            serializer = AdminServiceSerializer(page_obj.object_list, many=True, context={
                'request': request,
                'exclude_fields': ["created_at", "updated_at", "is_deleted", "created_by"]
            })
            paginated_response_data = {
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'total_items': paginator.count,
                'results': serializer.data
            }
            response_data = {
                'status': 'success',
                'message': 'AdminService Data',
                'data': paginated_response_data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            response_data = {
                'status': 'error',
                'message': 'Internal server error',
                'data': str(e)
            }
            return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """
        ### Soft Delete AdminService
        
        This method marks an AdminService and its related objects (SaService, Charges, Admin, ServiceProvider) 
        as soft deleted by setting their `is_deleted` and `is_deactive` attributes to True.

        ### Request Method
        - **Method**: DELETE
        - **Authentication**: Requires user authentication (`permission_classes = [IsAuthenticated]`).
        
        ### Request Parameters
        - **admin_service_id**: (in form data, required): The unique identifier of the AdminService to be deleted.

        ### Process Overview
        1. **Parameter Validation**: 
        - The method retrieves the `admin_service_id` from the request data.
        - If `admin_service_id` is not provided, the method returns a 400 (Bad Request) response.

        2. **Transaction Handling**:
        - The deletion process is wrapped in a transaction to ensure atomicity.

        3. **AdminService Retrieval**:
        - The method attempts to retrieve the AdminService object based on `admin_service_id`.
        - If the AdminService does not exist, a 404 (Not Found) response is returned.

        4. **Soft Delete Related Objects**:
        - **SaService**: The related SaService is soft deleted if it exists and is not already deleted.
        - **Charges**: Each related Charges object is soft deleted if it exists and is not already deleted.
        - **Admin**: The related Admin is soft deleted if it exists and is not already deleted.
        - **ServiceProvider**: The related ServiceProvider is soft deleted if it exists and is not already deleted.
        - Each deletion action is logged with relevant details in the `SaUserActivity` table.

        5. **AdminService Deletion**:
        - Finally, the AdminService itself is marked as soft deleted by setting its `is_deleted` and `is_deactive` attributes to True.
        - The deletion action is logged in the `SaUserActivity` table.

        6. **Response Handling**:
        - If any related objects were soft deleted, the method returns a success message indicating that both the AdminService and its related objects were deleted successfully.
        - If only the AdminService was deleted (without any related objects being soft deleted), a success message specific to the AdminService deletion is returned.

        ### Response Examples
        - **Success**:
            - `200 OK`: 
            ```json
            {
                "status": "success",
                "message": "AdminService and its related objects deleted successfully."
            }
            ```

        - **Error Handling**:
            - `400 Bad Request`: Returns a fail response if `admin_service_id` is not provided.
            - `404 Not Found`: Returns a fail response if the AdminService with the specified `admin_service_id` does not exist.
            - `500 Internal Server Error`: Returns an error message for any server-side issues during processing.

        ### Usage
        - This function is typically used within the `AdminServiceViewSet` class to handle the soft deletion of an AdminService and its associated objects based on the provided `admin_service_id`.
        """
        try:
            with transaction.atomic():
                admin_service_id = request.data.get('admin_service_id', None)
                admin_service = AdminService.objects.get(admin_service_id=admin_service_id)

                # Initialize flag to check if related objects were deleted
                related_objects_deleted = False

                # Soft delete related SaService
                sa_service = admin_service.service
                if sa_service and not sa_service.is_deleted:
                    sa_service.is_deleted = True
                    sa_service.is_deactive = True
                    sa_service.save()

                    # Log activity for SaService
                    activity = SaUserActivity(
                        table_id=sa_service.pk,
                        table_name='SaService',
                        ua_action='delete',
                        ua_description=f'Soft deleted SaService with ID {sa_service.pk}',
                        created_by=request.user,
                        request_data=request.data,
                    )
                    activity.save()

                    related_objects_deleted = True

                # Soft delete related Charges
                charges = admin_service.charges
                for i in charges:
                    try:
                        charges_obj = Charges.objects.get(pk=i)
                        charges_obj.is_deleted = True
                        charges_obj.is_deactive = True
                        charges_obj.save()

                        # Log activity for Charges
                        activity = SaUserActivity(
                            table_id=charges_obj.pk,
                            table_name='Charges',
                            ua_action='delete',
                            ua_description=f'Soft deleted Charges with ID {charges_obj.pk}',
                            created_by=request.user,
                            request_data=request.data,
                        )
                        activity.save()
                    except Charges.DoesNotExist:
                        return Response({
                            'status': 'fail',
                            'message': f'Charges with id {i} does not exist.'
                        }, status=status.HTTP_404_NOT_FOUND)

                    related_objects_deleted = True

                # Soft delete related Admin
                admin = admin_service.admin
                if admin and not admin.is_deleted:
                    admin.is_deleted = True
                    admin.is_deactive = True
                    admin.save()

                    # Log activity for Admin
                    activity = SaUserActivity(
                        table_id=admin.pk,
                        table_name='Admin',
                        ua_action='delete',
                        ua_description=f'Soft deleted Admin with ID {admin.pk}',
                        created_by=request.user,
                        request_data=request.data,
                    )
                    activity.save()

                    related_objects_deleted = True

                # Soft delete related ServiceProvider
                service_provider = admin_service.service_provider
                if service_provider and not service_provider.is_deleted:
                    service_provider.is_deleted = True
                    service_provider.is_deactive = True
                    service_provider.save()

                    # Log activity for ServiceProvider
                    activity = SaUserActivity(
                        table_id=service_provider.pk,
                        table_name='ServiceProvider',
                        ua_action='delete',
                        ua_description=f'Soft deleted ServiceProvider with ID {service_provider.pk}',
                        created_by=request.user,
                        request_data=request.data,
                    )
                    activity.save()

                    related_objects_deleted = True

                # Soft delete the AdminService
                admin_service.is_deleted = True
                admin_service.is_deactive = True
                admin_service.save()

                # Log activity for AdminService
                activity = SaUserActivity(
                    table_id=admin_service.pk,
                    table_name='AdminService',
                    ua_action='delete',
                    ua_description=f'Soft deleted AdminService with ID {admin_service.admin_service_id}',
                    created_by=request.user,
                    request_data=request.data,
                )
                activity.save()

                # Return response based on whether related objects were deleted
                if related_objects_deleted:
                    response_message = 'AdminService and its related objects deleted successfully.'
                else:
                    response_message = 'AdminService deleted successfully.'

                return Response({
                    'status': 'success',
                    'message': response_message
                }, status=status.HTTP_200_OK)

        except AdminService.DoesNotExist:
            return Response({
                'status': 'fail',
                'message': f'AdminService with id {admin_service_id} does not exist.'
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ProductApiView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        This method processes POST requests for two main purposes: fetching product data or creating a new product.

        **Request Handling**:
        - **Fetching Data**:
            - When `page_number` and `page_size` are present in the request data:
                - **Parameters**:
                    - `product_category` (integer, optional): Filters products by category.
                    - `brand_name` (string, optional): Filters products by brand name.
                    - `model_name` (string, optional): Filters products by model name.
                    - `date` (string, optional): Start date for filtering products by date.
                    - `price` (decimal, optional): Filters products by price.
                    - `quantity` (integer, optional): Filters products by quantity.
                    - `description` (string, optional): Filters products by description.
                    - `product_img` (array of files, optional): Allows uploading product images.
                    - `page_number` (integer, optional): Page number for pagination.
                    - `page_size` (integer, optional): Number of items per page for pagination.
                    - `product_id` (integer, optional): Filters products by ID.
                    - `start_date` (string, optional): Start date for filtering products.
                    - `end_date` (string, optional): End date for filtering products.
                    - `order_by` (string, optional): Specifies the order of results ('ascending' or 'descending').
                    - `search` (string, optional): Search query for filtering products by brand name, model name, or description.
                    - `is_deactive` (boolean, optional): Filters inactive products.
                - Calls the `fetch_data` method to return a paginated list of products based on the filters and pagination settings.

        - **Creating a Product**:
            - When `brand_name` and `model_name` are present in the request data:
                - **Parameters**:
                    - `product_category`, `brand_name`, `model_name`, `date`, `price`, `quantity`, `description`, `product_img`, etc.
                - Calls the `create_product` method to create a new product with the provided details.

        **Responses**:
        - **Successful Data Fetch (200)**:
            - Returns a list of products with pagination details if the request is valid.
            - Includes total pages, current page number, total items, and the list of products.
        - **Product Created Successfully (201)**:
            - Returns details of the newly created product.
        - **Bad Request (400)**:
            - Returns if there are validation errors or missing parameters in the request.
            - Includes an error message indicating what went wrong.
        - **Not Found (404)**:
            - Returns if the requested data (e.g., product) is not found.
            - Includes an error message indicating that the product could not be found.
        - **Internal Server Error (500)**:
            - Returns if an unexpected error occurs during processing.
            - Includes an error message detailing the problem.

        **Security**:
        - Requires Bearer token authentication.
        """
        try:
            if 'page_number' in request.data and 'page_size' in request.data:
                return self.fetch_data(request)
            elif 'brand_name' in request.data and 'model_name' in request.data:
                return self.create_product(request)
            else:
                return Response({'status': 'error', 'message': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_product(self, request):
        """
        This function handles the creation of a new product entry in the database. It processes the incoming 
        request data, which includes product details and associated image files. The function validates and saves 
        the images, associates them with the product, and ensures all operations are performed atomically to 
        maintain data integrity.

        **Request**:
        - The request is expected to contain product-related data, including multiple image files. 
        - The images should be included in the request with keys that start with 'product_img'.
        - Each image file must not exceed 10 MB in size.

        **Response**:
        - If the product is successfully created:
            - Returns an HTTP 201 Created status with a success message.
        - If there is a validation error (e.g., file size exceeds the limit):
            - Returns an HTTP 400 Bad Request status with an error message detailing the issue.
        - If an unexpected error occurs during processing:
            - Returns an HTTP 500 Internal Server Error status with an error message.
        
        The function ensures the following:
        - Validates the size of the uploaded images.
        - Saves the images to the server's media directory.
        - Validates and saves the product data using a serializer.
        - Wraps all operations in a database transaction to ensure atomicity.
        """

        try:
            with transaction.atomic():
                request_data = request.data.copy()
                # Initialize the serializer with the data from the request
                # files = request.data.getlist('product_img')
                file_paths = []
                for key, value in request_data.items():
                    if key.startswith('product_img'):
                       
                        file = value
                        # Validate file size
                        if file.size > 10 * 1024 * 1024 :
                            raise ValidationError("product_img must be less than 10 MB.")
                        # Construct the relative file path
                        relative_file_path = os.path.join('product_imgs', file.name)
                        file_paths.append(relative_file_path)

                        # Save the file to the media directory
                        file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directories if they don't exist

                        with open(file_path, 'wb+') as destination:
                            for chunk in file.chunks():
                                destination.write(chunk)

                product_img =  file_paths
                
                request_data['product_img'] = {}
                serializer = ProductSerializer(data=request_data, context={'request': request})
                if serializer.is_valid(raise_exception=True):
                    product = serializer.save(created_by=request.user)
                    product.save()
                    product.product_img = product_img
                    product.save()
                    return Response({'status': 'success', 'message': 'Product Created Successfully'}, status=status.HTTP_201_CREATED)
                return Response({'status': 'fail', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError  as e:
            return Response({'status': 'fail', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_data(self, request):
        """
        This function is responsible for fetching product data from the database based on various filtering, 
        pagination, and sorting criteria provided in the request. The function is designed to handle a variety 
        of query parameters and return a paginated list of products.

        **Request**:
        - The request is expected to contain the following parameters:
            - `product_id`: (optional) Filters the results to a specific product.
            - `page_size`: (required) Specifies the number of items per page for pagination. Must be a positive integer.
            - `page_number`: (optional) Specifies the page number to fetch. Defaults to 1. Must be a positive integer.
            - `start_date`: (optional) Filters products created from this date (in 'YYYY-MM-DD' format).
            - `end_date`: (optional) Filters products created up to this date (in 'YYYY-MM-DD' format).
            - `order_by`: (optional) Specifies the sort order of the results. Defaults to "ascending". Can be "ascending" or "descending".
            - `search_query`: (optional) Searches within the product's brand name, model name, or description.
            - `product_category`: (optional) Filters results by product category. If not "0", filters by the provided category.
            - `is_deactive`: (optional) Filters the results to active or deactive products based on boolean value ('true' or 'false').

        **Response**:
        - If successful:
            - Returns an HTTP 200 OK status with the following structure:
                - `status`: 'success'
                - `message`: 'Product Data'
                - `data`: Paginated product data, including total pages, current page, total items, and results (serialized product data).
            - If no products are found:
                - Returns an HTTP 200 OK status with `status: 'fail'` and a message indicating no data was found.
            - If a requested page is out of range:
                - Returns an HTTP 404 Not Found status with a message indicating that the page does not exist.

        **Functionality**:
        - The function first validates the `page_size` and `page_number` parameters to ensure they are positive integers.
        - It then constructs a queryset of products, applying filters based on the provided request parameters.
        - Filters include checking for a specific product ID, filtering by deactivation status, filtering by a date range, 
        searching within the product's brand, model name, or description, and filtering by product category.
        - The results can be sorted either in ascending or descending order based on the primary key.
        - The function paginates the results using the provided `page_size` and returns the specified page's data.
        - The paginated or full product data is serialized and returned in the response.
        
        - If any validation error or exception occurs during processing, an HTTP 400 Bad Request status is returned with the error message.
        """
        try:
            product_id = request.data.get('product_id')
            page_size = request.data.get('page_size')
            page_number = request.data.get('page_number', 1)
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            order_by = request.data.get('order_by', "descending")
            search_query = request.data.get('search', None)
            product_category = request.data.get('product_category', None)
            is_deactive = request.data.get('is_deactive', None)

            if not page_size or not page_size.isdigit() or int(page_size) <= 0:
                raise ValidationError("page_size parameter is required and must be a positive integer.")

            if not page_number or not page_number.isdigit() or int(page_number) <= 0:
                raise ValidationError("page_number parameter is required and must be a positive integer.")

            queryset = Product.objects.filter(is_deleted=False)
            if product_id:
                queryset = queryset.filter(pk=product_id)
            if is_deactive:
                queryset = queryset.filter(is_deactive=True) if is_deactive == 'true' else queryset.filter(is_deactive=False)
            if start_date and end_date:
                start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__range=[start_date_parsed, end_date_parsed + timedelta(days=1)])
            if search_query:
                queryset = queryset.filter(Q(brand_name__icontains=search_query) | Q(model_name__icontains=search_query) | Q(description__icontains=search_query))

            if product_category:
                if product_category != "0":
                    queryset = queryset.filter(product_category=product_category)
            if order_by == "ascending":
                queryset = queryset.order_by('pk')
            else:
                queryset = queryset.order_by('-pk')

            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except EmptyPage:
                return Response({'status': 'fail', 'message': 'Page not found.', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

            if page_obj:
                if not queryset.exists():
                    paginated_response_data = {'total_pages': 0, 'current_page': 0, 'total_items': 0, 'results': []}
                    return Response({'status': 'fail', 'message': 'Product Data not found.', 'data': paginated_response_data}, status=status.HTTP_200_OK)
                serializer = ProductSerializer(page_obj.object_list, many=True,  context={'request': request,'exclude_fields':["created_at", "updated_at", "is_deleted","updated_by", "created_by"]})
                paginated_response_data = {'total_pages': paginator.num_pages, 'current_page': page_obj.number, 'total_items': paginator.count, 'results': serializer.data}
                return Response({'status': 'success', 'message': 'Product Data', 'data': paginated_response_data}, status=status.HTTP_200_OK)
            
            serializer = ProductSerializer(queryset, many=True, context={'request': request,'exclude_fields':["created_at", "updated_at", "is_deleted","updated_by", "created_by"]})
            return Response({'status': 'success', 'message': 'Product Data', 'data': serializer.data}, status=status.HTTP_200_OK)
        except (ValidationError , ValueError, Exception) as e:
            return Response({'status': 'fail', 'message': str(e), 'data': {}}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        Updates the details of an existing product based on the provided data.

        **Request Parameters:**
        - `product_id` (integer, required): The ID of the product to update. This field is mandatory.
        - `product_category` (integer, optional): The category of the product.
        - `brand_name` (string, optional): The brand name of the product.
        - `model_name` (string, optional): The model name of the product.
        - `serial_number` (string, optional): The serial number of the product.
        - `date` (string, optional, format: date): The date associated with the product.
        - `price` (decimal, optional): The price of the product.
        - `quantity` (integer, optional): The quantity of the product.
        - `description` (string, optional): The description of the product.
        - `product_img` (array of files, optional): Array of images associated with the product.
        - `is_deactive` (boolean, optional): Flag to deactivate or activate the product.

        **Responses:**
        - **200 OK**: Returns when the product is successfully updated.
        - **400 Bad Request**: Returns if validation errors occur or if required fields are missing.
        - **404 Not Found**: Returns if the product with the specified ID does not exist.
        - **500 Internal Server Error**: Returns if an unexpected error occurs during processing.

        **Security:**
        - Requires Bearer token authentication.
        """
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({'status': 'fail', 'message': "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                try:
                    product = Product.objects.get(product_id=product_id, is_deleted=False)
                    request_data = request.data.copy()
                    product_imgs = None
                    if any(key.startswith('product_img') for key in request_data.keys()):
                        # Initialize the serializer with the data from the request
                        # files = request.data.getlist('product_img')
                        file_paths = []
                        for key, value in request_data.items():
                            if key.startswith('product_img'):
                            
                                file = value
                                # Validate file size
                                if file.size > 10 * 1024 * 1024 :
                                    raise ValidationError("product_img must be less than 10 MB.")
                                # Construct the relative file path
                                relative_file_path = os.path.join('product_imgs', file.name)
                                file_paths.append(relative_file_path)

                                # Save the file to the media directory
                                file_path = os.path.join(settings.MEDIA_ROOT, relative_file_path)
                                os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directories if they don't exist

                                with open(file_path, 'wb+') as destination:
                                    for chunk in file.chunks():
                                        destination.write(chunk)

                        product_imgs =  file_paths

                        request_data['product_img'] = {}
                    serializer = ProductSerializer(product, data=request_data, partial=True)
                    if serializer.is_valid():
                        product = serializer.save(updated_at=datetime.now(), updated_by=request.user)
                        if product_imgs:
                            product.product_img = product_imgs
                            product.save()
                        return Response({'status': 'success', 'message': 'Product Updated Successfully'}, status=status.HTTP_200_OK)
                    return Response({'status': 'fail', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                except Product.DoesNotExist:
                    return Response({'status': 'fail', 'message': "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """
        Deletes a product based on the provided `product_id`.

        **Request Parameters:**
        - `product_id` (integer, required): The ID of the product to be deleted. This field is mandatory.

        **Responses:**
        - **200 OK**: Returns when the product is successfully marked as deleted.
        - **404 Not Found**: Returns if the product with the specified ID does not exist or is already deleted.
        - **500 Internal Server Error**: Returns if an unexpected error occurs during the deletion process.

        **Security:**
        - Requires Bearer token authentication.
        """
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({'status': 'fail', 'message': "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                product = Product.objects.get(product_id=product_id, is_deleted=False)
                product.is_deleted = True
                product.save()
                return Response({'status': 'success', 'message': 'Product Deleted Successfully'}, status=status.HTTP_200_OK)
        except Product.DoesNotExist:
            return Response({'status': 'fail', 'message': "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PanVerification(APIView):
    
    # number=0000000

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles the POST request for verifying PAN numbers.

        This method processes the incoming request data to extract the PAN number and name. It generates a new verification ID based on the latest entry in the Admin model. 
        It then sends the verification request to the Cashfree service and returns the result of the verification.

        ###Request Parameters:
        - pan (str): The PAN number to verify.
        - name (str): The name associated with the PAN number.

        ###Responses:
        - 200 OK: Returns verification result including the status, verification ID, and whether the PAN is verified.
        - 400 Bad Request: Returns validation errors if the request parameters are missing or invalid.
        - 404 Not Found: Returns error if the PAN is not found or verification fails.
        - 500 Internal Server Error: Returns an error message if an exception occurs during the request.

        Example Request:
        POST /api/pan-verification/
        {
            "pan": "ABCDE1234F",
            "name": "John Doe"
        }

        Example Response (Success):
        {
            "status": "success",
            "message": "PAN verified successfully",
            "is_pan_verify": true,
            "verification_id": "TCPL000001"
        }

        Example Response (Failure):
        {
            "status": "fail",
            "message": "PAN not found"
        }
        """
        # PanVerification.number+=1
        # var = PanVerification.number
    
        pan = request.data.get('pan')
        # verification_id = request.data.get('verification_id')
        name = request.data.get('name')

        # if not pan or not name:
        #     return Response(
        #         {'status': 'fail', 'message': 'PAN and name are required'},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        with transaction.atomic():
            # last_admin=Admin.objects.select_for_update().order_by('-admin_id').first()
            # if last_admin and last_admin.verification_id:
            #     last_id=int(last_admin.verification_id.replace('TCPL',''))
            #     new_id=last_id+1
            # else:
            #     new_id=1
          
            
            unique_part = uuid.uuid4().hex[:6].upper()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            verification_id = f'TCPL{timestamp}{unique_part}'
            # print(verification_id,"ooooo")
            
            
            # # timestamp=datetime.now().strftime('%Y%m%d%H%M%S')
            # varification_id=f'TCPL{datetime.now().strftime("%Y%m%d%H%M%S")}{var:06d}'
            # print(varification_id,"llllll")
            # verification_id=f'{var:06d}'
            # print(verification_id,"rrrrrr")
                        
            

        payload = {
            'pan': pan,
            'verification_id': verification_id,
            'name': name
        }
        
        
        headers={
            'x-client-id': 'CF379597CS6CV2HJAM2C73E8JDU0',
            'x-client-secret': 'cfsk_ma_test_1cc91e0c23a5699ef48a5f1229c3cbe2_96d7df44',
            'Content-Type': 'application/json'
        }
        
        url = "https://sandbox.cashfree.com/verification/pan/advance"
        
        try:
            
            response = requests.post(
                url, 
                json=payload, 
                headers=headers
            )
            response_data = response.json()
    
            
            if response.status_code == 200 and response_data.get('status')=='VALID':
                response_data['is_pan_verify']=True
                response_data['verification_id']=verification_id
                
                
                return Response(
                    response_data,  
                    status=response.status_code
                )
            else:
                # error_message = response_data.get('message', 'Unknown error occurred')
                # error_type = response_data.get('type', 'error')
                # error_code = response_data.get('code', 'unknown_code')

                return Response(
                    response_data,
                    status=response.status_code
                )
        except requests.RequestException as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

                
                    


class GstVerification(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        ###Handles the POST request for verifying GST numbers.

        ###This method processes the incoming request data to extract the GSTIN. It sends a verification request to an external GST service 
        and returns the result of the verification.

        ###Request Parameters:
        - GSTIN (str): The GST number to verify.

        ###Responses:
        - 200 OK: Returns verification result including the status and GSTIN if verified successfully.
        - 400 Bad Request: Returns validation errors if the GSTIN is missing.
        - 404 Not Found: Returns an error if the GSTIN is not found or verification fails.
        - 500 Internal Server Error: Returns an error message if an exception occurs during the request.

        Example Request:
        POST /api/gst-verification/
        {
            "GSTIN": "29AABBCCDD1234Z"
        }

        Example Response (Success):
        {
            "status": "success",
            "message": "GST verified successfully",
            "is_gst_verify": true,
            "GSTIN": "29AABBCCDD1234Z"
        }

        Example Response (Failure):
        {
            "status": "fail",
            "message": "GST not found"
        }
        """
        # default_gstin = "29AABBCCDD1234Z"
        gst = request.data.get('GSTIN')

        if not gst:
            return Response(
                {'status': 'fail', 'message': 'GSTIN is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payload = {
            'GSTIN': gst
        }

        url = "https://sandbox.cashfree.com/verification/gstin"
        headers = {
            'x-client-id': 'CF379597CS6CV2HJAM2C73E8JDU0',
            'x-client-secret': 'cfsk_ma_test_1cc91e0c23a5699ef48a5f1229c3cbe2_96d7df44',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response_data = response.json()
            # print(response_data["message"])
            
            if response.status_code == 200 and response_data["message"]=="GSTIN Exists":
                response_data['is_gst_verify'] = True
              
                
                return Response(
                    response_data,  
                    status=response.status_code
                )
            else:
                return Response(
                    response_data,
                    status=response.status_code
                )
        except requests.RequestException as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        


class RegionListView(APIView):

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsAdmin | IsRetailer | IsSuperAdmin]

    def post(self, request, *args, **kwargs):
        try:
            if "file" in request.data:
                csv_file = request.FILES.get('file')

                if not csv_file.name.endswith('.csv'):
                    return Response({"error": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)

                csv_data = StringIO(csv_file.read().decode())
                reader = csv.DictReader(csv_data)

                for row in reader:
                    serializer = StateSerializer(data=row)
                    if serializer.is_valid():
                        serializer.save()
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                return Response({"status": "CSV data processed successfully."}, status=status.HTTP_201_CREATED)
            else:
                return self.fetch_data(request)

        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def fetch_data(self,request):

        try:
            regions_name = request.data.get("state_name")
            # india = Country.objects.get(name='India')
            regions = State.objects.all()
            if regions_name:
                regions = regions.filter(state_name__icontains=regions_name)
            regions_serializer = StateSerializer(regions, many=True,context={'request': request,'exclude_fields':["created_at","is_active","create_by","update_at","update_by"]})
            respons_data = {
                'status': 'success', 
                'message': 'State Data', 
                'data': regions_serializer.data
                }
            return Response(respons_data, status=status.HTTP_200_OK)
        except State.DoesNotExist:
            return Response({'status': 'error', "message": "India not found in the Country model"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CityList(APIView):

    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsDistributor | IsAdmin | IsRetailer | IsSuperAdmin]
    
    def post(self, request, *args, **kwargs):
        try:
            if "file" in request.data:
                csv_file = request.FILES.get('file')

                if not csv_file.name.endswith('.csv'):
                    return Response({"error": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)

                csv_data = StringIO(csv_file.read().decode())
                reader = csv.DictReader(csv_data)

                for row in reader:
                    serializer = CitySerializer(data=row)
                    if serializer.is_valid():
                        serializer.save()
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                return Response({"status": "CSV data processed successfully."}, status=status.HTTP_201_CREATED)
            else:
                return self.fetch_data(request)
        
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    
    def fetch_data(self, request):
        try:
            state_id = request.data.get('state_id')
            city_name = request.data.get('search')
            page_size = request.data.get('page_size')
            page_number = request.data.get('page_number', "1")

            # Validate page_size and page_number
            if not page_size or not page_size.isdigit() or int(page_size) < 0:
                raise ValidationError("page_size parameter is required and must be a positive integer.")

            if not page_number or not page_number.isdigit() or int(page_number) <= 0:
                raise ValidationError("page_number parameter is required and must be a positive integer.")

            cities = City.objects.all().order_by('city_name')
            if state_id:
                cities = cities.filter(state_id=state_id)
            if city_name:
                cities = cities.filter(city_name__icontains=city_name)

            if page_size == "0":
                city_serializer = CitySerializer(cities, many=True, context={'request': request, 'exclude_fields': ["created_at", "is_active", "create_by", "update_at", "update_by", "state_id"]})
                paginated_response_data = {
                    'total_pages': 1,
                    'current_page': 1, 
                    'total_items': cities.count(), 
                    'results': city_serializer.data
                    }
                return Response({'status': 'success', 'message': 'City Data', 'data': paginated_response_data}, status=status.HTTP_200_OK)      
            else :
                # Pagination
                paginator = Paginator(cities, page_size)
                try:
                    page_obj = paginator.page(page_number)
                except EmptyPage:
                    return Response({'status': 'fail', 'message': 'Page not found.', 'data': {}}, status=status.HTTP_404_NOT_FOUND)

                if not page_obj.object_list.exists():
                    paginated_response_data = {
                        'total_pages': 0, 
                        'current_page': 0, 
                        'total_items': 0, 
                        'results': []
                        }
                    return Response({
                        'status': 'fail', 
                        'message': 'City Data not found.', 
                        'data': paginated_response_data
                        }, 
                        status=status.HTTP_200_OK)

                city_serializer = CitySerializer(page_obj.object_list, many=True, context={'request': request, 'exclude_fields': ["created_at", "is_active", "create_by", "update_at", "update_by", "state_id"]})
                paginated_response_data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page_obj.number, 
                    'total_items': paginator.count, 
                    'results': city_serializer.data
                    }
                return Response({'status': 'success', 'message': 'City Data', 'data': paginated_response_data}, status=status.HTTP_200_OK)
            


        except ValidationError as e:
            return Response({'status': 'fail', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except City.DoesNotExist:
            return Response({'status': 'error', 'message': 'City not available'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)   
        
class CreteOrder(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return self.handle_order_request(request, method='POST')

    def get(self, request):
        return self.handle_order_request(request, method='GET')

    def handle_order_request(self, request, method):
        # Common headers for both POST and GET requests
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'x-api-version': '2023-08-01',
            'x-client-id': 'CF10200215CQOS9TNPU07S7391HH9G',
            'x-client-secret': 'cfsk_ma_test_b68698459f24796a6d655dd514e9b1b1_5180673a',
        }

        if method == 'POST':
            # Handle order creation
            customer_id = request.data.get('customer_id')
            customer_phone = request.data.get('customer_phone')
            order_currency = request.data.get('order_currency', 'INR')
            order_amount = request.data.get('order_amount')

            # Validate required fields
            if not customer_id or not customer_phone or not order_amount:
                return Response(
                    {'status': 'fail', 'message': 'customer_id, customer_phone, and order_amount are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Payload for the POST request
            payload = {
                "customer_details": {
                    "customer_id": customer_id,
                    "customer_phone": customer_phone
                },
                "order_currency": order_currency,
                "order_amount": order_amount
            }

            # URL for the POST request
            url = 'https://sandbox.cashfree.com/pg/orders'

            try:
                # Make the POST request
                response = requests.post(url, json=payload, headers=headers)
                response_data = response.json()

                # Handle the response
                if response.status_code == 200:
                    return Response(response_data, status=response.status_code)
                else:
                    return Response(response_data, status=response.status_code)
            except requests.RequestException as e:
                return Response(
                    {'status': 'error', 'message': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        elif method == 'GET':
            # Handle order retrieval
            order_id = request.query_params.get('order_id')

            # Validate required field
            if not order_id:
                return Response(
                    {'status': 'fail', 'message': 'order_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # URL for the GET request
            url = f'https://sandbox.cashfree.com/pg/orders/{order_id}'

            try:
                # Make the GET request
                response = requests.get(url, headers=headers)
                response_data = response.json()

                # Handle the response
                if response.status_code == 200:
                    return Response(response_data, status=response.status_code)
                else:
                    return Response(response_data, status=response.status_code)
            except requests.RequestException as e:
                return Response(
                    {'status': 'error', 'message': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        else:
            return Response(
                {'status': 'fail', 'message': 'Method not allowed'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )    
            

class Authentication(APIView):
    permission_classes = [IsAuthenticated]
    def post(self,request):
        try:
            
            url = "https://payout-gamma.cashfree.com/payout/v1/authorize"

            headers = {
                "accept": "application/json",
                "x-client-id": "CF10291673CR42HS7PU07S7391HLB0",
                "x-client-secret": "cfsk_ma_test_9eb6cecd33c1b105d615722ef0bbdcfc_39f33a19"
            }

            response = requests.post(url, headers=headers)

            return Response(
                    response.text,
                    status=response.status_code
                )
        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class Beneficiary(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            
            unique_part = uuid.uuid4().hex[:6].upper()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            beneficiary_id = f'TCPL{timestamp}{unique_part}'

            
            beneficiary_name = request.POST.get('beneficiary_name')
            bank_account_number = request.POST.get('bank_account_number')
            bank_ifsc = request.POST.get('bank_ifsc')
            vpa = request.POST.get('vpa', None) 

            beneficiary_email = request.POST.get('beneficiary_email')
            beneficiary_phone = request.POST.get('beneficiary_phone')
            beneficiary_country_code = request.POST.get('beneficiary_country_code')
            beneficiary_address = request.POST.get('beneficiary_address')
            beneficiary_city = request.POST.get('beneficiary_city')
            beneficiary_state = request.POST.get('beneficiary_state')
            beneficiary_postal_code = request.POST.get('beneficiary_postal_code')
            beneficiary_purpose = request.POST.get('beneficiary_purpose',None)

            
            missing_fields = []
            if not beneficiary_name: missing_fields.append('beneficiary_name')
            if not bank_account_number: missing_fields.append('bank_account_number')
            if not bank_ifsc: missing_fields.append('bank_ifsc')
            if not beneficiary_email: missing_fields.append('beneficiary_email')
            if not beneficiary_phone: missing_fields.append('beneficiary_phone')
            if not beneficiary_country_code: missing_fields.append('beneficiary_country_code')
            if not beneficiary_address: missing_fields.append('beneficiary_address')
            if not beneficiary_city: missing_fields.append('beneficiary_city')
            if not beneficiary_state: missing_fields.append('beneficiary_state')
            if not beneficiary_postal_code: missing_fields.append('beneficiary_postal_code')
            if not beneficiary_purpose: missing_fields.append('beneficiary_purpose')

            if missing_fields:
                return Response(
                    {'status': 'error', 'message': f"Missing required fields: {', '.join(missing_fields)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            
            if len(bank_ifsc) != 11:
                return Response(
                    {'status': 'error', 'message': 'Invalid IFSC code.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payload = {
                "beneficiary_id": f"{beneficiary_id}",
                "beneficiary_name": beneficiary_name,
                "beneficiary_instrument_details": {
                    "bank_account_number": bank_account_number,
                    "bank_ifsc": bank_ifsc,
                    "vpa": vpa
                },
                "beneficiary_contact_details": {
                    "beneficiary_email": beneficiary_email,
                    "beneficiary_phone": beneficiary_phone,
                    "beneficiary_country_code": beneficiary_country_code,
                    "beneficiary_address": beneficiary_address,
                    "beneficiary_city": beneficiary_city,
                    "beneficiary_state": beneficiary_state,
                    "beneficiary_postal_code": beneficiary_postal_code
                },
                "beneficiary_purpose": beneficiary_purpose
            }

            url = "https://sandbox.cashfree.com/payout/beneficiary"
            headers = {
                "accept": "application/json",
                "x-api-version": "2024-01-01",
                "content-type": "application/json",
                # "x-client-id": x_client_id,
                # "x-client-secret": x_client_secret
            }
            response = requests.post(url, json=payload, headers=headers)

            return Response(
                response.json(),
                status=response.status_code
            )

        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class Transfer(APIView):
    permission_classes = [IsAuthenticated]

    def post(self,request):
        try:
            unique_part = uuid.uuid4().hex[:6].upper()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            transfer_id = f'TCPL{timestamp}{unique_part}'

            transfer_type = request.data.get('transfer_type')
            if not transfer_type:
                return Response(
                    {'status': 'error', 'message': "Please select any one transfer type from this list ['with beneficiary_id','with beneficiary_detail','with card_detail','with fundsource_id']."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            
            transfer_amount = request.data.get("transfer_amount")
            
            
            if not transfer_amount:
                return Response(
                    {'status': 'error', 'message': "transfer_amount field is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                

            url = "https://sandbox.cashfree.com/payout/transfers"
            if transfer_type == "with beneficiary_id":
                beneficiary_id = request.data.get("beneficiary_id")
                missing_fields = []
                if not beneficiary_id: missing_fields.append('beneficiary_id')
                if missing_fields:
                    return Response(
                        {'status': 'error', 'message': f"Missing required fields: {', '.join(missing_fields)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                payload = {
                    "beneficiary_details": { "beneficiary_id": beneficiary_id },
                    "transfer_id": transfer_id,
                    "transfer_amount": transfer_amount
                }
            elif transfer_type == "with beneficiary_detail":
                transfer_mode = request.data.get("transfer_mode")
                bank_ifsc = request.data.get("bank_ifsc")
                bank_account_number = request.data.get("bank_account_number")
                missing_fields = []
                if not transfer_mode: missing_fields.append("transfer_mode")
                if not bank_ifsc : missing_fields.append("bank_ifsc")
                if not bank_account_number : missing_fields.append("bank_account_number")
                if missing_fields:
                    return Response(
                        {'status': 'error', 'message': f"Missing required fields: {', '.join(missing_fields)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                payload = {
                    "beneficiary_details": { "beneficiary_details": { "beneficiary_instrument_details": {
                                "bank_account_number": bank_account_number,
                                "bank_ifsc": bank_ifsc
                            } } },
                    "transfer_id": transfer_id,
                    "transfer_amount": transfer_amount,
                    "transfer_mode": transfer_mode
                }
            elif transfer_type == "with card_detail":
                card_token = request.data.get("card_token")
                card_network_type = request.data.get("card_network_type")
                card_token_expiry = request.data.get("card_token_expiry")
                card_type = request.data.get("card_type")
                card_token_PAN_sequence_number = request.data.get("card_token_PAN_sequence_number")
                transfer_mode = request.data.get("transfer_mode","imps")
                missing_fields = []
                if not card_token : missing_fields.append("card_token")
                if not card_network_type : missing_fields.append("card_network_type")
                if not card_token_expiry : missing_fields.append("card_token_expiry")
                if not card_type : missing_fields.append("card_type")
                if not card_token_PAN_sequence_number : missing_fields.append("card_token_PAN_sequence_number")
                if missing_fields:
                    return Response(
                        {'status': 'error', 'message': f"Missing required fields: {', '.join(missing_fields)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                payload = {
                    "beneficiary_details": { "beneficiary_details": { "beneficiary_instrument_details": { "card_details": {
                                    "card_token": card_token,
                                    "card_network_type": card_network_type,
                                    "card_cryptogram": "jjoutwsdgfdou124354ljlsdhgout968957",
                                    "card_token_expiry":card_token_expiry,
                                    "card_type": card_type,
                                    "card_token_PAN_sequence_number": card_token_PAN_sequence_number
                                } } } },
                    "transfer_id": transfer_id,
                    "transfer_amount": transfer_amount,
                    "transfer_mode": transfer_mode
                }
            elif transfer_type == "with fundsource_id":
                beneficiary_id = request.data.get("beneficiary_id")
                fundsource_id = request.data.get("fundsource_id")
                transfer_mode = request.data.get("transfer_mode","imps")
                missing_fields = []
                if not beneficiary_id: missing_fields.append('beneficiary_id')
                if not fundsource_id: missing_fields.append('fundsource_id')
                if missing_fields:
                    return Response(
                        {'status': 'error', 'message': f"Missing required fields: {', '.join(missing_fields)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                payload = {
                    "beneficiary_details": { "beneficiary_details": { "beneficiary_id": beneficiary_id } },
                    "transfer_id": transfer_id,
                    "transfer_amount": transfer_amount,
                    "transfer_mode": transfer_mode,
                    "fundsource_id": fundsource_id
                }


            headers = {
                "accept": "application/json",
                "x-api-version": "2024-01-01",
                "content-type": "application/json",
                # "x-client-id": x_client_id,
                # "x-client-secret": x_client_secret
            }

            response = requests.post(url, json=payload, headers=headers)

            return Response(
                response.json(),
                status=response.status_code
            )
        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class AdminFundRequestAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsSuperAdmin]

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
        payment_proof = request.FILES.get('payment_proof')
        remark = request.data.get('remark')
        transaction_id = request.data.get('transaction_id')
        utr_number = request.data.get('utr_number')
        transaction_mode = request.data.get('transaction_mode')

        try:
            if not deposite_category: return Response({'status': 'fail','message': 'deposite_category is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not bd_id: return Response({'status': 'fail','message': 'bd_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not deposit_amount: return Response({'status': 'fail','message': 'deposit_amount is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not payment_proof: return Response({'status': 'fail','message': 'payment_proof is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not remark: return Response({'status': 'fail','message': 'remark is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if request.user.pu_role != 'ADMIN': return Response({'status': 'fail', 'message': 'Unauthorized to add fund request.'}, status=status.HTTP_401_UNAUTHORIZED)

            try:
                deposite_category_json = json.loads(deposite_category)
            except json.JSONDecodeError:
                return Response({'status': 'fail', 'message': 'Invalid deposite category format'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                bank_detail = AdminBankDetails.objects.get(bd_id=bd_id, is_delete=False)
            except AdminBankDetails.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Bank does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

            # Determine charges category and get min/max amount
            if deposite_category_json.get("online_transaction"):
                print('bank_detail.online_charges', bank_detail.online_charges)
                minimum_amount = bank_detail.online_charges.get('minimum_amount')
                maximum_amount = bank_detail.online_charges.get('maximum_amount')
            elif deposite_category_json.get("counter_deposit"):
                print('bank_detail.counter_charges', bank_detail.counter_charges)
                minimum_amount = bank_detail.counter_charges.get('minimum_amount')
                maximum_amount = bank_detail.counter_charges.get('maximum_amount')
            elif deposite_category_json.get("cdm_deposit"):
                print('bank_detail.cdm_charges', bank_detail.cdm_charges)
                minimum_amount = bank_detail.cdm_charges.get('minimum_amount')
                maximum_amount = bank_detail.cdm_charges.get('maximum_amount')
            else:
                return Response({'status': 'fail', 'message': 'Invalid deposit category.'}, status=status.HTTP_400_BAD_REQUEST)

            # Convert deposit amount to float and validate against min/max
            try:
                deposit_amount = float(deposit_amount)
            except ValueError:
                return Response({'status': 'fail', 'message': 'Invalid deposit amount.'}, status=status.HTTP_400_BAD_REQUEST)

            if not (float(minimum_amount) <= float(deposit_amount) <= float(maximum_amount)):
                return Response({
                    'status': 'fail',
                    'message': f'Deposit amount must be between {minimum_amount} and {maximum_amount}.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Handle file upload
            file_path = handle_uploaded_file(payment_proof, 'Admin/PaymentProof') if payment_proof else None
            payment_proof_file_paths = {'payment_proof': file_path}

            sa_admin = Admin.objects.get(admin_id=request.user.id)

            if deposite_category_json.get("counter_deposit") or deposite_category_json.get("cdm_deposit"):
                if not transaction_id:
                    return Response({'status': 'fail', 'message': 'transaction_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
                if len(transaction_id) < 12 or len(transaction_id) > 16:
                    return Response({'status': 'fail', 'message': 'transaction_id length must be between 12 to 16.'}, status=status.HTTP_400_BAD_REQUEST)

                fund_request = AdminFundRequest.objects.create(
                    deposite_category=deposite_category_json, deposite_bank=bank_detail,
                    deposite_amount=deposit_amount, transaction_id=transaction_id, payment_proof=payment_proof_file_paths,
                    remark=remark, created_at=timezone.now(), created_by=sa_admin
                )

            elif deposite_category_json.get("online_transaction"):
                if not utr_number: return Response({'status': 'fail','message': 'utr_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
                if not transaction_mode: return Response({'status': 'fail','message': 'transaction_mode is required.'}, status=status.HTTP_400_BAD_REQUEST)

                transaction_mode_list = ["IMPS", "RTGS", "NEFT"]
                if transaction_mode not in transaction_mode_list:
                    return Response({'status': 'fail','message': 'transaction_mode must be IMPS, RTGS, or NEFT'}, status=status.HTTP_400_BAD_REQUEST)

                fund_request_utr_number = AdminFundRequest.objects.filter(utr_number=utr_number).first()
                if fund_request_utr_number:
                    return Response({'status': 'fail','message': 'utr_number already exists.'}, status=status.HTTP_400_BAD_REQUEST)

                fund_request = AdminFundRequest.objects.create(
                    deposite_category=deposite_category_json, deposite_bank=bank_detail,
                    deposite_amount=deposit_amount, utr_number=utr_number, payment_proof=payment_proof_file_paths,
                    transaction_mode=transaction_mode, remark=remark, created_at=timezone.now(),
                    created_by=sa_admin
                )

            else:
                return Response({'status': 'fail', 'message': 'At least one deposite category must be true.'}, status=status.HTTP_400_BAD_REQUEST)

            user_activity = {
                "table_id": fund_request.pk,
                "table_name": 'ad_fund_request',
                "ua_action": 'Create',  # Action performed
                "ua_description":"Fund request generated successfully.",  # Action description
                "created_by": request.user,  # Current user performing the action
                "request_data": dict(request.data),  # Request data
                "response_data": model_to_dict(fund_request)
            }

            add_user_activity(user_activity)

            return Response({"status": "success", "message": "Fund request generated successfully."}, status=status.HTTP_201_CREATED)

        except Admin.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Admin does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def fetch_fund_request(self, request):
        fr_id = request.data.get("fr_id", None)
        admin_id = request.data.get("admin_id", None)
        search = request.data.get("search", None)
        payment_status = request.data.get("payment_status", None)
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", datetime.now().date())
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size')
        user_role = getattr(request.user, 'pu_role', None)
        pu_role = "SUPERADMIN" if user_role == None else user_role
        
        try:
            if not page_size: return Response({'status': 'fail','message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not isnumber(page_size): return Response({'status': 'fail','message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if page_number:
                if not isnumber(page_number): return Response({'status': 'fail','message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if fr_id:
                if not isnumber(fr_id): return Response({'status': 'fail','message': 'fr_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

            if pu_role == "SUPERADMIN":
                queryset = AdminFundRequest.objects.filter(is_delete=False)
                if admin_id:
                    sa_admin = Admin.objects.get(admin_id=admin_id)

                    queryset = queryset.filter(created_by=sa_admin)
            elif pu_role == "ADMIN":
                sa_admin = Admin.objects.get(admin_id=request.user.id)

                queryset = AdminFundRequest.objects.filter(is_delete=False, created_by=sa_admin)
            else:
                return Response({'status': 'fail', 'message': 'You are not authorized to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
            
            if search:
                queryset = queryset.filter(
                    Q(utr_number__icontains=search) |
                    Q(transaction_mode__icontains=search) |
                    Q(transaction_id__icontains=search)
                )

            if payment_status:
                queryset = queryset.filter(request_status = payment_status)

            if start_date:
                queryset = queryset.filter(created_at__date__range=[start_date, end_date])

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
                serializer = AdminFundRequestSerializer(page_obj.object_list, many=True, context={'request': request})
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

            serializer = AdminFundRequestSerializer(queryset, many=True, context={'request': request})
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
            reason = request.data.get("reason", None)
            user_role = getattr(request.user, 'pu_role', None)
            pu_role = "SUPERADMIN" if user_role == None else user_role
            if pu_role != 'SUPERADMIN':
                return Response({'status': 'fail', 'message': 'You are not authorized to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

            if not fr_id: return Response({'status': 'fail', 'message': 'fr_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not request_status: return Response({'status': 'fail', 'message': 'request_status is required.'}, status=status.HTTP_400_BAD_REQUEST)

            get_fund_request = AdminFundRequest.objects.get(fr_id=fr_id)
            if get_fund_request.request_status == "REJECTED" or get_fund_request.request_status == "REVERSED":
                return Response({'status': 'fail', 'message': 'Fund request has already been processed.'}, status=status.HTTP_400_BAD_REQUEST)

            if request_status == "APPROVED" and get_fund_request.request_status != "PENDING":
                return Response({'status': 'fail', 'message': 'Fund request has already been processed.'}, status=status.HTTP_400_BAD_REQUEST)

            if request_status == "REVERSED" and get_fund_request.request_status != "APPROVED":
                return Response({'status': 'fail', 'message': 'Only requests with "APPROVED" status can be reversed.'}, status=status.HTTP_400_BAD_REQUEST)

            bank = AdminBankDetails.objects.get(bd_id=get_fund_request.deposite_bank.bd_id)
            charge = 0.00
            hsn_rate = 0.00
            if get_fund_request.deposite_category.get('online_transaction') == True:
                charge = bank.online_charges.get('Charge')
                charge_type = bank.online_charges.get('charge_type')
                minimum_amount = bank.online_charges.get('minimum_amount')
                maximum_amount = bank.online_charges.get('maximum_amount')
                hsn_rate = HSNSAC.objects.get(hsnsac_id=bank.online_charges.get('hsn_sac')).tax_rate
            elif get_fund_request.deposite_category.get('cdm_deposit') == True:
                charge = bank.cdm_charges.get('Charge')
                charge_type = bank.cdm_charges.get('charge_type')
                minimum_amount = bank.cdm_charges.get('minimum_amount')
                maximum_amount = bank.cdm_charges.get('maximum_amount')
                hsn_rate = HSNSAC.objects.get(hsnsac_id=bank.cdm_charges.get('hsn_sac')).tax_rate
            elif get_fund_request.deposite_category.get('counter_deposit') == True:
                charge = bank.counter_charges.get('Charge')
                charge_type = bank.counter_charges.get('charge_type')
                minimum_amount = bank.counter_charges.get('minimum_amount')
                maximum_amount = bank.counter_charges.get('maximum_amount')
                hsn_rate = HSNSAC.objects.get(hsnsac_id=bank.counter_charges.get('hsn_sac')).tax_rate
            else:
                charge = 0.00
                hsn_rate = 0.00
                minimum_amount = 0.00
                maximum_amount = 0.00

            deposit_amount = get_fund_request.deposite_amount
            request_user = get_fund_request.created_by
            admin_id = request_user.admin_id
            portal_user = PortalUser.objects.get(id=admin_id)
            rate_amount = float(deposit_amount) * (float(charge) / 100) if charge_type == 'is_percent' else float(charge)   

            gst_amount = rate_amount - (rate_amount/(1+(float(hsn_rate))/100))
            
            effective_ammount = float(deposit_amount) - float(rate_amount)

            try: 
                get_portal_user_wallet = PortalUserWallet.objects.get(pu=request_user.admin_id)
            except PortalUserWallet.DoesNotExist:
                return Response({'status': 'fail', 'message': 'PortalUser wallet not exists.'},
                            status=status.HTTP_404_NOT_FOUND)
            
            if request_status == "APPROVED" and get_fund_request.request_status == "PENDING":     
                main_wallet_amount = get_portal_user_wallet.main_wallet
                get_portal_user_wallet.main_wallet = float(main_wallet_amount) + effective_ammount
                get_portal_user_wallet.save()

                # Credit Deposit Amount in Admin Wallet
                global_transaction = GlTrn.objects.create(
                    service_trn_id=get_fund_request.pk,
                    gl_trn_amt=deposit_amount,
                    effectvie_wallet="main_wallet",
                    effectvie_amt=deposit_amount,
                    effective_type="CR",
                    pu=portal_user,
                    service_trn_table="ad_fund_request",
                    gl_trn_dt=timezone.now()
                )

                WalletTrn.objects.create(
                    action_id=global_transaction.pk,
                    action_type="fund_request",
                    wl_label=f"Fund_request_by_{portal_user.pu_name}_of_amount_{deposit_amount}",
                    effectvie_wallet="main_wallet",
                    effectvie_amt=deposit_amount,
                    effective_type="CR",
                    pu=portal_user,
                    current_balance=float(get_portal_user_wallet.main_wallet)+float(deposit_amount),
                    wl_trn_dt=timezone.now()
                )
                
                # Debit Charges from Admin Wallet
                global_transaction = GlTrn.objects.create(
                    service_trn_id=get_fund_request.pk,
                    gl_trn_amt=deposit_amount,
                    gl_tax_rate=hsn_rate,
                    gl_tax_amt=gst_amount,
                    effectvie_wallet="main_wallet",
                    effectvie_amt=rate_amount,
                    effective_type="DR",
                    pu=portal_user,
                    service_trn_table="ad_fund_request",
                    gl_trn_dt=timezone.now()
                )

                WalletTrn.objects.create(
                    action_id=global_transaction.pk,
                    action_type="fund_request",
                    wl_label=f"Fund_request_by_{portal_user.pu_name}_of_amount_{deposit_amount}",
                    effectvie_wallet="main_wallet",
                    effectvie_amt=rate_amount,
                    effective_type="DR",
                    pu=portal_user,
                    current_balance=float(get_portal_user_wallet.main_wallet)+float(deposit_amount)-float(rate_amount),
                    wl_trn_dt=timezone.now()
                )

                get_fund_request.request_status = request_status
                get_fund_request.reason = reason if reason else None
                get_fund_request.save()

                # Log the activity
                activity = SaUserActivity(
                    table_id=get_fund_request.pk,  # ID of the AboutUs entry
                    table_name='ad_fund_request',  # Name of the table
                    ua_action='Update',  # Action performed
                    ua_description='Fund request approved successfully.',  # Action description
                    created_by=request.user  # Current user performing the action
                )
                activity.save()

                return Response({'status': 'success', 'message': 'Fund request approved successfully.'},
                            status=status.HTTP_200_OK)

            elif request_status == "REVERSED" and get_fund_request.request_status == "APPROVED":

                main_wallet_amount = get_portal_user_wallet.main_wallet
                get_portal_user_wallet.main_wallet = float(main_wallet_amount) - effective_ammount
                get_portal_user_wallet.save()

                get_fund_request.request_status = request_status
                get_fund_request.reason = reason
                get_fund_request.save()
                # Log the activity
                activity = SaUserActivity(
                    table_id=get_fund_request.pk,  # ID of the AboutUs entry
                    table_name='ad_fund_request',  # Name of the table
                    ua_action='Update',  # Action performed
                    ua_description='Fund request reversed successfully.',  # Action description
                    created_by=request.user  # Current user performing the action
                )
                activity.save()

                return Response({'status': 'success', 'message': 'Fund request reversed successfully.'},
                            status=status.HTTP_200_OK)

            elif request_status == "REJECTED":
                get_fund_request.request_status = request_status
                get_fund_request.reason = reason
                get_fund_request.save()

                # Log the activity
                activity = SaUserActivity(
                    table_id=get_fund_request.pk,  # ID of the AboutUs entry
                    table_name='ad_fund_request',  # Name of the table
                    ua_action='Update',  # Action performed
                    ua_description='Fund request rejected successfully.',  # Action description
                    created_by=request.user  # Current user performing the action
                )
                activity.save()

                return Response({'status': 'success', 'message': 'Fund request rejected successfully.'},
                            status=status.HTTP_200_OK)
            
            else:
                return Response({'status': 'fail', 'message': 'Invalid request status.'},
                            status=status.HTTP_400_BAD_REQUEST) 

        except AdminFundRequest.DoesNotExist:
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
            fund_request_queryset = AdminFundRequest.objects.get(fr_id=fr_id, is_delete=False)
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
                file_path = handle_uploaded_file(payment_proof, 'Admin/PaymentProof') if payment_proof else None
                payment_proof_file_paths = {'payment_proof': file_path}

            bank_detail = AdminBankDetails.objects.get(bd_id=bd_id)

            if deposite_category_json.get("counter_deposit") == True or deposite_category_json.get("cdm_deposit") == True:
                if not transaction_id: return Response({'status': 'fail','message': 'transaction_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
                if len(transaction_id) < 12 or len(transaction_id) > 16: return Response({'status': 'fail', 'message': 'transaction_id length must be between 12 to 16.'}, status=status.HTTP_400_BAD_REQUEST)

                fund_request_queryset.deposite_category = deposite_category_json
                fund_request_queryset.deposite_bank = bank_detail
                fund_request_queryset.deposite_amount = deposit_amount
                fund_request_queryset.transaction_id = transaction_id
                if payment_proof:
                    fund_request_queryset.payment_proof = payment_proof_file_paths
                fund_request_queryset.remark = remark
                fund_request_queryset.save()

                # Log the activity
                activity = SaUserActivity(
                    table_id=fund_request_queryset.pk,  # ID of the AboutUs entry
                    table_name='ad_fund_request',  # Name of the table
                    ua_action='Update',  # Action performed
                    ua_description='Fund request updated successfully.',  # Action description
                    created_by=request.user  # Current user performing the action
                )
                activity.save()

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
                # Log the activity
                activity = SaUserActivity(
                    table_id=fund_request_queryset.pk,  # ID of the AboutUs entry
                    table_name='ad_fund_request',  # Name of the table
                    ua_action='Update',  # Action performed
                    ua_description='Fund request updated successfully.',  # Action description
                    created_by=request.user  # Current user performing the action
                )
                activity.save()

                return Response({"status": "success", "message": "Fund request updated successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': 'At least one deposite category must be true.'}, status=status.HTTP_400_BAD_REQUEST)

        except AdminBankDetails.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Bank does not exists.'}, status=status.HTTP_404_NOT_FOUND)
        except AdminFundRequest.DoesNotExist:
            return Response({"status": "fail", "message": "Fund request does not exist."},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminBankDetailsAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsSuperAdmin]

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
                return Response({'status': 'fail', 'message': 'Invalid account number. It should contain only digits and be between 11 and 16 characters long.'}, status=status.HTTP_400_BAD_REQUEST)

            deposite = json.loads(deposite_category)
            get_exists_bank = AdminBankDetails.objects.filter(bank_name=bank_name, ifsc_code=ifsc_code, account_number=account_number, is_delete=False).first()
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

            user = CustomUser.objects.get(id=request.user.id)
            AdminBankDetails.objects.create(
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
            bank_details_id = request.data.get('bank_details_id', None)
            search = request.data.get('search', None)
            depostie_category = request.data.get('depostie_category', None)
            if not page_size:
                return Response({'status': 'fail', 'message': 'Page size is required.'}, status=status.HTTP_400_BAD_REQUEST)

            get_bank_details = AdminBankDetails.objects.filter(is_delete=False)

            if search is not None:
                # if not search:
                #     return Response({'status': 'fail', 'message': 'Search is required.'}, status=status.HTTP_400_BAD_REQUEST)

                get_bank_details = get_bank_details.filter(Q(bank_name__icontains=search) | Q(ifsc_code__icontains=search) | Q(account_number__icontains=search))

            if bank_details_id is not None:
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

            bank_detail = AdminBankDetails.objects.get(bd_id=bank_details_id, is_delete=False)
            bank_detail.is_delete = True
            bank_detail.save()
            return Response({'status': 'success', 'message': 'Bank Details deleted successfully.'}, status=status.HTTP_200_OK)

        except AdminBankDetails.DoesNotExist:
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

            if not bank_details_id: return Response({'status': 'fail', 'message': 'bank details ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

            bank_id_validation = isnumber(bank_details_id)
            if bank_id_validation == False:
                return Response({'status': 'fail', 'message': 'Invalid bank details ID. It should contain only digits.'})
            get_bank_details = AdminBankDetails.objects.get(bd_id=bank_details_id, is_delete=False)
            if bank_details_id and not any([bank_name, deposite_category, ifsc_code, branch_name, account_type, account_number]):
                get_fund_request = AdminFundRequest.objects.filter(deposite_bank=get_bank_details, is_delete=False).first()
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
        

class AdminVerifyBankDetailsAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin | IsSuperAdmin]

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


class CredentialsJsonAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsSuperAdmin]

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
            
            service_provider = ServiceProvider.objects.get(sp_id=sp_id)
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


class AdminOtherChargesAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsSuperAdmin | IsAdmin]

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

            all_charges = SaOtherCharges.objects.filter(is_deleted=False).order_by('-pk')

            if oc_id:
                all_charges = all_charges.filter(oc_id=oc_id).order_by('-pk')
            
            if search != '':
                all_charges = all_charges.filter(oc_name__icontains=search).order_by('-pk')

            paginator = Paginator(all_charges, page_size)
            configeds = paginator.page(page_number)
            serializer = SaOtherChargesSerializer(configeds, many=True)
            for data in serializer.data:
                hsn_sac = HSNSAC.objects.get(hsnsac_id=data['hsn_sac'])
                data['hsn_sac'] = f'{hsn_sac.hsnsac_code} ({hsn_sac.tax_rate}%)'
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
        charge_type = request.data.get('charge_type', None)
        charge = request.data.get('charge', None)
        hsn_code = request.data.get('hsn_code', None)

        try:
            other_charges = SaOtherCharges.objects.get(oc_id=oc_id)
            if not charge_type and not charge and not hsn_code:

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
                    hsn_sac = HSNSAC.objects.get(hsnsac_id=hsn_code)

                other_charges.charge_type = charge_type if charge_type else other_charges.charge_type
                other_charges.charge = charge if charge else other_charges.charge
                other_charges.hsn_sac = hsn_sac if hsn_code else other_charges.hsn_code
                other_charges.save()

                return Response({'status': 'success', 'message': 'Other Charges updated successfully.'}, status=status.HTTP_200_OK)

        except AdHSNSAC.DoesNotExist:
            return Response({'status': 'fail', 'message': 'HSN dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except SaOtherCharges.DoesNotExist:
            return Response({'status': 'fail', 'message': 'other charge dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def delete(self, request):
        oc_id = request.data.get('oc_id')

        try:
            if not oc_id: return Response({'status': 'fail', 'message': 'oc_id is requried.'}, status=status.HTTP_400_BAD_REQUEST)

            other_charges = SaOtherCharges.objects.getr(oc_id=oc_id)

            other_charges.is_deleted = True
            other_charges.save()

            return Response({'status': 'success', 'message': 'Other Charges deleted successfully.'}, status=status.HTTP_200_OK)

        except SaOtherCharges.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Other charges dose not exists.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
