from django.urls import path
from .views import (
    AboutUsView, AddContactEnquiryApi, AnnouncementApiView, BannerView, NewsLetterApi, CustomuserAPIView, HomePageAboutUsApi, HomePageBannerApi, HomePagePartnerApi, HomePageRandomStuffApi, HomePageServiceGroup, HomePageServicesApi, HomePageTestimonialsApi, HomePageYoutubeVideoApi, Homepage_ServiceById, Homepage_ServiceGroup_Service, RandomstuffView, ContactUsView, LoginAPIView, 
    PartnerAPIView,RequestResetPassword, ResetPassword, SMTPConfigurationView, ServiceAPIView, ServiceGroupAPIView ,SubscribeEmailApiView
    , TestimonialView, VerifyCode, VerifyOTPView, YouTubeVideoAPIView,ContactEnquiryView
)

# Define URL patterns for the app
urlpatterns = [
    # URL pattern for user login
    path('login/', LoginAPIView.as_view(), name='login'),

    # URL pattern for OTP verification
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),

    # URL pattern for managing banners
    path('banners/', BannerView.as_view(), name='banner'),
    
    # URL pattern for managing testimonials
    path('testimonials/', TestimonialView.as_view(), name='testimonial'),

    # URL pattern for managing About Us content
    path('aboutUs/', AboutUsView.as_view(), name='aboutUs'),

    # URL pattern for managing Privacy Policy
    path('randomstuff/', RandomstuffView.as_view(), name='randomstuff'),

    # URL pattern for managing Contact Us information
    path('contactus/', ContactUsView.as_view(), name='contactus'),

    # URL pattern for managing service groups
    path('service_group/', ServiceGroupAPIView.as_view(), name='service_group'),
    
    # URL pattern for managing YouTube videos
    path('youtubevideo/', YouTubeVideoAPIView.as_view(), name='youtubevideo'),
    
    # URL pattern for managing partners
    path('partner/', PartnerAPIView.as_view(), name='partner'),
    
    # URL pattern for managing services
    path('service/', ServiceAPIView.as_view(), name='service'),
    
    # URL contact_enquiry for managing services
    path('contact_enquiry/', ContactEnquiryView.as_view(), name='contact_enquiry'),
    
    path('request_reset_password/', RequestResetPassword.as_view(), name='request-reset-code'),
    path('verify_reset_code/', VerifyCode.as_view(), name='verify-reset-code'),
    path('reset_password/', ResetPassword.as_view(), name='reset-password'),


      # URL homepage_banner for managing banner data on the homepage
    path('homepage_banner/', HomePageBannerApi.as_view(), name='homepage_banner'),

    # URL homepage_testimonials for managing testimonials data on the homepage
    path('homepage_testimonials/', HomePageTestimonialsApi.as_view(), name='homepage_testimonials'),

    # URL homepage_partner for managing partner data on the homepage
    path('homepage_partner/', HomePagePartnerApi.as_view(), name='homepage_partner'),

    # URL homepage_services for managing service data on the homepage
    path('homepage_services/', HomePageServicesApi.as_view(), name='homepage_services'),

    # URL homepage_about_us for managing About Us data on the homepage
    path('homepage_about_us/', HomePageAboutUsApi.as_view(), name='homepage_about_us'),

    # URL homepage_random_stuff for managing random stuff data on the homepage
    path('homepage_random_stuff/', HomePageRandomStuffApi.as_view(), name='homepage_random_stuff'),

    # URL homepage_contact_us for managing Contact Us data on the homepage
    # path('homepage_contact_us/', HomePageContactUsApi.as_view(), name='homepage_contact_us'),

    # URL broadcast_email for managing news_letter.
    path('news_letter/', NewsLetterApi.as_view(), name='news_letter'),

    path('subscribe_email/',SubscribeEmailApiView.as_view(), name='subscribe_email'),

    path('add_contact_enquiry/',AddContactEnquiryApi.as_view(), name='add_contact_enquiry'),

    # URL homepage_services_group for managing service group data on the homepage
    path('homepage_services_group/', HomePageServiceGroup.as_view(), name='homepage_services_group'),
    # URL for retrieving YouTube video data for the homepage
    path('homepage_youtubevideo/', HomePageYoutubeVideoApi.as_view(), name='homepage_youtubevideo'),


    # URL for SMTP configuration management
    path('smtp_configuration/', SMTPConfigurationView.as_view(), name='smtp_configuration'),
    # URL for custom user management
    path('custom_user/', CustomuserAPIView.as_view(), name='custom_user'),
    # URL for managing announcements
    path('announcement/', AnnouncementApiView.as_view(), name='announcement'),

    # URL for retrieving service data by ID
    path('homepage_service_by_id/', Homepage_ServiceById.as_view(), name='service-detail'),
    # URL for retrieving service group and service data
    path('Homepage_ServiceGroup_Service/', Homepage_ServiceGroup_Service.as_view(), name='homepage_servicegroup_service'),
     
]
 