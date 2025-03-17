from django.db import models


class PgTrnChoice(models.TextChoices):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    SETTLED = 'SETTLED'


class MrkTyChoice(models.TextChoices):
    CR = 'CR' 
    DR = 'DR'


class ServiceNatureChoice(models.TextChoices):
    charges = 'charges'
    commission = 'commission'


class RequestStatus(models.TextChoices):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    REVERSED = 'REVERSED'


class TransactionMode(models.TextChoices):
        IMPS = 'IMPS'
        RTGS = 'RTGS'
        NEFT = 'NEFT'


class AdHSNSAC(models.Model):
    hsnsac_id = models.AutoField(primary_key=True)
    hsnsac_code = models.CharField(max_length=255)
    tax_rate = models.DecimalField(max_digits=10, decimal_places=3)
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'PortalUser', on_delete=models.PROTECT, db_column='created_by', null=True)
    updated_at = models.DateTimeField(null=True)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.hsnsac_code

    class Meta:
        db_table = "ad_hsn_sac_code"
        app_label = 'admin_hub'


class AdService(models.Model):
    service_id = models.AutoField(primary_key=True)
    service_name = models.CharField(max_length=50)
    description = models.TextField(null=True)
    is_global = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'PortalUser', on_delete=models.PROTECT, db_column='created_by', null=True)
    updated_at = models.DateTimeField(null=True)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.service_name

    class Meta:
        db_table = "ad_service"
        app_label = 'admin_hub'


class AdServiceProvider(models.Model):
    sp_id = models.AutoField(primary_key=True)
    service = models.ForeignKey(
        AdService, on_delete=models.CASCADE)
    sp_name = models.CharField(max_length=150, null=True)
    label = models.CharField(max_length=255, null=True)
    tds_rate = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, default=0.000)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.ForeignKey(
        'PortalUser', on_delete=models.PROTECT, db_column='created_by', null=True)
    hsn_sac = models.ForeignKey(AdHSNSAC, on_delete=models.PROTECT, null=True)
    parent_id = models.IntegerField(null=True, blank=True)
    credentials_json = models.JSONField(null=True, blank=True)
    plateform_fee_type = models.CharField(max_length=50, null=True, blank=True)
    plateform_fee = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, default=0.000)
    required_key = models.JSONField(null=True, blank=True)
    is_self_config = models.BooleanField(default=False)
    service_nature = models.CharField(max_length=20, choices=ServiceNatureChoice.choices, null=True, blank=True)
    is_table_config  = models.BooleanField(default=False, null=True, blank=True)
    config_table_name  = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField(null=True)
    sa_provided = models.BooleanField(default=True)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.sp_name

    class Meta:
        db_table = "ad_service_provider"
        app_label = 'admin_hub'


class AdCharges(models.Model):
    CHARGES_TYPE_CHOICES = [
        ('CR', 'Credit'),
        ('DR', 'Debit'),
    ]

    CHARGES_RATE_TYPE_CHOICES = [
        ('is_flat', 'Is_Flat'),
        ('is_percent', 'Is_Percent'),
    ]
    CHARGE_CATEGORY_CHOICES = [
        ('to_us', 'To Us'),
        ('to_provide', 'To Provide'),
    ]
    charges_id = models.AutoField(primary_key=True)
    service_provider = models.ForeignKey(
        AdServiceProvider, on_delete=models.CASCADE)
    charges_type = models.CharField(max_length=2, choices=CHARGES_TYPE_CHOICES)
    rate_type = models.CharField(
        max_length=20, choices=CHARGES_RATE_TYPE_CHOICES)
    minimum = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0.000)
    maximum = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0.000)
    rate = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, default=0.000)
    charge_category = models.CharField(
        max_length=20, choices=CHARGE_CATEGORY_CHOICES, default='to_us')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'PortalUser', on_delete=models.CASCADE, db_column='created_by', null=True, blank=True)
    updated_at = models.DateTimeField(null=True)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.charges_id} ({self.service_provider.sp_name})"

    class Meta:
        db_table = 'ad_charges'
        app_label = 'admin_hub'


class AdCommissionCharges(models.Model):
    CHARGES_TYPE_CHOICES = [
        ('CR', 'Credit'),
        ('DR', 'Debit'),
    ]

    CHARGES_RATE_TYPE_CHOICES = [
        ('is_flat', 'Is_Flat'),
        ('is_percent', 'Is_Percent'),
        ('is_slab', 'Is_Slab'),
    ]

    commission_charges_id = models.AutoField(primary_key=True)
    service_provider = models.ForeignKey(
        AdServiceProvider, on_delete=models.CASCADE)
    charges_type = models.CharField(max_length=2, choices=CHARGES_TYPE_CHOICES, blank=True, null=True)
    rate_type = models.CharField(
        max_length=20, choices=CHARGES_RATE_TYPE_CHOICES)
    minimum = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0.000)
    maximum = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0.000)
    rate = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, default=0.000)
    is_slab = models.BooleanField(default=False, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'PortalUser', on_delete=models.CASCADE, db_column='created_by', null=True, blank=True)
    updated_at = models.DateTimeField(null=True)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.commission_charges_id} ({self.service_provider.sp_name})"

    class Meta:
        db_table = 'ad_commission_charges'
        app_label = 'admin_hub'


class PortalUser(models.Model):
    PORTAL_USER_TYPE = [
        ('Admin', 'Admin'),
        ('Distributor', 'Distributor'),
        ('Retailer', 'Retailer'),
    ]

    STATUS = [
        ('PENDING', 'PENDING'),
        ('APROVE', 'APROVE'),
        ('REJECT', 'REJECT'),
        ('KYC_UNDER_PROCESS', 'KYC_UNDER_PROCESS'),
    ]

    id = models.AutoField(primary_key=True)
    pu_name = models.CharField(max_length=150)
    pu_email = models.CharField(max_length=50)
    pu_contact_no = models.CharField(max_length=10) 
    pu_login_pin = models.CharField(max_length=128, null=True, blank=True)
    pu_role = models.CharField(max_length=20, choices=PORTAL_USER_TYPE)
    verify_code = models.CharField(max_length=128, blank=True, null=True)
    verify_code_expire_at = models.DateTimeField(blank=True, null=True)
    is_verify = models.BooleanField(default=False)
    is_kyc_verify = models.BooleanField(default=False, null=True, blank=True)
    pu_reason = models.TextField(null=True, blank=True)
    pu_status = models.CharField(max_length=255, default='PENDING', choices=STATUS, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('PortalUser', on_delete=models.PROTECT, related_name='portal_user_created_by', null=True, blank=True)
    updated_at = models.DateTimeField(null=True)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.id} ({self.pu_role})"

    class Meta:
        db_table = 'ad_portal_user'
        app_label = 'admin_hub'

    
class PortalUserLoginLogs(models.Model):
    id = models.AutoField(primary_key=True)
    pu_user = models.ForeignKey(PortalUser, on_delete=models.PROTECT, null=True, blank=True)
    pu_user_role = models.CharField(max_length=50)
    pu_token = models.CharField(max_length=300, null=True, blank=True)
    is_expire = models.BooleanField(default=False, null=True, blank=True)
    expire_datetime = models.DateTimeField(null=True, blank=True)
    browser_type = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.CharField(max_length=55, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} ({self.pu_user})"

    class Meta:
        db_table = 'ad_portal_user_login_logs'
        app_label = 'admin_hub'


class PortalUserDetails(models.Model):
    pud_id = models.AutoField(primary_key=True)
    pu = models.ForeignKey(PortalUser, on_delete=models.PROTECT, null=True, blank=True)
    dh = models.ForeignKey('DistributorHierarchy', on_delete=models.PROTECT, null=True, blank=True)
    pud_unique_id = models.CharField(max_length=8, null=True, blank=True)
    aadhaar_card = models.CharField(max_length=12, null=True, blank=True)
    pan_card = models.CharField(max_length=10, null=True, blank=True)
    pan_response = models.TextField(null=True, blank=True)
    dst_rtl_image = models.ImageField(upload_to='Retailer', null=True, blank=True)
    dst_rtl_location = models.JSONField(null=True, blank=True)
    shop_name = models.CharField(max_length=255, null=True, blank=True)
    shop_address = models.TextField(null=True, blank=True)
    shop_state = models.IntegerField(null=True, blank=True)
    shop_city = models.IntegerField(null=True, blank=True)
    shop_zip_code = models.CharField(max_length=6, null=True, blank=True)
    doc_images = models.JSONField(null=True, blank=True)
    shop_location = models.JSONField(null=True, blank=True)
    shop_gst_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    busniess_type = models.CharField(max_length=10, null=True, blank=True)
    alternate_contact_no = models.CharField(max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    kyc_current_location = models.JSONField(null=True, blank=True)
    state_id = models.IntegerField(null=True, blank=True)
    city_id = models.IntegerField(null=True, blank=True)
    zip_code = models.CharField(max_length=6, null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.pud_id}"
    
    class Meta:
        db_table = 'ad_portal_user_details'
        app_label = 'admin_hub'


# class Customer(models.Model):
#     customer_id = models.AutoField(primary_key=True)
#     customer_name = models.CharField(max_length=255)
#     customer_email = models.EmailField(max_length=254, null=True, blank=True)
#     customer_contact_no = models.CharField(max_length=10, unique=True)
#     pg_customer_id = models.CharField(max_length=13, unique=True)
#     verify_code = models.CharField(max_length=128, blank=True, null=True)
#     verify_code_expire_at = models.DateTimeField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(null=True)

#     def __str__(self):
#         return f"{self.customer_name}"

#     class Meta:
#         db_table = 'ad_customer'
#         app_label = 'control_panel'


# class PGTransaction(models.Model):
#     pg_trn_id = models.AutoField(primary_key=True)
#     customer_name = models.CharField(max_length=150)
#     customer_email = models.CharField(max_length=50)
#     customer_contact_no = models.CharField(max_length=10)
#     otp = models.CharField(max_length=6, null=True, blank=True)
#     is_verified = models.BooleanField(default=False)
#     pg_trn_amount = models.DecimalField(
#         max_digits=10, decimal_places=3, null=True, blank=True)
#     pg_trn_status = models.CharField(
#         max_length=20, choices=PgTrnChoice.choices, default=PgTrnChoice.PENDING)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(null=True)

#     def __str__(self):
#         return f"{self.pg_trn_id} ({self.pg_trn_status})"

#     class Meta:
#         db_table = 'ad_pg_transaction'
#         app_label = 'admin_hub'


# class RetailerBankAccounts(models.Model):
#     rtl_bnk_id = models.AutoField(primary_key=True)
#     rtl_beneficiary_id = models.CharField(max_length=12)
#     rtl_beneficiary_name = models.CharField(max_length=100)
#     rtl_bank_name = models.CharField(max_length=100)
#     bnk_acc_no = models.BigIntegerField(null=True, blank=True)
#     bnk_ifsc = models.TextField(null=True, blank=True)
#     rtl_vpa = models.CharField(max_length=50, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     created_by = models.ForeignKey(
#         PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True)
#     updated_at = models.DateTimeField(null=True)
#     updated_by = models.IntegerField(null=True, db_column='updated_by')
#     is_verified = models.BooleanField(default=True)
#     is_deactive = models.BooleanField(default=False)
#     is_deleted = models.BooleanField(default=False)

#     def __str__(self):
#         return f"{self.rtl_bnk_id} ({self.rtl_bank_name})"

#     class Meta:
#         db_table = 'ad_retailer_bank_accounts'
#         app_label = 'admin_hub'


class PortalUserWallet(models.Model):
    puw_id = models.AutoField(primary_key=True)
    pu = models.ForeignKey(PortalUser,on_delete=models.PROTECT, unique=True, null=True, blank=True)
    main_wallet = models.DecimalField(max_digits=19,decimal_places=3,default=0.000)
    commission_wallet = models.DecimalField(max_digits=19,decimal_places=3,default=0.000)
    cashin_wallet = models.DecimalField(max_digits=19,decimal_places=3, null=True, blank=True, default=0.000)
    pg_wallet = models.DecimalField(max_digits=19,decimal_places=3, null=True, blank=True, default=0.000)
    os_wallet = models.DecimalField(max_digits=19,decimal_places=3, null=True, blank=True, default=0.000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True, db_column='updated_by')

    def __str__(self):
        return f"{self.puw_id}"

    class Meta:
        db_table = 'ad_portal_user_wallet'
        app_label = 'admin_hub'


# class PyGTransaction(models.Model):
#     pg_trn_id = models.AutoField(primary_key=True)
#     voucher_id = models.IntegerField()
#     voucher_type = models.CharField(max_length=150)
#     pg_transfer_id = models.CharField(max_length=50,unique=True)
#     pg_trn_amount = models.DecimalField(max_digits=19,decimal_places=3)
#     pg_trn_mode = models.CharField(max_length=15)
#     pg_trn_status = models.CharField(max_length=20,default="PENDING")
#     created_at = models.DateTimeField(auto_now_add=True)
#     created_by = models.ForeignKey(
#         PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True)
#     updated_at = models.DateTimeField(null=True)
#     updated_by = models.IntegerField(null=True, db_column='updated_by')

#     def __str__(self):
#         return f"{self.pg_trn_id}"

#     class Meta:
#         db_table = 'ad_pyg_transaction'
#         app_label = 'admin_hub'


class DistributorHierarchy(models.Model):
    dh_id = models.AutoField(primary_key=True)
    dh_name = models.CharField(max_length=150, unique=True)
    dh_parent_id = models.IntegerField(null=True, blank=True)
    dh_description = models.TextField()
    dh_prefix = models.CharField(max_length=6, null=True, blank=True)
    is_used = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True, db_column='updated_by')

    def __str__(self) -> str:
        return super().__str__()

    class Meta:
        db_table = 'ad_distributor_hierarchy'
        app_label = 'admin_hub'


class HierarchyCharges(models.Model):
    hc_id = models.AutoField(primary_key=True)
    dh = models.ForeignKey(DistributorHierarchy, on_delete=models.PROTECT, null=True)
    sp = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    mark_type = models.CharField(max_length=10, choices=MrkTyChoice.choices, null=True)
    hc_charges = models.JSONField(null=True)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True, db_column='updated_by')

    def __str__(self) -> str:
        return super().__str__()

    class Meta:
        db_table = 'ad_hierarchy_charges'
        app_label = 'admin_hub'


class PortalUserCharges(models.Model):
    puc_id = models.AutoField(primary_key=True)
    sp = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True)
    dh = models.ForeignKey(DistributorHierarchy, on_delete=models.PROTECT, null=True)
    pu_id = models.IntegerField(null=True)
    parent_id = models.IntegerField(null=True)
    mark_type = models.CharField(max_length=10, choices=MrkTyChoice.choices, null=True)
    puc_charges = models.JSONField(null=True)
    is_pinned = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True, db_column='updated_by')

    def __str__(self) -> str:
        return super().__str__()

    class Meta:
        db_table = 'ad_portal_user_charges'
        app_label = 'admin_hub'


class UserCodeVerification(models.Model):
    ucv_id = models.AutoField(primary_key=True)
    ucv_data = models.CharField(max_length=30)
    verify_code = models.CharField(max_length=128, blank=True, null=True)
    verify_code_expire_at = models.DateTimeField(blank=True, null=True)
    is_verify = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return super().__str__()

    class Meta:
        db_table = 'ad_user_code_verification'
        app_label = 'admin_hub'

class BankDetails(models.Model):
    bd_id = models.AutoField(primary_key=True)
    deposite_category = models.JSONField()
    bank_name = models.CharField(max_length=128, blank=True, null=True)
    ifsc_code = models.CharField(max_length=128, blank=True, null=True)
    branch_name = models.CharField(max_length=128, blank=True, null=True)
    account_type = models.CharField(max_length=128, blank=True, null=True)
    account_number = models.CharField(max_length=128, blank=True, null=True)
    online_charges = models.JSONField(null=True, blank=True)
    cdm_charges = models.JSONField(null=True, blank=True)
    counter_charges = models.JSONField(null=True, blank=True)
    is_deactive = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.IntegerField(null=True, blank=True, db_column='updated_by')
   
    def __str__(self) -> str:
        return super().__str__()

    class Meta:
        db_table = 'ad_bank_detail'
        app_label = 'admin_hub'


class FundRequest(models.Model):
    fr_id = models.AutoField(primary_key=True)
    deposite_category = models.JSONField()
    deposite_bank = models.ForeignKey(BankDetails, on_delete=models.PROTECT)
    deposite_amount = models.DecimalField(max_digits=19, decimal_places=3, null=True, default=0.000)
    transaction_id = models.CharField(max_length=128,unique=True, blank=True, null=True)
    utr_number = models.CharField(max_length=128,unique=True, blank=True, null=True)
    transaction_mode = models.CharField(choices=TransactionMode, max_length=128, blank=True, null=True)
    payment_proof = models.JSONField()
    remark = models.TextField(null=True, blank=True)
    is_deactive = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    request_status = models.CharField(choices=RequestStatus, default=RequestStatus.PENDING, max_length=255)
    reasons = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True, db_column='updated_by')

    def __str__(self) -> str:
        return super().__str__()

    class Meta:
        db_table = 'ad_fund_request'
        app_label = 'admin_hub'


'''
Transaction Module (Service wise Transaction Model, Global Transaction Model, Wallet Transaction Model)
'''
class PyOtServiceTrn(models.Model):
    service_trn_id = models.AutoField(primary_key=True)
    sp = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT)
    trn_unique_id = models.CharField(max_length=55)
    trn_amount = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    trn_response = models.JSONField(null=True, blank=True)
    customer_name = models.CharField(max_length=50, null=True, blank=True)
    customer_aadhaar_no = models.CharField(max_length=12, null=True, blank=True)
    customer_contact_no = models.CharField(max_length=10, null=True, blank=True)
    trn_status = models.CharField(max_length=15, null=True, blank=True)
    service_trn_dt = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.service_trn_id}"

    class Meta:
        db_table = 'ad_payout_service_transaction'
        app_label = 'admin_hub'


class AirtelCMSTrn(models.Model):
    trn_id = models.AutoField(primary_key=True)
    cms_name = models.IntegerField(null=True, blank=True)
    trn_refid = models.CharField(max_length=55, null=True, blank=True)
    trn_biller_id = models.IntegerField(null=True, blank=True)
    trn_biller_name = models.CharField(max_length=255, null=True, blank=True)
    trn_mobile_no = models.CharField(max_length=10, null=True, blank=True)
    trn_commission = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    trn_utr = models.CharField(max_length=255, null=True, blank=True)
    trn_ackno = models.CharField(max_length=255, null=True, blank=True)
    trn_unique_id = models.CharField(max_length=55)
    trn_amount = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    trn_response = models.JSONField(null=True, blank=True)
    trn_status = models.CharField(max_length=15, null=True, blank=True)
    trn_dt = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.trn_id}"

    class Meta:
        db_table = 'ad_airtel_cms_transaction'
        app_label = 'admin_hub'


class GlTrn(models.Model):
    gl_trn_id = models.AutoField(primary_key=True)
    service_trn_id = models.IntegerField(null=True, blank=True)
    pu = models.ForeignKey(PortalUser, on_delete=models.PROTECT, null=True, blank=True)
    gl_trn_amt = models.DecimalField(max_digits=19, decimal_places=3 ,null=True, blank=True, default=0.000)
    gl_tds_rate = models.DecimalField(max_digits=19, decimal_places=3 ,null=True, blank=True, default=0.000)
    gl_tax_rate = models.DecimalField(max_digits=19, decimal_places=3 ,null=True, blank=True, default=0.000)
    gl_tds_amt = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    gl_tax_amt = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    service_trn_table = models.CharField(max_length=255, null=True, blank=True)
    effectvie_wallet = models.CharField(max_length=20, null=True, blank=True)
    effectvie_amt = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    effective_type = models.CharField(max_length=10, choices=MrkTyChoice.choices)
    gl_trn_dt = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gl_trn_id}"

    class Meta:
        db_table = 'ad_global_transaction'
        app_label = 'admin_hub'


class WalletTrn(models.Model):
    wl_trn_id = models.AutoField(primary_key=True)
    action_id = models.IntegerField(null=True, blank=True)
    action_type = models.CharField(max_length=255)
    pu = models.ForeignKey(PortalUser, on_delete=models.PROTECT, null=True, blank=True)
    wl_label = models.CharField(max_length=255)
    effectvie_wallet = models.CharField(max_length=20, null=True, blank=True)
    effectvie_amt = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    effective_type = models.CharField(max_length=10, choices=MrkTyChoice.choices)
    current_balance = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    wl_trn_des = models.CharField(max_length=500, null=True, blank=True)
    wl_trn_dt = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wl_trn_id}"

    class Meta:
        db_table = 'ad_wallet_transaction'
        app_label = 'admin_hub'


'''
Payout Module Start
'''
class PyOtCustomer(models.Model):
    pyot_customer_id = models.AutoField(primary_key=True)
    customer_first_name = models.CharField(max_length=255)
    customer_last_name = models.CharField(max_length=255, null=True, blank=True)
    customer_contact_no = models.CharField(max_length=10, unique=True)
    customer_address = models.CharField(max_length=1000, null=True, blank=True)
    customer_zip_code = models.IntegerField(null=True, blank=True)
    pyot_unique_id = models.CharField(max_length=13, unique=True, null=True, blank=True)
    verify_code = models.CharField(max_length=128, blank=True, null=True)
    verify_code_expire_at = models.DateTimeField(blank=True, null=True)
    is_verify = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.customer_first_name} {self.customer_last_name}"

    class Meta:
        db_table = 'ad_pyot_customer'
        app_label = 'admin_hub'


class PyOtBankAccount(models.Model):
    pyot_bnk_id = models.AutoField(primary_key=True)
    pyot_beneficiary_id = models.CharField(max_length=12)
    pyot_beneficiary_name = models.CharField(max_length=255)
    pyot_bank_name = models.CharField(max_length=255)
    bnk_acc_no = models.BigIntegerField(null=True, blank=True)
    bnk_ifsc = models.TextField(null=True, blank=True)
    pyot_vpa = models.CharField(max_length=50, null=True, blank=True)
    customer_contact = models.JSONField( null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True, db_column='updated_by')
    is_added = models.BooleanField(default=False, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.pyot_bnk_id} ({self.pyot_bank_name})"

    class Meta:
        db_table = 'ad_pyot_bank_account'
        app_label = 'admin_hub'


class PayoutTransaction(models.Model):
    py_trn_id = models.AutoField(primary_key=True)
    py_transfer_id = models.CharField(max_length=12, unique=True)
    pyot_bnk = models.ForeignKey(PyOtBankAccount, on_delete=models.PROTECT, null=True, blank=True)
    py_trn_amount = models.DecimalField(max_digits=19, decimal_places=3, default=0.000)
    py_trn_mode = models.CharField(max_length=15)
    py_trn_status = models.CharField(max_length=20, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True, db_column='updated_by')

    def __str__(self):
        return f"{self.py_trn_id}"

    class Meta:
        db_table = 'ad_payout_transaction'
        app_label = 'admin_hub'

'''
Payout Module End
'''

class UserActivity(models.Model):
    ua_id = models.AutoField(primary_key=True)
    table_id = models.IntegerField()
    table_name = models.CharField(max_length=255)
    ua_action = models.CharField(max_length=255)
    ua_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(PortalUser, on_delete=models.SET_NULL, null=True,db_column='created_by')
    request_data = models.TextField(null=True)
    response_data = models.TextField(null=True)

    def __str__(self):
        return f"{self.ua_action} on {self.table_name} at {self.created_at}"
    
    class Meta:
        db_table = "ad_user_activity"
        app_label = 'admin_hub'

'''
PaysPrint DMT Module Start
'''
class PaysPrintDmtCustomer(models.Model):
    pspdmt_customer_id = models.AutoField(primary_key=True)
    customer_first_name = models.CharField(max_length=255)
    customer_last_name = models.CharField(max_length=255, null=True, blank=True)
    customer_contact_no = models.CharField(max_length=10, unique=True)
    customer_address = models.CharField(max_length=1000, null=True, blank=True)
    customer_zip_code = models.IntegerField(null=True, blank=True)
    customer_aadhaar_no = models.CharField(max_length=12, null=True, blank=True)
    customer_amount_limit = models.IntegerField(null=True, blank=True)
    pspdmt_unique_id = models.CharField(max_length=13, unique=True, null=True, blank=True)
    verify_code = models.CharField(max_length=128, blank=True, null=True)
    verify_code_expire_at = models.DateTimeField(blank=True, null=True)
    is_generated = models.BooleanField(default=False)
    is_aadhar_verified = models.BooleanField(default=False)
    is_registered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.customer_first_name} {self.customer_last_name}"

    class Meta:
        db_table = 'ad_paysprint_dmt_customer'
        app_label = 'admin_hub'


class PaysPrintDmtBankAccount(models.Model):
    pspdmt_bnk_id = models.AutoField(primary_key=True)
    pspdmt_beneficiary_id = models.CharField(max_length=12)
    pspdmt_bene_id = models.CharField(max_length=12, blank=True, null=True)
    pspdmt_beneficiary_name = models.CharField(max_length=255)
    pspdmt_bank_name = models.CharField(max_length=255)
    bnk_acc_no = models.BigIntegerField(null=True, blank=True)
    bnk_ifsc = models.TextField(null=True, blank=True)
    pspdmt_vpa = models.CharField(max_length=50, null=True, blank=True)
    customer_contact = models.JSONField( null=True, blank=True)
    gst_state_code = models.IntegerField(null=True, blank=True)
    dob = models.CharField(max_length=255,null=True, blank=True)
    address = models.CharField(max_length=250,null=True, blank=True)
    pincode = models.CharField(max_length=255,null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True, db_column='updated_by')
    is_added = models.BooleanField(default=False, null=True, blank=True)
    verify_code = models.CharField(max_length=10, null=True, blank=True)
    verify_code_expire_at = models.DateTimeField(blank=True, null=True)
    is_verified_1 = models.BooleanField(default=False)
    is_verified_2 = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.pspdmt_bnk_id} ({self.pspdmt_bank_name})"

    class Meta:
        db_table = 'ad_paysprint_dmt_bank_account'
        app_label = 'admin_hub'


class DMTTransaction(models.Model):
    dmt_trn_id = models.AutoField(primary_key=True)
    dmt_customer_contact_number = models.CharField(max_length=10, null=True, blank=True)
    dmt_customer_name = models.CharField(max_length=255, null=True, blank=True)
    dmt_refrence_id = models.CharField(max_length=50, null=True, blank=True)
    dmt_txn_status = models.CharField(max_length=20, null=True, blank=True, default="PENDING")
    dmt_bene_id = models.ForeignKey(PaysPrintDmtBankAccount, on_delete=models.PROTECT, null=True, blank=True)
    dmt_txn_amount = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    dmt_txntype = models.CharField(max_length=20, null=True, blank=True)
    dmt_resposne = models.JSONField(null=True, blank=True)
    dmt_sp_id = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True, blank=True)
    dmt_service_trn_dt = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'ad_dmt_transaction'
        app_label = 'admin_hub'

class GlobalBankList(models.Model):
    dmt_bnk_lst_id = models.AutoField(primary_key=True)
    bank_id = models.IntegerField(null=True, blank=True)
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    bank_ifsc = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        db_table = 'ad_global_bank_list'
        app_label = 'admin_hub'

'''
PaysPrint DMT Module End
'''

class PgServiceTrn(models.Model):
    pg_service_trn_id = models.AutoField(primary_key=True)
    sp = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True, blank=True)
    pg_trn_unique_id = models.CharField(max_length=255, null=True, blank=True)
    pg_customer_id = models.CharField(max_length=13, null=True, blank=True)
    pg_trn_amount = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    pg_trn_response = models.JSONField(null=True, blank=True)
    pg_aadhaar_response = models.JSONField(null=True, blank=True)
    pg_customer_email = models.CharField(max_length=50, null=True, blank=True)
    pg_customer_name = models.CharField(max_length=50, null=True, blank=True)
    pg_customer_aadhaar_no = models.CharField(max_length=12, null=True, blank=True)
    pg_customer_contact_no = models.CharField(max_length=10, null=True, blank=True)
    pg_contact_verify_code = models.CharField(max_length=128, blank=True, null=True)
    pg_verify_code_expire_at = models.DateTimeField(blank=True, null=True)
    pg_trn_status = models.CharField(max_length=15, null=True, blank=True, default='PENDING')
    pg_service_trn_dt = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.pg_service_trn_id}"

    class Meta:
        db_table = 'ad_pg_service_transaction'
        app_label = 'admin_hub'


class CfPgCustomer(models.Model):
    cf_pg_customer_id = models.AutoField(primary_key=True)
    cf_pg_ekyc_document = models.JSONField(null=True, blank=True)
    cf_pg_customer_contact_no = models.CharField(max_length=10, null=True, blank=True)
    cf_pg_customer_pan_no = models.CharField(max_length=12, null=True, blank=True)
    cf_pg_contact_verify_code = models.CharField(max_length=128, blank=True, null=True)
    cf_pg_verify_code_expire_at = models.DateTimeField(blank=True, null=True)
    cf_pg_is_kyc = models.BooleanField(default=False, null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cf_pg_customer_id}"

    class Meta:
        db_table = 'ad_cashfree_pg_customer'
        app_label = 'admin_hub'

class CfPgServiceTrn(models.Model):
    cf_pg_service_trn_id = models.AutoField(primary_key=True)
    sp = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True, blank=True)
    cf_pg_trn_unique_id = models.CharField(max_length=255, null=True, blank=True)
    customer = models.ForeignKey(CfPgCustomer, on_delete=models.PROTECT, null=True, blank=True)
    cf_pg_trn_amount = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    cf_pg_trn_response = models.JSONField(null=True, blank=True)
    cf_pg_customer_contact_no = models.CharField(max_length=10, null=True, blank=True)
    cf_pg_trn_status = models.CharField(max_length=15, null=True, blank=True, default='PENDING')
    cf_pg_settle_status = models.CharField(max_length=15, null=True, blank=True, default='PENDING')
    cf_pg_service_trn_dt = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.cf_pg_service_trn_id}"

    class Meta:
        db_table = 'ad_cashfree_pg_service_transaction'
        app_label = 'admin_hub'


class AdCfPgConfiged(models.Model):
    ss_id = models.AutoField(primary_key=True)
    card_type = models.CharField(max_length=50, null=True, blank=True)
    card_network = models.CharField(max_length=50, null=True, blank=True)
    card_sub_type = models.CharField(max_length=20, null=True, blank=True)
    payment_method = models.CharField(max_length=20, null=True, blank=True)
    sd_charges = models.JSONField(null=True, blank=True)
    md_charges = models.JSONField(null=True, blank=True)
    dt_charges = models.JSONField(null=True, blank=True)
    rt_charges = models.JSONField(null=True, blank=True)
    to_us_charges = models.JSONField(null=True, blank=True)
    sa_provided = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_cf_pg_configed'
        app_label = 'admin_hub'


class Oprators(models.Model):
    ss_id = models.AutoField(primary_key=True)
    ss_name = models.CharField(max_length=55, null=True, blank=True)
    operator_code = models.CharField(max_length=55, null=True, blank=True)
    operator_type = models.CharField(max_length=55, null=True, blank=True)
    recharge_type = models.CharField(max_length=55, null=True, blank=True)
    sd_charges = models.JSONField(null=True, blank=True)
    md_charges = models.JSONField(null=True, blank=True)
    dt_charges = models.JSONField(null=True, blank=True)
    rt_charges = models.JSONField(null=True, blank=True)
    to_us_charges = models.JSONField(null=True, blank=True)
    sa_provided = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_operators'
        app_label = 'admin_hub'


class MobileRecharge(models.Model):
    mr_id = models.AutoField(primary_key=True)
    mr_optxnid = models.CharField(max_length=55, null=True, blank=True)
    mr_sp =  models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True, blank=True)
    mr_txnno = models.CharField(max_length=55, null=True, blank=True)
    mr_request_txnid = models.CharField(max_length=55, null=True, blank=True)
    mr_mobile_no = models.CharField(max_length=10, null=True, blank=True)
    mr_operator = models.CharField(max_length=55, null=True, blank=True)
    mr_amount = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    mr_circle = models.CharField(max_length=55, null=True, blank=True)
    mr_response = models.JSONField(null=True, blank=True)
    mr_status = models.CharField(max_length=15, null=True, blank=True)
    mr_dt = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    verify_code = models.CharField(max_length=128, blank=True, null=True)
    verify_code_expire_at = models.DateTimeField(blank=True, null=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_mobile_recharge'
        app_label = 'admin_hub'


class BBPSBillerCategory(models.Model):
    ss_id = models.AutoField(primary_key=True)
    ss_name = models.CharField(max_length=50, null=True, blank=True)
    sd_charges = models.JSONField(null=True, blank=True)
    md_charges = models.JSONField(null=True, blank=True)
    dt_charges = models.JSONField(null=True, blank=True)
    rt_charges = models.JSONField(null=True, blank=True)
    to_us_charges = models.JSONField(null=True, blank=True)
    sa_provided = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'bbps_biller_category'
        app_label = 'admin_hub'


class BBPSBiller(models.Model):
    bbps_biller_id = models.AutoField(primary_key=True)
    bbps_blr_id = models.CharField(max_length=50, null=True, blank=True)
    bbps_blr_name = models.CharField(max_length=255, null=True, blank=True)
    bbps_category = models.ForeignKey(BBPSBillerCategory, on_delete=models.PROTECT, null=True, blank=True)
    is_deleted = models.BooleanField(default=False, null=True, blank=True)
    is_deactive = models.BooleanField(default=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'bbps_biller'
        app_label = 'admin_hub'


class BBPSBillResponse(models.Model):
    bbps_id = models.AutoField(primary_key=True)
    bbps_biller_id = models.CharField(max_length=255, null=True, blank=True)
    bbps_biller_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bbps_biller_info'
        app_label = 'admin_hub'


class BBPSBillPayment(models.Model):
    bbps_id = models.AutoField(primary_key=True)
    bbps_blr_id = models.CharField(max_length=255, null=True, blank=True)
    bbps_sp = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True, blank=True)
    bbps_contact_no = models.CharField(max_length=10, null=True, blank=True)
    bbps_request_id = models.CharField(max_length=255, null=True, blank=True)
    bbps_bill_fetch_response = models.JSONField(null=True, blank=True)
    bbps_payment_response = models.JSONField(null=True, blank=True)
    bbps_amount = models.DecimalField(max_digits=19, decimal_places=3, null=True, blank=True, default=0.000)
    bbps_status = models.CharField(max_length=15, null=True, blank=True , default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'ad_bbps_bill_payment'
        app_label = 'admin_hub'


class BBPSComplaint(models.Model):
    complaint_id = models.AutoField(primary_key=True)
    comp_id = models.CharField(max_length=50, null=True, blank=True)
    trn_id = models.CharField(max_length=50, null=True, blank=True)
    complaint_response = models.JSONField(null=True, blank=True)
    tracking_response = models.JSONField(null=True, blank=True)
    complaint_status = models.CharField(max_length=15, null=True, blank=True, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'ad_bbps_complaint'
        app_label = 'admin_hub'


class PhonePeTransaction(models.Model):
    pp_trn_id = models.AutoField(primary_key=True)
    pp_marchant_trn_id = models.CharField(max_length=50, null=True, blank=True)
    pp_amount = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True, default=0.000)
    pp_contact_no = models.CharField(max_length=10, null=True, blank=True)
    pp_pay_response = models.JSONField(null=True, blank=True)
    pp_trn_response = models.JSONField(null=True, blank=True)
    pp_status = models.CharField(max_length=20, null=True, blank=True, default='PENDING')
    sp = models.ForeignKey(AdServiceProvider, on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'ad_phonepe_service_transaction'
        app_label = 'admin_hub'

class PhonePeConfiged(models.Model):
    ss_id = models.AutoField(primary_key=True)
    card_type = models.CharField(max_length=50, null=True, blank=True)
    card_network = models.CharField(max_length=50, null=True, blank=True)
    card_sub_type = models.CharField(max_length=20, null=True, blank=True)
    payment_method = models.CharField(max_length=20, null=True, blank=True)
    sd_charges = models.JSONField(null=True, blank=True)
    md_charges = models.JSONField(null=True, blank=True)
    dt_charges = models.JSONField(null=True, blank=True)
    rt_charges = models.JSONField(null=True, blank=True)
    to_us_charges = models.JSONField(null=True, blank=True)
    sa_provided = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_phonepe_pg_configed'
        app_label = 'admin_hub'


class OtherCharges(models.Model):
    oc_id = models.AutoField(primary_key=True)
    oc_name = models.CharField(max_length=125, null=True, blank=True)
    charge_type = models.CharField(max_length=50, null=True, blank=True)
    charge = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, default=0.000)
    minimum = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True, default=0.000)
    maximum = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True, default=0.000)
    hsn_sac = models.ForeignKey(AdHSNSAC, on_delete=models.PROTECT, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'ad_other_charges'
        app_label = 'admin_hub'


class TopUpTransaction(models.Model):
    tt_id = models.AutoField(primary_key=True)
    tt_amount = models.DecimalField(max_digits=20, decimal_places=3, null=True, blank=True, default=0.000)
    tt_trn_desc = models.CharField(max_length=500, null=True, blank=True)
    tt_trn_status = models.CharField(max_length=100, null=True, blank=True, default='PENDING')
    tt_trn_dt = models.DateTimeField(auto_now_add=True)
    is_settle_with_cash = models.BooleanField(default=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_topup_transaction'
        app_label = 'admin_hub'


class RetailerBankDetails(models.Model):
    rbd_id = models.AutoField(primary_key=True)
    bank_name = models.CharField(max_length=128, blank=True, null=True)
    ifsc_code = models.CharField(max_length=128, blank=True, null=True)
    branch_name = models.CharField(max_length=128, blank=True, null=True)
    account_type = models.CharField(max_length=128, blank=True, null=True)
    account_number = models.CharField(max_length=128, blank=True, null=True)
    rbd_status = models.CharField(max_length=128, null=True, blank=True, default='PENDING')
    is_deactive = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.IntegerField(null=True, blank=True, db_column='updated_by')
   
    def __str__(self) -> str:
        return super().__str__()

    class Meta:
        db_table = 'ad_retailer_bank_detail'
        app_label = 'admin_hub'


class Announcement(models.Model):
    an_id = models.AutoField(primary_key=True)
    an_title = models.CharField(max_length=255, null=True, blank=True)
    an_desc = models.TextField(null=True, blank=True)
    an_link = models.CharField(max_length=255, null=True, blank=True)
    is_deactive = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(PortalUser, on_delete=models.PROTECT, db_column='created_by', null=True, blank=True)
    
    class Meta:
        db_table = 'ad_announcement'
        app_label = 'admin_hub'
