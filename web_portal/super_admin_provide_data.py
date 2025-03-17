from control_panel.models import *
from control_panel.serializers import *
import csv
import os
import datetime

# Base directory for the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths to the CSV files
state_file_path = os.path.join(BASE_DIR, "state.csv")
city_file_path = os.path.join(BASE_DIR, "city.csv")
bbps_category_file_path = os.path.join(BASE_DIR, "bbps_category.csv")
recharge_operator_file_path = os.path.join(BASE_DIR, "recharge_operator.csv")

def upload_all_data(request):
    all_states = State.objects.all()
    all_citys = City.objects.all()
    all_bbps_category = SaBBPSBillerCategory.objects.all()
    all_recharge_oprator = SaOprators.objects.all()
    all_other_charges = SaOtherCharges.objects.all()

    if not all_states:
        with open(state_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            print('reader', reader)
            for row in reader:
                print('row', row.get('state_name'), 'code', row.get('code'))
                state = State.objects.create(state_name=row.get('state_name'), code=row.get('code'), created_at=datetime.datetime.now(), is_active=True)
                print('-======================', state)

    if not all_citys:
        with open(city_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                state = State.objects.get(state_id=row.get('state'))
                print('state', state)
                City.objects.create(city_name=row.get('city_name'), state=state)

    if not all_bbps_category:
        with open(bbps_category_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                SaBBPSBillerCategory.objects.create(ss_name=row.get('bbps_category_name'), is_deactive=True)

    if not all_recharge_oprator:
        with open(recharge_operator_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                SaOprators.objects.create(ss_name=row.get('oprator_name'), operator_code=row.get('oprator_code'), operator_type=row.get('oprator_type'), is_deactive=True)
    return True
    
    if not all_other_charges:
        data_list = [
            {'oc_name': 'pan_card'},
            {'oc_name': 'aadhaar_card'}
        ]

        for data in data_list:
            SaOtherCharges.objects.create(
                oc_name=data.get('oc_name')
            )

            
