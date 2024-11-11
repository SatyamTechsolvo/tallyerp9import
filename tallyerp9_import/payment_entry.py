import frappe
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import xml.sax.saxutils as saxutils
import uuid
import os

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

    try:
        # Load CSV, skipping unwanted rows
        df = pd.read_csv(file_path, skiprows=[*range(0, 15), 16, 17, 18, 19])
        df.columns = df.columns.str.strip()  # Strip any whitespace from column names
    except FileNotFoundError:
        print("CSV file not found at the specified path.")
        exit(1)

    # Create the XML root
    envelope = ET.Element("ENVELOPE")

    # Create HEADER
    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Import Data"

    # Create BODY
    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")

    request_desc = ET.SubElement(import_data, "REQUESTDESC")
    ET.SubElement(request_desc, "REPORTNAME").text = "Vouchers"
    static_variables = ET.SubElement(request_desc, "STATICVARIABLES")
    ET.SubElement(static_variables, "SVCURRENTCOMPANY").text = "Techsolvo"

    # Create REQUESTDATA
    request_data = ET.SubElement(import_data, "REQUESTDATA")

    # Iterate over rows to create VOUCHER elements
    for _, row in df.iterrows():
        # Format transaction date
        posting_date = row.get('posting_date', '')
        if pd.notna(posting_date):
            try:
                day, month, year = posting_date.split("-")
                formatted_date = f"{year}{month}{day}"
            except ValueError:
                print(f"Date format issue with {posting_date}")
                formatted_date = ""
        else:
            formatted_date = ""

        # Extract other required fields
        party_name = saxutils.escape(str(row.get('party_name', '')))
        voucher_number = saxutils.escape(str(row.get('payment_order', '')))
        amount = saxutils.escape(str(float(row.get('received_amount', 0)) + float(row.get('total_taxes_and_charges', 0))))
        
        # Create a unique GUID for each entry
        guid = str(uuid.uuid4())

        # Create VOUCHER element for payment entry
        voucher = ET.SubElement(request_data, "TALLYMESSAGE", xmlns_UDF="TallyUDF")
        voucher_element = ET.SubElement(voucher, "VOUCHER", {
            "REMOTEID": f"{guid}-000000bf",
            "VCHKEY": f"{guid}-0000b146:00000088",
            "VCHTYPE": "Payment",
            "ACTION": "Create",
            "OBJVIEW": "Accounting Voucher View"
        })

        # Add OLDAUDITENTRYIDS.LIST
        old_audit_entry_ids = ET.SubElement(voucher_element, "OLDAUDITENTRYIDS.LIST", TYPE="Number")
        ET.SubElement(old_audit_entry_ids, "OLDAUDITENTRYIDS").text = "-1"

        # Add DATE and GUID
        ET.SubElement(voucher_element, "DATE").text = formatted_date
        ET.SubElement(voucher_element, "GUID").text = guid
        
        # Add PARTYLEDGERNAME
        ET.SubElement(voucher_element, "PARTYLEDGERNAME").text = "Cash"

        # Add VOUCHERTYPENAME and other elements specific to Payment entry
        ET.SubElement(voucher_element, "VOUCHERTYPENAME").text = "Payment"
        ET.SubElement(voucher_element, "VOUCHERNUMBER").text = voucher_number
        ET.SubElement(voucher_element, "FBTPAYMENTTYPE").text = "Default"
        ET.SubElement(voucher_element, "PERSISTEDVIEW").text = "Accounting Voucher View"

        # Add additional fields as per the provided XML structure
        ET.SubElement(voucher_element, "CSTFORMISSUETYPE").text = ""
        ET.SubElement(voucher_element, "CSTFORMRECVTYPE").text = ""
        ET.SubElement(voucher_element, "VCHGSTCLASS").text = ""
        ET.SubElement(voucher_element, "DIFFACTUALQTY").text = "No"
        ET.SubElement(voucher_element, "ISMSTFROMSYNC").text = "No"
        ET.SubElement(voucher_element, "ASORIGINAL").text = "No"
        ET.SubElement(voucher_element, "AUDITED").text = "No"
        ET.SubElement(voucher_element, "FORJOBCOSTING").text = "No"
        ET.SubElement(voucher_element, "ISOPTIONAL").text = "No"
        ET.SubElement(voucher_element, "EFFECTIVEDATE").text = formatted_date
        ET.SubElement(voucher_element, "USEFOREXCISE").text = "No"
        ET.SubElement(voucher_element, "ISFORJOBWORKIN").text = "No"
        ET.SubElement(voucher_element, "ALLOWCONSUMPTION").text = "No"
        ET.SubElement(voucher_element, "USEFORINTEREST").text = "No"
        ET.SubElement(voucher_element, "USEFORGAINLOSS").text = "No"
        ET.SubElement(voucher_element, "USEFORGODOWNTRANSFER").text = "No"
        ET.SubElement(voucher_element, "USEFORCOMPOUND").text = "No"
        ET.SubElement(voucher_element, "USEFORSERVICETAX").text = "No"
        ET.SubElement(voucher_element, "ISDELETED").text = "No"
        ET.SubElement(voucher_element, "ISONHOLD").text = "No"
        ET.SubElement(voucher_element, "ISBOENOTAPPLICABLE").text = "No"
        ET.SubElement(voucher_element, "ISEXCISEVOUCHER").text = "No"
        ET.SubElement(voucher_element, "EXCISETAXOVERRIDE").text = "No"
        ET.SubElement(voucher_element, "USEFORTAXUNITTRANSFER").text = "No"
        ET.SubElement(voucher_element, "IGNOREPOSVALIDATION").text = "No"
        ET.SubElement(voucher_element, "EXCISEOPENING").text = "No"
        ET.SubElement(voucher_element, "USEFORFINALPRODUCTION").text = "No"
        ET.SubElement(voucher_element, "ISTDSOVERRIDDEN").text = "No"
        ET.SubElement(voucher_element, "ISTCSOVERRIDDEN").text = "No"
        ET.SubElement(voucher_element, "ISTDSTCSCASHVCH").text = "No"
        ET.SubElement(voucher_element, "INCLUDEADVPYMTVCH").text = "No"
        ET.SubElement(voucher_element, "ISSUBWORKSCONTRACT").text = "No"
        ET.SubElement(voucher_element, "ISVATOVERRIDDEN").text = "No"
        ET.SubElement(voucher_element, "IGNOREORIGVCHDATE").text = "No"
        ET.SubElement(voucher_element, "ISVATPAIDATCUSTOMS").text = "No"
        ET.SubElement(voucher_element, "ISDECLAREDTOCUSTOMS").text = "No"
        ET.SubElement(voucher_element, "ISSERVICETAXOVERRIDDEN").text = "No"
        ET.SubElement(voucher_element, "ISISDVOUCHER").text = "No"
        ET.SubElement(voucher_element, "ISEXCISEOVERRIDDEN").text = "No"
        ET.SubElement(voucher_element, "ISEXCISESUPPLYVCH").text = "No"
        ET.SubElement(voucher_element, "ISGSTOVERRIDDEN").text = "No"
        ET.SubElement(voucher_element, "GSTNOTEXPORTED").text = "No"
        ET.SubElement(voucher_element, "IGNOREGSTINVALIDATION").text = "No"
        ET.SubElement(voucher_element, "ISGSTREFUND").text = "No"
        ET.SubElement(voucher_element, "ISGSTSECSEVENAPPLICABLE").text = "No"
        ET.SubElement(voucher_element, "ISVATPRINCIPALACCOUNT").text = "No"
        ET.SubElement(voucher_element, "ISSHIPPINGWITHINSTATE").text = "No"
        ET.SubElement(voucher_element, "ISOVERSEASTOURISTTRANS").text = "No"
        ET.SubElement(voucher_element, "ISDESIGNATEDZONEPARTY").text = "No"
        ET.SubElement(voucher_element, "ISCANCELLED").text = "No"
        ET.SubElement(voucher_element, "HASCASHFLOW").text = "Yes"
        ET.SubElement(voucher_element, "ISPOSTDATED").text = "No"
        ET.SubElement(voucher_element, "USETRACKINGNUMBER").text = "No"
        ET.SubElement(voucher_element, "ISINVOICE").text = "No"
        ET.SubElement(voucher_element, "MFGJOURNAL").text = "No"
        ET.SubElement(voucher_element, "HASDISCOUNTS").text = "No"
        ET.SubElement(voucher_element, "ASPAYSLIP").text = "No"
        ET.SubElement(voucher_element, "ISCOSTCENTRE").text = "No"
        ET.SubElement(voucher_element, "ISSTXNONREALIZEDVCH").text = "No"
        ET.SubElement(voucher_element, "ISEXCISEMANUFACTURERON").text = "No"
        ET.SubElement(voucher_element, "ISBLANKCHEQUE").text = "No"
        ET.SubElement(voucher_element, "ISVOID").text = "No"
        ET.SubElement(voucher_element, "ORDERLINESTATUS").text = "No"
        ET.SubElement(voucher_element, "VATISAGNSTCANCSALES").text = "No"
        ET.SubElement(voucher_element, "VATISPURCEXEMPTED").text = "No"
        ET.SubElement(voucher_element, "ISVATRESTAXINVOICE").text = "No"
        ET.SubElement(voucher_element, "VATISASSESABLECALCVCH").text = "No"
        ET.SubElement(voucher_element, "ISVATDUTYPAID").text = "Yes"
        ET.SubElement(voucher_element, "ISDELIVERYSAMEASCONSIGNEE").text = "No"
        ET.SubElement(voucher_element, "ISDISPATCHSAMEASCONSIGNOR").text = "No"
        ET.SubElement(voucher_element, "CHANGEVCHMODE").text = "No"
        ET.SubElement(voucher_element, "ALTERID").text = "519"
        ET.SubElement(voucher_element, "MASTERID").text = "191"
        ET.SubElement(voucher_element, "VOUCHERKEY").text = str(uuid.uuid4())  # Unique key for each voucher

        # Create ALLLEDGERENTRIES.LIST for debit and credit entries
        all_ledger_entries = ET.SubElement(voucher_element, "ALLLEDGERENTRIES.LIST")

        # Add debit entry (for party)
        debit_entry = ET.SubElement(all_ledger_entries, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(debit_entry, "OLDAUDITENTRYIDS.LIST", TYPE="Number")
        ET.SubElement(debit_entry, "OLDAUDITENTRYIDS").text = "-1"
        ET.SubElement(debit_entry, "LEDGERNAME").text = party_name
        ET.SubElement(debit_entry, "GSTCLASS").text = ""
        ET.SubElement(debit_entry, "ISDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(debit_entry, "LEDGERFROMITEM").text = "No"
        ET.SubElement(debit_entry, "REMOVEZEROENTRIES").text = "No"
        ET.SubElement(debit_entry, "ISPARTYLEDGER").text = "No"
        ET.SubElement(debit_entry, "ISLASTDEEMEDPOSITIVE").text = "Yes"
        ET.SubElement(debit_entry, "ISCAPVATTAXALTERED").text = "No"
        ET.SubElement(debit_entry, "ISCAPVATNOTCLAIMED").text = "No"
        ET.SubElement(debit_entry, "AMOUNT").text = f"-{amount}"

        # Add credit entry (for Cash)
        credit_entry = ET.SubElement(all_ledger_entries, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(credit_entry, "OLDAUDITENTRYIDS.LIST", TYPE="Number")
        ET.SubElement(credit_entry, "OLDAUDITENTRYIDS").text = "-1"
        ET.SubElement(credit_entry, "LEDGERNAME").text = "Cash"
        ET.SubElement(credit_entry, "GSTCLASS").text = ""
        ET.SubElement(credit_entry, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(credit_entry, "LEDGERFROMITEM").text = "No"
        ET.SubElement(credit_entry, "REMOVEZEROENTRIES").text = "No"
        ET.SubElement(credit_entry, "ISPARTYLEDGER").text = "Yes"
        ET.SubElement(credit_entry, "ISLASTDEEMEDPOSITIVE").text = "No"
        ET.SubElement(credit_entry, "ISCAPVATTAXALTERED").text = "No"
        ET.SubElement(credit_entry, "ISCAPVATNOTCLAIMED").text = "No"
        ET.SubElement(credit_entry, "AMOUNT").text = amount

    # Convert to XML string
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
        unique_filename = f'payment_entry_output_{uuid.uuid4().hex[:8]}.xml'
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
