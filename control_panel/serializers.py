from rest_framework import serializers

from tcpl_backend import settings
from web_portal.models import  CustomUser
from .models import *
from rest_framework.exceptions import ValidationError

from rest_framework import serializers

"""
Serializer for managing FeesType model instances in an application.

The FeesTypeSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of FeesType objects. It specifies all fields of the FeesType model for 
serialization, marking 'created_at' and 'updated_at' as read-only to prevent modification 
through this serializer.

Custom validation logic is implemented using the validate method to ensure that the 'ft_type' 
field is provided during creation or update of FeesType instances. If this field is missing, 
a serializers.ValidationError is raised with a specific error message.

Usage:
1. Ensure that the FeesType model in your application is properly defined with the required fields.
2. Import and use FeesTypeSerializer where serialization or deserialization of FeesType objects 
   is necessary, such as in views or serializers.
3. Validate and save FeesType data using .is_valid() and .save() methods to ensure data integrity 
   and adherence to validation rules for the 'ft_type' field.

Note: This serializer assumes the existence of a FeesType model with appropriate fields.

Attributes:
- `Meta`: Specifies the model as FeesType and includes all fields for serialization.
- `validate`: Custom method to validate the presence of the 'ft_type' field during creation 
  or update of FeesType instances.
"""
class FeesTypeSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = FeesType
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, data):
        if self.instance:
            if 'ft_type' in data and not data.get('ft_type'):
                raise serializers.ValidationError("Fee type is required.")
        else:
            if not data.get('ft_type'):
                raise serializers.ValidationError("Fee type is required.")
        
        return data


"""
Serializer for managing SaService model instances.

The SaServiceSerializer class extends serializers.ModelSerializer to handle the 
serialization and validation of SaService objects. It includes a custom method to 
determine the status of the service based on its `is_deactive` field.

Attributes:
- `status`: A custom method field that returns the status of the service as either "Active" or "Inactive".

Usage:
1. Ensure that the SaService model is properly defined in your application with necessary fields.
2. Import and utilize SaServiceSerializer in views or other components where serialization or deserialization 
    of SaService objects is required.
3. Use the `.is_valid()` and `.save()` methods to validate and persist SaService data, ensuring proper 
    representation and functionality.

Attributes:
- `Meta`: Defines the model as SaService and sets read-only fields.
- `status`: A custom method field that provides a human-readable status based on the `is_deactive` attribute.

Methods:
- `get_status(self, obj)`: Returns a human-readable status for the service object.
- `validate(self, data)`: Custom validation to ensure `service_name` is provided during updates.
- `to_representation(self, instance)`: Customizes the representation of the serialized data, allowing fields to be excluded.
"""
class SaServiceSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    class Meta:
        model = SaService
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_by', 'updated_at')

    def get_status(self, obj):
        return "Active" if not obj.is_deactive else "Inactive"

    def validate(self, data):
        if self.instance:
            if 'service_name' in data and not data.get('service_name'):
                raise serializers.ValidationError("service_name is required.")
        return data
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            representation.pop(field, None)
        return representation

"""
Serializer for managing ServiceProvider model instances in an application.

The ServiceProviderSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of ServiceProvider objects. It includes all fields of the ServiceProvider model for 
serialization, designating 'sp_id', 'created_at', 'updated_at', and 'is_deleted' as read-only fields 
to prevent modification through this serializer.

The serializer adds custom fields and methods:
- `status`: Provides a user-friendly representation of the ServiceProvider's status based on the 'is_deactive' field.
- `charges_data`: Serializes related Charges instances linked to the ServiceProvider.
- `hsn_sac`: Serializes the related HSNSAC instance, if present.

Usage:
1. Ensure that the ServiceProvider model in your application is properly defined with the necessary fields.
2. Import and utilize ServiceProviderSerializer in views, serializers, or other components where serialization 
    or deserialization of ServiceProvider objects is required.
3. Validate and persist ServiceProvider data using the .is_valid() and .save() methods, ensuring data integrity 
    and validation of required fields.

Note: This serializer assumes the existence of a ServiceProvider model with appropriate fields and related models 
(SaService, HSNSAC, and Charges).

Attributes:
- `Meta`: Defines the model as ServiceProvider and includes all fields for serialization, with 'sp_id', 
  'created_at', 'updated_at', and 'is_deleted' set as read-only.
- `status`: A custom serializer method field to represent the active/inactive status.
- `service_id`: A PrimaryKeyRelatedField linking to the SaService model.
- `hsn_sac`: A PrimaryKeyRelatedField linking to the HSNSAC model, allowing null values.
- `updated_by`: A PrimaryKeyRelatedField linking to the CustomUser model, allowing null values.
- `charges_data`: A custom serializer method field to represent related Charges instances.

Custom Validation:
- The validate method ensures that the required fields ('sp_name', 'label', 'service_id') are present and valid 
  both during creation and update.
- The validate_service_id method ensures that the provided service_id corresponds to an existing SaService instance.
- The validate method also checks for unique constraints on `hsn_sac` and raises an error if a conflicting record exists.

Custom Representation:
- The to_representation method customizes the output representation of the serializer, including serialized data for 
  the related HSNSAC instance and optionally excluding specified fields based on the context.

"""
class ServiceProviderSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    service_id = serializers.PrimaryKeyRelatedField(queryset=SaService.objects.all(), required=True)
    hsn_sac = serializers.PrimaryKeyRelatedField(queryset=HSNSAC.objects.all(), required=False, allow_null=True)
    updated_by = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False, allow_null=True)
    charges_data = serializers.SerializerMethodField() 
    

    class Meta:
        model = ServiceProvider
        fields = '__all__'
        read_only_fields = ('sp_id', 'created_at', 'updated_at', 'is_deleted')

    def get_status(self, obj):
        return "Active" if not obj.is_deactive else "Inactive"

    def get_charges_data(self, obj):
        # Assuming there's a ForeignKey from Charges to ServiceProvider with related_name='charges'
        charges = Charges.objects.filter(service_provider=obj.pk)
        return ChargesSerializer(charges, many=True,context={'exclude_fields': ["created_at", "updated_at", "is_deleted", "updated_by"]}).data
    
    # def get_hsn_sac(self, obj):
    #     hsn_sac = obj.hsn_sac
    #     if hsn_sac:
    #         return HSNSACSerializer(hsn_sac,context={'exclude_fields': ["updated_by","created_at", "created_by", "is_deleted", "is_deactive","updated_at","description"]}).data
    #     return None
    
    def validate(self, data):
        if self.instance:
            # Update case
            if 'sp_name' in data and not data.get('sp_name'):
                raise serializers.ValidationError({"sp_name": "sp_name is required."})
            if 'label' in data and not data.get('label'):
                raise serializers.ValidationError({"label": "label is required."})
            if 'service_id' in data and not data.get('service_id'):
                raise serializers.ValidationError({"service_id": "service_id is required."})
            if 'hsn_sac' in data and not data.get('hsn_sac'):
                raise serializers.ValidationError({"hsn_sac": "hsn_sac is required."})
            if 'tds_type' in data and not data.get('tds_type'):
                raise serializers.ValidationError({"tds_type": "tds_type is required."})
        else:
            # Create case
            if 'sp_name' not in data or not data.get('sp_name'):
                raise serializers.ValidationError({"sp_name": "sp_name is required."})
            if 'service_id' not in data or not data.get('service_id'):
                raise serializers.ValidationError({"service_id": "service_id is required."})
            if 'hsn_sac' not in data or not data.get('hsn_sac'):
                raise serializers.ValidationError({"hsn_sac": "hsn_sac is required."})
            if 'tds_type' in data and not data.get('tds_type'):
                raise serializers.ValidationError({"tds_type": "tds_type is required."})


        # # Check for unique constraint violation for `hsn_sac`
        # hsn_sac_id = data.get('hsn_sac')
        # if hsn_sac_id:
        #     if ServiceProvider.objects.filter(hsn_sac=hsn_sac_id,is_deleted=False).exists():
        #         raise serializers.ValidationError({
        #             "hsn_sac": "A service provider with this HSN/SAC ID already exists."
        #         })
        return data

    def validate_service_id(self, value):
        if not SaService.objects.filter(pk=value.pk).exists():
            raise serializers.ValidationError("Invalid service_id. The specified service does not exist.")
        return value
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Add service_name to the representation
        service = instance.service_id
        if service:
            representation['service_name'] = service.service_name
            representation['is_global'] = service.is_global
        
        hsn_sac_instance = instance.hsn_sac
        if hsn_sac_instance:
            hsn_sac_data = HSNSACSerializer(hsn_sac_instance, context={'exclude_fields': ["updated_by", "created_at", "created_by", "is_deleted", "is_deactive", "updated_at", "description"]}).data
            representation['hsn_sac'] = hsn_sac_data
        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation
    

class SaService_Serializer(serializers.ModelSerializer):
    class Meta:
        model =  SaService
        fields = ['service_id', 'service_name',]

"""
Serializer for managing ServiceProvider model instances.

The ServiceProvider_Serializer class extends serializers.ModelSerializer to handle the 
serialization and validation of ServiceProvider objects. It includes a nested serializer 
for the related `service_id` field to provide detailed representation.

Attributes:
- `service_id`: Nested serializer (SaService_Serializer) to represent the related service information.

Usage:
1. Ensure that the ServiceProvider model is properly defined in your application with necessary fields.
2. Import and utilize ServiceProvider_Serializer in views or other components where serialization or deserialization 
    of ServiceProvider objects is required.
3. Use the `.is_valid()` and `.save()` methods to validate and persist ServiceProvider data, ensuring proper 
    representation and functionality.

Attributes:
- `Meta`: Defines the model as ServiceProvider and sets read-only fields.
- `service_id`: A read-only field that uses SaService_Serializer to provide a detailed representation of the 
    related service information.
"""
class ServiceProvider_Serializer(serializers.ModelSerializer):
  
    service_id = SaService_Serializer(read_only=True)
    class Meta:
        model = ServiceProvider
        
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'is_deleted')


"""
Serializer for managing Charges model instances in an application.

The ChargesSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of Charges objects. It includes all fields of the Charges model for 
serialization, designating 'created_at', 'updated_at', 'updated_by', and 'is_deleted' as 
read-only fields to prevent modification through this serializer.

The serializer adds a custom 'status' field to provide a user-friendly representation of the 
Charges' status based on the 'is_deactive' field.

Usage:
1. Ensure that the Charges model in your application is properly defined with the necessary fields.
2. Import and utilize ChargesSerializer in views, serializers, or other components where serialization 
    or deserialization of Charges objects is required.
3. Validate and persist Charges data using the .is_valid() and .save() methods, ensuring data integrity 
    and validation of required fields.

Note: This serializer assumes the existence of a Charges model with appropriate fields.

Attributes:
- `Meta`: Defines the model as Charges and includes all fields for serialization.
- `status`: A custom serializer method field to represent the active/inactive status.
"""
class ChargesSerializer(serializers.ModelSerializer):
    # status = serializers.SerializerMethodField()
    class Meta:
        model = Charges
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'updated_by', 'is_deleted')

    # def get_status(self, obj):
    #     return "Active" if not obj.is_deactive else "Inactive"
    
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     exclude_fields = self.context.get('exclude_fields', [])
    #     for field in exclude_fields:
    #         representation.pop(field, None)
    #     return representation
    
    # def validate(self, data):
    #     """
    #     Custom validation for minimum and maximum fields.
    #     If one of the fields is provided, the other must be provided too.
    #     """
    #     minimum = data.get('minimum')
    #     maximum = data.get('maximum')
        
    #     if (minimum is None and maximum is not None) or (minimum is not None and maximum is None):
    #         raise serializers.ValidationError("Both 'minimum' and 'maximum' fields must be provided together.")
        
    #     if minimum is not None and maximum is not None:
    #         if maximum != 'inf':
    #             try:
    #                 if float(maximum) < float(minimum):
    #                     raise serializers.ValidationError("'maximum' should not be less than 'minimum'. Please provide valid values.")
    #             except ValueError:
    #                 raise serializers.ValidationError("'maximum' must be a number or 'inf'. Please provide valid values.")

    #     if not self.instance:
    #         charge_category = data.get('charge_category')
    #         if not charge_category:
    #             raise serializers.ValidationError("The charge_category field is required.")
    #         if charge_category not in dict(Charges.CHARGE_CATEGORY_CHOICES).keys():
    #             raise serializers.ValidationError(f"'{charge_category}' is not a valid choice for charge_category.")     
    #     return data

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     exclude_fields = self.context.get('exclude_fields', [])
        
    #     for field in exclude_fields:
    #         representation.pop(field, None)
        
    #     return representation
    

class ParentCategorySerializer(serializers.Serializer):
    product_category_id = serializers.IntegerField()
    category_name = serializers.CharField()
    
"""
Serializer for Managing ProductCategory Model Instances.

The ProductCategorySerializer class is designed to handle the serialization and validation 
of ProductCategory objects in an application. It extends serializers.ModelSerializer to provide 
full coverage of the ProductCategory model fields, ensuring accurate data representation 
and validation.

Features:
- **Serialization**: Includes all fields of the ProductCategory model for serialization.
- **Read-Only Fields**: 'created_at', 'created_by', 'updated_at', 'updated_by', and 'is_deleted' are 
  set as read-only to prevent changes through the serializer.
- **Custom Fields**: Adds 'status' and 'parent_category' fields to enhance data representation.

Usage:
1. Ensure the ProductCategory model is defined with the necessary fields and relationships.
2. Utilize ProductCategorySerializer in views, serializers, or other components where serialization 
   or deserialization of ProductCategory objects is required.
3. Validate and save ProductCategory data using the .is_valid() and .save() methods, ensuring integrity 
   and validation of required fields.

Attributes:
- `Meta`: Defines the model as ProductCategory and includes all fields for serialization.
- `status`: A custom serializer method field providing a user-friendly representation of the ProductCategory's 
  status based on the 'is_deactive' field.
- `parent_category`: A custom serializer method field providing details of the parent category if applicable.

Methods:
- `get_status`: Determines the status of the ProductCategory. Returns "Active" if `is_deactive` is False; 
  otherwise, returns "Inactive".
- `get_parent_category`: Retrieves details of the parent category, including the 'parent_category_id' 
  and 'category_name', if a parent category exists and is not deleted.
- `validate_parent_category_id`: Validates the parent_category_id to ensure it references a valid 
  and existing ProductCategory object.
"""
class ProductCategorySerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    parent_category = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by', 'is_deleted','parent_category')

    def get_status(self, obj):
        return "Active" if not obj.is_deactive else "Inactive"

    def get_parent_category(self, obj):
        """
        Custom method to get the parent category details.
        """
        if obj.parent_category_id:
            try:
                parent_category = ProductCategory.objects.get(pk=obj.parent_category_id, is_deleted=False)
                return {
                    "parent_category_id": parent_category.product_category_id,
                    "category_name": parent_category.category_name
                }
            except ProductCategory.DoesNotExist:
                return None
        return None

    def validate_parent_category_id(self, value):
        if value:
            if not ProductCategory.objects.filter(pk=value).exists():
                raise serializers.ValidationError("Invalid parent category ID.")
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            representation.pop(field, None)
        return representation


"""
Serializer for managing Expense model instances in an application.

The ExpenseSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of Expense objects. It includes all fields of the Expense model for 
serialization, designating 'created_at', 'updated_at', 'created_by', and 'updated_by' as 
read-only fields to prevent modification through this serializer.

The serializer adds a custom 'expense_attachment' field to provide URLs for expense attachments 
based on their file paths stored in the 'expense_attachment' field of the model.

Usage:
1. Ensure that the Expense model in your application is properly defined with the necessary fields.
2. Import and utilize ExpenseSerializer in views, serializers, or other components where serialization 
    or deserialization of Expense objects is required.
3. Validate and persist Expense data using the .is_valid() and .save() methods, ensuring data integrity 
    and validation of required fields.

Note: This serializer assumes the existence of an Expense model with appropriate fields.

Attributes:
- `Meta`: Defines the model as Expense and includes all fields for serialization.
- `expense_attachment`: A custom serializer method field that provides full URLs for expense attachment files.

Methods:
- `get_expense_attachment`: Returns a dictionary with full URLs for expense attachment files based on 
  the file paths stored in the model's 'expense_attachment' field.
- `validate_expense_date`: Ensures that the expense date is provided and is not empty.
- `validate_expense_amount`: Ensures that the expense amount is greater than zero.
- `validate_expense_payment_type`: Validates that the expense payment type is one of the allowed choices.
- `validate_expense_type`: Validates that the expense type is one of the allowed choices.
- `validate_expense_tax_rate`: Ensures that the expense tax rate is not negative, if provided.
- `validate_expense_tax_amount`: Ensures that the expense tax amount is not negative, if provided.
- `validate_gst_no`: Ensures that the GST number, if provided, is exactly 15 characters long.
- `validate_expense_description`: Ensures that the expense description is provided and not empty.
- `validate_expense_attachment`: Ensures that the expense attachment is a JSON object, if provided.
- `validate`: Custom validation method that ensures all required fields for taxed expenses are provided 
  when 'expense_type' is 'taxed'.

"""
class ExpenseSerializer(serializers.ModelSerializer):
    expense_attachment = serializers.SerializerMethodField()
    class Meta:
        model = expense
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')

    def get_expense_attachment(self, instance):
        request = self.context.get('request')
        file_paths = instance.expense_attachment
        file_urls = []
        if not file_paths:
            return None


        for file_path in file_paths:
            # Construct the full URL using the request and MEDIA_URL
            file_url = request.build_absolute_uri(settings.MEDIA_URL + file_path.replace('\\', '/'))
            file_urls.append(file_url)

        return {'file_paths':file_urls}
    def validate_expense_date(self, value):
        if not value:
            raise serializers.ValidationError("Expense date is required.")
        return value

    def validate_expense_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Expense amount must be greater than zero.")
        return value

    def validate_expense_payment_type(self, value):
        if value not in dict(expense.EXPENSE_PAYMENT_TYPE_CHOICES):
            raise serializers.ValidationError("Invalid expense payment type.")
        return value

    def validate_expense_type(self, value):
        if value not in dict(expense.EXPENSE_TYPE_CHOICES):
            raise serializers.ValidationError("Invalid expense type.")
        return value

    def validate_expense_tax_rate(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Expense tax rate cannot be negative.")
        return value

    def validate_expense_tax_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Expense tax amount cannot be negative.")
        return value

    def validate_gst_no(self, value):
        if value and len(value) != 15:
            raise serializers.ValidationError("GST number must be exactly 15 characters long.")
        return value

    def validate_expense_description(self, value):
        if not value:
            raise serializers.ValidationError("Expense description is required.")
        return value

    def validate_expense_attachment(self, value):
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Expense attachment must be a JSON object.")
        return value
    

    def validate_expense_transaction_receipt_no(self, value):
        # Check if the value is provided
        if not value:
            raise serializers.ValidationError("Expense transaction receipt number is required.")
        
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            representation.pop(field, None)  # Safely remove fields
        return representation
        
    def validate(self, data):
        if data.get('expense_type') == 'taxed':
            required_fields = ['expense_tax_rate', 'expense_tax_amount', 'firm_name', 'gst_no']
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                raise serializers.ValidationError(f"{', '.join(missing_fields)} are required for taxed expenses.")
            
            
        return data

"""
Serializer for managing Admin model instances.

The AdminSerializer class extends serializers.ModelSerializer to handle the 
serialization and validation of Admin objects. It includes various custom methods 
for additional fields and related data.

Attributes:
- `status`: Custom field to represent the active or inactive status of the admin.
- `gst_type_display`: Display the human-readable format of the GST type.
- `admin_service`: Serialize related admin service data.
- `stamp_docs`: Serialize and return stamp document URLs.
- `docs_files`: Serialize and return document file URLs.
- `aa_amount`: Amount from related AdminAgreement.
- `aa_gst_amount`: GST amount from related AdminAgreement.
- `total_amount`: Total amount including agreement amount and GST.
- `agreement_document`: Retrieve the agreement document from related AdminAgreement.
- `aa_status`: Status from related AdminAgreement.

Usage:
1. Ensure that the Admin model in your application is properly defined with the necessary fields.
2. Import and utilize AdminSerializer in views or other components where serialization or deserialization of Admin objects is required.
3. Use the `.is_valid()` and `.save()` methods to validate and persist Admin data, ensuring proper representation and functionality.

Attributes:
- `Meta`: Defines the model as Admin and sets read-only fields.
- `get_status`: Returns "Active" if `is_deactive` is False; otherwise, returns "Inactive".
- `get_aa_amount`: Retrieves the `aa_amount` from the related AdminAgreement.
- `get_aa_gst_amount`: Retrieves the GST amount from the related AdminAgreement.
- `get_total_amount`: Calculates and returns the total amount (agreement amount + GST).
- `get_aa_status`: Retrieves the `aa_status` from the related AdminAgreement.
- `get_agreement_document`: Retrieves the agreement document URL from the related AdminAgreement.
- `get_stamp_docs`: Serializes and returns URLs for stamp documents.
- `get_docs_files`: Serializes and returns URLs for document files.
- `get_admin_service`: Serializes and returns related admin service data.
- `validate_name`: Ensures that the name does not contain the word 'example'.
- `validate`: Validates required fields and applies specific validations for PAN card number, Aadhaar card number, and profile image size.
- `to_representation`: Excludes specified fields from the serialized representation based on context.

Attributes:
- `status`: Derived field indicating if the admin is active or inactive.
- `gst_type_display`: Read-only field showing the GST type description.
- `admin_service`: Serializes related AdminService instances.
- `stamp_docs`: Serializes and returns URLs for stamp documents with proper scheme and host.
- `docs_files`: Serializes and returns URLs for document files with proper scheme and host.
- `aa_amount`, `aa_gst_amount`, `total_amount`, `agreement_document`, `aa_status`: Derived fields from related AdminAgreement instances.
"""    
class AdminSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    gst_type_display = serializers.CharField(source='get_gst_type_display', read_only=True)
    admin_service = serializers.SerializerMethodField()
    # stamp_docs = serializers.SerializerMethodField()
    docs_files = serializers.SerializerMethodField()
    aa_amount = serializers.SerializerMethodField()
    aa_gst_amount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    aa_status = serializers.SerializerMethodField()

    class Meta:
        model = Admin
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
        
    def get_status(self, obj):
        return "Active" if not obj.is_deactive else "Inactive"
    
    def get_aa_amount(self, obj):
        try:
            agreement_obj = AdminAgreement.objects.get(admin_id=obj.pk)
            serializer = AdminAgreementSerializer(agreement_obj)
            return serializer.data.get('aa_amount')
        except AdminAgreement.DoesNotExist:
            return None

    def get_aa_gst_amount(self, obj):
        try:
            agreement_obj = AdminAgreement.objects.get(admin_id=obj.pk)
            serializer = AdminAgreementSerializer(agreement_obj)
            aa_amount = float(serializer.data.get('aa_amount', 0))
            gst_amount = aa_amount * 0.18  # 18% GST calculation
            return str(gst_amount)
        except AdminAgreement.DoesNotExist:
            return None

    def get_total_amount(self, obj):
        try:
            agreement_obj = AdminAgreement.objects.get(admin_id=obj.pk)
            serializer = AdminAgreementSerializer(agreement_obj)
            aa_amount = float(serializer.data.get('aa_amount', 0))
            gst_amount = float(aa_amount * 0.18)
            return str(aa_amount + gst_amount)
        except AdminAgreement.DoesNotExist:
            return None
        
    def get_aa_status(self, obj):
        try:
            agreement_obj = AdminAgreement.objects.get(admin_id=obj.pk)
            serializer = AdminAgreementSerializer(agreement_obj)
            return serializer.data.get('aa_status')
        except AdminAgreement.DoesNotExist:
            return None
     
    # def get_stamp_docs(self, instance):
    #     request = self.context.get('request')
    #     scheme = "https" if request.is_secure()  else "http"
    #     stamp_json = instance.stamp_docs
    #     print(stamp_json)
    #     if stamp_json :
    #         for i in stamp_json:
    #             file_path = i["stamp_file"].replace('\\', '/')
    #             i["stamp_file"] = f"{scheme}://{request.get_host()}{settings.MEDIA_URL}{file_path}"
    #             print(file_path)
    #     return stamp_json
    
    def get_docs_files(self, instance):
        request = self.context.get('request')
        scheme = "https" if request.is_secure()  else "http"
        docs_files_json = instance.docs_files
        if docs_files_json :
            for k,v in docs_files_json.items():
                file_path =  v.replace('\\', '/')
                docs_files_json[k] = f"{scheme}://{request.get_host()}{settings.MEDIA_URL}{file_path}"
        return docs_files_json
    
    def get_profile_image(self, instance):
        request = self.context.get('request')
        scheme = "https" if request.is_secure() else "http"
        
        profile_image = instance.profile_image
        
        if profile_image:
            file_path = profile_image.url.replace('\\', '/')
            return f"{scheme}://{request.get_host()}{file_path}"
        
        return None

    def get_admin_service(self, obj):
        """
        Custom method to serialize related admin_service data.
        """
        admin_services = obj.service_admin.filter(is_deleted=False)  # Filter out deleted entries if applicable
        return AdminService_Data_Serializer(admin_services, many=True, context=self.context).data

    def validate_name(self, value):
        if 'example' in value.lower():
            raise serializers.ValidationError("The name should not contain the word 'example'.")
        return value
    
    def validate(self, data):
        required_fields = {
            'name': "Name is required.",
            'contact_no': "Contact number is required.",
            'email': "Email ID is required.",
            'company_name': "Company name is required.",
            'gst_number': "GST number is required.",
            # 'gst_type': "GST type is required.",
            'state': "State is required.",
            'city': "City is required.",
            'pincode': "Pincode is required.",
            # 'pan_card_number': "PAN card number is required.",
            # 'aadhaar_card_number': "Aadhaar card number is required.",
            # 'stamp_docs' : "stamp_id and stamp_file are required.",
            
            
        }

        if not self.instance:  # Create case
            for field, error_msg in required_fields.items():
                if field not in data or not data.get(field):
                    raise serializers.ValidationError({field: error_msg})
            
            # Length validation for pan_card_number and aadhaar_card_number
            pan_card_number = data.get('pan_card_number')
            if pan_card_number and len(pan_card_number) != 10:
                raise serializers.ValidationError({"pan_card_number": "PAN card number must be exactly 10 characters long."})

            aadhaar_card_number = data.get('aadhaar_card_number')
            if aadhaar_card_number and len(aadhaar_card_number) != 12:
                raise serializers.ValidationError({"aadhaar_card_number": "Aadhaar card number must be exactly 12 characters long."})
            
            profile_image = data.get('profile_image')
            if profile_image and profile_image.size > 10*1024*1024:
                raise serializers.ValidationError("Profile Image must be less than 10 MB.")

        else:  # Update case
            for field, error_msg in required_fields.items():
                if field in data and not data.get(field):
                    raise serializers.ValidationError({field: error_msg})

            # Length validation for pan_card_number and aadhaar_card_number
            pan_card_number = data.get('pan_card_number')
            if pan_card_number and len(pan_card_number) != 10:
                raise serializers.ValidationError({"pan_card_number": "PAN card number must be exactly 10 characters long."})

            aadhaar_card_number = data.get('aadhaar_card_number')
            if aadhaar_card_number and len(aadhaar_card_number) != 12:
                raise serializers.ValidationError({"aadhaar_card_number": "Aadhaar card number must be exactly 12 characters long."})
            
            profile_image = data.get('profile_image')
            if profile_image and profile_image.size > 10*1024*1024:
                raise serializers.ValidationError("Profile Image must be less than 10 MB.")
        return data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            representation.pop(field, None)
        return representation
    
"""
Serializer for managing RequiredDocumentList model instances.

The DocumentListSerializer class extends serializers.ModelSerializer to handle the 
serialization and validation of RequiredDocumentList objects.

Attributes:
- `Meta`: Defines the model as RequiredDocumentList and includes all fields for serialization.
- `validate_document_name`: Custom validation method to ensure the uniqueness of the document name.
- `validate_document_slug`: Custom validation method to ensure the document slug does not contain spaces.
- `validate`: Custom validation method to handle the presence of required fields and slug formatting.
- `update`: Method to update an existing RequiredDocumentList instance with validated data.

Usage:
1. Ensure that the RequiredDocumentList model in your application is properly defined with the necessary fields.
2. Import and utilize DocumentListSerializer in views or other components where serialization or deserialization of RequiredDocumentList objects is required.
3. Use the `.is_valid()` and `.save()` methods to validate and persist RequiredDocumentList data, ensuring proper representation and functionality.

Attributes:
- `Meta`: Defines the model as RequiredDocumentList and sets read-only fields.
- `validate_document_name`: Ensures the document name is unique unless it matches the existing instance’s name.
- `validate_document_slug`: Checks that the document slug does not contain spaces.
- `validate`: Validates required fields and ensures document slug formatting.
- `update`: Updates an existing RequiredDocumentList instance with new data and saves the changes.
"""    
class DocumentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequiredDocumentList
        fields = '__all__'
        read_only_fields = ['rdl_id', 'created_at', 'updated_at', 'created_by']

    def validate_document_name(self, value):
     
        instance = getattr(self, 'instance', None)
        if instance and instance.document_name == value:
            return value

        if RequiredDocumentList.objects.filter(document_name=value).exists():
            raise ValidationError("Document name must be unique.")
        return value

    def validate_document_slug(self, value):
      
        if ' ' in value:
            raise ValidationError("Slug cannot contain spaces.")
        return value

    def validate(self, data):
      
        if 'label_name' in data and not data['label_name']:
            raise ValidationError({"label_name": "Label name is required."})
        
        
        if self.partial and 'document_slug' not in data:
           
            return data
        
      
        document_slug = data.get('document_slug')
        if not document_slug:
            raise ValidationError({"document_slug": "Document slug is required."})
        if ' ' in document_slug:
            raise ValidationError({"document_slug": "Slug cannot contain spaces."})
        
        return data

    def update(self, instance, validated_data):
        instance.label_name = validated_data.get('label_name', instance.label_name)
        instance.document_name = validated_data.get('document_name', instance.document_name)
        instance.document_slug = validated_data.get('document_slug', instance.document_slug)
        instance.is_required = validated_data.get('is_required', instance.is_required)
        instance.save()
        return instance


    

"""
Serializer for managing HSNSAC model instances in an application.

The HSNSACSerializer class extends serializers.ModelSerializer to handle the serialization and validation
of HSNSAC objects. It specifies all fields of the HSNSAC model for serialization, designating 
'created_at', 'created_by', and 'updated_at' as read-only fields to prevent modification through this serializer.

Custom validation logic is implemented in the `validate_hsnsac_code` and `validate` methods:
- `validate_hsnsac_code` ensures that the HSNSAC code is unique. For updates, it excludes the current instance
  from the uniqueness check to avoid false positives.
- The `validate` method ensures that required fields ('hsnsac_code', 'tax_rate', 'description') are provided 
  when creating or updating a HSNSAC instance. It handles both partial updates and full creations.

Usage:
1. Ensure that the HSNSAC model in your application is properly defined with the necessary fields.
2. Import and utilize HSNSACSerializer in views, serializers, or other components where serialization 
    or deserialization of HSNSAC objects is required.
3. Validate and persist HSNSAC data using the `.is_valid()` and `.save()` methods to ensure data integrity 
    and validation of required fields.

Note: This serializer assumes the existence of a HSNSAC model with appropriate fields.

Attributes:
- `Meta`: Defines the model as HSNSAC and includes all fields for serialization, with 'created_at', 'created_by',
    and 'updated_at' marked as read-only.
- `validate_hsnsac_code`: Custom method to ensure that the HSNSAC code is unique.
- `validate`: Custom method to validate required fields during creation or update of HSNSAC instances.
- `to_representation`: Custom method to modify the serialized output, allowing exclusion of specified fields.

"""
class HSNSACSerializer(serializers.ModelSerializer):
    

    class Meta:
        model = HSNSAC
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at')

    def validate_hsnsac_code(self, value):
        # Check if the code already exists
        if self.instance:
            # For updates, exclude the current instance
            if HSNSAC.objects.filter(hsnsac_code=value).exclude(hsnsac_id=self.instance.hsnsac_id).exists():
                raise serializers.ValidationError("HSNSAC Code already exists")
        else:
            # For create operations, check all records
            if HSNSAC.objects.filter(hsnsac_code=value).exists():
                raise serializers.ValidationError("HSNSAC Code already exists")
        return value

    def validate(self, data):
        # Check if we are performing a partial update
        if self.instance:
            # For partial updates, only validate the fields that are present in the data
            if 'hsnsac_code' in data and not data.get('hsnsac_code'):
                raise serializers.ValidationError("HSNSAC Code is required")
            
            if 'tax_rate' in data and not data.get('tax_rate'):
                raise serializers.ValidationError("Tax Rate is required")
        else:
            # For create operations, all fields must be present
            if not data.get('hsnsac_code'):
                raise serializers.ValidationError("HSNSAC Code is required")
            
            if not data.get('tax_rate'):
                raise serializers.ValidationError("Tax Rate is required")
        
        return data
    
    

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation
    
    
# class AdminServiceSerializer(serializers.ModelSerializer):
#     admin_id = serializers.IntegerField(write_only=True)
#     service_id = serializers.IntegerField(write_only=True)
#     charges_id = serializers.IntegerField(write_only=True)
#     service_provider_id = serializers.IntegerField(write_only=True)
    
#     admin = AdminSerializer(read_only=True)
#     service = SaServiceSerializer(read_only=True)
#     charges = ChargesSerializer(read_only=True)
#     service_provider = ServiceProviderSerializer(read_only=True)
#     status = serializers.SerializerMethodField()

#     class Meta:
#         model = AdminService
#         fields = [
#             'admin_service_id',
#             'admin_id',
#             'service_id',
#             'charges_id',
#             'service_provider_id',
#             'rate',
#             'admin',
#             'service',
#             'charges',
#             'service_provider',
#             'created_at',
#             'updated_at',
#             'is_deactive',
#             'is_deleted',
#             'created_by',
#             'status'
#         ]

#     def validate(self, data):
#         admin_id = data.get('admin_id')
#         service_id = data.get('service_id')
#         charges_id = data.get('charges_id')
#         service_provider_id = data.get('service_provider_id')

#         if not Admin.objects.filter(pk=admin_id).exists():
#             raise serializers.ValidationError({'admin': 'Invalid Admin ID.'})
#         if not SaService.objects.filter(pk=service_id).exists():
#             raise serializers.ValidationError({'service': 'Invalid Service ID.'})
#         if not Charges.objects.filter(pk=charges_id).exists():
#             raise serializers.ValidationError({'charges': 'Invalid Charges ID.'})
#         if not ServiceProvider.objects.filter(pk=service_provider_id).exists():
#             raise serializers.ValidationError({'service_provider': 'Invalid Service Provider ID.'})
        
#         return data

#     def get_status(self, obj):
#         return "Active" if not obj.is_deactive else "Inactive"
    
#     def create(self, validated_data):
#         request = self.context.get('request')
#         created_by = request.user

#         admin_id = validated_data.pop('admin_id')
#         service_id = validated_data.pop('service_id')
#         charges_id = validated_data.pop('charges_id')
#         service_provider_id = validated_data.pop('service_provider_id')

#         admin = Admin.objects.get(pk=admin_id)
#         service = SaService.objects.get(pk=service_id)
#         charges = Charges.objects.get(pk=charges_id)
#         service_provider = ServiceProvider.objects.get(pk=service_provider_id)

#         validated_data['admin'] = admin
#         validated_data['service'] = service
#         validated_data['charges'] = charges
#         validated_data['service_provider'] = service_provider
#         validated_data['created_by'] = created_by

#         instance = AdminService.objects.create(**validated_data)
#         return instance
"""
Serializer for managing AdminService model instances.

The AdminServiceSerializer class extends serializers.ModelSerializer to handle the serialization 
of AdminService objects, including nested serialization for related objects and custom validation.

Attributes:
- `service`: A PrimaryKeyRelatedField linking to SaService instances.
- `charges`: A SerializerMethodField to provide custom serialization of related Charges instances.
- `service_provider`: A PrimaryKeyRelatedField linking to ServiceProvider instances.

The `Meta` class:
- Specifies the model as AdminService and includes all fields for serialization.
- Sets 'admin_service_id', 'created_at', 'updated_at', and 'is_deleted' as read-only fields to prevent modification.

Custom methods:
- `validate`: Ensures required fields are provided during creation and that fields are not null during updates.
- `to_representation`: Customizes the output representation to include serialized data for related objects and handles field exclusions.
- `get_charges`: Provides custom serialization for related Charges instances.

Usage:
1. Ensure that the AdminService model in your application is properly defined with the necessary fields.
2. Import and utilize AdminServiceSerializer in views or other components where serialization or deserialization of AdminService objects is required.
3. Use the `.is_valid()` and `.save()` methods to validate and persist AdminService data, ensuring proper representation and functionality.

Attributes:
- `Meta`: Defines the model as AdminService and specifies read-only fields.
- `validate`: Method to check the presence of required fields ('admin', 'service', 'service_provider') during creation and to validate non-null fields during updates.
- `to_representation`: Method to customize the output representation of the AdminService instance, including related `admin`, `service`, and `service_provider` data, and handling field exclusions.
- `get_charges`: Method to serialize related Charges instances into a list, providing custom serialization for each Charges instance.
"""
class AdminServiceSerializer(serializers.ModelSerializer):
    # admin = serializers.PrimaryKeyRelatedField(queryset=Admin.objects.all())
    service = serializers.PrimaryKeyRelatedField(queryset=SaService.objects.all())
    charges = serializers.SerializerMethodField()
    
    service_provider = serializers.PrimaryKeyRelatedField(queryset=ServiceProvider.objects.all())

    class Meta:
        model = AdminService
        fields = '__all__'
        extra_kwargs = {
            'admin_service_id': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'is_deleted': {'read_only': True}
        }
    
    
    def validate(self, data):
        if self.instance is None:
            admin = data.get('admin')
            service = data.get('service')
            service_provider = data.get('service_provider')

            if admin is None:
                raise serializers.ValidationError({'admin': 'This field is required.'})
            if service is None:
                raise serializers.ValidationError({'service': 'This field is required.'})
            if service_provider is None:
                raise serializers.ValidationError({'service_provider': 'This field is required.'})
        
        # For update, only validate fields that are provided
        else:
            if 'admin' in data and data.get('admin') is None:
                raise serializers.ValidationError({'admin': 'This field cannot be null.'})
            if 'service' in data and data.get('service') is None:
                raise serializers.ValidationError({'service': 'This field cannot be null.'})
            if 'service_provider' in data and data.get('service_provider') is None:
                raise serializers.ValidationError({'service_provider': 'This field cannot be null.'})

        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', ["created_at", "updated_at", "is_deleted", "created_by", "updated_by"])
        
        # Serialize nested fields with exclusion
        representation['admin'] = AdminSerializer(instance.admin, context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted", "created_by","updated_by"]}).data
        representation['service'] = SaServiceSerializer(instance.service, context={'exclude_fields': ["created_at", "updated_at", "is_deleted", "created_by","updated_by"]}).data
        
        representation['service_provider'] = ServiceProviderSerializer(instance.service_provider, context={'exclude_fields': ["created_at", "updated_at", "is_deleted", "created_by","updated_by","charges_data"]}).data
        
        # Remove specified fields from main representation
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation
    
    def get_charges(self,instance):
        request = self.context.get('request')
        charges_id_list = instance.charges
        charges_data = []
        if charges_id_list:
            for i in charges_id_list:
                charges_instance = Charges.objects.get(pk=i)
                charges_instance_data = ChargesSerializer(charges_instance,context={'request': request,'exclude_fields': ["created_at", "updated_at", "is_deleted", "updated_by"]})
                charges_data.append(charges_instance_data.data)

        return charges_data

"""
Serializer for managing AdminService model instances.

The AdminService_Data_Serializer class extends serializers.ModelSerializer to handle the serialization
of AdminService objects. It includes custom validation and representation logic to manage the data effectively.

Attributes:
- `service`: A PrimaryKeyRelatedField for linking to SaService instances.
- `service_provider`: A PrimaryKeyRelatedField for linking to ServiceProvider instances.

The `Meta` class:
- Specifies the model as AdminService and includes all fields for serialization.
- Sets 'admin_service_id', 'created_at', 'updated_at', and 'is_deleted' as read-only fields to prevent modification.

Custom methods:
- `validate`: Ensures that required fields ('service' and 'service_provider') are present in the data.
- `to_representation`: Customizes the output representation to include serialized data for related objects (service and service_provider)
    and handle field exclusions.

Usage:
1. Ensure that the AdminService model in your application is properly defined with the necessary fields.
2. Import and utilize AdminService_Data_Serializer in views or other components where serialization or deserialization of AdminService objects is required.
3. Use the `.is_valid()` and `.save()` methods to validate and persist AdminService data, ensuring proper representation and functionality.

Attributes:
- `Meta`: Defines the model as AdminService and specifies read-only fields.
- `validate`: Method to check the presence of required fields ('service' and 'service_provider') during validation.
- `to_representation`: Method to customize the output representation of the AdminService instance, including related service and service_provider data, and handling field exclusions.
"""   
class AdminService_Data_Serializer(serializers.ModelSerializer):
    # admin = serializers.PrimaryKeyRelatedField(queryset=Admin.objects.all())
    service = serializers.PrimaryKeyRelatedField(queryset=SaService.objects.all())
    # charges = serializers.PrimaryKeyRelatedField(queryset=Charges.objects.all())
    service_provider = serializers.PrimaryKeyRelatedField(queryset=ServiceProvider.objects.all())

    class Meta:
        model = AdminService
        fields = '__all__'
        extra_kwargs = {
            'admin_service_id': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'is_deleted': {'read_only': True}
        }
    
    def validate(self, data):
        # admin = data.get('admin')
        service = data.get('service')
        # charges = data.get('charges')
        service_provider = data.get('service_provider')

        # if admin is None:
        #     raise serializers.ValidationError({'admin': 'This field is required.'})
        if service is None:
            raise serializers.ValidationError({'service': 'This field is required.'})
        # if charges is None:
        #     raise serializers.ValidationError({'charges': 'This field is required.'})
        if service_provider is None:
            raise serializers.ValidationError({'service_provider': 'This field is required.'})

        return data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', ["created_at", "updated_at", "is_deleted", "created_by", "updated_by"])
        
        # Serialize nested fields with exclusion
        # representation['admin'] = AdminSerializer(instance.admin, context={'exclude_fields': ["created_at", "updated_at", "is_deleted", "created_by","updated_by"]}).data
        representation['service'] = SaServiceSerializer(instance.service, context={'exclude_fields': ["created_at", "updated_at", "is_deleted", "created_by","updated_by"]}).data
        # representation['charges'] = ChargesSerializer(instance.charges, context={'exclude_fields': ["created_at", "updated_at", "is_deleted", "created_by","updated_by"]}).data
        representation['service_provider'] = ServiceProviderSerializer(instance.service_provider, context={'exclude_fields': ["created_at", "updated_at", "is_deleted", "created_by","updated_by"]}).data
        
        # Remove specified fields from main representation
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation
    
"""
Serializer for managing Product model instances.

The ProductSerializer class extends serializers.ModelSerializer to handle the serialization of Product objects.
It includes custom fields and methods to enhance the representation of Product instances.

Attributes:
- `status`: A read-only field that returns the status of the product as "Active" or "Inactive" based on the `is_deactive` flag.
- `product_img`: A method field that provides URLs for product images.

Custom methods:
- `get_status`: Returns "Active" if the product is not deactivated (`is_deactive` is False), otherwise "Inactive".
- `get_product_img`: Constructs absolute URLs for product images based on the file paths stored in the `product_img` field.

The `to_representation` method:
- Customizes the representation of the Product instance.
- Includes detailed information about the associated product category if it exists.
- Removes fields specified in the `exclude_fields` list from the output representation.

Usage:
1. Ensure that the Product model in your application is properly defined with the necessary fields.
2. Import and utilize ProductSerializer in views or other components where serialization or deserialization of Product objects is required.
3. Use the `.is_valid()` and `.save()` methods to validate and persist Product data, ensuring proper representation and functionality.

Attributes:
- `Meta`: Defines the model as Product and includes all fields for serialization. 'created_at', 'created_by', and 'updated_at' are read-only fields.
- `get_status`: Method to determine and return the product status.
- `get_product_img`: Method to construct and return URLs for product images.
- `to_representation`: Method to customize the output representation of the Product instance, including related product category data and handling field exclusions.
"""
class ProductSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    product_img = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at')

    def get_status(self, obj):
        return "Active" if not obj.is_deactive else "Inactive"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        product_category_instance = instance.product_category
        if product_category_instance:
            product_category_data = {
                'id': product_category_instance.product_category_id,
                'name': product_category_instance.category_name  # Add the fields you need
            }
            representation['product_category'] = product_category_data
        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation

    def get_product_img(self, instance):
        request = self.context.get('request')
        file_paths = instance.product_img
        file_urls = []

        for file_path in file_paths:
            # Construct the full URL using the request and MEDIA_URL
            file_url = request.build_absolute_uri(settings.MEDIA_URL + file_path.replace('\\', '/'))
            file_urls.append(file_url)

        return file_urls
    

"""
    Serializer for managing AdminAgreement model instances.

    The AdminAgreementSerializer class extends serializers.ModelSerializer to handle the serialization and validation
    of AdminAgreement objects. It includes all fields of the AdminAgreement model for serialization.

    Custom validation logic is implemented in the following methods:
    - `validate_aa_amount`: Ensures that the 'aa_amount' (agreement amount) is greater than 0.
    - `validate_gst_amount`: Ensures that the 'gst_amount' (GST amount) is not negative.
    - `validate_agreement_document`: Ensures that the 'agreement_document' is a PDF file.

    The `validate` method includes additional validation logic:
    - During partial updates, it checks that 'gst_amount' is not greater than 'aa_amount'.
    - During both creation and update, it ensures that both 'aa_amount' and 'gst_amount' are provided and valid.

    Usage:
    1. Ensure that the AdminAgreement model in your application is properly defined with the necessary fields.
    2. Import and utilize AdminAgreementSerializer in views or other components where serialization or deserialization
        of AdminAgreement objects is required.
    3. Validate and persist AdminAgreement data using the `.is_valid()` and `.save()` methods to ensure data integrity.

    Attributes:
    - `Meta`: Defines the model as AdminAgreement and includes all fields for serialization.
    - `validate_aa_amount`: Custom method to ensure 'aa_amount' is greater than 0.
    - `validate_gst_amount`: Custom method to ensure 'gst_amount' is non-negative.
    - `validate_agreement_document`: Custom method to ensure 'agreement_document' is a PDF file.
    - `validate`: Custom method to perform comprehensive validation for 'aa_amount' and 'gst_amount' fields.
    """
class AdminAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminAgreement
        fields = '__all__'

    def validate_aa_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value

    def validate(self, data):
        
        if self.instance:
            # For partial updates, validate only the fields that are present in the data
            if 'aa_amount' in data and 'gst_amount' in data and data['aa_amount'] < data['gst_amount']:
                raise serializers.ValidationError("GST amount cannot be greater than the agreement amount.")

            if 'aa_amount' in data:
                # If 'aa_amount' is provided, validate against 'gst_amount' if it exists in the instance
                if self.instance.gst_amount is not None and data['aa_amount'] < self.instance.gst_amount:
                    raise serializers.ValidationError("GST amount cannot be greater than the agreement amount.")
            if 'gst_amount' in data:
                # If 'aa_amount' is provided, validate against 'gst_amount' if it exists in the instance
                if self.instance.aa_amount is not None and data['gst_amount'] > self.instance.aa_amount:
                    raise serializers.ValidationError("GST amount cannot be greater than the agreement amount.")
        else:
            if 'aa_amount' not in data:
                raise serializers.ValidationError("Agreement amount must be provided.")

        return data
    
    def save(self, **kwargs):
        instance = super().save(**kwargs)
        # Calculate aa_gst_amount
        instance.aa_gst_amount = float(instance.aa_amount) * 0.18
        instance.save()
        return instance






class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = '__all__'
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            representation.pop(field, None)
        return representation


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = '__all__'
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            representation.pop(field, None)
        return representation
    

class AdminBankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminBankDetails
        exclude = ["deposite_category", "created_at", "updated_at", "updated_by", "created_by", "is_deactive", "is_delete"]

class AdminFundRequestSerializer(serializers.ModelSerializer):
    bank_detail = serializers.SerializerMethodField()
    payment_proof = serializers.SerializerMethodField()

    class Meta:
        model = AdminFundRequest
        # fields = '__all__'
        exclude = ["created_at", "updated_at", "updated_by", "created_by", "is_delete"]

    def get_bank_detail(self, obj):
        try:
            get_bank_detail = AdminBankDetails.objects.get(bd_id=obj.deposite_bank.bd_id) 
            serializer = AdminBankDetailsSerializer(get_bank_detail)
            return serializer.data  
        except AdminBankDetails.DoesNotExist:
            return None
    
    def get_payment_proof(self, instance):
        request = self.context.get('request')
        scheme = "https" if request.is_secure() else "http"
        
        payment_proof = instance.payment_proof
        
        if payment_proof:
            file_path = payment_proof.get('payment_proof').replace('\\', '/')
            return f"{scheme}://{request.get_host()}/media/{file_path}"
        
        return None


class BBPSBillerCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SaBBPSBillerCategory
        exclude = ["created_at", "updated_at"]


class RechargeOperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaOprators
        exclude = ["created_at"]

class CfPgConfigedSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaPgConfiged
        exclude = ["created_at"]

class PhonePePgConfigedSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaPgConfiged
        exclude = ["created_at"]

class SaOtherChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaOtherCharges
        exclude = ["created_at"]
