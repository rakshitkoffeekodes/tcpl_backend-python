from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from tcpl_backend import settings
from .models import  AboutUs, Announcement, Banner, NewsLetter, ContactEnquiry,  ContactUs, CustomUser,  Randomstuff, SMTPConfiguration, Service, ServiceGroup,  Testimonial
from PIL import Image
import requests
from io import BytesIO
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError

# from superadmin_backend.apis_app import models
from . import models

def get_image_size(image_url):
    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        return f"{img.width}x{img.height}"
    except Exception as e:
        return str(e)
    
User = get_user_model()


"""
Serializer for managing Banner model instances in an application.

The BannerSerializer class extends a serializer base class to handle the serialization and validation of Banner objects.
It includes fields for all attributes of the Banner model, designating 'created_at' and 'created_by' as read-only fields.

Custom validation ensures that essential attributes such as 'title', 'image_for_web', 'image_for_mobile', and 'description'
are present when creating or updating a Banner instance. If any of these attributes are missing, a validation error is raised.
Additionally, it checks the size of 'image_for_web' and 'image_for_mobile' to ensure they do not exceed 5 MB.

Usage:
1. Ensure that the Banner model in your application is properly defined with the required attributes.
2. Utilize BannerSerializer in views, serializers, or other components where Banner object serialization or deserialization is required.
3. Validate and persist Banner data using the .is_valid() and .save() methods respectively.

Note: This serializer assumes the existence of the Banner model with the specified attributes.

Attributes:
- `status`: A read-only field added via `SerializerMethodField` that determines if the banner is 'Active' or 'Inactive' based on the `is_deactive` attribute.
- `image_for_web_size`: A read-only field via `SerializerMethodField` that fetches the size of the 'image_for_web' attribute.
- `image_for_mobile_size`: A read-only field via `SerializerMethodField` that fetches the size of the 'image_for_mobile' attribute.
"""




class BannerSerializer(serializers.ModelSerializer):
    # status = serializers.SerializerMethodField()
    # image_for_web_size = serializers.SerializerMethodField()
    # image_for_mobile_size = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        # fields = '__all__'  # Include all fields from the Banner model
        exclude = ['created_at', 'created_by',  'is_deleted']  # Make 'created_at' and 'created_by' read-onl

    # def get_status(self, obj):
    #     return "Active" if not obj.is_deactive else "Inactive"

    # def get_image_for_web_size(self, obj):
    #     if obj.image_for_web:
    #         return get_image_size(self.context['request'].build_absolute_uri(obj.image_for_web.url))
    #     return None

    # def get_image_for_mobile_size(self, obj):
    #     if obj.image_for_mobile:
    #         return get_image_size(self.context['request'].build_absolute_uri(obj.image_for_mobile.url))
    #     return None

    # def validate(self, data):
    #     max_size = 10 * 1024 * 1024  # 10 MB in bytes

    #     if self.instance:
    #         if 'title' in data and not data.get('title'):
    #             raise serializers.ValidationError("Title is required.")
    #         if 'image_for_web' in data and not data.get('image_for_web'):
    #             raise serializers.ValidationError("Image for web is required.")
    #         if 'image_for_mobile' in data and not data.get('image_for_mobile'):
    #             raise serializers.ValidationError("Image for mobile is required.")
    #         if 'description' in data and not data.get('description'):
    #             raise serializers.ValidationError("Description is required.")

    #         image_for_web = data.get('image_for_web')
    #         if image_for_web and image_for_web.size > max_size:
    #             raise serializers.ValidationError("Image for web must be less than 10 MB.")

    #         image_for_mobile = data.get('image_for_mobile')
    #         if image_for_mobile and image_for_mobile.size > max_size:
    #             raise serializers.ValidationError("Image for mobile must be less than 10 MB.")

    #     else:
    #         if not data.get('title'):
    #             raise serializers.ValidationError("Title is required.")
    #         if not data.get('image_for_web'):
    #             raise serializers.ValidationError("Image for web is required.")
    #         if not data.get('image_for_mobile'):
    #             raise serializers.ValidationError("Image for mobile is required.")
    #         if not data.get('description'):
    #             raise serializers.ValidationError("Description is required.")

    #         image_for_web = data.get('image_for_web')
    #         if image_for_web and image_for_web.size > max_size:
    #             raise serializers.ValidationError("Image for web must be less than 10 MB.")

    #         image_for_mobile = data.get('image_for_mobile')
    #         if image_for_mobile and image_for_mobile.size > max_size:
    #             raise serializers.ValidationError("Image for mobile must be less than 10 MB.")
            
    #     banner_date = Banner.objects.filter(title=data.get('title'), is_deleted=False).first()
    #     if banner_date:
    #         raise serializers.ValidationError("Banner with the same title already exists.")

    #     return data
    
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     exclude_fields = self.context.get('exclude_fields', [])
        
    #     for field in exclude_fields:
    #         representation.pop(field, None)
        
    #     return representation

    
    
 


"""
Serializer for managing Testimonial model instances in an application.

The TestimonialSerializer class extends serializers.ModelSerializer to handle the serialization and validation
of Testimonial objects. It specifies all fields of the Testimonial model for serialization, designating 
'created_at' and 'created_by' as read-only fields to prevent modification through this serializer.

Custom validation logic is implemented in the validate method to ensure that required fields ('name', 'email', 
'title', 'comments') are provided when creating or updating a Testimonial instance. If any of these fields are 
missing, a serializers.ValidationError is raised.

Usage:
1. Ensure that the Testimonial model in your application is properly defined with the necessary fields.
2. Import and utilize TestimonialSerializer in views, serializers, or other components where serialization 
   or deserialization of Testimonial objects is required.
3. Validate and persist Testimonial data using the .is_valid() and .save() methods, ensuring data integrity 
   and validation of required fields.

Note: This serializer assumes the existence of a Testimonial model with appropriate fields.

Attributes:
- `Meta`: Defines the model as Testimonial and includes all fields for serialization.
- `validate`: Custom method to validate required fields ('name', 'email', 'title', 'comments') during creation 
  or update of Testimonial instances.
"""


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        # fields = '__all__'
        exclude = ['created_at', 'created_by','modified_at']

    # def validate(self, data):
    #     # Check if we are performing a partial update
    #     if self.instance:
    #         # For partial updates, only validate the fields that are present in the data
    #         if 'name' in data and not data.get('name'):
    #             raise serializers.ValidationError("Name is required")
            
    #         if 'email' in data and not data.get('email'):
    #             raise serializers.ValidationError("Email is required")
            
    #         if 'title' in data and not data.get('title'):
    #             raise serializers.ValidationError("Title is required")
            
    #         if 'comments' in data and not data.get('comments'):
    #             raise serializers.ValidationError("Comments are required")
        
    #     else:
    #         # For create operations, all fields must be present
    #         if not data.get('name'):
    #             raise serializers.ValidationError("Name is required")
            
    #         if not data.get('email'):
    #             raise serializers.ValidationError("Email is required")
            
    #         if not data.get('title'):
    #             raise serializers.ValidationError("Title is required")
            
    #         if not data.get('comments'):
    #             raise serializers.ValidationError("Comments are required")
            
    #     testimonial_data = Testimonial.objects.filter(name=data.get('name'), email=data.get('email'), is_deleted=False).first()
    #     if testimonial_data:
    #         raise serializers.ValidationError("Testimonial with the same name and email already exists.")
        
    #     return data
    
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     exclude_fields = self.context.get('exclude_fields', [])
        
    #     for field in exclude_fields:
    #         representation.pop(field, None)
        
    #     return representation


"""
Serializer for managing AboutUs model instances in an application.

The AboutUsSerializer class extends serializers.ModelSerializer to handle the serialization and validation
of AboutUs objects. It specifies all fields of the AboutUs model for serialization, marking created_at,
created_by, and updated_at as read-only to prevent modification through this serializer.

Custom validation logic is implemented in the validate method to ensure the following:

Single Record Constraint: Only one AboutUs entry is allowed in the database at any time.
    If there is no existing instance (self.instance) and an AboutUs object already exists, a serializers.ValidationError is raised.
Exclusive Description Field: Only one description field can be provided at a time.
    There are four description fields: about_us_desc, our_focus_desc, our_mission_desc, our_vision_desc.
    At least one of these fields must be provided in the request data.
    If none of these fields are provided, a serializers.ValidationError is raised.
    If more than one of these fields is provided, a serializers.ValidationError is raised.
Usage
    Ensure that the AboutUs model in your application is properly defined with the required fields.
    Import and utilize AboutUsSerializer in views, serializers, or other components where serialization
    or deserialization of AboutUs objects is necessary.
    Validate and persist AboutUs data using the .is_valid() and .save() methods to ensure data integrity
    and adherence to the constraints mentioned above.
Attributes
    Meta: Defines the model as AboutUs and includes all fields for serialization, marking certain fields as read-only.
    validate: Custom method to enforce single record constraint and ensure only one description field is provided during creation or update of AboutUs instances.
"""



class AboutUsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AboutUs
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at')

    def validate(self, data):
        # Ensure there is only one record
        if not self.instance and AboutUs.objects.exists():
            raise serializers.ValidationError("Only one AboutUs entry is allowed.")

        # Ensure only one description field is provided
        desc_fields = ['about_us_desc', 'our_focus_desc', 'our_mission_desc', 'our_vision_desc']
        provided_descs = [field for field in desc_fields if data.get(field)]

        if len(provided_descs) == 0:
            raise serializers.ValidationError("At least one description field must be provided.")

        return data
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation



"""
Serializer for managing Randomstuff model instances in an application.

The RandomstuffSerializer class extends serializers.ModelSerializer to handle the serialization and validation
of Randomstuff objects. It specifies all fields of the Randomstuff model for serialization, marking created_at,
created_by, and updated_at as read-only to prevent modification through this serializer.

Custom validation logic is implemented in the validate method to ensure the following:

Single Record Constraint: Only one Randomstuff entry is allowed in the database at any time.
    If there is no existing instance (self.instance) and a Randomstuff object already exists, a serializers.ValidationError is raised.
Exclusive Description Field: Only one description field can be provided at a time.
    There are three description fields: privacy_policy_desc, terms_of_service_desc, cancellation_policy_desc.
    At least one of these fields must be provided in the request data.
    If none of these fields are provided, a serializers.ValidationError is raised.
    If more than one of these fields is provided, a serializers.ValidationError is raised.

Usage:
    Ensure that the Randomstuff model in your application is properly defined with the required fields.
    Import and utilize RandomstuffSerializer in views, serializers, or other components where serialization
    or deserialization of Randomstuff objects is necessary.
    Validate and persist Randomstuff data using the .is_valid() and .save() methods to ensure data integrity
    and adherence to the constraints mentioned above.

Attributes:
    Meta: Defines the model as Randomstuff and includes all fields for serialization, marking certain fields as read-only.
    validate: Custom method to enforce single record constraint and ensure only one description field is provided during creation or update of Randomstuff instances.
"""

class RandomstuffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Randomstuff
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at')

    def validate(self, data):
        # Ensure there is only one record
        if not self.instance and Randomstuff.objects.exists():
            raise serializers.ValidationError("Only one Randomstuff entry is allowed.")

        # Ensure only one description field is provided
        desc_fields = ['privacy_policy_desc', 'terms_of_service_desc', 'cancellation_policy_desc']
        provided_descs = [field for field in desc_fields if data.get(field)]

        if len(provided_descs) == 0:
            raise serializers.ValidationError("At least one description field must be provided.")
        

        return data
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation
    


"""
Serializer for managing ContactUs model instances in an application.

The ContactUsSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of ContactUs objects. It specifies all fields of the ContactUs model for 
serialization, marking 'created_at', 'created_by', and 'modified_at' as read-only to prevent 
modification through this serializer.

Custom validation logic is implemented in the validate method to ensure that the following 
fields are provided and meet specific criteria when creating or updating a ContactUs instance:
- 'contact_no': Must not be empty, must contain exactly 10 digits, and should contain only digits.
- 'address': Must not be empty.
- 'email': Must not be empty.
- 'social_media_links': Must not be empty.

If any of these fields are missing or do not meet the specified criteria, a serializers.ValidationError 
is raised with a corresponding error message.

Usage:
1. Ensure that the ContactUs model in your application is properly defined with the required fields.
2. Import and use ContactUsSerializer where serialization or deserialization of ContactUs 
   objects is necessary, such as in views or serializers.
3. Validate and save ContactUs data using .is_valid() and .save() methods, ensuring data 
   integrity and adherence to validation rules for the required fields.

Note: This serializer assumes the existence of a ContactUs model with appropriate fields.

Attributes:
- `Meta`: Specifies the model as ContactUs and includes all fields for serialization.
- `validate`: Custom method to validate the presence and format of required fields ('contact_no', 'address', 'email', 'social_media_links') 
  during creation or update of ContactUs instances, ensuring data integrity.
- `validate_contact_no`: Custom validation method specifically for the 'contact_no' field to ensure it contains exactly 10 digits.
"""


class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by','modified_at')

    def validate(self, data):
        if not self.instance:
            # For creation, ensure all fields are present and valid
            contact_no = data.get('contact_no')
            if not contact_no or not contact_no.strip():
                raise serializers.ValidationError({"contact_no": "Contact number is required and cannot be empty."})
            if not contact_no.isdigit():
                raise serializers.ValidationError({"contact_no": "Contact number must contain only digits."})
            if len(contact_no) != 10:
                raise serializers.ValidationError({"contact_no": "Contact number must be exactly 10 digits long."})

            address = data.get('address')
            if not address or not address.strip():
                raise serializers.ValidationError({"address": "Address is required and cannot be empty."})

            email = data.get('email')
            if not email or not email.strip():
                raise serializers.ValidationError({"email": "Email is required and cannot be empty."})

            social_media_links = data.get('social_media_links')
            if not social_media_links:
                raise serializers.ValidationError({"social_media_links": "Social media links are required."})

        else:
            # For updates, validate only the fields that are being updated
            if 'contact_no' in data:
                contact_no = data['contact_no']
                if not contact_no.strip():
                    raise serializers.ValidationError({"contact_no": "Contact number cannot be empty."})
                if not contact_no.isdigit():
                    raise serializers.ValidationError({"contact_no": "Contact number must contain only digits."})
                if len(contact_no) != 10:
                    raise serializers.ValidationError({"contact_no": "Contact number must be exactly 10 digits long."})

            if 'address' in data and not data['address'].strip():
                raise serializers.ValidationError({"address": "Address cannot be empty."})

            if 'email' in data and not data['email'].strip():
                raise serializers.ValidationError({"email": "Email cannot be empty."})

            if 'social_media_links' in data and not data['social_media_links']:
                raise serializers.ValidationError({"social_media_links": "Social media links cannot be empty."})

        return data

    def validate_contact_no(self, value):
        if len(value) != 10:
            raise serializers.ValidationError("Contact number must be exactly 10 digits long.")
        return value
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation


"""
Serializer for managing ServiceGroup model instances in an application.

The ServiceGroupSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of ServiceGroup objects. It specifies all fields of the ServiceGroup model for 
serialization, marking 'created_at', 'created_by', and 'modified_at' as read-only to prevent 
modification through this serializer.

Custom validation logic is implemented using the validate_group_name method to ensure that 
the 'group_name' field does not contain the substring 'example'. If the group name contains 
'example', a serializers.ValidationError is raised with a specific error message.

Additional validation in the validate method checks that the 'group_name' field is provided 
and not empty. If 'group_name' is missing or empty, a serializers.ValidationError is raised 
with a corresponding error message.

Usage:
1. Ensure that the ServiceGroup model in your application is properly defined with the required fields.
2. Import and use ServiceGroupSerializer where serialization or deserialization of ServiceGroup 
   objects is necessary, such as in views or serializers.
3. Validate and save ServiceGroup data using .is_valid() and .save() methods, ensuring data 
   integrity and adherence to validation rules for the 'group_name' field.

Note: This serializer assumes the existence of a ServiceGroup model with appropriate fields.

Attributes:
- `Meta`: Specifies the model as ServiceGroup and includes all fields for serialization.
- `get_status`: Custom method to retrieve and display the status of the ServiceGroup based on 
  the 'is_deactive' field.
- `validate_group_name`: Custom validation method specifically for the 'group_name' field to 
  ensure it does not contain the substring 'example', maintaining data integrity.
- `validate`: Custom method to validate the presence and format of required fields during creation 
  or update of ServiceGroup instances, ensuring adherence to validation rules.
"""



class ServiceGroupSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    class Meta:
        model = models.ServiceGroup
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by','modified_at','is_deleted')
        extra_kwargs = {
            'description': {'required': True},
        }
        
    def get_status(self, obj):
            return "Active" if not obj.is_deactive else "Inactive"

    def validate_group_name(self, value):
        if 'example' in value.lower():
            raise serializers.ValidationError("The group name should not contain the word 'example'.")
        return value
    def validate(self, data):
        if 'group_name' in data and not data['group_name']:
            raise serializers.ValidationError("group_name is required.")
        
        # if 'status' in data and not data['status']:
        #     raise serializers.ValidationError("Status is required.")
        
        if 'description' in data and not data['description']:
            raise serializers.ValidationError("Description is required.")
        
        return data
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation
    


"""
Serializer for managing Service model instances in an application.

The ServiceSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of Service objects. It specifies all fields of the Service model for 
serialization, marking 'created_at', 'created_by', and 'is_deleted' as read-only to prevent 
modification through this serializer.

Custom validation logic is implemented using the validate_service_group method to ensure 
that the 'service_group' field references an existing ServiceGroup instance. If the specified 
ServiceGroup instance does not exist, a serializers.ValidationError is raised with a specific 
error message.

Further validation in the validate method ensures that the following fields are provided and 
not empty when creating or updating a Service instance:
- 'title': Title of the service.
- 'image': Image associated with the service.
- 'description': Description of the service.

If any of these required fields are missing or empty, a serializers.ValidationError is raised 
with the appropriate error message.

Usage:
1. Ensure that the Service and ServiceGroup models in your application are properly defined with 
   the required fields.
2. Import and use ServiceSerializer where serialization or deserialization of Service objects 
   is necessary, such as in views or serializers.
3. Validate and save Service data using .is_valid() and .save() methods to ensure data integrity 
   and adherence to validation rules for the required fields.

Note: This serializer assumes the existence of Service and ServiceGroup models with appropriate fields.

Attributes:
- `Meta`: Specifies the model as Service and includes all fields for serialization.
- `validate_service_group`: Custom validation method to ensure that the 'service_group' field 
  references an existing ServiceGroup instance, maintaining data integrity.
- `validate`: Custom method to validate the presence and format of required fields during creation 
  or update of Service instances, ensuring adherence to validation rules.
"""



class ServiceSerializer(serializers.ModelSerializer):
   
    # status = serializers.SerializerMethodField()
    class Meta:
        model = models.Service
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by','is_deleted')
        
    # def get_status(self, obj):
    #     return "Active" if not obj.is_deactive else "Inactive"

    def validate_service_group(self, value):
        if not models.ServiceGroup.objects.filter(servicegroup_id=value.servicegroup_id).exists():
            raise serializers.ValidationError("The specified service group does not exist.")
        return value
    
    def validate(self, data):
        if 'title' in data and not data['title']:
            raise serializers.ValidationError("Title is required.")
        
        if 'image' in data and not data['image']:
            raise serializers.ValidationError("image is required.")

        if 'description' in data and not data['description']:
            raise serializers.ValidationError("Description is required.")

        # if 'status' in data and not data['status']:
        #     raise serializers.ValidationError("Status is required.")


        return data
    


"""
Serializer for managing Partner model instances in an application.

The PartnerSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of Partner objects. It specifies all fields of the Partner model for 
serialization, marking 'created_at', 'created_by', and 'modified_at' as read-only to prevent 
modification through this serializer.

Custom validation logic is implemented using the validate_partner_name method to ensure 
that the 'partner_name' field does not contain the substring 'example'. If the partner name 
contains 'example', a serializers.ValidationError is raised with a specific error message.

Further validation in the validate method ensures that the following fields are provided 
and not empty when creating or updating a Partner instance:
- 'partner_name': Name of the partner.
- 'logo': Logo associated with the partner.
- 'description': Description of the partner.

If any of these required fields are missing or empty, a serializers.ValidationError is raised 
with the appropriate error message.

Usage:
1. Ensure that the Partner model in your application is properly defined with the required fields.
2. Import and use PartnerSerializer where serialization or deserialization of Partner objects 
   is necessary, such as in views or serializers.
3. Validate and save Partner data using .is_valid() and .save() methods to ensure data integrity 
   and adherence to validation rules for the required fields.

Note: This serializer assumes the existence of a Partner model with appropriate fields.

Attributes:
- `Meta`: Specifies the model as Partner and includes all fields for serialization.
- `get_logo_size`: Method to retrieve the size of the partner's logo image, ensuring it is included 
  in serialized data.
- `validate_partner_name`: Custom validation method to check that the 'partner_name' field does not 
  contain the word 'example', maintaining data integrity.
- `validate`: Custom method to validate the presence and format of required fields during creation 
  or update of Partner instances.
"""



class PartnerSerializer(serializers.ModelSerializer):
    
    # status = serializers.SerializerMethodField()
    # logo_size = serializers.SerializerMethodField()

    class Meta:
        model = models.Partner
        # fields = '__all__'
        exclude = ['created_at', 'created_by','modified_at']
        
    # def get_logo_size(self, obj):
    #     if obj.logo:
    #         return get_image_size(self.context['request'].build_absolute_uri(obj.logo.url))
    #     return None
        
    # def validate_partner_name(self, value):
    #     if 'example' in value.lower():
    #         raise serializers.ValidationError("The partner name should not contain the word 'example'.")
    #     return value
    
    # def get_status(self, obj):
    #      return "Active" if not obj.is_deactive else "Inactive"

        
    # def validate(self, data):
    #     if 'partner_name' in data and not data['partner_name']:
    #         raise serializers.ValidationError("partner_name is required.")
        
    #     if 'logo' in data and not data['logo']:
    #         raise serializers.ValidationError("logo is required.")

    #     if 'description' in data and not data['description']:
    #         raise serializers.ValidationError("Description is required.")

    #     # if 'status' in data and not data['status']:
    #     #     raise serializers.ValidationError("Status is required.")


    #     return data
    
    # def validate_logo(self, value):
    #       max_size= 5 * 1024 * 1024  
          
    #       if value.size>max_size:
    #         raise serializers.ValidationError("Logo must be less than 5 MB")

    #       return value
    
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     exclude_fields = self.context.get('exclude_fields', [])
        
    #     for field in exclude_fields:
    #         representation.pop(field, None)
        
    #     return representation

    


"""
Serializer for managing YouTubeVideo model instances in an application.

The YoutubeSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of YouTubeVideo objects. It specifies all fields of the YouTubeVideo model for 
serialization, marking 'created_at', 'created_by', 'modified_at', and 'youtube_thumbnail_size' 
as read-only to prevent modification through this serializer.

Custom validation logic is implemented using the validate_youtube_link method to ensure 
that the 'youtube_link' field starts with 'https://www.youtube.com/'. If the YouTube link 
does not meet this criteria, a serializers.ValidationError is raised with a specific error 
message.

Further validation in the validate method checks that the 'video_title' field does not 
contain the substring 'example'. If the video title contains 'example', a 
serializers.ValidationError is raised with a specific error message.

Additional validation in the validate_youtube_thumbnail_image method ensures that the 
'youtube_thumbnail_image' field size does not exceed 5 MB. If the image exceeds this limit, 
a serializers.ValidationError is raised with an appropriate error message.

Usage:
1. Ensure that the YouTubeVideo model in your application is properly defined with the required 
   fields.
2. Import and use YoutubeSerializer where serialization or deserialization of YouTubeVideo 
   objects is necessary, such as in views or serializers.
3. Validate and save YouTubeVideo data using .is_valid() and .save() methods to ensure data 
   integrity and adherence to validation rules for the 'youtube_link', 'video_title', and 
   'youtube_thumbnail_image' fields.

Note: This serializer assumes the existence of a YouTubeVideo model with appropriate fields.

Attributes:
- `Meta`: Specifies the model as YouTubeVideo and includes all fields for serialization.
- `get_youtube_thumbnail_size`: Method to retrieve the size of the YouTube video's thumbnail image, 
  ensuring it is included in serialized data.
- `get_status`: Method to determine and include the status of the YouTube video (Active/Inactive) 
  in serialized data.
- `validate_youtube_link`: Custom validation method to enforce the correct format of the 'youtube_link' 
  field, maintaining data integrity.
- `validate`: Custom method to validate the presence and format of required fields during creation 
  or update of YouTubeVideo instances.
- `validate_youtube_thumbnail_image`: Custom validation method to restrict the size of the YouTube 
  video's thumbnail image, ensuring it does not exceed 5 MB.
"""


class YoutubeSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    youtube_thumbnail_size = serializers.SerializerMethodField()
    class Meta:
        model = models.YouTubeVideo
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by','modified_at','youtube_thumbnail_size')
        
    def get_youtube_thumbnail_size(self, obj):
        if obj.youtube_thumbnail_image:
            return get_image_size(self.context['request'].build_absolute_uri(obj.youtube_thumbnail_image.url))
        return None
        
    def get_status(self, obj):
            return "Active" if not obj.is_deactive else "Inactive"

    def validate_youtube_link(self, value):
        if not value.startswith('https://www.youtube.com/'):
            raise serializers.ValidationError("The YouTube link must start with 'https://www.youtube.com/'.")
        
        prohibited_terms=['search','live']
        for term in prohibited_terms:
            if term in value.lower():
                raise serializers.ValidationError("The YouTube link should not contain the term.")
        return value

    def validate(self, data):
        if 'video_title' in data and 'example' in data['video_title'].lower():
            raise serializers.ValidationError("The video title should not contain the word 'example'.")
        
        return data

    def validate_youtube_thumbnail_image(self, value):
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        
        if value.size > max_size:
            raise serializers.ValidationError("Thumbnail image must be less than 5 MB")
        return value
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation
    

"""
Serializer for managing Service model instances along with associated ServiceGroup details 
within an application.

The Service_Serializer class extends serializers.ModelSerializer to handle the serialization 
of Service objects. It specifies fields of the Service model for serialization, including 'service_id', 
'title', 'image', 'description', 'service_group', 'status', 'created_at', 'created_by', 'modified_at', 
'is_deactive', and 'size_of_image'. Fields 'created_at' and 'created_by' are marked as read-only 
to prevent modification through this serializer.

The 'service_group' field is serialized using Service_GroupSerializer in read-only mode. This allows 
for nested serialization of related ServiceGroup details when retrieving Service objects, but does 
not allow updates to the ServiceGroup through this serializer.

Custom serialization logic is implemented in the get_status method to determine the status ('Active' 
or 'Inactive') based on the value of the 'is_deactive' field.

Additional logic in the get_size_of_image method retrieves the size of the service's image and includes 
it in the serialized data.

Usage:
1. Ensure that the Service and ServiceGroup models in your application are properly defined with the 
   required fields.
2. Import and use Service_Serializer where serialization or deserialization of Service objects with 
   associated ServiceGroup details is required, such as in views or serializers.
3. Utilize the serializer to fetch Service objects with their associated ServiceGroup details, ensuring 
   data integrity and providing comprehensive representations of Service entities.

Note: This serializer assumes the existence of Service and ServiceGroup models with appropriate fields.

Attributes:
- `Meta`: Specifies the model as Service and includes specific fields for serialization.
- `service_group`: Nested serializer for serializing ServiceGroup details in read-only mode.
- `get_status`: Method to determine and include the status ('Active' or 'Inactive') based on the 
  'is_deactive' field in serialized data.
- `get_size_of_image`: Method to retrieve and include the size of the service's image in serialized data.
- `validate_image`: Custom validation method to restrict the size of the service's image, ensuring it 
  does not exceed 5 MB.
"""


class Service_GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceGroup
        fields = ['servicegroup_id', 'group_name','description']

class Service_Serializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    service_group = Service_GroupSerializer(read_only=True)
    size_of_image = serializers.SerializerMethodField()

    

    class Meta:
        model = Service
        fields = ['service_id', 'title', 'image', 'description', 'service_group', 'created_at', 'created_by','modified_at','status','is_deactive','size_of_image']
        read_only_fields = ('created_at', 'created_by')
        
    def get_size_of_image(self, obj):
        if obj.image:
            return get_image_size(self.context['request'].build_absolute_uri(obj.image.url))
        return None
        
    def get_status(self, obj):
        return "Active" if not obj.is_deactive else "Inactive"
        
        
    def validate_image(self, value):
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        
        if value.size > max_size:
            raise serializers.ValidationError("Image must be less than 5 MB")
        return value
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        
        for field in exclude_fields:
            representation.pop(field, None)
        
        return representation
    

"""
Serializer for managing ContactEnquiry model instances in an application.

The ContactEnquirySerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of ContactEnquiry objects. It specifies all fields of the ContactEnquiry model for 
serialization, marking 'created_at', 'updated_at', and 'update_by' as read-only to prevent modification 
through this serializer.

Custom validation logic is implemented using the validate method to ensure that required fields 
('ce_name', 'ce_email', 'ce_contact_no', 'ce_subject', 'ce_message') are provided during creation 
or update of ContactEnquiry instances. If any of these fields are missing, a serializers.ValidationError 
is raised with a specific error message.

Usage:
1. Ensure that the ContactEnquiry model in your application is properly defined with the required 
   fields.
2. Import and use ContactEnquirySerializer where serialization or deserialization of ContactEnquiry 
   objects is necessary, such as in views or serializers.
3. Validate and save ContactEnquiry data using .is_valid() and .save() methods to ensure data integrity 
   and adherence to validation rules for the 'ce_name', 'ce_email', 'ce_contact_no', 'ce_subject', and 
   'ce_message' fields.

Note: This serializer assumes the existence of a ContactEnquiry model with appropriate fields.

Attributes:
- `Meta`: Specifies the model as ContactEnquiry and includes all fields for serialization.
- `validate`: Custom method to validate the presence of required fields during creation or update 
  of ContactEnquiry instances.
"""


class ContactEnquirySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ContactEnquiry
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'update_by')

    def validate(self, data):
        if self.instance:
            if 'ce_name' in data and not data.get('ce_name'):
                raise serializers.ValidationError("Name is required.")
            if 'ce_email' in data and not data.get('ce_email'):
                raise serializers.ValidationError("Email is required.")
            if 'ce_contact_no' in data:
                contact_no = data.get('ce_contact_no')
                if contact_no is None:
                    raise serializers.ValidationError("Contact number is required.")
                if not isinstance(contact_no, str) or not contact_no.isdigit():
                    raise serializers.ValidationError("Contact number must be numeric.")
                if len(contact_no) != 10:
                    raise serializers.ValidationError("Contact number must be exactly 10 characters long.")
            if 'ce_subject' in data and not data.get('ce_subject'):
                raise serializers.ValidationError("Subject is required.")
            if 'ce_message' in data and not data.get('ce_message'):
                raise serializers.ValidationError("Message is required.")

        else:
            if not data.get('ce_name'):
                raise serializers.ValidationError("Name is required.")
            if not data.get('ce_email'):
                raise serializers.ValidationError("Email is required.")
            if 'ce_contact_no' in data:
                contact_no = data.get('ce_contact_no')
                if contact_no is None:
                    raise serializers.ValidationError("Contact number is required.")
                if not isinstance(contact_no, str) or not contact_no.isdigit():
                    raise serializers.ValidationError("Contact number must be numeric.")
                if len(contact_no) != 10:
                    raise serializers.ValidationError("Contact number must be exactly 10 characters long.")
            if not data.get('ce_subject'):
                raise serializers.ValidationError("Subject is required.")
            if not data.get('ce_message'):
                raise serializers.ValidationError("Message is required.")

        return data
    
class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class CodeSerializer(serializers.Serializer):
    # email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

class PasswordResetSerializer(serializers.Serializer):
    # email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)



"""
Serializer for managing SMTP configuration instances in an application.

The SMTPConfigurationSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of SMTPConfiguration objects. It specifies all fields of the SMTPConfiguration model for 
serialization, marking 'created_by', 'created_at', 'updated_at', and 'update_by' as read-only to prevent 
modification through this serializer.

Custom validation logic is implemented using the validate methods to ensure that required fields 
('smtp_server', 'port', 'password', 'encryption_method', 'sender_email', 'reply_to_email_address') 
are provided during creation or update of SMTPConfiguration instances. It also validates specific 
constraints such as port number range and encryption method validity.

Usage:
1. Ensure that the SMTPConfiguration model in your application is properly defined with the required 
    fields.
2. Import and use SMTPConfigurationSerializer where serialization or deserialization of SMTPConfiguration 
    objects is necessary, such as in views or serializers.
3. Validate and save SMTPConfiguration data using .is_valid() and .save() methods to ensure data integrity 
    and adherence to validation rules for the 'smtp_server', 'port', 'password', 'encryption_method', 
    'sender_email', and 'reply_to_email_address' fields.

Note: This serializer assumes the existence of an SMTPConfiguration model with appropriate fields.

Attributes:
- `Meta`: Specifies the model as SMTPConfiguration and includes all fields for serialization.
- `validate_port`: Validates the port number to ensure it falls within a valid range.
- `validate_encryption_method`: Validates the encryption method to ensure it is one of the defined choices.
- `validate`: Custom method to validate the presence of required fields during creation or update 
    of SMTPConfiguration instances.
"""
class SMTPConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMTPConfiguration
        fields = '__all__'
        read_only_fields = ('created_by','created_at', 'updated_at', 'update_by')
        
    def validate_port(self, value):
        if value is None:
            raise serializers.ValidationError("Port is required.")
        if value <= 0 or value > 65535:
            raise serializers.ValidationError("Port number must be between 1 and 65535.")
        return value
    
    def validate_encryption_method(self, value):
        if value not in dict(SMTPConfiguration.ENCRYPTION_CHOICES):
            raise serializers.ValidationError("Invalid encryption method.")
        return value
    
    def validate(self, data):
        if self.instance:  # For update
            if 'smtp_server' in data and not data.get('smtp_server'):
                raise serializers.ValidationError("SMTP server address is required.")
            if 'port' in data:
                port = data.get('port')
                if port is None:
                    raise serializers.ValidationError("Port is required.")
                if port <= 0 or port > 65535:
                    raise serializers.ValidationError("Port number must be between 1 and 65535.")
            if 'password' in data and not data.get('password'):
                raise serializers.ValidationError("Password is required.")
            if 'encryption_method' in data:
                encryption_method = data.get('encryption_method')
                if encryption_method not in dict(SMTPConfiguration.ENCRYPTION_CHOICES):
                    raise serializers.ValidationError("Invalid encryption method.")
            if 'sender_email' in data and not data.get('sender_email'):
                raise serializers.ValidationError("Sender email address is required.")
            
        else:  # For create
            if not data.get('smtp_server'):
                raise serializers.ValidationError("SMTP server address is required.")
            if not data.get('port'):
                raise serializers.ValidationError("Port is required.")
            if data['port'] <= 0 or data['port'] > 65535:
                raise serializers.ValidationError("Port number must be between 1 and 65535.")
            if not data.get('password'):
                raise serializers.ValidationError("Password is required.")
            if not data.get('encryption_method'):
                raise serializers.ValidationError("Encryption method is required.")
            if data['encryption_method'] not in dict(SMTPConfiguration.ENCRYPTION_CHOICES):
                raise serializers.ValidationError("Invalid encryption method.")
            if not data.get('sender_email'):
                raise serializers.ValidationError("Sender email address is required.")
            

        return data


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the CustomUser model.

    Fields:
    - id: AutoField, unique identifier for the user.
    - username: CharField, unique identifier for the user.
    - email: EmailField, email address of the user.
    - first_name: CharField, first name of the user.
    - last_name: CharField, last name of the user.
    - totp_secret: CharField, secret key for Two-Factor Authentication using TOTP.
    - verify_code: CharField, verification code for user authentication.
    - verify_code_expire_at: DateTimeField, expiry time for the verification code.
    """

    class Meta:
        model = CustomUser
        fields = ['id','first_name','last_name','username','email']
        # read_only_fields = ['password']



"""
Serializer for managing Announcement instances in an application.

The AnnouncementSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of Announcement objects. It specifies all fields of the Announcement model for 
serialization, marking 'created_by', 'created_at', 'updated_at', and 'updated_by' as read-only to 
prevent modification through this serializer.

Custom validation logic is implemented using the validate methods to ensure that required fields 
('title', 'announcement_type', 'date', 'expiry_date', 'start_time', 'end_time', 'description', 
'attachment_doc') are provided during creation or update of Announcement instances. It also validates 
specific constraints such as ensuring the 'expiry_date' is after the 'date' and the 'end_time' is after 
the 'start_time'.

Usage:
1. Ensure that the Announcement model in your application is properly defined with the required 
    fields.
2. Import and use AnnouncementSerializer where serialization or deserialization of Announcement 
    objects is necessary, such as in views or serializers.
3. Validate and save Announcement data using .is_valid() and .save() methods to ensure data integrity 
    and adherence to validation rules for the 'title', 'announcement_type', 'date', 'expiry_date', 
    'start_time', 'end_time', 'description', and 'attachment_doc' fields.

Note: This serializer assumes the existence of an Announcement model with appropriate fields.

Attributes:
- `Meta`: Specifies the model as Announcement and includes all fields for serialization.
- `get_status`: Method to get the status of the announcement as 'Active' or 'Inactive'.
- `get_attachment_doc`: Method to construct full URLs for attached documents.
- `validate_title`: Validates the title field.
- `validate_announcement_type`: Validates the announcement_type field.
- `validate_date`: Validates the date field.
- `validate_expiry_date`: Validates the expiry_date field.
- `validate_start_time`: Validates the start_time field.
- `validate_end_time`: Validates the end_time field.
- `validate_description`: Validates the description field.
- `validate_attachment_doc`: Validates the attachment_doc field.
- `validate`: Custom method to validate specific constraints for Announcement instances.
"""
class AnnouncementSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    attachment_doc = serializers.SerializerMethodField()
    class Meta:
        model = Announcement
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')

    def get_status(self, obj):
        return "Active" if not obj.is_deactive else "Inactive"
    
    def get_attachment_doc(self, instance):
        request = self.context.get('request')
        file_paths = instance.attachment_doc['file_paths']
        file_urls = []

        for file_path in file_paths:
            # Construct the full URL using the request and MEDIA_URL
            file_url = request.build_absolute_uri(settings.MEDIA_URL + file_path.replace('\\', '/'))
            file_urls.append(file_url)

        return {'file_paths':file_urls}
        
    def validate_title(self, value):
        if not value:
            raise serializers.ValidationError("Title is required.")
        if len(value) > 255:
            raise serializers.ValidationError("Title must be less than 255 characters.")
        return value
    
    def validate_announcement_type(self, value):
        if value not in dict(Announcement.ANNOUNCEMENT_TYPES):
            raise serializers.ValidationError("Invalid announcement type.")
        return value

    def validate_date(self, value):
        if not value:
            raise serializers.ValidationError("Date is required.")
        return value

    def validate_expiry_date(self, value):
        if not value:
            raise serializers.ValidationError("Expiry date is required.")
        return value

    def validate_start_time(self, value):
        if not value:
            raise serializers.ValidationError("Start time is required.")
        return value

    def validate_end_time(self, value):
        if not value:
            raise serializers.ValidationError("End time is required.")
        return value

    def validate_description(self, value):
        if not value:
            raise serializers.ValidationError("Description is required.")
        return value

    def validate_attachment_doc(self, value):
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Attachment document must be a JSON object.")
        return value
    
    def validate(self, data):
        if self.instance:  # For update
            if 'date' in data and data['date'] >= data.get('expiry_date', self.instance.expiry_date):
                raise serializers.ValidationError("Expiry date must be after the date.")
            if 'expiry_date' in data and data['expiry_date'] <= data.get('date', self.instance.date):
                raise serializers.ValidationError("Expiry date must be after the date.")
            if 'start_time' in data and data['start_time'] >= data.get('end_time', self.instance.end_time):
                raise serializers.ValidationError("End time must be after the start time.")
            if 'end_time' in data and data['end_time'] <= data.get('start_time', self.instance.start_time):
                raise serializers.ValidationError("End time must be after the start time.")
        else:  # For create
            if 'date' in data and 'expiry_date' in data and data['date'] >= data['expiry_date']:
                raise serializers.ValidationError("Expiry date must be after the date.")
            if 'start_time' in data and 'end_time' in data and data['start_time'] >= data['end_time']:
                raise serializers.ValidationError("End time must be after the start time.")
        return data

"""
Serializer for managing NewsLetter model instances in an application.

The NewsLetterSerializer class extends serializers.ModelSerializer to handle the serialization 
and validation of NewsLetter objects. It includes all fields of the NewsLetter model for 
serialization, designating 'created_at', 'created_by', and 'updated_at' as read-only fields to prevent 
modification through this serializer.

The serializer adds a custom 'status' field to provide a user-friendly representation of the 
NewsLetter's status based on the 'is_deactive' field.

Custom validation logic is implemented in the validate_email method to ensure that the provided email 
address, if any, is in a valid format. If the email format is invalid, a serializers.ValidationError is raised.

Usage:
1. Ensure that the NewsLetter model in your application is properly defined with the necessary fields.
2. Import and utilize NewsLetterSerializer in views, serializers, or other components where serialization 
    or deserialization of NewsLetter objects is required.
3. Validate and persist NewsLetter data using the .is_valid() and .save() methods, ensuring data integrity 
    and validation of required fields.

Note: This serializer assumes the existence of a NewsLetter model with appropriate fields.

Attributes:
- `Meta`: Defines the model as NewsLetter and includes all fields for serialization.
- `status`: A custom serializer method field to represent the active/inactive status.
- `validate_email`: Custom method to validate the email format if provided.
"""
class NewsLetterSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    class Meta:
        model = NewsLetter
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at')

    def get_status(self, obj):
        return "Active" if not obj.is_deactive else "Inactive"
    
    def validate_email(self, value):
        """
        Custom validator to check email format if provided.
        """
        if value:
            validator = EmailValidator()
            try:
                validator(value)
            except ValidationError as e:
                raise serializers.ValidationError(str(e))
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            representation.pop(field, None)
        return representation
    
class ServiceDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['service_id', 'title', 'image', 'description', 'is_deactive', 'created_at', 'modified_at', 'created_by', 'is_deleted']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            representation.pop(field, None)
        return representation
        
        
class ServiceGroupDetailSerializer(serializers.ModelSerializer):
    services=ServiceDetailSerializer(many=True,read_only=True)
    
    class Meta:
        model = ServiceGroup
        fields = ['servicegroup_id', 'group_name', 'description', 'is_deactive', 'created_at', 'modified_at', 'created_by', 'is_deleted', 'services']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            representation.pop(field, None)
        return representation
    
    
# class CodeSerializer(serializers.Serializer):
#     code = serializers.CharField(required=True)
        
        