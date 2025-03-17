import json
import re
from django.db import connections, transaction
from django.utils.timezone import now
from .models import (
    PortalUserCharges, AdHSNSAC, AdServiceProvider, 
    WalletTrn, PortalUserWallet, GlTrn, PortalUser, AdService, BBPSBillerCategory, Oprators
)


def fetch_user_hierarchy(user_id):
    user_lst = []

    user = PortalUser.objects.get(id=user_id)

    # Recursive Query to fetch all users in the hierarchy
    cursor = connections['tcpl_admin_db'].cursor()
    
    query = f'''WITH RECURSIVE "Descendants" AS (
    SELECT "pud_id", "created_by", "dh_id", "pu_id"
    FROM "ad_portal_user_details"
    WHERE "pu_id" = {user.id}
    UNION ALL
    SELECT n."pud_id", n."created_by", n."dh_id", n."pu_id"
    FROM "ad_portal_user_details" n
    JOIN "Descendants" d ON n."pu_id" = d."created_by"
    WHERE n."pud_id" != 1
    )
    SELECT * FROM "Descendants";'''

    
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    
    for res in result:
        pud_id, created_by, dh_id, pu_id = res

        user_lst.append({'user_id':pu_id, 'dh_id':dh_id})

    return user_lst


def fetch_user_charges_hierarchy(user_id, sp_id):
    user_lst = []

    user = PortalUser.objects.get(id=user_id)
    
    # Recursive Query to fetch all users in the hierarchy
    cursor = connections['tcpl_admin_db'].cursor()
    
    query = f'''WITH RECURSIVE "Descendants" AS (
        SELECT "pu_id", "parent_id", "puc_charges", "mark_type", "sp_id", "dh_id"
        FROM "ad_portal_user_charges"
        WHERE "pu_id" = {user.id} AND "sp_id" = {sp_id}
        UNION ALL
        SELECT n."pu_id", n."parent_id", n."puc_charges", n."mark_type", n."sp_id", n."dh_id"
        FROM "ad_portal_user_charges" n
        JOIN "Descendants" d ON n."pu_id" = d."parent_id" AND n."sp_id" = d."sp_id"
        )
        SELECT * FROM "Descendants";'''

    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    
    for res in result:
        pu_id, parent_id, puc_charges, charge_type, sp_id, dh_id = res

        user_lst.append({'pu_id':pu_id, 'parent_id': parent_id, 'puc_charges': puc_charges, 'charge_type': charge_type, 'sp_id':sp_id,  'dh_id':dh_id})

    return user_lst
