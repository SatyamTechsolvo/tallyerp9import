import frappe
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import io, os
# from frappe.utils.file_manager import get_site_path

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


    # Read the uploaded CSV file
    df = pd.read_csv(file_path, skiprows=[*range(0, 15), 16, 17, 18, 19], encoding='utf-8')
    df.columns = df.columns.str.strip()  # Strip whitespace from column names
    df = df.fillna("")  

    # Create the envelope and header
    envelope = ET.Element("ENVELOPE")
    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Import Data"
    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")
    request_desc = ET.SubElement(import_data, "REQUESTDESC")
    ET.SubElement(request_desc, "REPORTNAME").text = "All Masters"
    static_variables = ET.SubElement(request_desc, "STATICVARIABLES")
    ET.SubElement(static_variables, "SVCURRENTCOMPANY").text = "Techsolvo"
    request_data = ET.SubElement(import_data, "REQUESTDATA")
    tally_message = ET.SubElement(request_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})

    grouped_entries = {}
    current_name = None

    for index, row in df.iterrows():
        if row['name']:
            current_name = row['name']
            grouped_entries[current_name] = {
                'main_entry': row,
                'related_entries': []
            }
        else:
            if current_name:
                grouped_entries[current_name]['related_entries'].append(row)

    for name, entry in grouped_entries.items():
        main_row = entry['main_entry']
        voucher = ET.SubElement(tally_message, "VOUCHER")
        remote_id = f"{str(uuid.uuid4())}-00000001"
        vch_key = f"{str(uuid.uuid4())}-0000b146:00000008"
        voucher.set("REMOTEID", remote_id)
        voucher.set("VCHKEY", vch_key)
        voucher.set("VCHTYPE", "Journal")
        voucher.set("ACTION", "Create")
        voucher.set("OBJVIEW", "Accounting Voucher View")

        old_audit_entry_ids_list = ET.SubElement(voucher, "OLDAUDITENTRYIDS.LIST", TYPE="Number")
        ET.SubElement(old_audit_entry_ids_list, "OLDAUDITENTRYIDS").text = "-1"

        if 'posting_date' in main_row and main_row['posting_date']:
            day, month, year = main_row['posting_date'].split("-")
            formatted_date = f"{year}{month}{day}"
        else:
            formatted_date = ""

        ET.SubElement(voucher, "DATE").text = formatted_date
        ET.SubElement(voucher, "GUID").text = remote_id
        ET.SubElement(voucher, "PARTYLEDGERNAME").text = main_row.get('party')
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = 'Journal'

        main_ledger_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(main_ledger_entry, "LEDGERNAME").text = main_row.get('party')
        is_deemed_positive = "Yes" if main_row.get('party_type') == 'Customer' else "No"
        ET.SubElement(main_ledger_entry, "ISDEEMEDPOSITIVE").text = is_deemed_positive
        amount = main_row.get('debit_in_account_currency', 0) if is_deemed_positive == "Yes" else main_row.get('credit_in_account_currency', 0)
        ET.SubElement(main_ledger_entry, "AMOUNT").text = str(-abs(amount) if is_deemed_positive == "Yes" else abs(amount))

        for related_row in entry['related_entries']:
            ledger_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
            ET.SubElement(ledger_entry, "LEDGERNAME").text = related_row.get('party', 'Ledger')
            is_deemed_positive = "Yes" if related_row['party_type'] == 'Customer' else "No"
            ET.SubElement(ledger_entry, "ISDEEMEDPOSITIVE").text = is_deemed_positive
            amount = related_row.get('debit_in_account_currency', 0) if related_row['party_type'] == 'Customer' else related_row.get('credit_in_account_currency', 0)
            ET.SubElement(ledger_entry, "AMOUNT").text = str(-abs(amount) if is_deemed_positive == "Yes" else abs(amount))

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
        unique_filename = f'journal_entry_output_{uuid.uuid4().hex[:8]}.xml'
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