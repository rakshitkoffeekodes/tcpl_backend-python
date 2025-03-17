from .commission_calculations import *
from .models import *


def charges_calculation_function(request, data):
    
    service_trn_id = data.get('service_id')
    amount = data.get('amount')
    table_name = data.get('table_name')
    wl_label = data.get('wl_label')
    gst_rate = data.get('gst_rate')
    admin_tax_amt = data.get('admin_tax_amt')
    char_comm_amt = data.get('char_comm_amt')
    admin_charges_type = data.get('admin_charges_type')
    sp_id = data.get('sp_id')
    contact_number = data.get('contact_number')
    name = data.get('name')
    response_data = data.get('response_data')
    label = data.get('label')
    category = data.get('category')
    is_self_config = data.get('is_self_config')
    charge_level = data.get('charge_level')
    print('========================================= ccf function')

    service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
    service_id = service_provider.service.service_id

    rtl_wallet = PortalUserWallet.objects.get(pu_id=request.user.id)

    if int(service_id) == 1:
        effective_wallet = 'pg_wallet'
        effective_type = 'CR'
        rtl_wallet.pg_wallet = float(rtl_wallet.pg_wallet) + float(amount)
    else:
        effective_wallet = 'main_wallet'
        effective_type = 'DR'
        rtl_wallet.main_wallet = float(rtl_wallet.main_wallet) - float(amount)

    rtl_wallet.updated_at = now()
    rtl_wallet.save()
    
    # for retailer
    rt_gl = GlTrn.objects.create(
        service_trn_id=service_trn_id,
        pu_id=request.user.id,
        gl_trn_amt=amount,
        effectvie_wallet=effective_wallet,
        effectvie_amt=amount,
        service_trn_table=table_name,
        effective_type=effective_type,
        gl_trn_dt=now(),
    )

    WalletTrn.objects.create(
        action_id=rt_gl.pk,
        action_type='Order',
        pu_id=request.user.id,
        wl_label=wl_label,
        effectvie_wallet=effective_wallet,
        effectvie_amt=amount,
        effective_type=effective_type,
        current_balance=rtl_wallet.pg_wallet if int(service_id) == 1 else rtl_wallet.main_wallet,
        wl_trn_dt=now()
    )


    # DMT SERVICE
    charge_tax_rate = service_provider.hsn_sac.tax_rate
    if service_provider.sp_name == 'PaySprint' and service_provider.service.service_name == 'DMT':
        charge_rate = 12.00

        cal_charge = float(amount) * 1.2 / 100

        if float(cal_charge) >= charge_rate:
            charge_rate = cal_charge
        else:
            charge_rate = charge_rate

        gst_charge_amt = float(charge_rate) - (float(charge_rate)/(1+(float(charge_tax_rate)/100)))
        print('========================')
        rtl_wallet = PortalUserWallet.objects.get(pu_id=request.user.id)
        rtl_wallet.main_wallet = float(rtl_wallet.main_wallet) - float(charge_rate)
        rtl_wallet.updated_at = now()
        rtl_wallet.save()
        # for retailer
        rt_gl = GlTrn.objects.create(
            service_trn_id=service_trn_id,
            pu_id=request.user.id,
            gl_trn_amt=amount,
            gl_tax_rate=charge_tax_rate if charge_tax_rate else None,
            gl_tax_amt=gst_charge_amt,
            effectvie_wallet='main_wallet',
            effectvie_amt=charge_rate,
            service_trn_table=table_name,
            effective_type='DR',
            gl_trn_dt=now(),
        )

        WalletTrn.objects.create(
            action_id=rt_gl.pk,
            action_type='Order',
            pu_id=request.user.id,
            wl_label=wl_label,
            effectvie_wallet='main_wallet',
            effectvie_amt=charge_rate,
            effective_type='DR',
            current_balance=rtl_wallet.main_wallet,
            wl_trn_dt=now()
        )

        admin_wallet = PortalUserWallet.objects.get(pu_id=1)
        admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(charge_rate)
        admin_wallet.updated_at = now()
        admin_wallet.save()
        print('========================111111')
        admin_gl = GlTrn.objects.create(
            service_trn_id=service_trn_id,
            pu_id=1,
            gl_tax_rate=charge_tax_rate if charge_tax_rate else None,
            gl_tax_amt=gst_charge_amt,
            gl_trn_amt=amount,
            effectvie_wallet='main_wallet',
            effectvie_amt=charge_rate,
            service_trn_table=table_name,
            effective_type='DR',
            gl_trn_dt=now(),
        )

        WalletTrn.objects.create(
            action_id=admin_gl.pk,
            action_type='Order',
            pu_id=1,
            wl_label=wl_label,
            effectvie_wallet='main_wallet',
            effectvie_amt=charge_rate,
            effective_type='DR',
            current_balance=admin_wallet.main_wallet,
            wl_trn_dt=now()
        )
        
        
        print('========================2222222222')

    tax_rate = None
    # for admin
    if is_self_config==True:
        service_provider = AdServiceProvider.objects.get(sp_id=sp_id)
        plateform_fee = service_provider.plateform_fee
        plateform_fee_type = service_provider.plateform_fee_type
        tax_rate = service_provider.hsn_sac.tax_rate
        rate_amount = amount * (plateform_fee / 100) if plateform_fee_type == 'is_percent' else plateform_fee                      
        gst_amount = float(rate_amount) - (float(rate_amount)/(1+(float(tax_rate)/100)))

        admin_amount = rate_amount
    else:
        admin_amount=amount
        gst_amount=amount
    
    admin_wallet = PortalUserWallet.objects.get(pu_id=1)
    admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(admin_amount)
    admin_wallet.updated_at = now()
    admin_wallet.save()

    admin_gl = GlTrn.objects.create(
        service_trn_id=service_trn_id,
        pu_id=1,
        gl_tax_rate=tax_rate if tax_rate else None,
        gl_tax_amt=gst_amount,
        gl_trn_amt=admin_amount,
        effectvie_wallet='main_wallet',
        effectvie_amt=admin_amount,
        service_trn_table=table_name,
        effective_type='DR',
        gl_trn_dt=now(),
    )

    WalletTrn.objects.create(
        action_id=admin_gl.pk,
        action_type='Order',
        pu_id=1,
        wl_label=wl_label,
        effectvie_wallet='main_wallet',
        effectvie_amt=admin_amount,
        effective_type='DR',
        current_balance=admin_wallet.main_wallet,
        wl_trn_dt=now()
    )
    
    if is_self_config==False:
        admin_wallet = PortalUserWallet.objects.get(pu_id=1)
        if admin_charges_type == 'CR':
            admin_wallet.main_wallet = float(admin_wallet.main_wallet) + float(char_comm_amt)
        else:
            admin_wallet.main_wallet = float(admin_wallet.main_wallet) - float(char_comm_amt)
        admin_wallet.updated_at = now()
        admin_wallet.save()
        print('admin_charges_type', admin_charges_type)
        admin_gl = GlTrn.objects.create(
            service_trn_id=service_trn_id,
            pu_id=1,
            gl_tax_rate=gst_rate,
            gl_tax_amt=admin_tax_amt,
            gl_trn_amt=amount,
            effectvie_wallet='main_wallet',
            effectvie_amt=char_comm_amt,
            service_trn_table=table_name,
            effective_type=admin_charges_type,
            gl_trn_dt=now(),
        )
        print('admin_gl', admin_gl)
        WalletTrn.objects.create(
            action_id=service_trn_id,
            action_type='Order',
            pu_id=1,
            wl_label=wl_label,
            effectvie_wallet='main_wallet',
            effectvie_amt=char_comm_amt,
            effective_type=admin_charges_type,
            current_balance=admin_wallet.main_wallet,
            wl_trn_dt=now()
        )
    
    data = {
        'order_amount': amount,
        'id': request.user.id,
        'sp_id': sp_id,
        'customer_contact_no': contact_number,
        'customer_name': name,
        'trn_response': response_data,
        'service_trn': service_trn_id,
        'label': label,
        'category': category,
        'table_name': table_name,
        'charge_level': charge_level
    }
    print('before after tx_cal in charges calculation', data)
    after_tx_cal(request, data)
