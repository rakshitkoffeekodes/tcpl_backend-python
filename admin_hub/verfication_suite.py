import requests
from rest_framework import status
from django.utils.crypto import get_random_string
import base64
import json

client_id = "76034597"
client_secret = "jIzkvvBkEFvIYjde8O7lini65ghUk5Yo"

def aadhaar_verify(aadhaar_card):
    
    # Encode client_id and client_secret in Base64
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    url = "https://svc.digitap.ai/ent/v3/kyc/intiate-kyc-auto"

    unique = get_random_string(length=7, allowed_chars='0123456789')
    uniqueId = f'DTADHVF_{unique}'
    payload = {
        "uniqueId": uniqueId,
        "uid":aadhaar_card
    }
    headers = {
        "content-type": "application/json",
        "Authorization": encoded_credentials
    }

    aadhaar_response = requests.post(url, json=payload, headers=headers)
    res = aadhaar_response.json()
    if aadhaar_response.status_code == 200:

        response_data = {   'status': status.HTTP_200_OK,
                            'data': {
                                'status': 'success',
                                'message': 'OTP sent successfully',
                                'is_final': False,
                                'data': {'ref_id': res['model']}
                            }
                        }
        
    else:
        response_data = {
            'status': aadhaar_response.status_code,
            'data': res  
        }
    return response_data


def aadhaar_otp_verify(aadhaar_otp, ref_id, fwdp, codeVerifier):
    
    url = "https://svc.digitap.ai/ent/v3/kyc/submit-otp"

    payload = json.dumps({
    "transactionId": ref_id,
    "fwdp": fwdp,
    "codeVerifier": codeVerifier,
    "otp": aadhaar_otp,
    "shareCode": "1234",
    "isSendPdf": True
    })
    headers = {
        "content-type": "application/json",
        "Authorization": "NzYwMzQ1OTc6akl6a3Z2QmtFRnZJWWpkZThPN2xpbmk2NWdoVWs1WW8="
    }

    otp_response = requests.request("POST", url, headers=headers, data=payload)
    res = otp_response.json()
    if otp_response.status_code == 200:
        response_data = {   'status': status.HTTP_200_OK,
                            'data': {
                                'status': 'success',
                                'message': 'Aadhaar verified successfully',
                                'is_final': False,
                                'aadhaar_data': res,
                                
                            }
                        }
    else:
        response_data = {
            'status': otp_response.status_code,
            'data': res
        }
    return response_data


def verify_pan_card(pan_card):
    pan_url = "https://svc.digitap.ai/validation/kyc/v1/pan_details"

    pan_payload = {
        "pan": pan_card,
        "client_ref_num": get_random_string(length=10)
    }

    auth_string = f"{client_id}:{client_secret}"

    encode_auth_string = base64.b64encode(bytes(auth_string, 'utf-8')) # byte

    pan_headers = {
        "content-type": "application/json",
        "Authorization": encode_auth_string,
    }

    pan_response = requests.post(pan_url, json=pan_payload, headers=pan_headers)

    res = pan_response.json()
    if pan_response.status_code == 200:

        response_data = {   'status': status.HTTP_200_OK,
                            'data': {
                                'status': 'success',
                                'message': 'Pan verified successfully',
                                'is_final': False,
                                'data': res
                            }                            
                        }
    else:
        response_data = {
            'status': pan_response.status_code,
            'data': res
        }

    return response_data
