from ipaddress import ip_address
from urllib import response
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    totp_secret = models.CharField(max_length=50, blank=True, null=True)
    verify_code = models.CharField(max_length=128, blank=True, null=True)
    verify_code_expire_at = models.DateTimeField(blank=True, null=True)
    is_verify = models.BooleanField(default=False)

    def __str__(self):
        return self.username
    
    class Meta:
        db_table  = "sa_custom_user"


class Banner(models.Model):
    banner_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    image_for_web = models.ImageField(upload_to='Banners/Web/')
    image_for_mobile = models.ImageField(upload_to='Banners/Mobile/')
    description = models.TextField()
    is_deactive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(null=True) 
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by')
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        db_table  = "web_banner"
    

class Partner(models.Model):
    partner_id = models.AutoField(primary_key=True)
    partner_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='Partners/Logos/')
    description = models.TextField()
    is_deactive = models.BooleanField(default=False)  # True for active, False for inactive
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by')
    is_deleted = models.BooleanField(default=False)


    def __str__(self):
        return self.partner_name

    class Meta:
        db_table  = "web_partner"
        

class YouTubeVideo(models.Model):
    youtubevideo_id = models.AutoField(primary_key=True)
    video_title = models.CharField(max_length=255)
    youtube_link = models.URLField()
    youtube_thumbnail_image = models.ImageField(upload_to='Youtube/Thumbnails/')
    is_deactive = models.BooleanField(default=False)  # True for active, False for inactive
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by')
    is_deleted = models.BooleanField(default=False)


    def __str__(self):
        return self.video_title

    class Meta:
        db_table  = "web_youtube_video"
        

class Testimonial(models.Model):
    PENDING = 'Pending'
    REVIEW = 'Review'
    CLOSED = 'Closed'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (REVIEW, 'Review'),
        (CLOSED, 'Closed'),
    ]
    testimonial_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    title = models.CharField(max_length=255)
    comments = models.TextField()
    status = models.CharField(max_length=7, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by')
    is_deleted = models.BooleanField(default=False)
    is_deactive = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        db_table  = "web_testimonial"
        

class AboutUs(models.Model):
    about_us_id = models.AutoField(primary_key=True)
    about_us_desc = models.TextField(null=True)
    our_focus_desc = models.TextField(null=True)
    our_mission_desc = models.TextField(null=True)
    our_vision_desc = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by')

    def __str__(self):
        return f'AboutUs Entry #{self.about_us_id}'

    class Meta:
        db_table = "web_about_us"
        

class ServiceGroup(models.Model):
    servicegroup_id = models.AutoField(primary_key=True)
    description = models.TextField(null=True)
    group_name = models.CharField(max_length=255)
    is_deactive = models.BooleanField(default=False)  # True for active, False for inactive
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by')
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.group_name
    
    class Meta:
        db_table  = "web_service_group"


class Service(models.Model):
    service_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='Services/')
    description = models.TextField()
    service_group = models.ForeignKey(ServiceGroup, on_delete=models.CASCADE, related_name='services',null=True)
    is_deactive = models.BooleanField(default=False)  # True for active, False for inactive
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by')
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    
    class Meta:
        db_table  = "web_service"


class Randomstuff(models.Model):
    randomstuff_id = models.AutoField(primary_key=True)
    privacy_policy_desc = models.TextField(null=True)
    terms_of_service_desc = models.TextField(null=True)
    cancellation_policy_desc = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by')

    def __str__(self):
        return f'RandomStuff Entry #{self.randomstuff_id}'

    class Meta:
        db_table = "web_random_stuff"


class ContactUs(models.Model):
    contactus_id = models.AutoField(primary_key=True)
    contact_no = models.CharField(max_length=20)
    address = models.TextField()
    email = models.EmailField()
    social_media_links = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, db_column='created_by')
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return "Contact Us"
       
    
    class Meta:
        db_table  = "web_contact_us"


class LoginLog(models.Model):
    loginlog_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='login_logs')
    logintime = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(null=True,max_length=255)
    browser_name = models.CharField(null=True,max_length=255)

    def __str__(self):
        return f'{self.user.username} - {self.logintime}'
    
    class Meta:
        db_table  = "sa_login_log"


class SaUserActivity(models.Model):
    ua_id = models.AutoField(primary_key=True)
    table_id = models.IntegerField()
    table_name = models.CharField(max_length=100)
    ua_action = models.CharField(max_length=100)
    ua_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True,db_column='created_by')
    request_data = models.TextField(null=True)
    response_data = models.TextField(null=True)

    def __str__(self):
        return f"{self.ua_action} on {self.table_name} at {self.created_at}"
    
    class Meta:
        db_table = "web_user_activity"
    

class ContactEnquiry(models.Model):
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Processing', 'Processing'),
        ('Resolved', 'Resolved')
    ]
    
    ce_id = models.AutoField(primary_key=True)
    ce_name = models.CharField(max_length=255)
    ce_email = models.EmailField(max_length=255)
    ce_contact_no = models.CharField(max_length=15)
    ce_subject = models.CharField(max_length=255)
    ce_message = models.TextField()
    ce_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='New')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    update_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, db_column='updated_by')
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.ce_name
    
    class Meta:
        db_table = "web_contact_enquiry"


class NewsLetter(models.Model):
    broadcast_email_id =  models.AutoField(primary_key=True)
    subscriber_name = models.CharField(max_length=250,null=True)
    email = models.EmailField(max_length=255,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True, db_column='updated_by')
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.email
    
    class Meta:
        db_table = "web_news_letter"


class SMTPConfiguration(models.Model):
    smtpconfig_id = models.AutoField(primary_key=True)
    smtp_server = models.CharField(max_length=255)
    port = models.PositiveIntegerField(blank=False, null=True)
    password = models.CharField(max_length=255)
    ENCRYPTION_CHOICES = [
        ('SSL/TLS', 'SSL/TLS'),
        ('STARTTLS', 'STARTTLS'),
    ]
    encryption_method = models.CharField(max_length=10, choices=ENCRYPTION_CHOICES)
    sender_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser, related_name='smtpconfig_created_by',on_delete=models.CASCADE,db_column='created_by')
    updated_by = models.ForeignKey(CustomUser, related_name='smtpconfig_updated_by', on_delete=models.CASCADE,null=True, db_column='updated_by')
    is_deactive = models.BooleanField(default=False)

    def __str__(self):
        return f"SMTP Configuration for {self.sender_email}"
    
    class Meta:
        db_table = "web_smtp_configuration"


class Announcement(models.Model):
    ANNOUNCEMENT_TYPES = [
        ('Service Update', 'Service Update'),
        ('Regulatory Compliance', 'Regulatory Compliance'),
        ('security Alerts', 'security Alerts'),
        ('Product Launches', 'Product Launches'),
        ('Service Interruptions','Service Interruptions'),
        ('Industry News','Industry News'),
        ('Policy Updates','Policy Updates'),
    ]

    announcement_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    announcement_type = models.CharField(max_length=50, choices=ANNOUNCEMENT_TYPES)
    date = models.DateTimeField()
    expiry_date = models.DateTimeField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField()
    attachment_doc =  models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    created_by = models.ForeignKey(CustomUser,related_name='announcement_created_by',on_delete=models.CASCADE,db_column='created_by')
    updated_by = models.ForeignKey(CustomUser, related_name='announcement_updated_by',on_delete=models.CASCADE,null=True, db_column='updated_by')
    is_deactive = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    
    class Meta:
        db_table = "web_announcement"
