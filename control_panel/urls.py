from django.urls import path
from .views import *
from .sa_sub_service import *


# Define URL patterns for the app
urlpatterns = [
    # URL contact_enquiry for managing services
    path('fees_type/', FeesTypeView.as_view(), name='fees_type'),



    path('SaService/', SaServiceAPIView.as_view(), name='SaService'),
    path('ServiceProvider/',ServiceProviderAPIView.as_view(), name='ServiceProvider'),

    path('Charges/',ChargesView.as_view(), name='Charges'),
   

    path('product_category/',ProductCategoryApiView.as_view(), name='product_category'),

    path('expense/',ExpenseApiView.as_view(), name='expense'),
    
    path('SaAdmin/',AdminAPIView.as_view(), name='Admin'),

    path('admin/serivce-charges/', AdminServicesChargesAPIView.as_view()),
    
    path('RequiredDocumentList/',RequiredDocumentListAPI.as_view(), name='RequiredDocumentList'),



    # URL for HSNSAC code management
    path('hsnsac/', HSNSACApiView.as_view(), name='hsnsac'),
    
    path('AdminService/', AdminServiceAPIView.as_view(), name='AdminService'),

    path('product/', ProductApiView.as_view(), name='product'),
    
    path('verify-pan/', PanVerification.as_view(), name='verify-pan'),
    
    path('verify-gst/', GstVerification.as_view(), name='verify-gst'),
    
    path('states/',RegionListView.as_view(), name="states"),

    path('city/',CityList.as_view(), name="city"),

    path('beneficiary/',Beneficiary.as_view(),name="beneficiary"),

    path('authentication/',Authentication.as_view(),name="authentication"),

    path('transfer/',Transfer.as_view(),name="transfer"),
    
    path('CreteOrder/', CreteOrder.as_view(), name='CreteOrder'),

    #bank details
    path('admin/banks/bank-details/', AdminBankDetailsAPIView.as_view()),
    path('admin/banks/verify-bank-details/', AdminVerifyBankDetailsAPIView.as_view()),

    # Fund request
    path('admin/fund-request/', AdminFundRequestAPIView.as_view()),

    # bbps category
    path('admin/service/sub-service/', AdminCategoryAPIView.as_view()),

    # credentials json
    path('service/provider/credentials/json/', CredentialsJsonAPIView.as_view()),

    #admin other charges
    path('admin/other/charges/', AdminOtherChargesAPIView.as_view()),

] 