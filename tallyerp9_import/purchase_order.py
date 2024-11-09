import frappe
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import io, os
import re
import xml.sax.saxutils as saxutils
from datetime import datetime, timedelta

@frappe.whitelist()
def convert_csv_to_xml(doctype, docname, csv_file):
    try:
        file_doc = frappe.get_doc('File', {'file_url': csv_file})
        
        # Determine the correct file path for both public and private files
        if file_doc.is_private:
            # For private files
            file_path = frappe.get_site_path('private', 'files', file_doc.file_name)
        else:
            # For public files
            file_path = frappe.get_site_path('public', 'files', file_doc.file_name)
        
        print(f"File Path: {file_path}")
        print(f"Is Private: {file_doc.is_private}")
        
        # Check if the file exists
        if not os.path.exists(file_path):
            frappe.throw(f"File {file_path} not found")

    except Exception as file_error:
        frappe.log_error(f"File Retrieval Error: {str(file_error)}")
        frappe.throw(f"Error retrieving CSV file: {str(file_error)}")

    df = pd.read_csv(file_path, skiprows=[*range(0, 15), 16, 17, 18, 19], encoding='utf-8')
    df.columns = df.columns.str.strip()

    # Create the XML root
    envelope = ET.Element("ENVELOPE")

    # Create HEADER
    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Import Data"

    # Create BODY
    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")

    # Create REQUESTDESC
    request_desc = ET.SubElement(import_data, "REQUESTDESC")
    ET.SubElement(request_desc, "REPORTNAME").text = "Vouchers"
    static_variables = ET.SubElement(request_desc, "STATICVARIABLES")
    ET.SubElement(static_variables, "SVCURRENTCOMPANY").text = "Techsolvo"

    # Create REQUESTDATA
    request_data = ET.SubElement(import_data, "REQUESTDATA")

    # Iterate over the rows to create VOUCHER elements
    for _, row in df.iterrows():
        if 'transaction_date' in row and row['transaction_date']:
            day, month, year = row['transaction_date'].split("-")
            formatted_date = f"{year}{month}{day}"
        else:
            formatted_date = ""

        purchase_order_number = saxutils.escape(str(row.get('name', '')).strip())
        delivery_due_date = saxutils.escape(str(row.get('schedule_date', '')).strip())
        supplier_name = saxutils.escape(str(row.get('supplier_name', '')))
        amount = saxutils.escape(str(row.get('total', '')))

        # Create a unique GUID for this purchase order
        guid = str(uuid.uuid4())

        # Create VOUCHER element
        voucher = ET.SubElement(request_data, "TALLYMESSAGE", xmlns_UDF="TallyUDF")
        voucher_element = ET.SubElement(voucher, "VOUCHER", {
            "REMOTEID": f"{guid}-00000008",
            "VCHKEY": f"{guid}-0000b146:00000010",
            "VCHTYPE": "Purchase Order",
            "ACTION": "Create",
            "OBJVIEW": "Invoice Voucher View"
        })

        # Add fields to VOUCHER, Add OLDAUDITENTRYIDS.LIST
        old_audit_entry_ids = ET.SubElement(voucher_element, "OLDAUDITENTRYIDS.LIST", TYPE="Number")
        ET.SubElement(old_audit_entry_ids, "OLDAUDITENTRYIDS").text = str(row.get('old_audit_entry_id', '-1'))  # Default to -1 if not present
        ET.SubElement(voucher_element, "DATE").text = formatted_date
        ET.SubElement(voucher_element, "GUID").text = f"{guid}-00000008"
        ET.SubElement(voucher_element, "COUNTRYOFRESIDENCE").text = str(row.get('country_of_residence', 'India'))  # Default to India
        ET.SubElement(voucher_element, "PLACEOFSUPPLY").text = str(row.get('shipping_address', 'Delhi'))  # Default to Delhi
        ET.SubElement(voucher_element, "PARTYNAME").text = saxutils.escape(str(row['supplier'])) 
        ET.SubElement(voucher_element, "PARTYLEDGERNAME").text = supplier_name  # Assuming same as PARTYNAME
        ET.SubElement(voucher_element, "VOUCHERTYPENAME").text = str(row.get('voucher_type_name', 'Purchase Order'))  # Default to Purchase Order
        ET.SubElement(voucher_element, "REFERENCE").text = purchase_order_number
        ET.SubElement(voucher_element, "VOUCHERNUMBER").text = str(row.get('voucher_number', '1'))  # Assuming constant value
        ET.SubElement(voucher_element, "BASICBASEPARTYNAME").text = supplier_name
        ET.SubElement(voucher_element, "CSTFORMISSUETYPE").text = str(row.get('cst_form_issue_type', ''))
        ET.SubElement(voucher_element, "CSTFORMRECVTYPE").text = str(row.get('cst_form_recv_type', ''))
        ET.SubElement(voucher_element, "FBTPAYMENTTYPE").text = str(row.get('fbt_payment_type', 'Default'))  # Default to Default
        ET.SubElement(voucher_element, "PERSISTEDVIEW").text = str(row.get('persisted_view', 'Invoice Voucher View'))  # Default to Invoice Voucher View
        ET.SubElement(voucher_element, "BASICBUYERNAME").text = str(row.get('basic_buyer_name', 'Techsolvo'))  # Default to Techsolvo
        ET.SubElement(voucher_element, "VCHGSTCLASS").text = str(row.get('vch_gst_class', ''))
        ET.SubElement(voucher_element, "DIFFACTUALQTY").text = str(row.get('diff_actual_qty', 'No'))
        ET.SubElement(voucher_element, "ISMSTFROMSYNC").text = str(row.get('is_mst_from_sync', 'No'))
        ET.SubElement(voucher_element, "ASORIGINAL").text = str(row.get('as_original', 'No'))
        ET.SubElement(voucher_element, "AUDITED").text = str(row.get('audited', 'No'))
        ET.SubElement(voucher_element, "FORJOBCOSTING").text = str(row.get('for_job_costing', 'No'))
        ET.SubElement(voucher_element, "ISOPTIONAL").text = str(row.get('is_optional', 'No'))
        ET.SubElement(voucher_element, "EFFECTIVEDATE").text = formatted_date
        ET.SubElement(voucher_element, "USEFOREXCISE").text = str(row.get('use_for_excise', 'No'))
        ET.SubElement(voucher_element, "ISFORJOBWORKIN").text = str(row.get('is_for_job_work_in', 'No'))
        ET.SubElement(voucher_element, "ALLOWCONSUMPTION").text = str(row.get('allow_consumption', 'No'))
        ET.SubElement(voucher_element, "USEFORINTEREST").text = str(row.get('use_for_interest', 'No'))
        ET.SubElement(voucher_element, "USEFORGAINLOSS").text = str(row.get('use_for_gain_loss', 'No'))
        ET.SubElement(voucher_element, "USEFORGODOWNTRANSFER").text = str(row.get('use_for_godown_transfer', 'No'))
        ET.SubElement(voucher_element, "USEFORCOMPOUND").text = str(row.get('use_for_compound', 'No'))
        ET.SubElement(voucher_element, "USEFORSERVICETAX").text = str(row.get('use_for_service_tax', 'No'))
        ET.SubElement(voucher_element, "ISDELETED").text = str(row.get('is_deleted', 'No'))
        ET.SubElement(voucher_element, "ISONHOLD").text = str(row.get('is_on_hold', 'No'))
        ET.SubElement(voucher_element, "ISBOENOTAPPLICABLE").text = str(row.get('is_boe_not_applicable', 'No'))
        ET.SubElement(voucher_element, "ISEXCISEVOUCHER").text = str(row.get('is_excise_voucher', 'No'))
        ET.SubElement(voucher_element, "EXCISETAXOVERRIDE").text = str(row.get('excise_tax_override', 'No'))
        ET.SubElement(voucher_element, "USEFORTAXUNITTRANSFER").text = str(row.get('use_for_tax_unit_transfer', 'No'))
        ET.SubElement(voucher_element, "IGNOREPOSVALIDATION").text = str(row.get('ignore_pos_validation', 'No'))
        ET.SubElement(voucher_element, "EXCISEOPENING").text = str(row.get('excise_opening', 'No'))
        ET.SubElement(voucher_element, "USEFORFINALPRODUCTION").text = str(row.get('use_for_final_production', 'No'))
        ET.SubElement(voucher_element, "ISTDSOVERRIDDEN").text = str(row.get('is_tds_overridden', 'No'))
        ET.SubElement(voucher_element, "ISTCSOVERRIDDEN").text = str(row.get('is_tcs_overridden', 'No'))
        ET.SubElement(voucher_element, "ISTDSTCSCASHVCH").text = str(row.get('is_tds_tcs_cash_vch', 'No'))
        ET.SubElement(voucher_element, "INCLUDEADVPYMTVCH").text = str(row.get('include_adv_payment_vch', 'No'))
        ET.SubElement(voucher_element, "ISSUBWORKSCONTRACT").text = str(row.get('is_sub_works_contract', 'No'))
        ET.SubElement(voucher_element, "ISVATOVERRIDDEN").text = str(row.get('is_vat_overridden', 'No'))
        ET.SubElement(voucher_element, "IGNOREORIGVCHDATE").text = str(row.get('ignore_orig_vch_date', 'No'))
        ET.SubElement(voucher_element, "ISVATPAIDATCUSTOMS").text = str(row.get('is_vat_paid_at_customs', 'No'))
        ET.SubElement(voucher_element, "ISDECLAREDTOCUSTOMS").text = str(row.get('is_declared_to_customs', 'No'))
        ET.SubElement(voucher_element, "ISSERVICETAXOVERRIDDEN").text = str(row.get('is_service_tax_overridden', 'No'))
        ET.SubElement(voucher_element, "ISISDVOUCHER").text = str(row.get('is_isd_voucher', 'No'))
        ET.SubElement(voucher_element, "ISEXCISEOVERRIDDEN").text = str(row.get('is_excise_overridden', 'No'))
        ET.SubElement(voucher_element, "ISEXCISESUPPLYVCH").text = str(row.get('is_excise_supply_vch', 'No'))
        ET.SubElement(voucher_element, "ISGSTOVERRIDDEN").text = str(row.get('is_gst_overridden', 'No'))
        ET.SubElement(voucher_element, "GSTNOTEXPORTED").text = str(row.get('gst_not_exported', 'No'))
        ET.SubElement(voucher_element, "IGNOREGSTINVALIDATION").text = str(row.get('ignore_gst_invalidation', 'No'))
        ET.SubElement(voucher_element, "ISGSTREFUND").text = str(row.get('is_gst_refund', 'No'))
        ET.SubElement(voucher_element, "ISGSTSECSEVENAPPLICABLE").text = str(row.get('is_gst_sec_seven_applicable', 'No'))
        ET.SubElement(voucher_element, "ISVATPRINCIPALACCOUNT").text = str(row.get('is_vat_principal_account', 'No'))
        ET.SubElement(voucher_element, "ISSHIPPINGWITHINSTATE").text = str(row.get('is_shipping_within_state', 'No'))
        ET.SubElement(voucher_element, "ISOVERSEASTOURISTTRANS").text = str(row.get('is_overseas_tourist_trans', 'No'))
        ET.SubElement(voucher_element, "ISDESIGNATEDZONEPARTY").text = str(row.get('is_designated_zone_party', 'No'))
        ET.SubElement(voucher_element, "ISCANCELLED").text = str(row.get('is_cancelled', 'No'))
        ET.SubElement(voucher_element, "HASCASHFLOW").text = str(row.get('has_cash_flow', 'No'))
        ET.SubElement(voucher_element, "ISPOSTDATED").text = str(row.get('is_post_dated', 'No'))
        ET.SubElement(voucher_element, "USETRACKINGNUMBER").text = str(row.get('use_tracking_number', 'No'))
        ET.SubElement(voucher_element, "ISINVOICE").text = str(row.get('is_invoice', 'Yes'))
        ET.SubElement(voucher_element, "ISJOURNAL").text = str(row.get('is_journal', 'No'))
        ET.SubElement(voucher_element, "HASDISCOUNTS").text = str(row.get('has_discounts', 'No'))
        ET.SubElement(voucher_element, "ASPAYSLIP").text = str(row.get('as_pay_slip', 'No'))
        ET.SubElement(voucher_element, "ISCOSTCENTRE").text = str(row.get('is_cost_centre', 'No'))
        ET.SubElement(voucher_element, "ISSTXNONREALIZEDVCH").text = str(row.get('is_stx_non_realized_vch', 'No'))
        ET.SubElement(voucher_element, "ISEXCISEMANUFACTURERON").text = str(row.get('is_excise_manufacturer_on', 'No'))
        ET.SubElement(voucher_element, "ISBLANKCHEQUE").text = str(row.get('is_blank_cheque', 'No'))
        ET.SubElement(voucher_element, "ISVOID").text = str(row.get('is_void', 'No'))
        ET.SubElement(voucher_element, "ORDERLINESTATUS").text = str(row.get('order_line_status', 'No'))
        ET.SubElement(voucher_element, "VATISAGNSTCANCSALES").text = str(row.get('vat_is_against_cancel_sales', 'No'))
        ET.SubElement(voucher_element, "VATISPURCEXEMPTED").text = str(row.get('vat_is_purchase_exempted', 'No'))
        ET.SubElement(voucher_element, "ISVATRESTAXINVOICE").text = str(row.get('is_vat_rest_tax_invoice', 'No'))
        ET.SubElement(voucher_element, "VATISASSESABLECALCVCH").text = str(row.get('vat_is_assessable_calc_vch', 'No'))
        ET.SubElement(voucher_element, "ISVATDUTYPAID").text = str(row.get('is_vat_duty_paid', 'Yes'))
        ET.SubElement(voucher_element, "ISDELIVERYSAMEASCONSIGNEE").text = str(row.get('is_delivery_same_as_consignee', 'No'))
        ET.SubElement(voucher_element, "ISDISPATCHSAMEASCONSIGNOR").text = str(row.get('is_dispatch_same_as consignor', 'No'))
        ET.SubElement(voucher_element, "CHANGEVCHMODE").text = str(row.get('change_vch_mode', 'No'))
        ET.SubElement(voucher_element, "ALTERID").text = str(row.get('alter_id', _+1)) 
        ET.SubElement(voucher_element, "MASTERID").text = str(row.get('master_id', _+1))  
        ET.SubElement(voucher_element, "VOUCHERKEY").text = str(row.get('voucher_key', '194914205827104'))  
        ET.SubElement(voucher_element, "EWAYBILLDETAILS.LIST").text = "     " 
        ET.SubElement(voucher_element, "EXCLUDEDTAXATIONS.LIST").text = "     "
        # Add OLDAUDITENTRIES.LIST
        ET.SubElement(voucher_element, "OLDAUDITENTRIES.LIST").text = "     "
        # Add ACCOUNTAUDITENTRIES.LIST
        account_audit_entries = ET.SubElement(voucher_element, "ACCOUNTAUDITENTRIES.LIST").text = "     "
        # Add necessary sub-elements to ACCOUNTINGAUDITENTRIES.LIST if needed
        # Add AUDITENTRIES.LIST
        ET.SubElement(voucher_element, "AUDITENTRIES.LIST").text = "     "
        # Add DUTYHEADDETAILS.LIST
        ET.SubElement(voucher_element, "DUTYHEADDETAILS.LIST").text = "     "
        # Add INVENTORYENTRIES.LIST
        inventory_entries = ET.SubElement(voucher_element, "INVENTORYENTRIES.LIST")
        item_name = saxutils.escape(str(row.get('item_name')))
        is_deemed_positive = saxutils.escape(str(row.get('is_deemed_positive', 'Yes')))
        is_last_deemed_positive = saxutils.escape(str(row.get('is_last_deemed_positive', 'Yes')))
        is_auto_negate = saxutils.escape(str(row.get('is_auto_negate', 'No')))
        is_customs_clearance = saxutils.escape(str(row.get('is_customs_clearance', 'No')))
        is_track_component = saxutils.escape(str(row.get('is_track_component', 'No')))
        is_track_production = saxutils.escape(str(row.get('is_track_production', 'No')))
        is_primary_item = saxutils.escape(str(row.get('is_primary_item', 'No')))
        is_scrap = saxutils.escape(str(row.get('is_scrap', 'No')))
        rate = saxutils.escape(str(row.get('base_rate')))  # Adjust as necessary
        amount = saxutils.escape(str(row.get('amount')))  # Adjust as necessary
        actual_qty = saxutils.escape(str(row.get('qty')))  # Adjust as necessary
        billed_qty = saxutils.escape(str(row.get('qty')))  # Adjust as necessary
        # Add details inside INVENTORYENTRIES.LIST
        ET.SubElement(inventory_entries, "STOCKITEMNAME").text = item_name
        ET.SubElement(inventory_entries, "ISDEEMEDPOSITIVE").text = is_deemed_positive
        ET.SubElement(inventory_entries, "ISLASTDEEMEDPOSITIVE").text = is_last_deemed_positive
        ET.SubElement(inventory_entries, "ISAUTONEGATE").text = is_auto_negate
        ET.SubElement(inventory_entries, "ISCUSTOMSCLEARANCE").text = is_customs_clearance
        ET.SubElement(inventory_entries, "ISTRACKCOMPONENT").text = is_track_component
        ET.SubElement(inventory_entries, "ISTRACKPRODUCTION").text = is_track_production
        ET.SubElement(inventory_entries, "ISPRIMARYITEM").text = is_primary_item
        ET.SubElement(inventory_entries, "ISSCRAP").text = is_scrap
        ET.SubElement(inventory_entries, "RATE").text = rate
        ET.SubElement(inventory_entries, "AMOUNT").text = amount
        ET.SubElement(inventory_entries, "ACTUALQTY").text = actual_qty
        ET.SubElement(inventory_entries, "BILLEDQTY").text = billed_qty
        # Create BATCHALLOCATIONS.LIST element
        batch_allocations = ET.SubElement(inventory_entries, "BATCHALLOCATIONS.LIST")
        # Assuming 'row' contains the relevant data
        batch_name = str(row.get('batch_name', 'Primary Batch'))  # Default to "Primary Batch"
        indent_no = str(row.get('indent_no', ''))  # Default to empty string
        order_no = str(row.get('name', 'PUR/ORD/001_24'))  # Default to "PUR/ORD/001_24"
        tracking_number = str(row.get('tracking_number', ''))  # Default to empty string
        dynamic_cst_is_cleared = str(row.get('dynamic_cst_is_cleared', 'No'))  # Default to "No"
        amount = str(row.get('amount')) 
        actual_qty = str(row.get('stock_qty'))  
        billed_qty = str(row.get('stock_qty')) 
        order_due_date = str(row.get('order_due_date'))  
        order_due_date_jd = str(row.get('order_due_date_jd')) 
        order_due_date_p = str(row.get('order_due_date_p'))  
        # Add elements to BATCHALLOCATIONS.LIST
        ET.SubElement(batch_allocations, "BATCHNAME").text = batch_name
        ET.SubElement(batch_allocations, "INDENTNO").text = indent_no
        ET.SubElement(batch_allocations, "ORDERNO").text = order_no
        ET.SubElement(batch_allocations, "TRACKINGNUMBER").text = tracking_number
        ET.SubElement(batch_allocations, "DYNAMICCSTISCLEARED").text = dynamic_cst_is_cleared
        ET.SubElement(batch_allocations, "AMOUNT").text = amount
        ET.SubElement(batch_allocations, "ACTUALQTY").text = actual_qty
        ET.SubElement(batch_allocations, "BILLEDQTY").text = billed_qty
        td = saxutils.escape(str(row.get('transaction_date')))
        new_date_str = (datetime.strptime(td, "%d-%m-%Y") + timedelta(days=0)).strftime("%d-%b-%Y").lstrip("0")
        ET.SubElement(batch_allocations, "ORDERDUEDATE", JD=str(_+1), P=new_date_str).text = new_date_str
        ET.SubElement(batch_allocations, "ADDITIONALDETAILS.LIST").text = "     "
        ET.SubElement(batch_allocations, "VOUCHERCOMPONENTLIST.LIST").text = "     "
        # Add ACCOUNTINGALLOCATIONS.LIST
        accounting_allocations = ET.SubElement(inventory_entries, "ACCOUNTINGALLOCATIONS.LIST")
        # OLDAUDITENTRYIDS.LIST
        old_audit_entry_ids = ET.SubElement(accounting_allocations, "OLDAUDITENTRYIDS.LIST", TYPE="Number")
        ET.SubElement(old_audit_entry_ids, "OLDAUDITENTRYIDS").text = str(row.get('old_audit_entry_id', '-1'))   
        gst_class = str(row.get('gst_class', ''))  # Default to empty string
        is_deemed_positive = str(row.get('is_deemed_positive', 'Yes'))  # Default to "Yes"
        ledger_from_item = str(row.get('ledger_from_item', 'No'))  # Default to "No"
        remove_zero_entries = str(row.get('remove_zero_entries', 'No'))  # Default to "No"
        is_party_ledger = str(row.get('is_party_ledger', 'No'))  # Default to "No"
        is_last_deemed_positive = str(row.get('is_last_deemed_positive', 'Yes'))  # Default to "Yes"
        is_cap_vat_tax_altered = str(row.get('is_cap_vat_tax_altered', 'No'))  # Default to "No"
        is_cap_vat_not_claimed = str(row.get('is_cap_vat_not_claimed', 'No'))  # Default to "No"
        amount = str(row.get('amount'))  
        # Add elements to ACCOUNTINGALLOCATIONS.LIST
        ET.SubElement(accounting_allocations, "LEDGERNAME").text = "PRCORD" 
        ET.SubElement(accounting_allocations, "GSTCLASS").text = gst_class
        ET.SubElement(accounting_allocations, "ISDEEMEDPOSITIVE").text = is_deemed_positive
        ET.SubElement(accounting_allocations, "LEDGERFROMITEM").text = ledger_from_item
        ET.SubElement(accounting_allocations, "REMOVEZEROENTRIES").text = remove_zero_entries
        ET.SubElement(accounting_allocations, "ISPARTYLEDGER").text = is_party_ledger
        ET.SubElement(accounting_allocations, "ISLASTDEEMEDPOSITIVE").text = is_last_deemed_positive
        ET.SubElement(accounting_allocations, "ISCAPVATTAXALTERED").text = is_cap_vat_tax_altered
        ET.SubElement(accounting_allocations, "ISCAPVATNOTCLAIMED").text = is_cap_vat_not_claimed
        ET.SubElement(accounting_allocations, "AMOUNT").text = amount

        # Add closed sub-lists with empty content
        def add_empty_element(parent, tag):
            element = ET.SubElement(parent, tag)
            element.text = "        "  # Ensure it has empty text for desired output

        add_empty_element(accounting_allocations, "SERVICETAXDETAILS.LIST")
        add_empty_element(accounting_allocations, "BANKALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "BILLALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "INTERESTCOLLECTION.LIST")
        add_empty_element(accounting_allocations, "OLDAUDITENTRIES.LIST")
        add_empty_element(accounting_allocations, "ACCOUNTAUDITENTRIES.LIST")
        add_empty_element(accounting_allocations, "AUDITENTRIES.LIST")
        add_empty_element(accounting_allocations, "INPUTCRALLOCS.LIST")
        add_empty_element(accounting_allocations, "DUTYHEADDETAILS.LIST")
        add_empty_element(accounting_allocations, "EXCISEDUTYHEADDETAILS.LIST")
        add_empty_element(accounting_allocations, "RATEDETAILS.LIST")
        add_empty_element(accounting_allocations, "SUMMARYALLOCS.LIST")
        add_empty_element(accounting_allocations, "STPYMTDETAILS.LIST")
        add_empty_element(accounting_allocations, "EXCISEPAYMENTALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "TAXBILLALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "TAXOBJECTALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "TDSEXPENSEALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "VATSTATUTORYDETAILS.LIST")
        add_empty_element(accounting_allocations, "COSTTRACKALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "REFVOUCHERDETAILS.LIST")
        add_empty_element(accounting_allocations, "INVOICEWISEDETAILS.LIST")
        add_empty_element(accounting_allocations, "VATITCDETAILS.LIST")
        add_empty_element(accounting_allocations, "ADVANCETAXDETAILS.LIST")

        def add_empty_element(parent, tag):
            element = ET.SubElement(parent, tag)
            element.text = "        "  

        # Create the ACCOUNTINGALLOCATIONS.LIST element
        accounting_allocations = ET.SubElement(inventory_entries, "ACCOUNTINGALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "DUTYHEADDETAILS.LIST")
        add_empty_element(accounting_allocations, "SUPPLEMENTARYDUTYHEADDETAILS.LIST")
        add_empty_element(accounting_allocations, "TAXOBJECTALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "REFVOUCHERDETAILS.LIST")
        add_empty_element(accounting_allocations, "EXCISEALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "EXPENSEALLOCATIONS.LIST")
        add_empty_element(accounting_allocations, "INVOICEDELNOTES.LIST")
        add_empty_element(accounting_allocations, "INVOICEORDERLIST.LIST")
        add_empty_element(accounting_allocations, "INVOICEINDENTLIST.LIST")
        add_empty_element(accounting_allocations, "ATTENDANCEENTRIES.LIST")
        add_empty_element(accounting_allocations, "ORIGINVOICEDETAILS.LIST")
        add_empty_element(accounting_allocations, "INVOICEEXPORTLIST.LIST")

        # Creating LEDGERENTRIES.LIST with nested elements
        ledger_entries = ET.SubElement(accounting_allocations, "LEDGERENTRIES.LIST")
        old_audit_entry_ids_list = ET.SubElement(ledger_entries, "OLDAUDITENTRYIDS.LIST", TYPE="Number")
        ET.SubElement(old_audit_entry_ids_list, "OLDAUDITENTRYIDS").text = str(row.get('old_audit_entry_id', '-1'))  # Default to -1 if not present
        # Assuming 'row' contains the relevant data
        gst_class = str(row.get('gst_class', 'Standard Rate')) 
        is_deemed_positive = str(row.get('is_deemed_positive', 'No'))  # Default to "No"
        ledger_from_item = str(row.get('ledger_from_item', 'No'))  # Default to "No"
        remove_zero_entries = str(row.get('remove_zero_entries', 'No'))  # Default to "No"
        is_party_ledger = str(row.get('is_party_ledger', 'Yes'))  # Default to "Yes"
        is_last_deemed_positive = str(row.get('is_last_deemed_positive', 'No'))  # Default to "No"
        is_cap_vat_tax_altered = str(row.get('is_cap_vat_tax_altered', 'No'))  # Default to "No"
        is_cap_vat_not_claimed = str(row.get('is_cap_vat_not_claimed', 'No'))  # Default to "No"
        amount = str(row.get('amount')) 

        # Add elements to LEDGERENTRIES.LIST
        ET.SubElement(ledger_entries, "LEDGERNAME").text = str(row.get('supplier_name'))
        ET.SubElement(ledger_entries, "GSTCLASS").text = gst_class
        ET.SubElement(ledger_entries, "ISDEEMEDPOSITIVE").text = is_deemed_positive
        ET.SubElement(ledger_entries, "LEDGERFROMITEM").text = ledger_from_item
        ET.SubElement(ledger_entries, "REMOVEZEROENTRIES").text = remove_zero_entries
        ET.SubElement(ledger_entries, "ISPARTYLEDGER").text = is_party_ledger
        ET.SubElement(ledger_entries, "ISLASTDEEMEDPOSITIVE").text = is_last_deemed_positive
        ET.SubElement(ledger_entries, "ISCAPVATTAXALTERED").text = is_cap_vat_tax_altered
        ET.SubElement(ledger_entries, "ISCAPVATNOTCLAIMED").text = is_cap_vat_not_claimed
        ET.SubElement(ledger_entries, "AMOUNT").text = amount
        add_empty_element(ledger_entries, "SERVICETAXDETAILS.LIST")
        add_empty_element(ledger_entries, "BANKALLOCATIONS.LIST")
        add_empty_element(ledger_entries, "BILLALLOCATIONS.LIST")
        add_empty_element(ledger_entries, "INTERESTCOLLECTION.LIST")
        add_empty_element(ledger_entries, "OLDAUDITENTRIES.LIST")
        add_empty_element(ledger_entries, "ACCOUNTAUDITENTRIES.LIST")
        add_empty_element(ledger_entries, "AUDITENTRIES.LIST")
        add_empty_element(ledger_entries, "INPUTCRALLOCS.LIST")
        add_empty_element(ledger_entries, "DUTYHEADDETAILS.LIST")
        add_empty_element(ledger_entries, "EXCISEDUTYHEADDETAILS.LIST")
        add_empty_element(ledger_entries, "RATEDETAILS.LIST")
        add_empty_element(ledger_entries, "SUMMARYALLOCS.LIST")
        add_empty_element(ledger_entries, "STPYMTDETAILS.LIST")
        add_empty_element(ledger_entries, "EXCISEPAYMENTALLOCATIONS.LIST")
        add_empty_element(ledger_entries, "TAXBILLALLOCATIONS.LIST")
        add_empty_element(ledger_entries, "TAXOBJECTALLOCATIONS.LIST")
        add_empty_element(ledger_entries, "TDSEXPENSEALLOCATIONS.LIST")
        add_empty_element(ledger_entries, "VATSTATUTORYDETAILS.LIST")
        add_empty_element(ledger_entries, "COSTTRACKALLOCATIONS.LIST")
        add_empty_element(ledger_entries, "REFVOUCHERDETAILS.LIST")
        add_empty_element(ledger_entries, "INVOICEWISEDETAILS.LIST")
        add_empty_element(ledger_entries, "VATITCDETAILS.LIST")
        add_empty_element(ledger_entries, "ADVANCETAXDETAILS.LIST")
        add_empty_element(accounting_allocations, "PAYROLLMODEOFPAYMENT.LIST")
        add_empty_element(accounting_allocations, "ATTDRECORDS.LIST")
        add_empty_element(accounting_allocations, "GSTEWAYCONSIGNORADDRESS.LIST")
        add_empty_element(accounting_allocations, "GSTEWAYCONSIGNEEADDRESS.LIST")
        add_empty_element(accounting_allocations, "TEMPGSTRATEDETAILS.LIST")

    xml_str = ET.tostring(envelope, encoding='utf-8')
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml_as_string = parsed_xml.toprettyxml(indent="  ")

    try:
        # Save XML to a file
        xml_dir = frappe.get_site_path('public', 'files')
        if not os.path.exists(xml_dir):
            os.makedirs(xml_dir)
            print(f"Created directory: {xml_dir}")

        # Generate a unique filename to prevent overwriting
        unique_filename = f'purchase_order_output_{uuid.uuid4().hex[:8]}.xml'
        xml_file_path = os.path.join(xml_dir, unique_filename)

        try:
            with open(xml_file_path, 'w', encoding='utf-8') as xml_file:
                xml_file.write(pretty_xml_as_string)
            print(f"XML file created successfully at: {xml_file_path}")
        except Exception as e:
            print(f"Error saving XML file: {str(e)}")
            frappe.throw(f"Error saving XML file: {str(e)}")

        # Create Frappe File document
        try:
            # Construct a proper file URL
            site_name = frappe.local.site
            file_url = f'/files/{unique_filename}'
            
            file_doc = frappe.get_doc({
                'doctype': 'File',
                'file_name': unique_filename,
                'file_url': file_url,
                'is_private': 0,
                'folder': 'Home/Attachments'
            }).insert(ignore_permissions=True)
            print(f"Frappe File document created: {file_doc.name}")

        except Exception as e:
            print(f"Error creating Frappe File document: {str(e)}")
            frappe.throw(f"Error creating Frappe File document: {str(e)}")

        # Return file details with a full URL
        return {
            'file_url': file_url,
            'file_name': unique_filename,
            'file_path': xml_file_path
        }
    
    except Exception as main_error:
        print(f"Main error: {str(main_error)}")
        frappe.log_error(f"XML Generation Error: {str(main_error)}")
        frappe.throw(f"Error in generating XML file: {str(main_error)}")