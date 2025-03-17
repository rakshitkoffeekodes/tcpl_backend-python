from .views import *
import os
import random
import string
import hashlib
import binascii
import pandas as pd
from rest_framework.decorators import api_view
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
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from .commission_calculations import *
from .utilies import *
from rest_framework.exceptions import ValidationError
from .charges_calculation import *
from django.utils.timezone import localtime, make_aware


def unpad(data, block_size):
    pad_len = data[-1]
    if pad_len > block_size:
        raise ValueError("Invalid padding")
    return data[:-pad_len]

def hextobin(hex_string):
    return binascii.unhexlify(hex_string)


def pad(data, block_size):
    pad_len = block_size - len(data) % block_size
    return data + bytes([pad_len] * pad_len)

def generate_random_filename(extension="xml"):
    """Generate a random filename with the specified extension."""
    random_name = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{random_name}.{extension}"

# class BbpsCategoryAPIView(APIView):
#     authentication_classes = [CustomJWTAuthentication]
#     permission_classes = [IsRetailer]

#     def get(self, request):
#         get_all = BBPSBillerCategory.objects.filter(is_deleted=False, is_deactive=False)
#         bbps_category_serializer = BBPSBillerCategorySerializer(get_all, many=True)
#         return Response({'status': 'success', 'message': 'get all bbps category', 'data': bbps_category_serializer.data}, status=status.HTTP_200_OK)
    

# class BbpsBillerListAPIView(APIView):
#     authentication_classes = [CustomJWTAuthentication]
#     permission_classes = [IsRetailer]

#     def post(self, request):
#         if 'page_size' in request.data or 'page_number' in request.data:
#             return self.get_bbps_biller_list(request)
#         else:
#             return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)
    
#     def get_bbps_biller_list(self, request):
#         page_size = request.data.get('page_size', 10)
#         page_number = request.data.get('page_number', 1)
#         category_id = request.data.get('category_id', None)
#         search = request.data.get('search', None)
#         biller_id = request.data.get('biller_id', None)
#         page_size = int(page_size)
#         page_number = int(page_number)

#         if not page_size: return Response({'status': 'fail','message': 'page_size is required.'}, status=status.HTTP_400_BAD_REQUEST)

#         if not isnumber(page_size): return Response({'status': 'fail','message': 'page_size must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
#         if not isnumber(page_number): return Response({'status': 'fail','message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)

#         try:
            
#             biller_list = BBPSBiller.objects.filter(is_deleted=False, is_deactive=False)
            
#             if category_id:
#                 if not isnumber(category_id): return Response({'status': 'fail','message': 'category_id must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
#                 biller_list = biller_list.filter(bbps_category__bbps_id=category_id)
            
#             if search:
#                 biller_list = biller_list.filter(Q(bbps_blr_name__icontains=search) | Q(bbps_blr_id__icontains=search))

#             if biller_id:
#                 biller_list = biller_list.filter(bbps_blr_id=biller_id)

#             start_index = (page_number - 1) * page_size
#             end_index = start_index + page_size
#             paginated_biller = biller_list[start_index:end_index]
#             total_items = biller_list.count()
#             total_pages = (len(biller_list) + page_size - 1) // page_size
#             serializer = BBPSBillerSerializer(paginated_biller, many=True)
#             data = {
#                 'total_pages': total_pages,
#                 'current_page': page_number,
#                 'total_items': total_items,
#                 'results': serializer.data
#             }

#             return Response({'status': 'success', 'message': 'get bbps biller list', 'data': data}, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class ProcessExcelToXml(APIView):
#     authentication_classes = []
#     permission_classes = []
#     def post(self, request):
#         try:
#             file = request.FILES.get('file')

#             if not file:
#                 return Response({"error": "File not provided."}, status=status.HTTP_400_BAD_REQUEST)

#             df = pd.read_excel(file)

#             if 'blr_id' not in df.columns:
#                 return Response({"error": "'blr_id' column not found in the uploaded file."}, status=status.HTTP_400_BAD_REQUEST)

#             blr_ids = df['blr_id'].dropna().head(1)

#             root = Element('billerInfoRequest')
#             for blr_id in blr_ids:
#                 SubElement(root, 'billerId').text = str(blr_id)

#             xml_response = '<?xml version="1.0" encoding="UTF-8"?>' + tostring(root, encoding="unicode", method="xml").replace("\n", "").replace("\t", "").strip()

#             print("xml_response---->>>",xml_response)
#             # Save XML file
#             file_name = generate_random_filename("xml")
#             file_path = os.path.join(r"C:\Users\Hello\Desktop\txt", file_name)
#             os.makedirs(os.path.dirname(file_path), exist_ok=True)
#             with open(file_path, 'w', encoding='utf-8') as file:
#                 file.write(xml_response)

#             return Response({"message": "XML file created successfully.", "file_name": file_name}, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EncryptData(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        try:
            key = "5D3FC3F011A3105AB0E4312563AD31C6"
            key = hextobin(hashlib.md5(key.encode()).hexdigest())
            init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])

            plain_text = request.data.get('plain_text')
            # if not uploaded_file:
            #     return Response({"error": "File not provided."}, status=status.HTTP_400_BAD_REQUEST)

            # plain_text = uploaded_file.read().decode()

            cipher = AES.new(key, AES.MODE_CBC, init_vector)
            plain_text_padded = pad(plain_text.encode(), AES.block_size)
            encrypted_text = cipher.encrypt(plain_text_padded)
            encrypted_hex = binascii.hexlify(encrypted_text).decode()

            storage_path = getattr(settings, 'ENCRYPTED_FILES_DIR', './encrypted_files/')
            os.makedirs(storage_path, exist_ok=True)

            file_name = generate_random_filename("enc")
            file_path = os.path.join(storage_path, file_name)
            with open(file_path, 'w') as file:
                file.write(encrypted_hex)

            return Response({"message": "File encrypted and saved successfully.", "file_name": file_name}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# def save_xml(data, file_path):
#     """Save XML data to the specified file path."""
#     try:
#         tree = ET.ElementTree(data)
#         tree.write(file_path, encoding="utf-8", xml_declaration=True)
#     except Exception as e:
#         raise ValueError(f"Error saving XML file: {str(e)}")


# class DecryptData(APIView):
#     authentication_classes = []
#     permission_classes = []
#     def post(slef, request):
#         try:
#             # Retrieve the uploaded file
#             uploaded_file = request.data.get('plain_text')
#             if not uploaded_file:
#                 return Response({"error": "File not provided."}, status=status.HTTP_400_BAD_REQUEST)

#             # Read and decode the uploaded file
#             encrypted_text = uploaded_file

#             # Define the decryption key and initialization vector
#             key = "5D3FC3F011A3105AB0E4312563AD31C6"
#             key = hextobin(hashlib.md5(key.encode()).hexdigest())
#             init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])

#             # Decrypt the data
#             encrypted_text_bytes = binascii.unhexlify(encrypted_text)
#             cipher = AES.new(key, AES.MODE_CBC, init_vector)
#             decrypted_text_padded = cipher.decrypt(encrypted_text_bytes)
#             decrypted_text = unpad(decrypted_text_padded, AES.block_size).decode()

#             decrypted_xml = ET.fromstring(decrypted_text)

#             storage_path = getattr(settings, 'DECRYPTED_FILES_DIR', './decrypted_files/')
#             os.makedirs(storage_path, exist_ok=True)

#             file_name = generate_random_filename("dec")
#             file_path = os.path.join(storage_path, file_name)
#             with open(file_path, 'wb') as file:
#                 file.write(ET.tostring(decrypted_xml, encoding='utf-8', xml_declaration=True))

#             return Response({
#                 "message": "File decrypted and saved successfully.",
#                 "file_name": file_name,
#                 "decrypted_data": ET.tostring(decrypted_xml, encoding='utf-8', xml_declaration=True).decode()
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConvertXmlToJson(APIView):
    permission_classes = []
    authentication_classes = []
    
    def post(self, request):
        xml_file = request.FILES.get('xml_data')
        try:
            # Parse the XML file
            xml_content = xml_file.read()  # Read the file's content
            dict_data = xmltodict.parse(xml_content)  # Convert XML to dictionary

            # Convert dictionary to JSON
            json_data = json.dumps(dict_data, indent=4)

            # Define file path for saving JSON
            storage_path = getattr(settings, 'JSON_FILES_DIR', './json_files/')
            os.makedirs(storage_path, exist_ok=True)

            file_name = generate_random_filename("json")
            file_path = os.path.join(storage_path, file_name)

            # Save the JSON data to a file
            with open(file_path, "w", encoding="utf-8") as json_file:
                json_file.write(json_data)
            json_data_data = json.loads(json_data)
            return Response({
                "message": "XML data converted to JSON successfully.",
                "json_data": json_data_data,
                # "file_path": file_path
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class BillFetch(APIView):
#     authentication_classes = []
#     permission_classes = []
#     def post(self,request):
#         # File handling
#         xml_file = request.data.get('xml_data')
#         if not xml_file:
#             return Response({"error": "XML file not provided."}, status=400)

#         # Reading file content
#         try:
#             xml_data = xml_file.read()
#         except Exception as e:
#             return Response({"error": f"Failed to read file: {str(e)}"}, status=400)

#         # API details
        # url = "https://api.billavenue.com/billpay/extBillCntrl/billFetchRequest/xml"
        # params = {
        #     "accessCode": "AVJK31UI93YO87BWHH",
        #     "requestId": "TEST000MNPREQ0000000000000000000042",
        #     "ver": "1.0",
        #     "instituteId": "AC31",
        # }

#         try:
#             # Sending request with XML data as plain text
#             response = requests.post(url, params=params, data=xml_data, headers={"Content-Type": "text/plain"})
#             response.raise_for_status()  # Raise an error for HTTP error responses

#             # Save the response to a file
#             storage_path = getattr(settings, 'BILL_FATCHED_FILES_DIR', './bill_fatched_files/')
#             os.makedirs(storage_path, exist_ok=True)

#             file_name = generate_random_filename("xml")
#             file_path = os.path.join(storage_path, file_name)

#             with open(file_path, "w", encoding="utf-8") as file:
#                 file.write(response.text)

        # except requests.exceptions.RequestException as e:
        #     return Response({"error": f"Request failed: {str(e)}"}, status=500)
#         except Exception as e:
#             return Response({"error": f"File saving error: {str(e)}"}, status=500)

#         # Returning plain text response
#         return Response(response.text, content_type="text/plain", status=response.status_code)


# class BbpsBillerEntryAPIView(APIView):
#     authentication_classes = []
#     permission_classes = []

#     def post(self, request):
#         file = request.FILES.get('file')

#         if not file:
#             return Response({"error": "File not provided."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             df = pd.read_excel(file, engine='openpyxl')
#         except Exception as e:
#             return Response({"error": f"Error reading Excel file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

#         if 'blr_id' not in df.columns:
#             return Response({"error": "Column 'blr_id' not found in the Excel file."}, status=status.HTTP_400_BAD_REQUEST)

#         blr_ids = df['blr_id'].dropna()
#         total_blr_ids = len(blr_ids)

#         if total_blr_ids == 0:
#             return Response({"error": "No valid 'blr_id' values found in the file."}, status=status.HTTP_400_BAD_REQUEST)

#         chunk_size = 2000
#         chunks = [blr_ids[i:i + chunk_size].tolist() for i in range(0, total_blr_ids, chunk_size)]

#         # Ensure the API URL is correct
#         api_url = "https://api.billavenue.com/billpay/extBillCntrl/billFetchRequest/xml"
#         api_params = {
#             "accessCode": "AVJK31UI93YO87BWHH",
#             "requestId": "TEST000MNPREQ0000000000000000001656",
#             "ver": "1.0",
#             "instituteId": "AC31",
#         }

#         xml_response_list = []
#         try:
#             for chunk in chunks:
#                 root = Element('billerInfoRequest')
#                 for blr_id in chunk:
#                     SubElement(root, 'billerId').text = str(blr_id)

#                 xml_data = '<?xml version="1.0" encoding="UTF-8"?>' + tostring(
#                     root, encoding="unicode", method="xml"
#                 ).replace("\n", "").replace("\t", "").strip()

#                 # Log the outgoing request for debugging
#                 print(f"Sending request to {api_url} with params: {api_params} and XML: {xml_data}")

#                 response = requests.post(api_url, params=api_params, data=xml_data, headers={"Content-Type": "text/plain"})

#                 # Log the response for debugging
#                 print(f"Response status: {response.status_code}, Response text: {response.text}")

#                 if response.status_code == 200:
#                     json_data = xmltodict.parse(response.text)
#                     xml_response_list.append(json_data)

#                     # Save to the database
#                     for data in json_data.get('billerInfoResponse', {}).get('biller', []):
#                         BBPSBillResponse.objects.create(
#                             bbps_biller_id=data['billerId'],
#                             bbps_biller_response=json.dumps(data)
#                         )
#                 else:
#                     return Response(
#                         {"error": f"Request failed with status code {response.status_code}: {response.text}"},
#                         status=status.HTTP_500_INTERNAL_SERVER_ERROR
#                     )

#         except requests.exceptions.RequestException as e:
#             return Response({"error": f"Request failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         return Response(
#             {
#                 'total_blr_ids': total_blr_ids,
#                 'chunks_processed': len(chunks),
#                 'responses': xml_response_list
#             },
#             status=status.HTTP_200_OK
#         )


class BbpsBillerAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsRetailer]

    def post(self, request):
        if 'is_categorey' in request.data and 'page_number' in request.data and 'page_size' in request.data:
            return self.get_bbps_biller_category(request)
        elif 'category_id' in request.data and 'page_number' in request.data and 'page_size' in request.data:
            return self.get_bbps_biller_list(request)
        elif 'blr_id' in request.data and 'page_number' in request.data and 'page_size' in request.data:
            return self.get_bbps_biller_details(request)
        elif 'blr_id' in request.data and 'blr_request_id' in request.data and 'blr_payment_request_data' in request.data:
            return self.bill_payment(request)
        elif 'blr_id' in request.data and 'blr_request_data':
            return self.fetch_biller_request(request)
        elif 'request_id' in request.data and 'page_number' in request.data and 'page_size' in request.data:
            return self.update_bbps_biller_status(request)
        elif 'page_number' in request.data or 'page_size' in request.data and 'transaction_data' in request.data:
            return self.get_bbps_biller_transaction_list(request)
        else:
            return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)
        
    def encrypt_data(self, xml_data):
        try:
            key = "5D3FC3F011A3105AB0E4312563AD31C6"
            key = hextobin(hashlib.md5(key.encode()).hexdigest())
            init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])


            cipher = AES.new(key, AES.MODE_CBC, init_vector)
            plain_text_padded = pad(xml_data.encode(), AES.block_size)
            encrypted_text = cipher.encrypt(plain_text_padded)
            encrypted_hex = binascii.hexlify(encrypted_text).decode()

            return encrypted_hex

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def decrypt_data(self, string_data):
        try:
            encrypted_text = string_data
            # Define the decryption key and initialization vector
            key = "5D3FC3F011A3105AB0E4312563AD31C6"
            key = hextobin(hashlib.md5(key.encode()).hexdigest())
            init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])

            # Decrypt the data
            encrypted_text_bytes = binascii.unhexlify(encrypted_text)
            cipher = AES.new(key, AES.MODE_CBC, init_vector)
            decrypted_text_padded = cipher.decrypt(encrypted_text_bytes)
            decrypted_text = unpad(decrypted_text_padded, AES.block_size).decode()
            decrypted_xml = ET.fromstring(decrypted_text)

            storage_path = getattr(settings, 'DECRYPTED_FILES_DIR', './decrypted_files/')
            os.makedirs(storage_path, exist_ok=True)

            file_name = generate_random_filename("dec")
            file_path = os.path.join(storage_path, file_name)
            with open(file_path, 'wb') as file:
                file.write(ET.tostring(decrypted_xml, encoding='utf-8', xml_declaration=True))
            
            xml = ET.tostring(decrypted_xml, encoding='utf-8', xml_declaration=True)

            return xml

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def xml_to_json(self, xml_data):
        try:

            # Convert XML to dictionary
            dict_data = xmltodict.parse(xml_data)
            
            # Convert dictionary to JSON
            json_data = json.dumps(dict_data, indent=4)

            # Return success response
            return json_data

        except Exception as e:
            # Handle any exceptions and return error response
            return Response({
                "error": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
         
    def generate_reference_id(self):
        random_chars = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=27))

        now = datetime.now()

        year_last_digit = str(now.year)[-1]
        day_of_year = f"{now.timetuple().tm_yday:03d}"
        hour = f"{now.hour:02d}"
        minute = f"{now.minute:02d}"

        julian_suffix = f"{year_last_digit}{day_of_year}{hour}{minute}"

        reference_id = random_chars + julian_suffix
        return reference_id    
    
    def get_bbps_biller_category(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        search = request.data.get('search', '')
        try:
            all_categories = BBPSBillerCategory.objects.filter(is_deleted=False, is_deactive=False)
            if search != '':
                all_categories=all_categories.filter(ss_name__icontains=search)
            serializer = BBPSBillerCategorySerializer(all_categories, many=True)
            data = {
                'results': serializer.data
            }
            return Response({'status': 'success', 'message': 'get all bbps category','data': data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_bbps_biller_list(self, request):
        category_id = request.data.get('category_id')

        try:
            # Use filter() to retrieve multiple records 
            fetch_info = BBPSBiller.objects.filter(bbps_category__ss_id=category_id, is_deleted=False, is_deactive=False)

            if not fetch_info.exists():
                return Response({'status': 'fail', 'message': 'Biller not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Serialize the queryset
            serializer = BBPSBillerSerializer(fetch_info, many=True)
            data = {
                'results': serializer.data
            }
            return Response({'status': 'success', 'data': data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'status': 'fail', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
     
    def get_bbps_biller_details(self, request):
        blr_id = request.data.get('blr_id')
        try:
            bbps_biller_details = BBPSBillResponse.objects.get(bbps_biller_id=blr_id)
            bbps_category = BBPSBiller.objects.get(bbps_blr_id=blr_id)
            serializer = BBPSBillerResponseSerializer(bbps_biller_details)
            json_data = json.loads(serializer.data.get('bbps_biller_response'))
            if type(json_data.get('billerInputParams').get("paramInfo")) == list:
                list_data = json_data.get('billerInputParams').get("paramInfo")
            else:
                list_data = [json_data.get('billerInputParams').get("paramInfo")]
            biller_adhoc = json_data.get('billerAdhoc')
            split_mode = json_data.get('billerPaymentModes').replace(' ', '').split(',')
            if 'Cash' in split_mode:
                channel_info = json_data.get('billerPaymentChannels').get('paymentChannelInfo') 
                for info in channel_info:
                    if info.get('paymentChannelName') == 'INT':
                        minimum = info.get('minAmount')
                        if bbps_category.bbps_category.ss_name == 'Credit Card':
                            maximum = '49999'
                            biller_adhoc = False
                        else:
                            maximum = info.get('maxAmount')
                data = {'results': {'billerInfoResponse':list_data,
                        'billerId': json_data.get('billerId'), 'billerAdhoc': biller_adhoc, 'min': minimum, 'max': maximum, 'cash': True}} #===json_data.get('billerAdhoc') change billerAdhoc and Adhoc False editable
            else:
                data = {'results': {'billerInfoResponse':list_data,
                        'billerId': json_data.get('billerId'), 'billerAdhoc': biller_adhoc, 'cash': False}}
            return Response({'status': 'success', 'message': 'Get bbps biller details','data': data}, status=status.HTTP_200_OK)
        except BBPSBiller.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Biller not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'fail', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
    def fetch_biller_request(self, request):
        blr_id = request.data.get('blr_id')
        contact_number = request.data.get('contact_no')
        blr_request_data = request.data.get('blr_request_data')
        sp_id=request.data.get('sp_id')
        accessCode = ''
        instituteId = ''
        try:
            convert_blr_request_data = json.loads(blr_request_data)
            print('convert_blr_request_data', convert_blr_request_data)
            # Root element
            root = ET.Element("billFetchRequest")

            # Static data
            agent_id = ET.SubElement(root, "agentId")
            agent_id.text = "CC01AC31AGTU00000006"

            agent_device_info = ET.SubElement(root, "agentDeviceInfo")
            ip = ET.SubElement(agent_device_info, "ip")
            ip.text = "110.227.212.120"

            init_channel = ET.SubElement(agent_device_info, "initChannel")
            init_channel.text = "AGT"

            mac = ET.SubElement(agent_device_info, "mac")
            mac.text = "94-BB-43-F0-FB-C8"

            customer_info = ET.SubElement(root, "customerInfo")
            customer_mobile = ET.SubElement(customer_info, "customerMobile")
            customer_mobile.text = contact_number

            customer_email = ET.SubElement(customer_info, "customerEmail")
            customer_email.text = ""

            customer_adhaar = ET.SubElement(customer_info, "customerAdhaar")
            customer_adhaar.text = ""

            customer_pan = ET.SubElement(customer_info, "customerPan")
            customer_pan.text = ""

            biller_id = ET.SubElement(root, "billerId")
            biller_id.text = blr_id

            # Dynamic input parameters
            input_params = ET.SubElement(root, "inputParams")
            for param in convert_blr_request_data:
                input_element = ET.SubElement(input_params, "input")

                param_name = ET.SubElement(input_element, "paramName")
                param_name.text = param.get("paramName", "")

                param_value = ET.SubElement(input_element, "paramValue")
                param_value.text = param.get("paramValue", "")

            # Convert to string
            xml_data = ET.tostring(root, encoding="unicode")
            print('xml_data', xml_data)
            encrypted_data = self.encrypt_data(xml_data)
            request_id = self.generate_reference_id()

            url = "https://api.billavenue.com/billpay/extBillCntrl/billFetchRequest/xml"

            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                accessCode = sp.credentials_json.get('accessCode')
                instituteId = sp.credentials_json.get('instituteId')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                accessCode = service_provider.credentials_json.get('accessCode')
                instituteId = service_provider.credentials_json.get('instituteId')
            print('accessCode', accessCode)
            parems = {
                'accessCode': accessCode,
                # 'accessCode': 'AVJK31UI93YO87BWHH',
                'requestId': request_id,
                'ver': '1.0',
                'instituteId': instituteId,
                # 'instituteId': 'AC31',
                'encRequest': encrypted_data
            }

            response = requests.post(url, params=parems)
            decrypt_data = self.decrypt_data(response.text) 
            xml_to_json = self.xml_to_json(decrypt_data)
            json_data = json.loads(xml_to_json)
            print('json_data', json_data)
            if response.status_code == 200:
                print('json_data', json_data)
                if json_data.get("billFetchResponse").get("responseCode") == "000":
                    bill_payment = BBPSBillPayment.objects.create(
                        bbps_request_id=request_id,
                        bbps_bill_fetch_response=json_data,
                        bbps_contact_no=contact_number,
                        bbps_blr_id=blr_id,
                        created_by=request.user.id
                    )
                    data = {'results':{'bill_request_id': request_id, 'bill_request_resposne': json_data}}
                    user_activity = {
                        "table_id": bill_payment.pk,
                        "table_name": 'ad_bbps_bill_payment',
                        "ua_action": 'Create',  # Action performed
                        "ua_description": 'Bill Fetch Request successfully.',  # Action description
                        "created_by": request.user,  # Current user performing the action
                        "request_data": dict(request.data),  # Request data
                        "response_data": model_to_dict(bill_payment)
                    }

                    add_user_activity(user_activity)
                    return Response({'status': 'success', 'message': 'Get Biller Fetch Request','data': data}, status=status.HTTP_200_OK)
                else:
                    print('json_data', json_data)
                    message = json_data.get("billFetchResponse").get("errorInfo").get("error").get("errorMessage")
                    return Response({'status': 'fail', 'message': message}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({'status': 'fail', 'message': response.text, 'data': json_data}, status=status.HTTP_400_BAD_REQUEST)

        except json.JSONDecodeError:
            return Response({"status": "fail", "message": "blr_request_data must be valid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'fail', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
    def bill_payment(self, request):
        blr_id = request.data.get('blr_id')
        contact_no = request.data.get('contact_no')
        amount = request.data.get('amount')
        formatted_amount = "{:.2f}".format(float(amount)/100)
        blr_request_id = request.data.get('blr_request_id')
        sp_id = request.data.get('sp_id')
        blr_payment_request_data = request.data.get('blr_payment_request_data')
        accessCode = ''
        instituteId = ''
    
        try:
            # admin_wallet = check_admin_wallet(request, formatted_amount) 

            # retailer_wallet = check_retailer_wallet(request, formatted_amount, request.user.id)
            
            if not float(PortalUserWallet.objects.get(pu_id=1).main_wallet) > 0.00 and not float(PortalUserWallet.objects.get(pu_id=1).main_wallet) > float(amount):
                return Response({'status': 'success', 'message': 'Admin wallet has insufficient balance'}, status=status.HTTP_200_OK)
            if not float(PortalUserWallet.objects.get(pu_id=request.user.id).main_wallet) > 0.00 and not float(PortalUserWallet.objects.get(pu_id=request.user.id).main_wallet) > float(amount):
                return Response({'status': 'success', 'message': 'User wallet has insufficient balance'}, status=status.HTTP_200_OK)

            biller = BBPSBillPayment.objects.get(bbps_request_id=blr_request_id , bbps_contact_no=contact_no)
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            additional_info_data = None
            biller_response_data = biller.bbps_bill_fetch_response.get('billFetchResponse').get('billerResponse')
            if biller.bbps_bill_fetch_response.get('billFetchResponse').get('additionalInfo'):
                additional_info_data = biller.bbps_bill_fetch_response.get('billFetchResponse').get('additionalInfo').get('info')
                print('additional_info_data', additional_info_data)
            convert_blr_payment_request_data = json.loads(blr_payment_request_data)

            # Root element
            root = ET.Element("billPaymentRequest")

            # Static data
            agent_id = ET.SubElement(root, "agentId")
            agent_id.text = "CC01AC31AGTU00000006"

            biller_adhoc = ET.SubElement(root, "billerAdhoc")
            biller_adhoc.text = "false"

            agent_device_info = ET.SubElement(root, "agentDeviceInfo")
            ip = ET.SubElement(agent_device_info, "ip")
            ip.text = "110.227.212.120"

            init_channel = ET.SubElement(agent_device_info, "initChannel")
            init_channel.text = "AGT"

            mac = ET.SubElement(agent_device_info, "mac")
            mac.text = "94-BB-43-F0-FB-C8"

            # Customer Info (static for now)
            customer_info = ET.SubElement(root, "customerInfo")
            customer_mobile = ET.SubElement(customer_info, "customerMobile")
            customer_mobile.text = contact_no
            customer_email = ET.SubElement(customer_info, "customerEmail")
            customer_email.text = ""
            customer_adhaar = ET.SubElement(customer_info, "customerAdhaar")
            customer_adhaar.text = ""
            customer_pan = ET.SubElement(customer_info, "customerPan")
            customer_pan.text = ""

            biller_id = ET.SubElement(root, "billerId")
            biller_id.text = blr_id

            # Dynamic input parameters
            input_params = ET.SubElement(root, "inputParams")
            for param in convert_blr_payment_request_data:
                input_element = ET.SubElement(input_params, "input")

                param_name = ET.SubElement(input_element, "paramName")
                param_name.text = param.get("paramName", "")

                param_value = ET.SubElement(input_element, "paramValue")
                param_value.text = param.get("paramValue", "")

            # Dynamic biller response
            biller_response = ET.SubElement(root, "billerResponse")
            for key, value in biller_response_data.items():
                response_element = ET.SubElement(biller_response, key)
                response_element.text = str(value)

             # dict object declaration
            check_obj = {}

            # Conditional additional info
            if additional_info_data:
                if type(additional_info_data) == type(check_obj):
                    additional_info_data = [additional_info_data]
                
                additional_info = ET.SubElement(root, "additionalInfo")
                
                for info in additional_info_data:
                    info_element = ET.SubElement(additional_info, "info")
                    info_name = ET.SubElement(info_element, "infoName")
                    info_name.text = info.get("infoName", "")
                    info_value = ET.SubElement(info_element, "infoValue")
                    info_value.text = info.get("infoValue", "")

            # Amount Info (static for now)
            amount_info = ET.SubElement(root, "amountInfo")

            # Use a different variable name for the XML element
            amount_element = ET.SubElement(amount_info, "amount")
            amount_element.text = amount  # Set the value fetched from request.data

            currency = ET.SubElement(amount_info, "currency")
            currency.text = "356"

            cust_conv_fee = ET.SubElement(amount_info, "custConvFee")
            cust_conv_fee.text = "0"

            amount_tags = ET.SubElement(amount_info, "amountTags")
            amount_tags.text = ""

            # Payment Method (static for now)
            payment_method = ET.SubElement(root, "paymentMethod")
            payment_mode = ET.SubElement(payment_method, "paymentMode")
            payment_mode.text = "Cash"
            quick_pay = ET.SubElement(payment_method, "quickPay")
            quick_pay.text = "N"
            split_pay = ET.SubElement(payment_method, "splitPay")
            split_pay.text = "N"

            # Payment Info (static for now)
            payment_info = ET.SubElement(root, "paymentInfo")
            payment_info_entry = ET.SubElement(payment_info, "info")
            info_name = ET.SubElement(payment_info_entry, "infoName")
            info_name.text = "Remarks"
            info_value = ET.SubElement(payment_info_entry, "infoValue")
            info_value.text = "Received"

            # Convert to string
            xml_data = ET.tostring(root, encoding="unicode")
            encrypted_data = self.encrypt_data(xml_data)

            url = "https://api.billavenue.com/billpay/extBillPayCntrl/billPayRequest/xml"

            if sp.is_self_config == True:
                instituteId = sp.credentials_json.get('instituteId')
                accessCode = sp.credentials_json.get('accessCode')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                instituteId = service_provider.credentials_json.get('instituteId')
                accessCode = service_provider.credentials_json.get('accessCode')

            parems = {
                'accessCode': accessCode,
                # 'accessCode': 'AVJK31UI93YO87BWHH',
                'requestId': blr_request_id,
                'ver': '1.0',
                'instituteId': instituteId,
                # 'instituteId': 'AC31',
                'encRequest': encrypted_data
            }

            response = requests.post(url, params=parems)
            decrypt_data = self.decrypt_data(response.text)
            
            xml_to_json = self.xml_to_json(decrypt_data)
            xml = json.loads(xml_to_json)
            print('----------------------', xml)
            if response.status_code == 200:
                print('======================')
                if xml.get('ExtBillPayResponse').get('responseCode') == "000":
                    print('-==========-===-=-=-=-=')
                    formatted_amount = "{:.2f}".format(float(amount)/100)
                    
                    biller.bbps_payment_response = xml
                    biller.updated_at = datetime.now()
                    biller.bbps_amount = formatted_amount
                    biller.bbps_sp = sp
                    biller.bbps_status = 'SUCCESS'
                    biller.save()
                    print('----==================')
                    category = BBPSBiller.objects.filter(bbps_blr_id=blr_id).first()
                    
                    service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
                    
                    gst_rate = service_provider.hsn_sac.tax_rate
                    admin_charges = None 
                
                    # fetch admin charges
                    admin_charge_queryset = AdCharges.objects.filter(service_provider_id=sp_id)

                    if admin_charge_queryset.exists():  # Ensure queryset is not empty
                        for charge in admin_charge_queryset:
                            if charge.minimum <= float(transaction_data.pp_amount) <= charge.maximum:
                                admin_charges = charge  # Assign matching charge
                                break  # Exit loop early if a match is found

                        # If no specific charge matched, assign the first one
                        if admin_charges is None:
                            admin_charges = admin_charge_queryset.first()

                    # Ensure admin_charges is valid before accessing attributes
                    if admin_charges:
                        admin_rate = admin_charges.rate
                        admin_rate_type = admin_charges.rate_type
                        admin_charges_type = admin_charges.charges_type
                    else:
                        admin_rate = 0  # Set default values to avoid errors
                        admin_rate_type = None
                        admin_charges_type = None
                    
                    char_comm_amt = float(formatted_amount) * (admin_rate / 100) if admin_rate_type == 'is_percent' else admin_rate
                    admin_tax_amt = float(char_comm_amt) - (float(char_comm_amt)/(1+(float(gst_rate)/100)))
                    
                    portal_user_details = PortalUserDetails.objects.get(pu_id=request.user.id)
                    
                    data = {
                        "service_id": biller.pk,
                        "amount": formatted_amount,
                        "table_name": "ad_bbps_bill_payment",
                        "wl_label": f"BBPS_by_{portal_user_details.pud_unique_id}_of_amount_{formatted_amount}_with_tx_id_{biller.bbps_request_id}",
                        "gst_rate": gst_rate,
                        "admin_tax_amt": admin_tax_amt,
                        "char_comm_amt": char_comm_amt,
                        "admin_charges_type": admin_charges_type,
                        "sp_id": sp_id,
                        "contact_number": contact_no,
                        "name": None,
                        "response_data": xml,
                        "label": service_provider.label,
                        "category": category.bbps_category.ss_id,
                        "is_self_config": service_provider.is_self_config
                    }
                    print('data', data)
                    charges_calculation_function(request, data)

                    # # for retailer
                    # rt_gl = GlTrn.objects.create(
                    #     service_trn_id=biller.pk,
                    #     pu_id=request.user.id,
                    #     gl_trn_amt=formatted_amount,
                    #     effectvie_wallet='main_wallet',
                    #     effectvie_amt=formatted_amount,
                    #     service_trn_table='ad_bbps_service_trnasaction',
                    #     effective_type='DR',
                    #     gl_trn_dt=now(),
                    # )

                    # WalletTrn.objects.create(
                    #     action_id=rt_gl.pk,
                    #     action_type='Order',
                    #     pu_id=request.user.id,
                    #     wl_label=f"BBPS_by_{portal_user_details.pud_unique_id}_of_amount_{formatted_amount}_with_tx_id_{biller.bbps_request_id}",
                    #     effectvie_wallet='main_wallet',
                    #     effectvie_amt=formatted_amount,
                    #     effective_type='DR',
                    #     wl_trn_dt=now()
                    # )

                    # rtl_wallet = PortalUserWallet.objects.get(pu_id=request.user.id)
                    # rtl_wallet.main_wallet = float(rtl_wallet.main_wallet) - float(formatted_amount)
                    # rtl_wallet.updated_at = now()
                    # rtl_wallet.save()

                    # # for admin
                    # if sp.is_self_config==True:
                    #     service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
                    #     plateform_fee = service_provider.plateform_fee
                    #     plateform_fee_type = service_provider.plateform_fee_type
                    #     tax_rate = service_provider.hsn_sac.tax_rate
                    #     rate_amount = formatted_amount * (plateform_fee / 100) if plateform_fee_type == 'is_percent' else plateform_fee                      
                    #     gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(tax_rate)/100)))

                    #     admin_amount = rate_amount
                    # else:
                    #     gst_amount=formatted_amount
                    #     admin_amount=formatted_amount

                    # admin_gl = GlTrn.objects.create(
                    #     service_trn_id=biller.pk,
                    #     pu_id=1,
                    #     gl_tax_rate=tax_rate if tax_rate else None,
                    #     gl_tax_amt=gst_amount if tax_rate else None,
                    #     gl_trn_amt=admin_amount,
                    #     effectvie_wallet='main_wallet',
                    #     effectvie_amt=admin_amount,
                    #     service_trn_table='ad_bbps_service_trnasaction',
                    #     effective_type='DR',
                    #     gl_trn_dt=now(),
                    # )

                    # WalletTrn.objects.create(
                    #     action_id=admin_gl.pk,
                    #     action_type='Order',
                    #     pu_id=1,
                    #     wl_label=f"BBPS_by_{portal_user_details.pud_unique_id}_of_amount_{admin_amount}_with_tx_id_{biller.bbps_request_id}",
                    #     effectvie_wallet='main_wallet',
                    #     effectvie_amt=admin_amount,
                    #     effective_type='DR',
                    #     wl_trn_dt=now()
                    # )
                    
                    # admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                    # admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(admin_amount)
                    # admin_wallet.updated_at = now()
                    # admin_wallet.save()
                    

                    # if sp.is_self_config == False:
                    #     admin_gl = GlTrn.objects.create(
                    #         service_trn_id=biller.pk,
                    #         pu_id=1,
                    #         gl_tax_rate=gst_rate,
                    #         gl_tax_amt=admin_tax_amt,
                    #         gl_trn_amt=formatted_amount,
                    #         effectvie_wallet='main_wallet',
                    #         effectvie_amt=char_comm_amt,
                    #         service_trn_table='ad_bbps_service_trnasaction',
                    #         effective_type=admin_charges_type,
                    #         gl_trn_dt=now(),
                    #     )

                    #     WalletTrn.objects.create(
                    #         action_id=biller.pk,
                    #         action_type='Order',
                    #         pu_id=1,
                    #         wl_label=f"BBPS_by_{portal_user_details.pud_unique_id}_of_amount_{formatted_amount}_with_tx_id_{biller.bbps_request_id}",
                    #         effectvie_wallet='main_wallet',
                    #         effectvie_amt=char_comm_amt,
                    #         effective_type=admin_charges_type,
                    #         wl_trn_dt=now()
                    #     )

                    #     admin_wallet = PortalUserWallet.objects.get(pu_id=1)
                    #     if admin_charges_type == 'CR':
                    #         admin_wallet.main_wallet = float(admin_wallet.main_wallet) + float(char_comm_amt)
                    #     else:
                    #         admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(char_comm_amt)
                    #     admin_wallet.updated_at = now()
                    #     admin_wallet.save()
                    # data = {
                    #     'order_amount': formatted_amount,
                    #     'id': request.user.id,
                    #     'sp_id': sp_id,
                    #     'customer_contact_no': contact_no,
                    #     'customer_name': None,
                    #     'trn_response': xml,
                    #     'service_trn': biller.pk,
                    #     'label': service_provider.label,
                    #     'category': category.bbps_category.bbps_id,
                    #     'table_name': 'ad_bbps_service_transaction'
                    # }

                    # after_tx_cal(request, data)

                    user_activity = {
                        "table_id": biller.pk,
                        "table_name": 'ad_bbps_bill_payment',
                        "ua_action": 'Create',  # Action performed
                        "ua_description": 'Bill Payment successfully.',  # Action description
                        "created_by": request.user,  # Current user performing the action
                        "request_data": dict(request.data),  # Request data
                        "response_data": model_to_dict(biller)
                    }

                    add_user_activity(user_activity)
                    return Response({'status': 'success', 'message': 'Bill Payment Successfully.'}, status=status.HTTP_200_OK)
                
                elif xml.get('ExtBillPayResponse').get('responseCode') == "204":
                    message = xml.get('ExtBillPayResponse').get('errorInfo').get('error').get('errorMessage')
                    return Response({'status': 'fail', 'message': message}, status=status.HTTP_200_OK)
                else:
                    pass

            else:
                biller.bbps_status = 'FAILED'
                biller.updated_at = datetime.now()
                biller.save()
                return Response({'status': 'fail', 'message': response.text, 'data': xml_to_json}, status=status.HTTP_400_BAD_REQUEST)

        except json.JSONDecodeError:
            return Response({"status": "fail", "message": "blr_payment_request_data must be valid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        except BBPSBillPayment.DoesNotExist:
            return Response({'status': 'fail', 'message': 'request id dose not exists.'}, status=status.HTTP_400_BAD_REQUEST)
        
        except AdServiceProvider.DoesNotExist:
            return Response({'status': 'fail', 'message': 'service provider not found.'}, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as e:
            message = str(e)
            if "ErrorDetail" in message:
                message = message.split("string='")[1].split("', code=")[0]  
            return Response({'status': 'fail', 'message': message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    def update_bbps_biller_status(self, request):
        trnasaction_request_id = request.data.get('request_id')
        sp_id = request.data.get('sp_id')
        accessCode = ''
        instituteId = ''
        try:
            update_status = BBPSBillPayment.objects.get(bbps_request_id=trnasaction_request_id)
            retailer = PortalUser.objects.get(id=request.user.id)

            # Generate XML
            root = ET.Element("transactionStatusReq")

            # Static data with proper formatting
            track_type = ET.SubElement(root, "trackType")
            track_type.text = "REQUEST_ID"

            track_value = ET.SubElement(root, "trackValue")
            track_value.text = trnasaction_request_id

            # Convert to XML string with declaration
            xml_data = ET.tostring(root, encoding="unicode")
            xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_data
            encrypted_data = self.encrypt_data(xml_declaration)
            request_id = self.generate_reference_id()

            url = "https://api.billavenue.com/billpay/transactionStatus/fetchInfo/xml"
            
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                instituteId = sp.credentials_json.get('instituteId')
                accessCode = sp.credentials_json.get('accessCode')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                instituteId = service_provider.credentials_json.get('instituteId')
                accessCode = service_provider.credentials_json.get('accessCode')

            parems = {
                'accessCode': accessCode,
                # 'accessCode': 'AVJK31UI93YO87BWHH',
                'requestId': request_id,
                'ver': '1.0',
                'instituteId': instituteId,
                # 'instituteId': 'AC31',
                'encRequest': encrypted_data
            }

            response = requests.post(url, params=parems)
            decrypt_data = self.decrypt_data(response.text)

            xml_to_json = self.xml_to_json(decrypt_data)
            xml = json.loads(xml_to_json)

            if response.status_code == 200:
                if xml.get('transactionStatusResp', {}).get('responseCode') == "000":
                    biller_name = BBPSBiller.objects.get(
                        bbps_blr_id=xml.get('transactionStatusResp', {}).get('txnList', {}).get('billerId')
                    ).bbps_blr_name
                    bbps_response = BBPSBillPayment.objects.get(bbps_request_id=trnasaction_request_id)

                    # Fix: Properly parse the transaction date
                    txn_date_str = xml.get('transactionStatusResp', {}).get('txnList', {}).get('txnDate')
                    if "T" in txn_date_str:
                        txn_date = datetime.fromisoformat(txn_date_str)  # Works for '2025-02-03T17:04:00+05:04'
                    else:
                        txn_date = datetime.strptime(txn_date_str, "%Y%m%d%H%M%S")  # Fallback for expected format

                    txn_date_formatted = txn_date.strftime("%d/%m/%Y %I:%M %p")

                    bill_date = datetime.today().date()  # Fix: Get today's date correctly
                    bill_number = 'xxxxxxxxxx'
                    bill_period = 'NA'

                    bill_fetch_response = bbps_response.bbps_bill_fetch_response.get('billFetchResponse', {}).get('billerResponse', {})
                    if bill_fetch_response:
                        bill_date = bill_fetch_response.get('billDate', bill_date)
                        bill_number = bill_fetch_response.get('billNumber', bill_number)
                        bill_period = bill_fetch_response.get('bill_period', bill_period)

                    report_data = {
                        'Retailer Name/Contact Number': f"{retailer.pu_name} / {retailer.pu_contact_no}",
                        'Consumer Name/Contact Number': f"{xml.get('transactionStatusResp', {}).get('txnList', {}).get('respCustomerName')} / {xml.get('transactionStatusResp', {}).get('txnList', {}).get('mobile')}",
                        'Transaction Date': txn_date_formatted,
                        'Transaction ID': xml.get('transactionStatusResp', {}).get('txnList', {}).get('payRequestId'),
                        'Biller Name': biller_name,
                        'Biller ID': xml.get('transactionStatusResp', {}).get('txnList', {}).get('billerId'),
                        'Consumer Account Number': 'xxxxxxxxxxxx',
                        'Bill Date': bill_date,
                        'Payment Reference ID': xml.get('transactionStatusResp', {}).get('txnList', {}).get('payRequestId'),
                        'BBPS Transaction Reference ID': xml.get('transactionStatusResp', {}).get('txnList', {}).get('txnReferenceId'),
                        'Payment Mode': 'Cash',
                        'Amount': bbps_response.bbps_amount,
                        'Customer Convenience Fee': xml.get('transactionStatusResp', {}).get('txnList', {}).get('custConvFee'),
                        'Total Amount': bbps_response.bbps_amount,
                        'Bill Number': bill_number,
                        'Bill Period': bill_period,
                        'Payment Method': 'Cash'
                    }
                    return Response({'status': 'success', 'message': 'Transaction status retrieved.', 'data': {'results': report_data}}, status=status.HTTP_200_OK)

                else:
                    return Response({'status': 'fail', 'message': xml}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({'status': 'fail', 'message': xml}, status=status.HTTP_400_BAD_REQUEST)

        except BBPSBillPayment.DoesNotExist:
            return Response({'status': 'fail', 'message': 'Request ID not found.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'fail', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_bbps_biller_transaction_list(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        transaction_data = request.data.get('transaction_data', None)
        search = request.data.get('search', '')
        transaction_status = request.data.get('transaction_status', '')
        date_filter = request.data.get('date_filter', '')  # today, weekly, monthly, yearly, custom
        start_date = request.data.get('start_date', '')
        end_date = request.data.get('end_date', '')

        data = {
            'total_pages': 0,
            'current_page': 0,
            'total_items': 0,
            'results': []
        }
        try:
            if not page_number:
                return Response({'status': 'fail', 'message': 'page_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not isnumber(page_number):
                return Response({'status': 'fail', 'message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            
            page_number = int(page_number)
            page_size = int(page_size)

            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if transaction_data and transaction_data != 'True':
                return Response({'status': 'fail', 'message': 'transaction_data must be true.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                fetch_info = BBPSBillPayment.objects.exclude(Q(bbps_status='PENDING') & Q(bbps_status='BILL_FETCHED'), created_by=request.user.id).order_by('-pk')

                if search != '':
                    # Search within BBPSBillPayment directly
                    fetch_info = fetch_info.filter(
                        Q(bbps_blr_id__icontains=search) |
                        Q(bbps_request_id__icontains=search) |
                        Q(bbps_contact_no__icontains=search)
                    )

                    # Get matching biller IDs from BBPSBiller based on category search
                    biller_ids = BBPSBiller.objects.filter(
                        bbps_category__ss_name__icontains=search
                    ).values_list('bbps_blr_id', flat=True)

                    # Also filter based on biller IDs if found
                    if biller_ids:
                        fetch_info = fetch_info | BBPSBillPayment.objects.filter(bbps_blr_id__in=biller_ids)

                    print('Final Query:', fetch_info.query)
                
                if transaction_status != '':
                    fetch_info = fetch_info.filter(bbps_status=transaction_status)

                # Apply Date Filters
                if date_filter or start_date and end_date:
                    # Ensure timezone-aware date
                    today = localtime().date()
                    now = localtime()
                    if date_filter.strip() == 'today':
                        start_datetime = make_aware(datetime.combine(today, datetime.min.time()))
                        end_datetime = make_aware(datetime.combine(today + timedelta(days=1), datetime.min.time()))
                        fetch_info = fetch_info.filter(created_at__gte=start_datetime, created_at__lt=end_datetime)

                    elif date_filter == 'weekly':
                        start_of_week = today - timedelta(days=today.weekday())  # Start of the week (Monday)
                        start_datetime = make_aware(datetime.combine(start_of_week, datetime.min.time()))
                        fetch_info = fetch_info.filter(created_at__gte=start_datetime)

                    elif date_filter == 'monthly':
                        start_of_month = today.replace(day=1)  # First day of the current month
                        start_datetime = make_aware(datetime.combine(start_of_month, datetime.min.time()))
                        fetch_info = fetch_info.filter(created_at__gte=start_datetime)

                    elif date_filter == 'yearly':
                        start_of_year = today.replace(month=1, day=1)  # First day of the current year
                        start_datetime = make_aware(datetime.combine(start_of_year, datetime.min.time()))
                        fetch_info = fetch_info.filter(created_at__gte=start_datetime)

                    elif date_filter == 'custom' and start_date and end_date:
                        try:
                            start_date = make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
                            end_date = make_aware(datetime.strptime(end_date, "%Y-%m-%d")) + timedelta(days=1)  # Include end date
                            fetch_info = fetch_info.filter(created_at__gte=start_date, created_at__lt=end_date)
                        except ValueError:
                            return Response({'status': 'fail', 'message': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

                if not fetch_info.exists():
                    return Response({'status': 'success', 'message': 'Biller transaction not found.','data': data}, status=status.HTTP_200_OK)

                paginator = Paginator(fetch_info, page_size)
                page = paginator.get_page(page_number)
                serializer = BBPSBillerPaymentSerializer(page, many=True)
                for data in serializer.data:
                    category = BBPSBiller.objects.get(bbps_blr_id=data['bbps_blr_id'])
                    data['category'] = category.bbps_category.ss_name
                    # Convert to datetime if it's a string
                    if isinstance(data['created_at'], str):
                        data['created_at'] = datetime.strptime(data['created_at'], "%Y-%m-%dT%H:%M:%S.%f%z")

                    data['created_at'] = data['created_at'].strftime("%d-%m-%Y %I:%M %p")


                data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }

                return Response({'status': 'success', 'message': 'Biller transaction list.', 'data': data}, status=status.HTTP_200_OK)
            except BBPSBillPayment.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Biller transaction not found.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BbpsComplaintAPIView(APIView):
    authentication_classes=[CustomJWTAuthentication]
    permission_classes=[IsRetailer]

    def encrypt_data(self, xml_data):
        try:
            key = "5D3FC3F011A3105AB0E4312563AD31C6"
            key = hextobin(hashlib.md5(key.encode()).hexdigest())
            init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])


            cipher = AES.new(key, AES.MODE_CBC, init_vector)
            plain_text_padded = pad(xml_data.encode(), AES.block_size)
            encrypted_text = cipher.encrypt(plain_text_padded)
            encrypted_hex = binascii.hexlify(encrypted_text).decode()

            return encrypted_hex

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def decrypt_data(self, string_data):
        try:
            encrypted_text = string_data
            # Define the decryption key and initialization vector
            key = "5D3FC3F011A3105AB0E4312563AD31C6"
            key = hextobin(hashlib.md5(key.encode()).hexdigest())
            init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])

            # Decrypt the data
            encrypted_text_bytes = binascii.unhexlify(encrypted_text)
            cipher = AES.new(key, AES.MODE_CBC, init_vector)
            decrypted_text_padded = cipher.decrypt(encrypted_text_bytes)
            decrypted_text = unpad(decrypted_text_padded, AES.block_size).decode()
            decrypted_xml = ET.fromstring(decrypted_text)
            
            xml = ET.tostring(decrypted_xml, encoding='utf-8', xml_declaration=True)

            return xml

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def xml_to_json(self, xml_data):
        try:

            # Convert XML to dictionary
            dict_data = xmltodict.parse(xml_data)
            
            # Convert dictionary to JSON
            json_data = json.dumps(dict_data, indent=4)

            # Return success response
            return json_data

        except Exception as e:
            # Handle any exceptions and return error response
            return Response({
                "error": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def generate_reference_id(self):
        random_chars = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=27))

        now = datetime.now()

        year_last_digit = str(now.year)[-1]
        day_of_year = f"{now.timetuple().tm_yday:03d}"
        hour = f"{now.hour:02d}"
        minute = f"{now.minute:02d}"

        julian_suffix = f"{year_last_digit}{day_of_year}{hour}{minute}"

        reference_id = random_chars + julian_suffix
        return reference_id

    def post(self, request):
        try:
            if 'txnRefId' in request.data and 'complaintDesc' in request.data and 'complaintDisposition' in request.data:
                return self.complaint_register(request)
            elif 'complaintId' in request.data:
                return self.complaint_tracking(request)
            elif 'page_number' in request.data or 'page_size' in request.data:
                return self.all_complaints(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid data.'},status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def complaint_register(self, request):
        txnRefId = request.data.get('txnRefId')
        complaintDesc = request.data.get('complaintDesc')
        complaintDisposition = request.data.get('complaintDisposition')
        sp_id = request.data.get('sp_id')
        accessCode = ''
        instituteId = ''
        try:
            if not txnRefId: return Response({'status': 'fail', 'message': 'txnRefId is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not complaintDesc: return Response({'status': 'fail', 'message': 'complaintDesc is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not complaintDisposition: return Response({'status': 'fail', 'message': 'complaintDisposition is required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Root element
            root = ET.Element("complaintRegistrationReq")

            # Static data
            complaint_type = ET.SubElement(root, "complaintType")
            complaint_type.text = "Transaction"

            participation_type = ET.SubElement(root, "participationType")
            participation_type.text = ""

            agent_id = ET.SubElement(root, "agentId")
            agent_id.text = ""

            txn_ref_id = ET.SubElement(root, "txnRefId")
            txn_ref_id.text = txnRefId

            biller_id = ET.SubElement(root, "billerId")
            biller_id.text = ""

            complaint_desc = ET.SubElement(root, "complaintDesc")
            complaint_desc.text = complaintDesc

            serv_reason = ET.SubElement(root, "servReason")
            serv_reason.text = ""

            complaint_disposition = ET.SubElement(root, "complaintDisposition")
            complaint_disposition.text = complaintDisposition

            # Convert to string
            xml_data = ET.tostring(root, encoding="unicode")
            encrypted_data = self.encrypt_data(xml_data)
            request_id = self.generate_reference_id()

            url = "https://api.billavenue.com/billpay/extComplaints/register/xml"

            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                accessCode = sp.credentials_json.get('accessCode')
                instituteId = sp.credentials_json.get('instituteId')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                accessCode = service_provider.credentials_json.get('accessCode')
                instituteId = service_provider.credentials_json.get('instituteId')

            parems = {
                'accessCode': accessCode,
                # 'accessCode': 'AVJK31UI93YO87BWHH',
                'requestId': request_id,
                'ver': '1.0',
                'instituteId': instituteId,
                # 'instituteId': 'AC31',
                'encRequest': encrypted_data
            }

            response = requests.post(url, params=parems)
            decrypt_data = self.decrypt_data(response.text) 
            xml_to_json = self.xml_to_json(decrypt_data)
            json_data = json.loads(xml_to_json)
            if response.status_code == 200:
                if json_data.get("complaintRegistrationResp").get("responseCode") == "000":
                    bill_complaint = BBPSComplaint.objects.create(
                        trn_id=txnRefId,
                        comp_id=json_data.get('complaintRegistrationResp').get('complaintId'),
                        complaint_response=json_data,
                        complaint_status="SUCCESS",
                        created_by=request.user.id
                    )
                    user_activity = {
                        "table_id": bill_complaint.pk,
                        "table_name": 'ad_bbps_complaint',
                        "ua_action": 'Create',  # Action performed
                        "ua_description": 'Bill Complaint successfully.',  # Action description
                        "created_by": request.user,  # Current user performing the action
                        "request_data": dict(request.data),  # Request data
                        "response_data": model_to_dict(bill_complaint)
                    }

                    add_user_activity(user_activity)
                    return Response({'status': 'success', 'message': 'Complaint register successfully.','data': data}, status=status.HTTP_200_OK)
                else:
                    print('json_data', json_data)
                    message = json_data.get("complaintRegistrationResp").get("responseReason")
                    return Response({'status': 'fail', 'message': message}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({'status': 'fail', 'message': response.text, 'data': json_data}, status=status.HTTP_400_BAD_REQUEST)

        except json.JSONDecodeError:
            return Response({"status": "fail", "message": "blr_request_data must be valid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def complaint_tracking(self, request):
        complaintId = request.data.get('complaintId')
        sp_id = request.data.get('sp_id')
        instituteId = ''
        accessCode = ''
        try:
            if not complaintId: return Response({'status': 'fail', 'message': 'complaintId is required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Root element
            root = ET.Element("complaintTrackingReq")

            # Static data
            complaint_type = ET.SubElement(root, "complaintType")
            complaint_type.text = "Transaction"

            complaint_id = ET.SubElement(root, "complaintId")
            complaint_id.text = complaintId

            # Convert to string
            xml_data = ET.tostring(root, encoding="unicode")
            encrypted_data = self.encrypt_data(xml_data)
            request_id = self.generate_reference_id()

            url = "https://api.billavenue.com/billpay/extComplaints/track/xml"
            
            sp = AdServiceProvider.objects.get(sp_id=sp_id)
            if sp.is_self_config == True:
                instituteId = sp.credentials_json.get('instituteId')
                accessCode = sp.credentials_json.get('accessCode')
            else:
                service_provider = ServiceProvider.objects.get(sp_id=sp.sp_id)
                instituteId = service_provider.credentials_json.get('instituteId')
                accessCode = service_provider.credentials_json.get('accessCode')

            parems = {
                'accessCode': accessCode,
                # 'accessCode': 'AVJK31UI93YO87BWHH',
                'requestId': request_id,
                'ver': '1.0',
                'instituteId': instituteId,
                # 'instituteId': 'AC31',
                'encRequest': encrypted_data
            }

            response = requests.post(url, params=parems)
            decrypt_data = self.decrypt_data(response.text) 
            xml_to_json = self.xml_to_json(decrypt_data)
            json_data = json.loads(xml_to_json)
            
            if response.status_code == 200:
                complaint = BBPSComplaint.objects.get(comp_id=complaintId)
                complaint.tracking_response = json_data
                complaint.save()
                return Response({'status': 'success', 'message': json_data.get('complaintTrackingResp').get('complaintAssigned')}, status=status.HTTP_200_OK)
            
            else:
                return Response({'status': 'fail', 'message': response.text, 'data': json_data}, status=status.HTTP_400_BAD_REQUEST)
        
        except BBPSComplaint.DoesNotExist:
            return Response({'status': 'fail', 'message': f'{complaintId} is dose not exists.'},status=status.HTTP_404_NOT_FOUND)
            
        except json.JSONDecodeError:
            return Response({"status": "fail", "message": "blr_request_data must be valid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def all_complaints(self, request):
        page_number = request.data.get('page_number', 1)
        page_size = request.data.get('page_size', 10)
        search = request.data.get('search', '')

        try:
            if not page_number:
                return Response({'status': 'fail', 'message': 'page_number is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not isnumber(page_number):
                return Response({'status': 'fail', 'message': 'page_number must contain only digits.'}, status=status.HTTP_400_BAD_REQUEST)
            
            page_number = int(page_number)
            page_size = int(page_size)

            if page_number < 1 or page_size < 1:
                return Response({'status': 'fail', 'message': 'page_number and page_size must be greater than 0.'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                fetch_complaint = BBPSComplaint.objects.filter(created_by=request.user.id).order_by('-pk')

                if search != '':
                    fetch_complaint = fetch_complaint.filter(Q(comp_id__icontains=search) | Q(trn_id__icontains=search)).order_by('-pk')

                if not fetch_complaint.exists():
                    return Response({'status': 'success', 'message': 'Biller Complaints not found.'}, status=status.HTTP_404_NOT_FOUND)

                paginator = Paginator(fetch_complaint, page_size)
                page = paginator.get_page(page_number)
                serializer = BBPSComplaintSerializer(page, many=True)
                for data in serializer.data:
                    if isinstance(data['created_at'], str):
                        data['created_at'] = datetime.strptime(data['created_at'], "%Y-%m-%dT%H:%M:%S.%f%z")

                    data['created_at'] = data['created_at'].strftime("%d-%m-%Y %I:%M %p")

                data = {
                    'total_pages': paginator.num_pages,
                    'current_page': page.number,
                    'total_items': paginator.count,
                    'results': serializer.data
                }

                return Response({'status': 'success', 'message': 'Biller complaints list.', 'data': data}, status=status.HTTP_200_OK)
            except BBPSComplaint.DoesNotExist:
                return Response({'status': 'fail', 'message': 'Biller complaints not found.'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BbpsBillerEntryAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request):
        try:
            if 'excel_file' in request.data:
                return self.insert_excel_bbps_biller(request)
            elif 'blr_id' in request.data and 'blr_name' in request.data and 'bbps_category_id' in request.data and 'sd_charges' in request.data and 'md_charges' in request.data and 'dt_charges' in request.data and 'rt_charges' in request.data:
                return self.insert_bbps_biller(request)
            else:
                return Response({'status': 'fail', 'message': 'Invalid Request data.'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def insert_excel_bbps_biller(self, request):
        excel_file = request.data.get('excel_file')
        try:
            if not excel_file: return Response({'status': 'fail', 'message': 'excel file is required.'}, status=status.HTTP_400_BAD_REQUEST)
            df = pd.read_excel(excel_file)

            required_columns = ['blr_id', 'blr_name', 'blr_category_name']

            for col in required_columns:
                if col not in df.columns:
                    return Response({'status': 'fail', 'message': f'Missing required column: {col}'},status=status.HTTP_400_BAD_REQUEST)
                
            for _, row in df.iterrows():
                try:
                    category = None
                    if row['blr_category_name']:
                        category = BBPSBillerCategory.objects.filter(ss_name=row['blr_category_name']).first()
                        if not category:
                            return Response({'status': 'fail', 'message': f'Invalid category ID: {row["blr_category_name"]}'}, status=status.HTTP_400_BAD_REQUEST)

                    BBPSBiller.objects.create(
                        bbps_blr_id=row['blr_id'],
                        bbps_blr_name=row['blr_name'],
                        bbps_category=category,
                    )
                except Exception as inner_e:
                    return Response({'status': 'fail', 'message': f'Error inserting row: {str(inner_e)}'},status=status.HTTP_400_BAD_REQUEST)

            return Response({'status': 'success', 'message': 'Data inserted successfully.'},status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def insert_bbps_biller(self, request):
        blr_id = request.data.get('blr_id')
        blr_name = request.data.get('blr_name')
        bbps_category_id = request.data.get('bbps_category_id')
        sd_charges = request.data.get('sd_charges')
        md_charges = request.data.get('md_charges')
        dt_charges = request.data.get('dt_charges')
        rt_charges = request.data.get('rt_charges')

        try:
            if not blr_id: return Response({'status': 'fail', 'message': 'blr id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not blr_name: return Response({'status': 'fail', 'message': 'blr name is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not bbps_category_id: return Response({'status': 'fail', 'message': 'bbps category id is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not sd_charges: return Response({'status': 'fail', 'message': 'sd charges is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not md_charges: return Response({'status': 'fail', 'message': 'md_charges is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not dt_charges: return Response({'status': 'fail', 'message': 'dt charges is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not rt_charges: return Response({'status': 'fail', 'message': 'rt charges is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if not isnumber(bbps_category_id): return Response({'status': 'fail', 'message': 'Invalid Category ID. It must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

            category = BBPSBillerCategory.objects.filter(ss_id=bbps_category_id).first()
            if not category:
                return Response({'status': 'fail', 'message': f'Invalid category ID: {bbps_category_id}'}, status=status.HTTP_400_BAD_REQUEST)

            BBPSBiller.objects.create(
                bbps_blr_id=blr_id,
                bbps_blr_name=blr_name,
                bbps_category=category,
                sd_charges=sd_charges,
                md_charges=md_charges,
                dt_charges=dt_charges,
                rt_charges=rt_charges
            )
            return Response({'status': 'success', 'message': 'Data inserted successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BbpsBillerInfoEntryAPIView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request):
        info = request.data.get('info')
        json_data = {}
        try:
            all_bbps_biller = BBPSBiller.objects.filter(is_deleted=False, is_deactive=False).values_list('bbps_blr_id', flat=True)
            data_list = list(all_bbps_biller)
            chunk_size = 2000
            chunks = [data_list[i:i + chunk_size] for i in range(0, len(data_list), chunk_size)]
            for chunk in chunks:
                root = Element('billerInfoRequest')
                for bbps_blr_id in chunk:
                    SubElement(root, 'billerId').text = bbps_blr_id
                raw_xml = tostring(root, encoding='utf-8')
                pretty_xml = parseString(raw_xml).toprettyxml(indent="  ")
                encrypted_hex = encrypt_data(pretty_xml)

                url = "https://api.billavenue.com/billpay/extMdmCntrl/mdmRequestNew/xml"
                params = {
                    "accessCode": "AVJK31UI93YO87BWHH",
                    "requestId": "TEST000MNPREQ0000000000000000001112",
                    "ver": "1.0",
                    "instituteId": "AC31",
                }
                
                response = requests.post(url, params=params, data=encrypted_hex, headers={"Content-Type": "text/plain"})
                response.raise_for_status()
                
                encrypted_response = response.text
                decrypted_text = decrypt_data(encrypted_response)
                # Convert XML to JSON and ensure proper handling
                dict_data = xmltodict.parse(decrypted_text)
                json_data = json.loads(json.dumps(dict_data))  # Ensure it's a dictionary
                
                for data in json_data["billerInfoResponse"]["biller"]:
                    BBPSBillResponse.objects.create(
                        bbps_biller_id=data["billerId"],
                        bbps_biller_response=json.dumps(data)  # Save as a JSON string
                    )
            return Response({'status': 'success', 'data': 'Data inserted successfully.......................'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'message': f'Internal server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def encrypt_data(xml_data):
    try:
        key = "5D3FC3F011A3105AB0E4312563AD31C6"
        key = binascii.unhexlify(hashlib.md5(key.encode()).hexdigest())
        init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])

        cipher = AES.new(key, AES.MODE_CBC, init_vector)
        plain_text_padded = pad(xml_data.encode(), AES.block_size)
        encrypted_text = cipher.encrypt(plain_text_padded)
        encrypted_hex = binascii.hexlify(encrypted_text).decode()

        return encrypted_hex

    except Exception as e:
        raise Exception(f"Encryption error: {str(e)}")


def decrypt_data(string_data):
    try:
        key = "5D3FC3F011A3105AB0E4312563AD31C6"
        key = binascii.unhexlify(hashlib.md5(key.encode()).hexdigest())
        init_vector = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f])

        encrypted_text_bytes = binascii.unhexlify(string_data)
        cipher = AES.new(key, AES.MODE_CBC, init_vector)
        decrypted_text_padded = cipher.decrypt(encrypted_text_bytes)
        decrypted_text = unpad(decrypted_text_padded, AES.block_size).decode()

        return decrypted_text

    except Exception as e:
        raise Exception(f"Decryption error: {str(e)}")


def xml_to_json(xml_data):
    try:
        dict_data = xmltodict.parse(xml_data)
        return json.dumps(dict_data, indent=4)
    except Exception as e:
        raise Exception(f"XML to JSON conversion error: {str(e)}")

