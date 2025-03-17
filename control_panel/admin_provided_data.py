from .models import *
from admin_hub.models import *
from control_panel.models import *

def provided_data(request):
    sa_bbps_category = SaBBPSBillerCategory.objects.filter(is_deleted=False)
    sa_oprator = SaOprators.objects.filter(is_deleted=False)
    other_charges = OtherCharges.objects.all()

    for bbps_category in sa_bbps_category:
        BBPSBillerCategory.objects.create(ss_name=bbps_category.ss_name, is_deactive=True)

    for oprator in sa_oprator:
        Oprators.objects.create(ss_name=oprator.ss_name, operator_code=oprator.operator_code, is_deactive=True, operator_type=oprator.operator_type)


    distributor_data = [{'dh_name': 'SUPER DISTRIBUTOR', 'dh_description': 'SUPER DISTRIBUTOR', 'is_used': True, 'dh_parent_id': None, 'dh_prefix': 'SD'},
                            {'dh_name': 'MASTER DISTRIBUTOR', 'dh_description': 'MASTER DISTRIBUTOR', 'is_used': True, 'dh_parent_id': 1, 'dh_prefix': 'MD'},
                            {'dh_name': 'DISTRIBUTOR', 'dh_description': 'DISTRIBUTOR', 'is_used': False, 'dh_parent_id': 2, 'dh_prefix': 'DT'}]
    for data in distributor_data:
        DistributorHierarchy.objects.using('tcpl_admin_db').create(
            dh_name=data['dh_name'],
            dh_description=data['dh_description'],
            is_used=data['is_used'],
            dh_parent_id=data['dh_parent_id'],
            dh_prefix=data['dh_prefix'],
        )

    if not other_charges:
        data_list = [
            {'oc_name': 'quick_transfer_charges'},
            {'oc_name': 'cashin_to_bank_charges'},
            {'oc_name': 'dmt_kyc'}
        ]
        for data in data_list:
            OtherCharges.objects.create(
                oc_name=data.get('oc_name')
            )