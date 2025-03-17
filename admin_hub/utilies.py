from .models import *
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

def add_user_activity(data):
    try:
        UserActivity.objects.create(**data)

        response_data = {
            'status': 'success',
            'message': 'user activity added successfully',
        }
        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
def check_admin_wallet(request, amount):
    try:
        admin = PortalUser.objects.get(pu_role='ADMIN')
        admin_wallet = PortalUserWallet.objects.get(pu=admin)
        if admin_wallet.main_wallet > 0:
            if float(admin_wallet.main_wallet) >= float(amount):
                return True
            else:
                raise ValidationError("Admin wallet has insufficient balance.")
        else:
            raise ValidationError("Admin wallet is empty.")
    except PortalUserWallet.DoesNotExist:
        raise ValidationError("Admin wallet not found.")
    except PortalUser.DoesNotExist:
        raise ValidationError("Admin not found.")
    except Exception as e:
        raise ValidationError(f"Internal server error: {str(e)}")


def check_retailer_wallet(request, amount, pu_id):
    try:
        user = PortalUser.objects.get(id=pu_id)
        user_wallet = PortalUserWallet.objects.get(pu=user)
        if float(user_wallet.main_wallet) > 0.00:
            if float(user_wallet.main_wallet) >= float(amount):
                return True
            else:
                raise ValidationError("User wallet has insufficient balance.")
        else:
            raise ValidationError("User wallet is empty.")
    except PortalUserWallet.DoesNotExist:
        raise ValidationError("User wallet not found.")
    except PortalUser.DoesNotExist:
        raise ValidationError("User not found.")
    except Exception as e:
        raise ValidationError(f"Internal server error: {str(e)}")

