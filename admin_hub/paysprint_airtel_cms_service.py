from .views import *
from .utilies import *

class AirtelCmsAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if 'refid' in request.data and 'latitude' in request.data and 'lognitude' in request.data:
            return self.get_airtel_cms(request)
        elif 'refid' in request.data and 'url' in request.data and 'service_name' in request.data:
            return self.create_airtel_cms(request)
        else:
            return Response({'status': 'fail', 'message': 'Invalid request data.'}, status=status.HTTP_400_BAD_REQUEST)

    def get_airtel_cms(self, request):
        refid = request.data.get('refid')
        latitude = request.data.get('latitude')
        longitude = request.data.get('lognitude')

        url = "https://sit.paysprint.in/service-api/api/v1/service/airtelcms/V2/airtel/index"

        payload = {
            "refid": refid,
            "latitude": latitude,
            "longitude": longitude
        }
        
        headers = {
            'Token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJQQVlTUFJJTlQiLCJ0aW1lc3RhbXAiOjE2MTAwMjYzMzgsInBhcnRuZXJJZCI6IlBTMDAxIiwicHJvZHVjdCI6IldBTExFVCIsInJlcWlkIjoxNjEwMDI2MzM4fQ.buzD40O8X_41RmJ0PCYbBYx3IBlsmNb9iVmrVH9Ix64',
            'accept': 'application/json',
            'content-type': 'application/json',
            'authorisedkey': 'MzNkYzllOGJmZGVhNWRkZTc1YTgzM2Y5ZDFlY2EyZTQ='
        }

        response = requests.post(url, json=payload, headers=headers)
        response_json = response.json()
        return Response({'message': response_json}) 

    def create_airtel_cms(self, request):
        refid = request.data.get('refid')
        url = request.data.get('url')
        service_name = request.data.get('service_name') 
        amount = request.data.get('amount')
        biller_id = request.data.get('biller_id')
        biller_name = request.data.get('biller_name')
        mobile_no = request.data.get('mobile_no')
        commission = request.data.get('commission', None)
        utr = request.data.get('utr', None)
        ackno = request.data.get('ackno', None)
        admin_wallet = check_admin_wallet(request, amount)
        headers = {
            'Token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJQQVlTUFJJTlQiLCJ0aW1lc3RhbXAiOjE2MTAwMjYzMzgsInBhcnRuZXJJZCI6IlBTMDAxIiwicHJvZHVjdCI6IldBTExFVCIsInJlcWlkIjoxNjEwMDI2MzM4fQ.buzD40O8X_41RmJ0PCYbBYx3IBlsmNb9iVmrVH9Ix64',
            'accept': 'application/json',
            'content-type': 'application/json',
            'authorisedkey': 'MzNkYzllOGJmZGVhNWRkZTc1YTgzM2Y5ZDFlY2EyZTQ='
        }

        if not refid:
            return Response({'status': 'fail', 'message': 'refid is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not url:
            return Response({'status': 'fail', 'message': 'url is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not service_name:
            return Response({'status': 'fail', 'message': 'service_name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not amount:  
            return Response({'status': 'fail', 'message': 'amount is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not biller_id:
            return Response({'status': 'fail', 'message': 'biller_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not biller_name:
            return Response({'status': 'fail', 'message': 'biller_name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not mobile_no:
            return Response({'status': 'fail', 'message': 'mobile_no is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if service_name == 'CMS_BALANCE_INQUIRY':
            import logging
            import requests
            from django.http import JsonResponse
            from django.utils.timezone import now

            # Logging configuration (optional for debugging)
            logging.basicConfig(level=logging.DEBUG)

            payload = {
                "event": service_name,
                "param": {
                    "refid": refid,
                    "amount": amount,
                    "biller_id": biller_id,
                    "biller_name": biller_name,
                    "mobile_no": mobile_no,
                    "datetime": now().strftime('%Y-%m-%d')
                }
            }
            # call_url = f'{url}/{service_name}'  # Endpoint URL

            try:
                logging.debug('Making a POST request...')
                logging.debug('Request URL: %s', url)
                logging.debug('Payload: %s', payload)

                response = requests.post(url, json=payload, headers=headers, timeout=10)
                logging.debug('Response status code: %d', response.status_code)
                logging.debug('Response headers: %s', response.headers)

                # Raw response text for debugging
                logging.debug('Raw response text: %s', response.text)

                # Content-Type verification
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    # Attempt to parse JSON response
                    response_data = response.json()
                    logging.debug('Parsed JSON response: %s', response_data)
                elif response.text.strip() == '':
                    # Handle empty response body
                    response_data = {'error': 'Empty response from server'}
                    logging.error('Empty response body detected.')
                else:
                    # Handle unexpected non-JSON responses
                    response_data = {
                        'error': 'Non-JSON response',
                        'details': response.text
                    }
                    logging.error('Non-JSON response detected: %s', response.text)

                # Return processed response
                return JsonResponse(response_data, status=status.HTTP_200_OK)

            except requests.exceptions.JSONDecodeError as json_error:
                logging.error('JSON decode error: %s', str(json_error))
                return JsonResponse(
                    {'error': 'Invalid JSON response from server', 'details': str(json_error)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except requests.exceptions.RequestException as req_error:
                logging.error('Request exception: %s', str(req_error))
                return JsonResponse(
                    {'error': 'Request failed', 'details': str(req_error)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        elif service_name == 'CMS_BALANCE_DEBIT':
            payload = {
                "event": service_name,
                "param": {
                    "refid": refid,
                    "amount": amount,
                    "biller_id": biller_id,
                    "biller_name": biller_name,
                    "mobile_no": mobile_no,
                    "commission": commission,
                    "datetime": timezone.now().strftime('%Y-%m-%d')
                }
            }

            response = requests.post(url, json=payload, headers=headers)
            response_json = response.json()
            if response_json.get('status') == 'SUCCESS':
                # AirtelCMSTrn.objects.create(
                #     refid=refid,
                #     service_name=service_name,
                #     amount=amount,
                #     biller_id=biller_id,
                #     biller_name=biller_name,
                #     mobile_no=mobile_no,
                #     trn_response=response_json,
                # )
                return Response({'status': 'success', 'message': response_json.get('message')}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': response_json.get('message')}, status=status.HTTP_400_BAD_REQUEST)

        elif service_name == 'CMS_LOW_BALANCE_INQUIRY':
            payload = {
                "event": service_name,
                "param": {
                    "refid": refid,
                    "amount": amount,
                    "biller_id": biller_id,
                    "biller_name": biller_name,
                    "mobile_no": mobile_no,
                    "status": 0,
                    "errormsg": 'Your wallet balance is less than debit amount.',
                    "datetime": timezone.now().strftime('%Y-%m-%d')
                }
            }

            response = requests.post(url, json=payload, headers=headers)
            response_json = response.json()
            if response_json.get('status') == 'SUCCESS':
                # AirtelCMSTrn.objects.create(
                #     refid=refid,
                #     service_name=service_name,
                #     amount=amount,
                #     biller_id=biller_id,
                #     biller_name=biller_name,
                #     mobile_no=mobile_no,
                #     trn_response=response_json,
                # )
                return Response({'status': 'success', 'message': response_json.get('message')}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': response_json.get('message')}, status=status.HTTP_400_BAD_REQUEST)

        elif service_name == 'CMS_POSTING':
            payload = {
                "event": service_name,
                "param": {
                    "refid": refid,
                    "utr": utr,
                    "biller_name": biller_name,
                    "mobile_no": mobile_no,
                    "biller_id": biller_id,
                    "ackno": ackno,
                    "unique_id": '0001',
                    "status": 1,
                    "datetime": timezone.now().strftime('%Y-%m-%d')
                }
            }

            response = requests.post(url, json=payload, headers=headers)
            response_json = response.json()
            if response_json.get('status') == 'SUCCESS':
                # AirtelCMSTrn.objects.create(
                #     refid=refid,
                #     service_name=service_name,
                #     amount=amount,
                #     biller_id=biller_id,
                #     biller_name=biller_name,
                #     mobile_no=mobile_no,
                #     trn_response=response_json,
                # )
                return Response({'status': 'success', 'message': response_json.get('message')}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'fail', 'message': response_json.get('message')}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({'status': 'fail', 'message': 'Invalid service name.'}, status=status.HTTP_400_BAD_REQUEST)


