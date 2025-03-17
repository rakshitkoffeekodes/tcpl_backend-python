import os
import random
import string
import hashlib
import binascii
import pandas as pd
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import os
import random
import string
import pandas as pd
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from xml.etree.ElementTree import Element, SubElement, tostring
import xmltodict
import json
import xml.etree.ElementTree as ET
import html
import requests
from .models import *



# def generate_random_filename(extension="xml"):
#     """Generate a random filename with the specified extension."""
#     random_name = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
#     return f"{random_name}.{extension}"



def process_excel_to_xml(blr_ids):
    try:
        # file = request.FILES.get('file')

        # if not file:
        #     return Response({"error": "File not provided."}, status=status.HTTP_400_BAD_REQUEST)

        # df = pd.read_excel(file)

        # if 'blr_id' not in df.columns:
        #     return Response({"error": "'blr_id' column not found in the uploaded file."}, status=status.HTTP_400_BAD_REQUEST)

        # blr_ids = df['blr_id'].dropna().head(1)
        root = Element('billerInfoRequest')
        # for blr_id in blr_ids:
        SubElement(root, 'billerId').text = str(blr_ids)

        xml_response = '<?xml version="1.0" encoding="UTF-8"?>' + tostring(root, encoding="unicode", method="xml").replace("\n", "").replace("\t", "").strip()

        # file_name = generate_random_filename("xml")
        # file_path = os.path.join(r"C:\Users\Hello\Desktop\txt", file_name)
        # os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # with open(file_path, 'w', encoding='utf-8') as file:
        #     file.write(xml_response)

        return xml_response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def hextobin(hex_string):
    return binascii.unhexlify(hex_string)


def pad(data, block_size):
    pad_len = block_size - len(data) % block_size
    return data + bytes([pad_len] * pad_len)

def encrypt(plain_text):
    try:
        key = "5D3FC3F011A3105AB0E4312563AD31C6"
        key = hextobin(hashlib.md5(key.encode()).hexdigest())
        init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])

        # uploaded_file = request.FILES.get('plain_text')
        # if not uploaded_file:
        #     return Response({"error": "File not provided."}, status=status.HTTP_400_BAD_REQUEST)

        # plain_text = uploaded_file.read().decode()

        cipher = AES.new(key, AES.MODE_CBC, init_vector)
        plain_text_padded = pad(plain_text.encode(), AES.block_size)
        encrypted_text = cipher.encrypt(plain_text_padded)
        encrypted_hex = binascii.hexlify(encrypted_text).decode()

        # file_name = generate_random_filename("enc")
        # file_path = os.path.join(r"C:\Users\Hello\Desktop\enc", file_name)
        # os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # with open(file_path, 'w') as file:
        #     file.write(encrypted_hex)

        return encrypted_hex

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def unpad(data, block_size):
    pad_len = data[-1]
    if pad_len > block_size:
        raise ValueError("Invalid padding")
    return data[:-pad_len]

# def save_xml(data, file_path):
#     """Save XML data to the specified file path."""
#     try:
#         tree = ET.ElementTree(data)
#         tree.write(file_path, encoding="utf-8", xml_declaration=True)
#     except Exception as e:
#         raise ValueError(f"Error saving XML file: {str(e)}")


def generate_random_filename(extension):
    import uuid
    return f"{uuid.uuid4().hex}.{extension}"

def save_xml(root, file_path):
    tree = ET.ElementTree(root)
    tree.write(file_path, encoding='utf-8', xml_declaration=True)

def decrypt(plain_text):
    try:
        # Retrieve the uploaded file
        # uploaded_file = request.FILES.get('xml_data')
        # if not uploaded_file:
        #     return Response({"error": "File not provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Read and decode the uploaded file
        encrypted_text = plain_text

        # Define the decryption key and initialization vector
        key = "5D3FC3F011A3105AB0E4312563AD31C6"
        key = hextobin(hashlib.md5(key.encode()).hexdigest())
        init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])

        # Decrypt the data
        encrypted_text_bytes = binascii.unhexlify(encrypted_text)
        cipher = AES.new(key, AES.MODE_CBC, init_vector)
        decrypted_text_padded = cipher.decrypt(encrypted_text_bytes)
        decrypted_text = unpad(decrypted_text_padded, AES.block_size).decode()

        # Parse the decrypted XML string
        decrypted_xml = ET.fromstring(decrypted_text)

        # Generate a random filename for the output file
        file_name = generate_random_filename("xml")
        file_path = os.path.join(r"C:\Users\Hello\Desktop\dec", file_name)

        # Save the XML content to the file
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as file:
            file.write(ET.tostring(decrypted_xml, encoding='utf-8', xml_declaration=True))

        # Prepare the response
        return file_name

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def convert_xml_to_json(file_name):
    try:
        # Define input file path
        input_file_path = os.path.join(r"C:\Users\Hello\Desktop\dec", file_name)
        
        # Ensure the input file exists
        if not os.path.exists(input_file_path):
            return Response({
                "error": f"The file '{file_name}' does not exist."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Read the XML file
        with open(input_file_path, "r", encoding="utf-8") as xml_file:
            xml_content = xml_file.read()

        # Convert XML to dictionary
        dict_data = xmltodict.parse(xml_content)
        
        # Convert dictionary to JSON
        json_data = json.dumps(dict_data, indent=4)

        # Define output file path
        output_file_name = generate_random_filename("json")
        output_file_path = os.path.join(r"C:\Users\Hello\Desktop\json", output_file_name)

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        # Save the JSON data to a file
        with open(output_file_path, "w", encoding="utf-8") as json_file:
            json_file.write(json_data)

        # Return success response
        return json_data

    except Exception as e:
        # Handle any exceptions and return error response
        return Response({
            "error": f"An error occurred: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def bill_fatch(xml_data):
    # File handling
    # xml_file = request.FILES.get('xml_data')
    # if not xml_file:
    #     return Response({"error": "XML file not provided."}, status=400)

    # # Reading file content
    # try:
    #     xml_data = xml_file.read()
    # except Exception as e:
    #     return Response({"error": f"Failed to read file: {str(e)}"}, status=400)

    # API details
    url = "https://api.billavenue.com/billpay/extMdmCntrl/mdmRequestNew/xml"
    params = {
        "accessCode": "AVJK31UI93YO87BWHH",
        "requestId": "TEST000MNPREQ0000000000000000000042",
        "ver": "1.0",
        "instituteId": "AC31",
    }

    try:
        # Sending request with XML data as plain text
        response = requests.post(url, params=params, data=xml_data, headers={"Content-Type": "text/plain"})
        response.raise_for_status()  # Raise an error for HTTP error responses

        # Save the response to a file
        # file_name = generate_random_filename("xml")
        # file_path = os.path.join(r"C:\Users\Hello\Desktop\apiresponse", file_name)
        # os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # with open(file_path, "w", encoding="utf-8") as file:
        #     file.write(response.text)

    except requests.exceptions.RequestException as e:
        return Response({"error": f"Request failed: {str(e)}"}, status=500)
    except Exception as e:
        return Response({"error": f"File saving error: {str(e)}"}, status=500)

    # Returning plain text response
    return response.text

@api_view(['POST'])
@permission_classes([AllowAny])
def biller(request):
    file = request.data.get('biller_id')
    try:
        xml = process_excel_to_xml(file)
        encrypt_data = encrypt(xml)
        biller_info = bill_fatch(encrypt_data)
        decrypt_data = decrypt(biller_info)
        xml_to_json = convert_xml_to_json(decrypt_data)
        BBPSBillResponse.objects.create(bbps_biller_id='VODA00000NAT96', bbps_biller_response= xml_to_json)

        return Response({'status': 'success', 'message': 'success'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)