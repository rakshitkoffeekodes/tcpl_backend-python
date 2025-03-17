from rest_framework import serializers
from tcpl_backend import settings
from .models import *
from django.utils.crypto import get_random_string
from control_panel.models import *

class ContactNoSerializer(serializers.Serializer):
    contact_no = serializers.CharField(max_length=10)


class CodeSerializer(serializers.Serializer):
    # email = serializers.EmailField()
    code = serializers.CharField(max_length=6)


class GenerateCredentialsSerializer(serializers.Serializer):
    pu_login_pin = serializers.CharField(required=True)


# class RetailerBankAccountsSerializer(serializers.ModelSerializer):
#     status = serializers.SerializerMethodField()

#     class Meta:
#         model = RetailerBankAccounts
#         fields = '__all__'
#         read_only_fields = ('created_at', 'updated_by', 'updated_at')
#         extra_kwargs = {
#             'rtl_beneficiary_id': {'required': False}
#         }

#     def get_status(self, obj):
#         return "Active" if not obj.is_deactive else "Inactive"

#     def validate(self, data):
#         required_fields = [
#             'rtl_beneficiary_name', 'rtl_bank_name',
#             'bnk_acc_no', 'bnk_ifsc'
#         ]

#         for field in required_fields:
#             if not data.get(field):
#                 raise serializers.ValidationError(
#                     f"{field.replace('_', ' ').title()} is required.")

#         return data

#     def create(self, validated_data):
#         if not validated_data.get('rtl_beneficiary_id'):
#             validated_data['rtl_beneficiary_id'] = get_random_string(length=12)
#         return super().create(validated_data)

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         exclude_fields = self.context.get('exclude_fields', [])
#         for field in exclude_fields:
#             representation.pop(field, None)
#         return representation


# class PayoutTransactionSerializer(serializers.ModelSerializer):
#     """
#     Serializer for the Payout Transaction model.
#     """

#     class Meta:
#         model = PayoutTransaction
#         fields = "__all__"

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         exclude_fields = self.context.get('exclude_fields', [])
#         for field in exclude_fields:
#             representation.pop(field, None)
#         return representation
    

class PortalUserWalletSerializer(serializers.ModelSerializer):

    class Meta:
        model = PortalUserWallet
        fields = ['main_wallet', 'commission_wallet']


class PortalUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the PortalUser model.
    """

    class Meta:
        model = PortalUser
        fields = ['id', 'pu_name', 'pu_email', 'pu_contact_no', 'pu_role']
        # read_only_fields = ['password']


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City  
        fields = ['city_name']  


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State  
        fields = ['state_name'] 


class PortalUserDetailsSerializers(serializers.ModelSerializer):
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    doc_images = serializers.SerializerMethodField()

    class Meta:
        model = PortalUserDetails
        exclude = ['created_at', 'updated_at', 'pu', 'created_by']

    def get_doc_images(self, obj):
        request = self.context.get('request')
        scheme = "https" if request.is_secure() else "http"
        
        docs_files_json = obj.doc_images
        
        # if docs_files_json :
        #     for k,v in docs_files_json.items():
        #         file_path =  v.replace('\\', '/')
        #         docs_files_json[k] = f"{scheme}://{request.get_host()}{settings.MEDIA_URL}{file_path}"
        return docs_files_json

    def get_city(self, obj):
        try:
            city = City.objects.get(city_id=obj.city_id) 
            serializer = CitySerializer(city)
            return serializer.data  
        except City.DoesNotExist:
            return None

    def get_state(self, obj):
        try:
            state = State.objects.get(state_id=obj.state_id)  
            serializer = StateSerializer(state)
            return serializer.data  
        except State.DoesNotExist:
            return None

class HSNSACSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdHSNSAC
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdService
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ServiceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdServiceProvider
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCharges
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class DistributorHierarchySerializer(serializers.ModelSerializer):
    # Define parent_category_name as a SerializerMethodField
    parent_category_name = serializers.SerializerMethodField()
    hc_charges = serializers.SerializerMethodField()

    class Meta:
        model = DistributorHierarchy
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_parent_category_name(self, obj):
        # Check if `dh_parent_id` exists and return its name
        if obj.dh_parent_id:
            parent_category_name = DistributorHierarchy.objects.get(dh_id=obj.dh_parent_id).dh_name
        else:
            parent_category_name = None
        return parent_category_name
    
    def get_hc_charges(self, obj):
        # Check if `dh_parent_id` exists and return its name
        sp_id = self.context.get('request').data.get('sp_id')

        if obj.dh_id:
            try:
                hirerchy_charges_data = HierarchyCharges.objects.get(dh=obj.dh_id, sp=sp_id).hc_charges
            except:
                hirerchy_charges_data = []
        else:
            hirerchy_charges_data = []

        return hirerchy_charges_data
    
class HierarchyChargesSerializer(serializers.ModelSerializer):

    class Meta:
        model = HierarchyCharges
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # hsn_sac_instance = instance.hsn_sac
        # if hsn_sac_instance:
        #     hsn_sac_data = HSNSACSerializer(hsn_sac_instance, context={'exclude_fields': ["updated_by", "created_at", "created_by", "is_deleted", "is_deactive", "updated_at", "description"]}).data
        #     representation['hsn_sac'] = hsn_sac_data

        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation


# class CustomerSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Customer
#         exclude = ['created_at', 'updated_at', 'verify_code', 'verify_code_expire_at']

class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        exclude = ["deposite_category", "created_at", "updated_at", "updated_by", "created_by", "is_deactive", "is_delete"]

class FundRequestSerializer(serializers.ModelSerializer):
    bank_detail = serializers.SerializerMethodField()
    payment_proof = serializers.SerializerMethodField()
    retailer_name = serializers.SerializerMethodField()
    pud_unique_id = serializers.SerializerMethodField()

    class Meta:
        model = FundRequest
        exclude = ["updated_by", "is_delete"]

    def get_bank_detail(self, obj):
        try:
            get_bank_detail = BankDetails.objects.get(bd_id=obj.deposite_bank.bd_id) 
            serializer = BankDetailsSerializer(get_bank_detail)
            return serializer.data  
        except BankDetails.DoesNotExist:
            return None
    
    def get_payment_proof(self, instance):
        request = self.context.get('request')
        scheme = "https" if request.is_secure() else "http"
        
        payment_proof = instance.payment_proof
        
        if payment_proof:
            file_path = payment_proof.get('payment_proof').replace('\\', '/')
            return f"{scheme}://{request.get_host()}/media/{file_path}"
        
        return None

    def get_retailer_name(self, obj):
        return obj.created_by.pu_name if obj.created_by else None

    def get_pud_unique_id(self, obj):
        try:
            return PortalUserDetails.objects.get(pu=obj.created_by).pud_unique_id
        except PortalUserDetails.DoesNotExist:
            return None
    

class PyOtBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = PyOtBankAccount
        exclude = ["created_at", "updated_at", "updated_by", "created_by", "is_deleted"]

class PyOtCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PyOtCustomer
        exclude = ["created_at", "updated_at", "verify_code", "verify_code_expire_at"]

class WalletTrnSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTrn
        exclude = ['created_at']

class PyOtServiceTrnSerializer(serializers.ModelSerializer):
    class Meta:
        model = PyOtServiceTrn
        exclude = ['created_at']

class PgServiceTrnSerializer(serializers.ModelSerializer):
    class Meta:
        model = PgServiceTrn
        exclude = ['created_at']

class PaysPrintDmtBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaysPrintDmtBankAccount
        exclude = ["created_at", "updated_at", "updated_by", "created_by", "is_deleted"]

class PaysPrintDmtCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaysPrintDmtCustomer
        exclude = ["created_at", "updated_at", "verify_code", "verify_code_expire_at"]

class PaysPrintGlobalBankListSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalBankList
        exclude = ["created_at"]

class PaySprintDmtTrnSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMTTransaction
        exclude = ['created_at']

class GlTrnSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlTrn
        exclude = ['created_at']

class AdOperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Oprators
        fields = '__all__'

class BBPSBillerCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BBPSBillerCategory
        exclude = ["created_at", "updated_at"]

class BBPSBillerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BBPSBiller
        exclude = ["created_at", "updated_at"]

class BBPSBillerResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BBPSBillResponse
        exclude = ["created_at"]

class BBPSBillerPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BBPSBillPayment
        exclude = ["updated_at"]

class BBPSComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = BBPSComplaint
        exclude = ["updated_at"]

class MobileRechargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileRecharge
        exclude = ["created_at"]

class CfPgServiceTrnSerializer(serializers.ModelSerializer):
    class Meta:
        model = CfPgServiceTrn
        fields = "__all__"

class AdCfPgConfigedSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCfPgConfiged
        fields = "__all__"

class PhonePeConfigedSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCfPgConfiged
        fields = "__all__"

class PhonePeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhonePeTransaction
        exclude = ["updated_at"]

class OtherChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherCharges
        fields = "__all__"

class TopUpTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopUpTransaction
        fields = "__all__"

class RetailerBanksSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetailerBankDetails
        exclude = ["updated_at", "updated_by"]

class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = "__all__"

class PortalUserLoginLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalUserLoginLogs
        fields = "__all__"
        
class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = "__all__"
