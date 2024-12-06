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
    df = df.fillna("")
    
    # Create the root element
    envelope = ET.Element("ENVELOPE")

    # Add HEADER
    header = ET.SubElement(envelope, "HEADER")
    tally_request = ET.SubElement(header, "TALLYREQUEST")
    tally_request.text = "Import Data"

    # Add BODY
    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")

    # Add REQUESTDESC
    request_desc = ET.SubElement(import_data, "REQUESTDESC")
    report_name = ET.SubElement(request_desc, "REPORTNAME")
    report_name.text = "Vouchers"
    static_variables = ET.SubElement(request_desc, "STATICVARIABLES")
    sv_company = ET.SubElement(static_variables, "SVCURRENTCOMPANY")
    sv_company.text = "Techsolvo"

    # Add REQUESTDATA
    request_data = ET.SubElement(import_data, "REQUESTDATA")

    # Define a set to track created sales orders to prevent duplication
    created_sales_orders = set()

    # Helper function to normalize order names for duplicate checking within the CSV file
    def normalize_name(name):
        return re.sub(r'\s+', '', name).lower()
        
    for index, row in df.iterrows():
        # Normalize order name to prevent duplicates
        order_name = row['name']
        if normalize_name(order_name) in created_sales_orders:
            continue
        created_sales_orders.add(normalize_name(order_name))

        # Create TALLYMESSAGE element for each Sales Order
        tally_message = ET.SubElement(request_data, "TALLYMESSAGE")
        tally_message.set("xmlns:UDF", "TallyUDF")

        base_uuid = str(uuid.uuid4())
        # Generate unique identifiers
        remote_id = f"{base_uuid}-00000001"
        vch_key = f"{base_uuid}-0000b146:00000008"

        # Create VOUCHER element with necessary attributes
        voucher = ET.SubElement(tally_message, "VOUCHER")
        voucher.set("REMOTEID", remote_id)
        voucher.set("VCHKEY", vch_key)
        voucher.set("VCHTYPE", "Sales Order")
        voucher.set("ACTION", "Create")
        voucher.set("OBJVIEW", "Invoice Voucher View")

        # --- Static and Calculated Fields ---
        old_audit_entry_ids_list = ET.SubElement(voucher, "OLDAUDITENTRYIDS.LIST", {"TYPE": "Number"})
        # Create the OLDAUDITENTRYIDS element with text content "-1"
        old_audit_entry_ids = ET.Element("OLDAUDITENTRYIDS")
        old_audit_entry_ids.text = "-1"

        # Append OLDAUDITENTRYIDS to OLDAUDITENTRYIDS.LIST
        old_audit_entry_ids_list.append(old_audit_entry_ids)
        if 'transaction_date' in row and row['transaction_date']:
            day, month, year = row['transaction_date'].split("-")
            formatted_date = f"{year}{month}{day}"
        else:
            formatted_date = ""

        # Add the DATE element with the formatted date
        ET.SubElement(voucher, "DATE").text = formatted_date
        ET.SubElement(voucher, "GUID").text = remote_id
        ET.SubElement(voucher, "VATDEALERTYPE").text = "Unregistered"
        ET.SubElement(voucher, "NARRATION").text = saxutils.escape("New Sales Order")
        ET.SubElement(voucher, "COUNTRYOFRESIDENCE").text = saxutils.escape("India")
        ET.SubElement(voucher, "PARTYNAME").text = saxutils.escape(str(row['customer_name']))  # Updated to use 'customer_name'
        ET.SubElement(voucher, "PARTYLEDGERNAME").text = saxutils.escape(str(row['customer_name']))  
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = "Sales Order"
        ET.SubElement(voucher, "REFERENCE").text = saxutils.escape(str(row['name']))  # Order reference
        ET.SubElement(voucher, "VOUCHERNUMBER").text = str(index + 1)  # Voucher number
        ET.SubElement(voucher, "BASICBASEPARTYNAME").text = saxutils.escape(str(row['customer_name']))  # Updated to use 'customer_name'
        ET.SubElement(voucher, "CSTFORMISSUETYPE").text = saxutils.escape(str(row.get('cst_form_issue_type', '')))  # Dynamic value, default to empty
        ET.SubElement(voucher, "CSTFORMRECVTYPE").text = saxutils.escape(str(row.get('cst_form_recv_type', '')))  # Dynamic value, default to empty
        ET.SubElement(voucher, "FBTPAYMENTTYPE").text = saxutils.escape(str(row.get('payment_type', 'Default')))  # Default value if not present
        ET.SubElement(voucher, "PERSISTEDVIEW").text = "Invoice Voucher View"
        ET.SubElement(voucher, "BASICBUYERNAME").text = saxutils.escape(str(row['customer_name']))  # Updated to use 'customer_name'
        ET.SubElement(voucher, "VCHGSTCLASS").text = saxutils.escape(str(row.get('gst_category', '')))  # Dynamic GST class, default to empty

        # Static fields set to "No" or "Yes"
        no_elements = [
            "DIFFACTUALQTY", "ISMSTFROMSYNC", "ASORIGINAL", "AUDITED", "FORJOBCOSTING",
            "ISOPTIONAL", "USEFOREXCISE", "ISFORJOBWORKIN", "ALLOWCONSUMPTION",
            "USEFORINTEREST", "USEFORGAINLOSS", "USEFORGODOWNTRANSFER",
            "USEFORCOMPOUND", "USEFORSERVICETAX", "ISDELETED", "ISONHOLD",
            "ISBOENOTAPPLICABLE", "ISEXCISEVOUCHER", "EXCISETAXOVERRIDE",
            "USEFORTAXUNITTRANSFER", "IGNOREPOSVALIDATION", "EXCISEOPENING",
            "USEFORFINALPRODUCTION", "ISTDSOVERRIDDEN", "ISTCSOVERRIDDEN",
            "ISTDSTCSCASHVCH", "INCLUDEADVPYMTVCH", "ISSUBWORKSCONTRACT",
            "ISVATOVERRIDDEN", "IGNOREORIGVCHDATE", "ISVATPAIDATCUSTOMS",
            "ISDECLAREDTOCUSTOMS", "ISSERVICETAXOVERRIDDEN", "ISISDVOUCHER",
            "ISEXCISEOVERRIDDEN", "ISEXCISESUPPLYVCH", "ISGSTOVERRIDDEN",
            "GSTNOTEXPORTED", "IGNOREGSTINVALIDATION", "ISGSTREFUND",
            "ISGSTSECSEVENAPPLICABLE", "ISVATPRINCIPALACCOUNT", "ISSHIPPINGWITHINSTATE",
            "ISOVERSEASTOURISTTRANS", "ISDESIGNATEDZONEPARTY", "ISCANCELLED", 
            "ISPOSTDATED", "USETRACKINGNUMBER", "ISINVOICE", 
            "MFGJOURNAL", "HASDISCOUNTS", "ASPAYSLIP", "ISCOSTCENTRE", 
            "ISSTXNONREALIZEDVCH", "ISEXCISEMANUFACTURERON", "ISBLANKCHEQUE", 
            "ISVOID", "ORDERLINESTATUS", "VATISAGNSTCANCSALES", "VATISPURCEXEMPTED", 
            "ISVATRESTAXINVOICE", "VATISASSESABLECALCVCH", "ISDELIVERYSAMEASCONSIGNEE", 
            "ISDISPATCHSAMEASCONSIGNOR", "CHANGEVCHMODE" 
        ]

        yes_elements = ["HASCASHFLOW", "ISVATDUTYPAID"]
        for element_name in no_elements:
            ET.SubElement(voucher, element_name).text = "No"
        
        ET.SubElement(voucher, "ALTERID").text = str(index + 1)
        ET.SubElement(voucher, "MASTERID").text = str(index + 1)
        ET.SubElement(voucher, "VOUCHERKEY").text = vch_key
        ET.SubElement(voucher, "EFFECTIVEDATE").text = formatted_date

        for element_name in yes_elements:
            ET.SubElement(voucher, element_name).text = "Yes"

        # Create empty elements
        empty_elements = [
            "EWAYBILLDETAILS.LIST", "EXCLUDEDTAXATIONS.LIST", "OLDAUDITENTRIES.LIST", "ACCOUNTAUDITENTRIES.LIST", "AUDITENTRIES.LIST", "DUTYHEADDETAILS.LIST"
        ]

        for element_name in empty_elements:
            element = ET.SubElement(voucher, element_name)
            element.text = "      "

        # Create INVENTORYENTRIES.LIST
        inventory_entries = ET.SubElement(voucher, "INVENTORYENTRIES.LIST")

        # Map fields from row dictionary to XML elements
        ET.SubElement(inventory_entries, "STOCKITEMNAME").text = saxutils.escape(str(row.get("item_name")))
        ET.SubElement(inventory_entries, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(inventory_entries, "ISLASTDEEMEDPOSITIVE").text = "No"
        ET.SubElement(inventory_entries, "ISAUTONEGATE").text = "No"
        ET.SubElement(inventory_entries, "ISCUSTOMSCLEARANCE").text = "No"
        ET.SubElement(inventory_entries, "ISTRACKCOMPONENT").text = "No"
        ET.SubElement(inventory_entries, "ISTRACKPRODUCTION").text = "No"
        ET.SubElement(inventory_entries, "ISPRIMARYITEM").text = "No"
        ET.SubElement(inventory_entries, "ISSCRAP").text = "No"
        ET.SubElement(inventory_entries, "RATE").text = saxutils.escape(str(row.get('rate')))
        ET.SubElement(inventory_entries, "AMOUNT").text = saxutils.escape(str(row.get('total')))
        ET.SubElement(inventory_entries, "ACTUALQTY").text = saxutils.escape(str(row.get('stock_qty')))
        ET.SubElement(inventory_entries, "BILLEDQTY").text = saxutils.escape(str(row.get('stock_qty')))

        batch_allocation = ET.SubElement(inventory_entries, "BATCHALLOCATIONS.LIST")

        # Add sub-elements for BATCHALLOCATIONS
        ET.SubElement(batch_allocation, "BATCHNAME").text = saxutils.escape(row.get("batch_name", "Primary Batch"))
        ET.SubElement(batch_allocation, "INDENTNO").text = saxutils.escape(row.get("indent_no", ""))
        ET.SubElement(batch_allocation, "ORDERNO").text = str(row.get("name"))
        ET.SubElement(batch_allocation, "TRACKINGNUMBER").text = saxutils.escape(row.get("tracking_number", ""))
        ET.SubElement(batch_allocation, "DYNAMICCSTISCLEARED").text = "No"
        ET.SubElement(batch_allocation, "AMOUNT").text = saxutils.escape(str(row.get('total')))
        ET.SubElement(batch_allocation, "ACTUALQTY").text = saxutils.escape(str(row.get('stock_qty')))
        ET.SubElement(batch_allocation, "BILLEDQTY").text = saxutils.escape(str(row.get('stock_qty')))

        # Add ORDERDUEDATE with attributes
        td = saxutils.escape(str(row.get('transaction_date')))
        new_date_str = (datetime.strptime(td, "%d-%m-%Y") + timedelta(days=0)).strftime("%d-%b-%Y").lstrip("0")
        ET.SubElement(batch_allocation, "ORDERDUEDATE", JD=str(index+1), P=new_date_str).text = new_date_str

        empty_elements = [
            "ADDITIONALDETAILS.LIST", "VOUCHERCOMPONENTLIST.LIST"
        ]

        for element_name in empty_elements:
            element = ET.SubElement(batch_allocation, element_name)
            element.text = "      "

        def add_empty_element(parent, tag):
            element = ET.SubElement(parent, tag)
            element.text = "        "  # Ensure it has empty text for desired output

        amount = str(row.get('amount')) 
        # Create ACCOUNTINGALLOCATIONS.LIST and populate it
        accounting_allocations = ET.SubElement(inventory_entries, "ACCOUNTINGALLOCATIONS.LIST")
        # OLDAUDITENTRYIDS.LIST for ACCOUNTINGALLOCATIONS.LIST
        old_audit_entry_ids = ET.SubElement(accounting_allocations, "OLDAUDITENTRYIDS.LIST", TYPE="Number")
        ET.SubElement(old_audit_entry_ids, "OLDAUDITENTRYIDS").text = str(row.get('old_audit_entry_id', '-1'))

        # Populate ACCOUNTINGALLOCATIONS.LIST attributes
        ledger_name = 'SALORD'
        gst_class = str(row.get('gst_class', ''))
        is_deemed_positive = str(row.get('is_deemed_positive', 'Yes'))
        ledger_from_item = str(row.get('ledger_from_item', 'No'))
        remove_zero_entries = str(row.get('remove_zero_entries', 'No'))
        is_party_ledger = str(row.get('is_party_ledger', 'No'))
        is_last_deemed_positive = str(row.get('is_last_deemed_positive', 'Yes'))
        is_cap_vat_tax_altered = str(row.get('is_cap_vat_tax_altered', 'No'))
        is_cap_vat_not_claimed = str(row.get('is_cap_vat_not_claimed', 'No'))
        amount = str(row.get('amount'))

        # Add fields to ACCOUNTINGALLOCATIONS.LIST
        ET.SubElement(accounting_allocations, "LEDGERNAME").text = "SALORD"
        ET.SubElement(accounting_allocations, "GSTCLASS").text = gst_class
        ET.SubElement(accounting_allocations, "ISDEEMEDPOSITIVE").text = is_deemed_positive
        ET.SubElement(accounting_allocations, "LEDGERFROMITEM").text = ledger_from_item
        ET.SubElement(accounting_allocations, "REMOVEZEROENTRIES").text = remove_zero_entries
        ET.SubElement(accounting_allocations, "ISPARTYLEDGER").text = is_party_ledger
        ET.SubElement(accounting_allocations, "ISLASTDEEMEDPOSITIVE").text = is_last_deemed_positive
        ET.SubElement(accounting_allocations, "ISCAPVATTAXALTERED").text = is_cap_vat_tax_altered
        ET.SubElement(accounting_allocations, "ISCAPVATNOTCLAIMED").text = is_cap_vat_not_claimed
        ET.SubElement(accounting_allocations, "AMOUNT").text = amount

        # Add empty elements to ACCOUNTINGALLOCATIONS.LIST
        empty_tags = [
            "SERVICETAXDETAILS.LIST", "BANKALLOCATIONS.LIST", "BILLALLOCATIONS.LIST", "INTERESTCOLLECTION.LIST",
            "OLDAUDITENTRIES.LIST", "ACCOUNTAUDITENTRIES.LIST", "AUDITENTRIES.LIST", "INPUTCRALLOCS.LIST",
            "DUTYHEADDETAILS.LIST", "EXCISEDUTYHEADDETAILS.LIST", "RATEDETAILS.LIST", "SUMMARYALLOCS.LIST",
            "STPYMTDETAILS.LIST", "EXCISEPAYMENTALLOCATIONS.LIST", "TAXBILLALLOCATIONS.LIST", "TAXOBJECTALLOCATIONS.LIST",
            "TDSEXPENSEALLOCATIONS.LIST", "VATSTATUTORYDETAILS.LIST", "COSTTRACKALLOCATIONS.LIST", "REFVOUCHERDETAILS.LIST",
            "INVOICEWISEDETAILS.LIST", "VATITCDETAILS.LIST", "ADVANCETAXDETAILS.LIST"
        ]

        for tag in empty_tags:
            add_empty_element(accounting_allocations, tag)

        # Close ACCOUNTINGALLOCATIONS.LIST

        # Begin LEDGERENTRIES.LIST outside ACCOUNTINGALLOCATIONS.LIST
        ledger_entries = ET.SubElement(inventory_entries, "LEDGERENTRIES.LIST")

        # Populate LEDGERENTRIES.LIST fields
        ET.SubElement(ledger_entries, "LEDGERNAME").text = str(row.get('customer_name'))
        ET.SubElement(ledger_entries, "GSTCLASS").text = gst_class
        ET.SubElement(ledger_entries, "ISDEEMEDPOSITIVE").text = is_deemed_positive
        ET.SubElement(ledger_entries, "LEDGERFROMITEM").text = ledger_from_item
        ET.SubElement(ledger_entries, "REMOVEZEROENTRIES").text = remove_zero_entries
        ET.SubElement(ledger_entries, "ISPARTYLEDGER").text = is_party_ledger
        ET.SubElement(ledger_entries, "ISLASTDEEMEDPOSITIVE").text = is_last_deemed_positive
        ET.SubElement(ledger_entries, "ISCAPVATTAXALTERED").text = is_cap_vat_tax_altered
        ET.SubElement(ledger_entries, "ISCAPVATNOTCLAIMED").text = is_cap_vat_not_claimed
        ET.SubElement(ledger_entries, "AMOUNT").text = amount

        # Add empty elements to LEDGERENTRIES.LIST
        for tag in empty_tags + ["PAYROLLMODEOFPAYMENT.LIST", "ATTDRECORDS.LIST", "GSTEWAYCONSIGNORADDRESS.LIST", 
                                "GSTEWAYCONSIGNEEADDRESS.LIST", "TEMPGSTRATEDETAILS.LIST"]:
            add_empty_element(ledger_entries, tag)


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
        unique_filename = f'sales_order_output_{uuid.uuid4().hex[:8]}.xml'
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
