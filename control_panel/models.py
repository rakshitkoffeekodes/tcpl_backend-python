from cProfile import label
from pickle import TRUE
from xml.parsers.expat import model
from django.db import models
from admin_hub.models import *
from web_portal.models import  CustomUser


class ServiceNatureChoice(models.TextChoices):
    charges = 'charges'
    commission = 'commission'


# Create your models here.
class HSNSAC(models.Model):
    """
    Model to store details of various HSNSAC entries.

    Attributes:
    - hsnsac_id (AutoField): Primary key for the HSNSAC entry.
    - hsnsac_code (CharField): Code associated with the HSNSAC entry.
    - tax_rate (DecimalField): Tax rate associated with the HSNSAC entry.
    - description (TextField, nullable): Description of the HSNSAC entry.
    - created_at (DateTimeField): Date and time when the HSNSAC entry was created. Automatically set to the current timestamp.
    - updated_at (DateTimeField, nullable): Date and time when the HSNSAC entry was last updated.
    - created_by (ForeignKey to CustomUser): References the user who created the HSNSAC entry.
    - updated_by (ForeignKey to CustomUser, nullable): References the user who last updated the HSNSAC entry.
    - is_deactive (BooleanField): Flag indicating whether the HSNSAC entry is deactivated (default is False).
    - is_deleted (BooleanField): Flag indicating whether the HSNSAC entry is deleted (default is False).

    Methods:
    - __str__: Returns the hsnsac_code of the HSNSAC entry.

    Meta:
    - db_table: Specifies the database table name as "hsnsac" for storing HSNSAC details.
    """
    hsnsac_id = models.AutoField(primary_key=True)
    hsnsac_code = models.CharField(max_length=255,unique=True)
    tax_rate = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, related_name='hsnsac_created_by', on_delete=models.CASCADE,db_column='created_by')
    updated_by = models.ForeignKey(CustomUser, related_name='hsnsac_updated_by', on_delete=models.CASCADE, null=True, blank=True, db_column='updated_by')
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.hsnsac_code
    

    class Meta:
        db_table = "sa_hsnsac"




class State(models.Model):
    state_id = models.AutoField(primary_key=True)
    state_name = models.CharField(max_length=100,unique=True)
    code = models.CharField(null=True,max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    create_by = models.IntegerField(null=True)
    update_at = models.DateTimeField(null=True)
    update_by = models.IntegerField(null=True)

    def __str__(self):
        return self.state_name
    
    class Meta:
        db_table = 'sa_state'


class City(models.Model):
    city_id = models.AutoField(primary_key=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    city_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    create_by = models.IntegerField(null=True)
    update_at = models.DateTimeField(null=True)
    update_by = models.IntegerField(null=True)

    def __str__(self):
        return self.city_name
    
    class Meta:
        db_table = 'sa_city'
        constraints = [
            models.UniqueConstraint(fields=['city_name', 'state_id'], name='unique_city_name_state_id')
        ]
        
class Admin(models.Model):
    """
    Model to store and manage information about administrators in the system.

    This model includes fields for storing various attributes related to an admin, 
    such as personal details, company information, and verification status. It also 
    manages relationships with other users and tracks creation and modification details.

    Attributes:
    - admin_id (AutoField): Primary key for the admin, automatically incremented.
    - name (CharField): Name of the admin, with a maximum length of 80 characters. Must be unique.
    - contact_no (CharField): Contact number of the admin, limited to 10 characters. Must be unique.
    - email (EmailField): Email address of the admin, with a maximum length of 254 characters. Must be unique.
    - profile_image (ImageField): Profile image of the admin, uploaded to the 'Admin/profile_image/' directory. Optional.
    - pan_card_number (CharField): PAN card number of the admin, with a maximum length of 15 characters. Must be unique.
    - verification_id (CharField): Unique verification ID for the admin, with a maximum length of 12 characters. Optional.
    - is_pan_verify (BooleanField): Indicates whether the PAN card has been verified. Defaults to False.
    - is_gst_verify (BooleanField): Indicates whether the GST number has been verified. Defaults to False.
    - aadhaar_card_number (CharField): Aadhaar card number of the admin, with a maximum length of 12 characters. Must be unique.
    - docs_files (JSONField): JSON field to store related document files. Optional.
    - company_name (CharField): Name of the company the admin is associated with. Optional.
    - gst_number (CharField): GST number of the company, with a maximum length of 15 characters. Must be unique.
    - gst_type (CharField): Type of GST applicable to the company. Choices are defined by `GST_TYPE_CHOICES`. Defaults to 'Composition'.
    - created_at (DateTimeField): Date and time when the admin record was created. Automatically set to the current timestamp.
    - state (CharField): State where the company is located. Optional.
    - city (CharField): City where the company is located. Optional.
    - pincode (CharField): Pincode for the company's location, with a maximum length of 10 characters. Optional.
    - is_deleted (BooleanField): Indicates whether the admin record is marked as deleted. Defaults to False.
    - is_deactive (BooleanField): Indicates whether the admin is currently inactive. Defaults to False.
    - stamp_docs (JSONField): JSON field to store stamp-related documents. Optional.
    - updated_at (DateTimeField): Date and time when the admin record was last updated. Automatically updated on save.
    - created_by (ForeignKey to CustomUser): References the user who created this admin record. Set to null if the user is deleted.
    - updated_by (ForeignKey to CustomUser): References the user who last updated this admin record. Cascades on deletion.

    Methods:
    - __str__: Returns the name of the admin as its string representation.

    Meta:
    - db_table (str): Specifies the database table name as "sa_admin".
    """

    
    COMPOSITION = 'Composition'
    REGULAR = 'Regular'
    UNREGISTER = 'Unregister'
    SEZ = 'SEZ'
    EXPORTS = 'Exports'
    ECOMMERCE = 'Ecommerce'
    PENDING = 'PENDING'
    APROVE = 'APROVE'
    REJECT = 'REJECT'
    
    GST_TYPE_CHOICES = [
        (COMPOSITION, 'Composition'),
        (REGULAR, 'Regular'),
        (UNREGISTER, 'Unregister'),
        (SEZ, 'SEZ'),
        (EXPORTS, 'Exports'),
        (ECOMMERCE, 'Ecommerce'),
    ]

    STATUS = [
        (PENDING, 'PENDING'),
        (APROVE, 'APROVE'),
        (REJECT, 'REJECT')
    ]
    
    admin_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=80,null=True,unique=True)
    contact_no = models.CharField(max_length=10,unique=True)
    email = models.EmailField(max_length=254,null=True,unique=True)
    profile_image = models.ImageField(upload_to='Admin/profile_image/',null=True)
    pan_card_number = models.CharField(max_length=15,null=True,unique=True)
    verification_id = models.CharField(max_length=30, unique=True,null=True)
    is_pan_verify=models.BooleanField(default=False)
    is_gst_verify=models.BooleanField(default=False) 
    aadhaar_card_number = models.CharField(max_length=12,null=True,unique=True)
    docs_files = models.JSONField(null=True)
    company_name = models.CharField(max_length=255,null=True)
    gst_number = models.CharField(max_length=15,null=True,unique=True)
    gst_type = models.CharField(max_length=15, choices=GST_TYPE_CHOICES, default=COMPOSITION)
    admin_status = models.CharField(max_length=255, default=PENDING, choices=STATUS, null=True, blank=True)
    reason = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # state = models.CharField(max_length=255,null=True)
    # city = models.CharField(max_length=255,null=True)
    pincode = models.CharField(max_length=10,null=True)
    is_deleted = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=False) 
    # stamp_docs = models.JSONField(null=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='admins_created',db_column='created_by')
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, related_name='admins',db_column='state')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, related_name='admins',db_column='city')
    admin_pdf = models.FileField(upload_to='admin_pdfs/', null=True, blank=True)
    

    def __str__(self):
        """
        Returns a string representation of the admin.

        Example:
        If the admin's name is 'John Doe', this method would return 'John Doe'.
        """
        return self.name
    
    class Meta:
        db_table = "sa_admin"
        
        
class AdminAgreement(models.Model):
    """
    Model to represent agreements associated with administrators.

    This model is used to store details about agreements, including amounts, 
    documents, and statuses. It also tracks the creation and modification 
    timestamps, and maintains references to related users and administrators.

    Attributes:
    - aa_id (AutoField): Primary key for the agreement, automatically incremented.
    - aa_amount (DecimalField): The amount associated with the agreement, with up to 19 digits and 2 decimal places. Optional.
    - gst_amount (DecimalField): The GST amount applicable to the agreement, with up to 19 digits and 2 decimal places. Optional.
    - agreement_document (FileField): File field to upload and store the agreement document, saved in 'agreement_document/' directory. Optional.
    - aa_status (CharField): Status of the agreement, chosen from predefined status options. Defaults to 'IN PROGRESS'.
    - created_at (DateTimeField): Date and time when the agreement record was created. Automatically set to the current timestamp.
    - updated_at (DateTimeField): Date and time when the agreement record was last updated. Automatically updated on save.
    - created_by (ForeignKey to CustomUser): References the user who created the agreement record. Set to null if the user is deleted.
    - admin_id (ForeignKey to Admin): References the admin associated with the agreement. Cascades on deletion of the related admin.
    - is_deleted (BooleanField): Indicates whether the agreement record is marked as deleted. Defaults to False.

    Methods:
    - __str__: Returns the string representation of the agreement's ID.

    Meta:
    - db_table (str): Specifies the database table name as "sa_admin_agreement".
    """
    AA_STATUS_CHOICES = [
        ('IN PROGRESS','IN PROGRESS'),
        ('SUCCESS','SUCCESS'),
        ('PENDING','PENDING'),
        ('FAILURE','FAILURE'),
        ('EXPIRED','EXPIRED')
    ]
    aa_id = models.AutoField(primary_key=True)
    aa_amount = models.DecimalField(max_digits=19, decimal_places=2,null=True)
    gst_amount = models.DecimalField(max_digits=19, decimal_places=2,null=True)
    agreement_document = models.FileField(upload_to='agreement_document/',null=True) 
    aa_status = models.CharField(max_length=50,choices=AA_STATUS_CHOICES,default="IN PROGRESS")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True,db_column='created_by')
    admin_id = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='admin', null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.aa_id
    
    class Meta:
        db_table = "sa_admin_agreement"
        


        
    
class RequiredDocumentList(models.Model):
    """
    Model to represent a list of required documents.

    This model is used to store details about required documents, including their labels,
    names, and whether they are mandatory. It also tracks who created the record and handles 
    deletion status.

    Attributes:
    - rdl_id (AutoField): Primary key for the required document list item, automatically incremented.
    - label_name (CharField): Label or name used to identify the required document (up to 80 characters).
    - is_required (BooleanField): Indicates if the document is mandatory. Defaults to False.
    - document_name (CharField): The name of the document (up to 80 characters). Must be unique if provided.
    - created_at (DateTimeField): Date and time when the document list item was created. Automatically set to the current timestamp.
    - updated_at (DateTimeField): Date and time when the document list item was last updated. Automatically updated on save.
    - created_by (ForeignKey to CustomUser): References the user who created the document list item. Set to null if the user is deleted.
    - is_deleted (BooleanField): Indicates whether the document list item is marked as deleted. Defaults to False.
    - document_slug (CharField): A slugified version of the document name (up to 100 characters). Must be unique if provided.

    Methods:
    - __str__: Returns the string representation of the document's label name.

    Meta:
    - db_table (str): Specifies the database table name as "sa_required_document_list".
    """
    rdl_id = models.AutoField(primary_key=True)
    label_name = models.CharField(max_length=80)
    is_required = models.BooleanField(default=False)
    document_name = models.CharField(max_length=80, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, db_column='created_by')
    is_deleted = models.BooleanField(default=False)
    document_slug= models.CharField(max_length=100, null=True,unique=True)

    def __str__(self):
        return self.label_name

    class Meta:
        db_table = "sa_required_document_list"
        
        
# class Document(models.Model):
#     document_id = models.AutoField(primary_key=True)
#     type_of_document = models.CharField(max_length=70)
#     is_compulsory = models.IntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True, null=True)
#     created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True,db_column='created_by')
#     dg_id = models.ForeignKey(DocumentGroup, on_delete=models.CASCADE, related_name='document_group')
    
#     def __str__(self):
#         return self.type_of_document

#     class Meta:
#         db_table = "sa_document"


class FeesType(models.Model):
    """
    Model to represent different types of fees.

    This model is used to store various types of fees applicable in the system. It includes information
    about each fee type, such as its name, creation and update timestamps, and the user who created the record.

    Attributes:
    - ft_id (AutoField): Primary key for the fee type, automatically incremented.
    - ft_type (CharField): Name or description of the fee type (up to 90 characters).
    - created_at (DateTimeField): Date and time when the fee type was created. Automatically set to the current timestamp.
    - updated_at (DateTimeField): Date and time when the fee type was last updated. Automatically updated on save.
    - created_by (ForeignKey to CustomUser): References the user who created the fee type. Set to null if the user is deleted.
    - is_deleted (BooleanField): Indicates whether the fee type is marked as deleted. Defaults to False.

    Methods:
    - __str__: Returns the string representation of the fee type's name.

    Meta:
    - db_table (str): Specifies the database table name as "sa_fees_type".
    """
    ft_id = models.AutoField(primary_key=True)
    ft_type = models.CharField(max_length=90)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True,db_column='created_by')
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.ft_type

    class Meta:
        db_table = "sa_fees_type"
        

class SaService(models.Model):
    """
    Model to represent a service offered in the system.

    This model is used to store details about various services, including their name, description, and status.
    It tracks the creation and update timestamps, as well as the user who last updated the record.

    Attributes:
    - service_id (AutoField): Primary key for the service, automatically incremented.
    - service_name (CharField): Name of the service (up to 50 characters).
    - description (TextField): Detailed description of the service. Can be null.
    - created_at (DateTimeField): Date and time when the service was created. Automatically set to the current timestamp.
    - updated_at (DateTimeField): Date and time when the service was last updated. Automatically updated on save.
    - updated_by (ForeignKey to CustomUser): References the user who last updated the service. Set to null if the user is deleted.
    - is_deactive (BooleanField): Indicates whether the service is marked as inactive. Defaults to False.
    - is_deleted (BooleanField): Indicates whether the service is marked as deleted. Defaults to False.

    Methods:
    - __str__: Returns the string representation of the service's name.

    Meta:
    - db_table (str): Specifies the database table name as "sa_service".
    """
    service_id = models.AutoField(primary_key=True)
    service_name = models.CharField(max_length=50)
    description = models.TextField(null=True)
    is_global = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, db_column='updated_by')
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)


    def __str__(self):
        return self.service_name

    class Meta:
        db_table = "sa_service"


class ServiceProvider(models.Model):
    """
    Model to represent and store details of various service providers.

    This model maintains information about service providers associated with specific services. It includes attributes for 
    service provider names, labels, and associated codes, as well as auditing fields to track updates and status.

    Attributes:
    - sp_id (AutoField): Primary key for the ServiceProvider entry. Automatically incremented for each new record.
    - service_id (ForeignKey to SaService): Foreign key linking to the `SaService` model. Represents the service associated with the service provider.
    - sp_name (CharField, nullable): Name of the service provider. This field can be null.
    - label (CharField, nullable): A label or identifier associated with the service provider. This field can be null.
    - hsn_sac (ForeignKey to HSNSAC, nullable): Foreign key linking to the `HSNSAC` model. Represents the HSNSAC code associated with the service provider.
    - updated_at (DateTimeField, nullable): Timestamp indicating the date and time when the service provider entry was last updated. This field can be null.
    - updated_by (ForeignKey to CustomUser, nullable): Foreign key linking to the `CustomUser` model. Represents the user who last updated the service provider entry. This field can be null.
    - is_deactive (BooleanField): Boolean flag indicating whether the service provider entry is marked as deactivated. Defaults to `False`.
    - is_deleted (BooleanField): Boolean flag indicating whether the service provider entry is marked as deleted. Defaults to `False`.

    Methods:
    - __str__: Returns the label of the service provider as a string. Useful for displaying the service provider in the Django admin interface and other parts of the application.

    Meta:
    - db_table (str): Specifies the database table name as "sa_service_provider" for storing service provider details.
    """
    WITH_TDS = 'WITH TDS'
    WITHOUT_TDS = 'WITHOUT TDS'
    
    TDS_TYPE = [
        (WITH_TDS, 'WITH TDS'),
        (WITHOUT_TDS, 'WITHOUT TDS')
    ]

    sp_id = models.AutoField(primary_key=True)
    service_id = models.ForeignKey(SaService, on_delete=models.CASCADE, related_name='service')
    sp_name = models.CharField(max_length=150,null=True)
    parent_id = models.IntegerField(null=True, blank=True)
    label = models.CharField(max_length=255,null=True)
    hsn_sac = models.ForeignKey(HSNSAC, on_delete=models.CASCADE,null=True)
    tds_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tds_type = models.CharField(choices=TDS_TYPE, max_length=255, null=True, blank=True)
    service_nature = models.CharField(max_length=20, choices=ServiceNatureChoice.choices, null=True, blank=True)
    credentials_json = models.JSONField(null=True, blank=True)
    plateform_fee_type = models.CharField(max_length=50, null=True, blank=True)
    plateform_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    required_key = models.JSONField(null=True, blank=True)
    is_table_config  = models.BooleanField(default=False, null=True, blank=True)
    config_table_name  = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, db_column='updated_by')
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.label

    class Meta:
        db_table = "sa_service_provider"


class Charges(models.Model):
    """
    Model to represent and store details of various charges entries related to service providers.

    This model maintains information about charges associated with specific service providers. It includes attributes for 
    different types of charges, their rates, and status flags for auditing purposes.

    Attributes:
    - charges_id (AutoField): Primary key for the Charges entry. Automatically incremented for each new record.
    - service_provider (ForeignKey to ServiceProvider): Foreign key linking to the `ServiceProvider` model. Represents the service provider associated with the charge.
    - charges_type (CharField): Type of the charge. Options include 'Credit' (CR) or 'Debit' (DR).
    - rate_type (CharField): Type of rate applied to the charge. Options include 'Is_Flat' or 'Is_Percent'.
    - minimum (DecimalField, nullable): Minimum charge amount. This field can be null if not applicable.
    - maximum (CharField, nullable): Maximum charge amount. This field can be null if not applicable.
    - rate (DecimalField, nullable, blank=True): Rate applied to the charge. This field can be null or blank if not applicable.
    - charge_category (CharField): Category of the charge. Options include 'To Us' or 'To Provide'. Default is 'To Us'.
    - created_at (DateTimeField): Timestamp indicating when the charge entry was created. Automatically set to the current timestamp.
    - updated_at (DateTimeField, nullable): Timestamp indicating when the charge entry was last updated. This field can be null.
    - updated_by (ForeignKey to CustomUser, nullable): Foreign key linking to the `CustomUser` model. Represents the user who last updated the charge entry. This field can be null.
    - is_deactive (BooleanField): Boolean flag indicating whether the charge entry is marked as deactivated. Default is `False`.
    - is_deleted (BooleanField): Boolean flag indicating whether the charge entry is marked as deleted. Default is `False`.

    Methods:
    - __str__: Returns a string representation of the charge entry, combining the `charges_id` with the label of the associated service provider.

    Meta:
    - db_table (str): Specifies the database table name as "sa_charges" for storing charge details.
    """
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
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    charges_type = models.CharField(max_length=2, choices=CHARGES_TYPE_CHOICES)
    rate_type = models.CharField(max_length=20, choices=CHARGES_RATE_TYPE_CHOICES)
    minimum = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    maximum = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    charge_category = models.CharField(max_length=20, choices=CHARGE_CATEGORY_CHOICES, default='to_us')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, db_column='updated_by')
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.charges_id} ({self.service_provider.label})"
    
    class Meta:
        db_table = 'sa_charges'



class expense(models.Model):
    """
    Model to store details of various expense entries.

    Attributes:
    - expense_id (AutoField): Primary key for the Expense entry.
    - expense_date (DateTimeField): The date and time when the expense was incurred.
    - expense_amount (DecimalField): The amount of the expense. This field has a maximum of 10 digits with 2 decimal places.
    - expense_payment_type (CharField): The method of payment for the expense, chosen from predefined options (Credit Card, Bank Transfer, Cash, Online, Other).
    - expense_transaction_receipt (FileField): An uploaded file associated with the expense transaction. The file is stored under 'expense/transaction_receipt/' directory.
    - expense_type (CharField): Indicates whether the expense is taxed or non-taxed, chosen from predefined options (Taxed, Non-Taxed).
    - expense_tax_rate (DecimalField, nullable): The tax rate applied to the expense, with a maximum of 10 digits and 2 decimal places. This field is optional.
    - expense_tax_amount (DecimalField, nullable): The tax amount associated with the expense, with a maximum of 10 digits and 2 decimal places. This field is optional.
    - firm_name (CharField, nullable): The name of the firm associated with the expense. This field is optional.
    - gst_no (CharField, nullable): The GST number related to the expense. This field is optional.
    - expense_description (TextField): A detailed description of the expense.
    - expense_attachment (JSONField, nullable): A JSON field to store additional attachment information related to the expense. This field is optional.
    - created_at (DateTimeField): The date and time when the expense entry was created. Automatically set to the current timestamp.
    - created_by (ForeignKey to CustomUser): References the user who created the expense entry.
    - updated_at (DateTimeField, nullable): The date and time when the expense entry was last updated. This field is optional.
    - updated_by (ForeignKey to CustomUser, nullable): References the user who last updated the expense entry. This field is optional.
    - is_deleted (BooleanField): A flag indicating whether the expense entry is deleted (default is False).

    Methods:
    - __str__: Returns a string representation of the expense entry in the format of "expense_id (expense_date)".

    Meta:
    - db_table: Specifies the database table name as "expense" for storing Expense details.
    """
    EXPENSE_PAYMENT_TYPE_CHOICES = [
        ('credit card','Credit Card'),
        ('bank transfer','Bank Transfer'),
        ('cash','Cash'),
        ('online','Online'),
        ('other','Other')
    ]
    EXPENSE_TYPE_CHOICES = [
        ('taxed','Taxed'),
        ('non-taxed','Non-Taxed')
    ]
    expense_id = models.AutoField(primary_key=True)
    expense_date = models.DateTimeField()
    expense_amount = models.DecimalField(max_digits=10, decimal_places=2)
    expense_payment_type = models.CharField(max_length=20, choices=EXPENSE_PAYMENT_TYPE_CHOICES)
    expense_transaction_receipt_no = models.CharField(max_length=150,null=True)
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES)
    expense_tax_rate = models.DecimalField(max_digits=10, decimal_places=2,null=True)
    expense_tax_amount = models.DecimalField(max_digits=10, decimal_places=2,null=True)
    firm_name = models.CharField(max_length=150,null=True)
    gst_no = models.CharField(max_length=150,null=True)
    expense_description = models.TextField()
    expense_attachment = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, related_name='expense_created_by',on_delete=models.CASCADE,db_column='created_by')
    updated_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(CustomUser, related_name='expense_updated_by',on_delete=models.CASCADE,null=True, db_column='updated_by')
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.expense_id} ({self.expense_date})"
    
    class Meta:
        db_table = 'sa_expense'


class ProductCategory(models.Model):
    """
    Model to store details of various product categories.

    Attributes:
    - product_category_id (AutoField): Primary key for the ProductCategory entry.
    - category_name (CharField): The name of the product category. This field has a maximum length of 150 characters.
    - category_description (TextField): A detailed description of the product category.
    - created_at (DateTimeField): The date and time when the product category entry was created. Automatically set to the current timestamp.
    - created_by (ForeignKey to CustomUser): References the user who created the product category entry.
    - updated_at (DateTimeField, nullable): The date and time when the product category entry was last updated. This field is optional.
    - updated_by (ForeignKey to CustomUser, nullable): References the user who last updated the product category entry. This field is optional.
    - is_deactive (BooleanField): A flag indicating whether the product category entry is deactivated (default is False).
    - is_deleted (BooleanField): A flag indicating whether the product category entry is deleted (default is False).

    Methods:
    - __str__: Returns the name of the product category.

    Meta:
    - db_table: Specifies the database table name as "product_category" for storing ProductCategory details.
    """
    product_category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=150,unique=True)
    category_description = models.TextField()
    parent_category_id = models.IntegerField( null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, related_name='product_category_created_by',on_delete=models.CASCADE,db_column='created_by')
    updated_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(CustomUser, related_name='product_category_updated_by',on_delete=models.CASCADE,null=True, db_column='updated_by')
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.category_name}"
    
    class Meta:
        db_table = 'sa_product_category'


class AdminService(models.Model):
    """
    Model to manage the association between an Admin and a Service, including details about charges, rates, and service providers.

    This model represents a link between an admin and a specific service, detailing the associated charges, rate, and service provider information.

    Attributes:
    - admin_service_id (AutoField): Primary key for the AdminService entry. Automatically incremented for each new record.
    - admin (ForeignKey to Admin): Foreign key linking to the `Admin` model. Represents the admin associated with the service.
    - service (ForeignKey to SaService): Foreign key linking to the `SaService` model. Represents the service associated with the admin.
    - charges (JSONField, nullable): A JSON field to store various charges related to the service. This field can store complex nested data structures.
    - rate (FloatField): The rate applied to the service. This field is required.
    - service_provider (ForeignKey to ServiceProvider): Foreign key linking to the `ServiceProvider` model. Represents the service provider associated with the service.
    - created_at (DateTimeField): Timestamp indicating when the AdminService entry was created. Automatically set to the current timestamp.
    - updated_at (DateTimeField, nullable): Timestamp indicating when the AdminService entry was last updated. This field can be null.
    - is_deactive (BooleanField): Boolean flag indicating whether the AdminService entry is marked as deactivated. Default is `False`.
    - is_deleted (BooleanField): Boolean flag indicating whether the AdminService entry is marked as deleted. Default is `False`.
    - created_by (ForeignKey to CustomUser, nullable): Foreign key linking to the `CustomUser` model. Represents the user who created the AdminService entry. This field can be null.

    Methods:
    - __str__: Returns a string representation of the AdminService entry, combining the `admin_service_id` with a descriptive label.

    Meta:
    - db_table (str): Specifies the database table name as "sa_admin_service" for storing AdminService details.
    """
    admin_service_id = models.AutoField(primary_key=True)
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='service_admin',null=True, blank=True)
    service = models.ForeignKey(SaService, on_delete=models.CASCADE, related_name='services')
    charges = models.JSONField(null=True)
    rate = models.FloatField()
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='admin_service_providers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_admin_services',db_column='created_by')

    def __str__(self):
        return f"AdminService {self.admin_service_id}"

    class Meta:
        db_table = 'sa_admin_service'



class Product(models.Model):
    """
    Model to store details of various products.

    This model represents a product with its category, brand, model, and additional attributes such as price, quantity, and images.

    Attributes:
    - product_id (AutoField): Primary key for the Product entry. Automatically incremented for each new record.
    - product_category (ForeignKey to ProductCategory): Foreign key linking to the `ProductCategory` model. Represents the category to which the product belongs.
    - brand_name (CharField): Name of the brand of the product.
    - model_name (CharField): Model name of the product.
    - serial_number (CharField, nullable): Serial number of the product. This field can be null if not applicable.
    - date (DateField): Date when the product was created or registered.
    - price (DecimalField): Price of the product. Stored with up to 10 digits and 2 decimal places.
    - quantity (IntegerField): Available quantity of the product in stock.
    - description (TextField, nullable): Description of the product. This field can be null if no description is provided.
    - product_img (JSONField, nullable): JSON field to store URLs or paths to product images. This field allows for multiple images and can be null.
    - created_at (DateTimeField): Timestamp indicating when the Product entry was created. Automatically set to the current timestamp.
    - created_by (ForeignKey to CustomUser): Foreign key linking to the `CustomUser` model. Represents the user who created the Product entry.
    - updated_at (DateTimeField, nullable): Timestamp indicating when the Product entry was last updated. This field can be null.
    - updated_by (ForeignKey to CustomUser, nullable): Foreign key linking to the `CustomUser` model. Represents the user who last updated the Product entry. This field can be null.
    - is_deleted (BooleanField): Boolean flag indicating whether the Product entry is marked as deleted. Default is `False`.
    - is_deactive (BooleanField): Boolean flag indicating whether the Product entry is marked as deactivated. Default is `False`.

    Methods:
    - __str__: Returns a string representation of the Product entry, combining the `brand_name` and `model_name` for easy identification.

    Meta:
    - db_table (str): Specifies the database table name as "sa_product" for storing Product details.
    """
    product_id = models.AutoField(primary_key=True)
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    brand_name = models.CharField(max_length=255)
    model_name = models.CharField(max_length=255)
    serial_number  = models.CharField(max_length=255,null=True)
    date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    description = models.TextField(null=True)
    product_img = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, related_name='product_created_by', on_delete=models.CASCADE, db_column='created_by')
    updated_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(CustomUser, related_name='product_updated_by', on_delete=models.CASCADE, null=True, db_column='updated_by')
    is_deleted = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.brand_name} {self.model_name}"

    class Meta:
        db_table = 'sa_product'


class AdminBankDetails(models.Model):
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
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by', null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.IntegerField(null=True, blank=True, db_column='updated_by')
   
    def __str__(self) -> str:
        return super().__str__()

    class Meta:
        db_table = 'sa_bank_detail'


class AdminFundRequest(models.Model):
    fr_id = models.AutoField(primary_key=True)
    deposite_category = models.JSONField()
    deposite_bank = models.ForeignKey(AdminBankDetails, on_delete=models.PROTECT)
    deposite_amount = models.DecimalField(max_digits=19, decimal_places=2, null=True)
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
    created_by = models.ForeignKey(Admin, on_delete=models.PROTECT, db_column='created_by', null=True, blank=True)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.IntegerField(null=True, db_column='updated_by')

    def __str__(self) -> str:
        return super().__str__()

    class Meta:
        db_table = 'sa_fund_request'

class SaBBPSBillerCategory(models.Model):
    ss_id = models.AutoField(primary_key=True)
    ss_name = models.CharField(max_length=50, null=True, blank=True)
    to_us_charges = models.JSONField(null=True, blank=True)
    to_provide_charges = models.JSONField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, null=True, blank=True)
    is_deactive = models.BooleanField(default=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'sa_bbps_biller_category'


class SaOprators(models.Model):
    ss_id = models.AutoField(primary_key=True)
    ss_name = models.CharField(max_length=55, null=True, blank=True)
    operator_code = models.CharField(max_length=55, null=True, blank=True)
    to_us_charges = models.JSONField(null=True, blank=True)
    to_provide_charges = models.JSONField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, null=True, blank=True)
    is_deactive = models.BooleanField(default=False, null=True, blank=True)
    operator_type = models.CharField(max_length=55, null=True, blank=True)
    recharge_type = models.CharField(max_length=55, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sa_operators'


class SaPgConfiged(models.Model):
    ss_id = models.AutoField(primary_key=True)
    card_type = models.CharField(max_length=50, null=True, blank=True)
    card_network = models.CharField(max_length=50, null=True, blank=True)
    card_sub_type = models.CharField(max_length=20, null=True, blank=True)
    payment_method = models.CharField(max_length=20, null=True, blank=True)
    to_us_charges = models.JSONField(null=True, blank=True)
    to_provide_charges = models.JSONField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, null=True, blank=True)
    is_deactive = models.BooleanField(default=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sa_pg_configed'

class SaPhonePePgConfiged(models.Model):
    ss_id = models.AutoField(primary_key=True)
    card_type = models.CharField(max_length=50, null=True, blank=True)
    card_network = models.CharField(max_length=50, null=True, blank=True)
    card_sub_type = models.CharField(max_length=20, null=True, blank=True)
    payment_method = models.CharField(max_length=20, null=True, blank=True)
    to_us_charges = models.JSONField(null=True, blank=True)
    to_provide_charges = models.JSONField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, null=True, blank=True)
    is_deactive = models.BooleanField(default=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sa_phonepe_pg_configed'


class SaOtherCharges(models.Model):
    oc_id = models.AutoField(primary_key=True)
    oc_name = models.CharField(max_length=125, null=True, blank=True)
    charge_type = models.CharField(max_length=50, null=True, blank=True)
    charge = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    hsn_sac = models.ForeignKey(HSNSAC, on_delete=models.PROTECT, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'sa_other_charges'

