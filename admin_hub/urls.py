from django.urls import path
from .views import *
from .payout_service import *
from .razorpay_services import *
from .commission_calculations import *
from .paysprint_airtel_cms_service import *
from .cashfree_pg_service import *
from .mobile_recharge_service import *
from .paysprint_dmt_service import *
from .bbps_service import *
from .testing import *
from .phonepe_pg_service import *
from .ad_sub_service import *

urlpatterns = [
    # Auth Module
    path('auth/verify-contact/', VerifyContactNoAPIView.as_view()),
    path('auth/verify-code/', VerifyCodeAPIView.as_view()),
    path('auth/verify-distributor-details/', VerifyDistributorDetailsAPIView.as_view()),
    path('auth/verify-retailer-details/', VerifyRetailerDetailsAPIView.as_view()),
    path('auth/user-authenticate/', AuthHandlerAPIView.as_view()),
    path('auth/user-login/', UserLoginAPIView.as_view()),

    # kyc details
    path('user/kyc/info/', KYCinfoAPIView.as_view()),
    
    # kyc verfied api
    path('kyc/kyc-verified/', KYCVerifiedAPIView.as_view()),

    # HSN/SAC Module
    path('master/hsn-sac/', HsnSacAPIView.as_view()), 

    # Service Module
    path('master/service/', ServiceAPIView.as_view()),

    # Announcement Module
    path('master/announcement/', AnnouncementPIView.as_view()),

    # Service Provider Module
    path('master/service-provider/', ServiceProviderAPIView.as_view()),

    # User Profile Module
    path('profile/user-profile/', UserProfileAPIView.as_view()),

    # Partner Cateogry Module
    path('partners/partner-category/', PartnerCategoryAPIView.as_view()),

    ## CashFree Payout APIs
    path('payout/cf/', CfPayOutAPIView.as_view()),
    path('paysprint/paysprint-dmt/', PaysPrintDmtAPIView.as_view()),
    path('paysprint/paysprint-dmt/beneficiary/', PaysPrintDmtBeneficiaryAPIView.as_view()),
    path('paysprint/paysprint-dmt/dmt-bank-list/', PaysPrintGlobalBankListAPIView.as_view()),

    #customer payout bank account
    path('payout/beneficiary/', CfPayoutBeneficiaryAPIView.as_view()),

    # CashFree Payment Gateway APIs
    path('payment-gateway/cashfree/', CashfreePaymentAPIView.as_view()),

    # Razorpay Payment Gateway APIs
    path('payment-gateway/razorpay/', RazorpayAPIView.as_view()),

    # Users/Downline and Create user
    path('users/user/', UserAPIView.as_view()),

    # Users/Service and Charges
    path('users/service-charges/', UserServicesChargesAPIView.as_view()),

    # Create and fetch Fund Request API
    path('retailers/fund-request/', FundRequestAPIView.as_view()),

    #get device active
    path('device/', DeviceAPIView.as_view()),

    # switching portal module
    path('session-bypass/session-bypass-user/', SessionByPassUserAPIView.as_view()),
    path('user/switch/', tcpl@2025prod.as_view()),

    #bank details
    path('banks/bank-details/', BankDetailsAPIView.as_view()),
    path('banks/verify-bank-details/', VerifyBankDetailsAPIView.as_view()),

    #wallet to wallet 
    path('wallet/wallet-transaction/', WalletAPIView.as_view()),

    #service provider pined
    path('retailers/dynamic-service-provider/', RetailerDynamicServiceProviderAPIView.as_view()),

    # portal user wallet
    path('user/user-wallet/', PortalUsertWalletAPIView.as_view()),

    # airtel cms service
    path('airtel/cms/', AirtelCmsAPIView.as_view()),

    #mobile reacharge
    path('mobile/recharge/', MobileRechargeAPIView.as_view()),

    # upload bank list
    path('upload-bank-list/', UploadBankListAPIView.as_view(), name='upload-bank-list'),

    # bbps category
    # path('bbps/category/', BbpsCategoryAPIView.as_view()),

    # bbps biller list
    # path('bbps/biller-list/', BbpsBillerListAPIView.as_view()),

    # process excel to xml
    path('process/excel/xml/', process_excel_to_xml),

    # encrypt data
    path('encrypt/', encrypt),
    
    # decrypt data
    # path('decrypt/', DecryptData.as_view()),

    # xml to encrypt data
    path('encrypt/data/', EncryptData.as_view()),

    # convert xml to json
    path('convert/xml/json/', ConvertXmlToJson.as_view()),

    # bill fatch
    path('bill/fetch/', bill_fatch),

    #bbps API
    path('bbps/biller/', BbpsBillerAPIView.as_view()),
    path('bbps/complaint/', BbpsComplaintAPIView.as_view()),
    # path('bbps/biller/entery/', BbpsBillerEntryAPIView.as_view()),

    # credentials_json
    path('credentials/json/', CredentialsJsonAPIView.as_view()),

    # biller
    path('biller/', biller), 
    path('bbps/biller/entery/', BbpsBillerEntryAPIView.as_view()),
    path('bbps/biller/biller-info/entry/', BbpsBillerInfoEntryAPIView.as_view()),
    # path('response/entery/', ResponseEntery.as_view())

   # update category charges
    path('user/service/sub-service/', UpdateServiceCategoryCharges.as_view()),

    # transaction API / tds rate API / tax API 
    path('transactions/transaction/', TransactionAPIView.as_view()),
    path('reports/tds-rate/', TdsRateAPIView.as_view()),
    path('earning/earn/', EarnAPIView.as_view()),
    # path('reports/tax/', TaxAPIView.as_view()),

    # test commission calculations
    path('test/calculations', TestCalculation.as_view()),

    #manually credit or debit
    path('admin/user-credit-debit/', AdminCreditDebit.as_view()),

    # phone pe 
    path('phonepe/', PhonePeAPIView.as_view()),
    path('phonepe/response/', PhonePeResponse.as_view()),

    # other charges wallet
    path('other/charges/wallet/', OtherChargesAPIView.as_view()),

    # os transaction
    path('top-up/transaction/', TopUpTransactionAPIView.as_view()),

    # retailer bank details
    path('retailer/bank/details/', RetailerBankAPIView.as_view()),

    # DISTRIBUTOR dashboard
    path('distributor/dashboard/', DistributorDashBoard.as_view()),

    # RETAILER dashboard
    path('retailer/dashboard/', RetailerDashBoard.as_view()),

    # User Activity
    path('user/activity/', UserActivityAPIView.as_view()),

    # user log
    path('user/dashboard/log/', UserLogList.as_view()),

    # update bank list
    path('user/bank-details/', UserBankDetailsAPIView.as_view()),

]
