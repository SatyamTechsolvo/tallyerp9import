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

    # Read the uploaded CSV file
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()  # Remove any extra whitespace from column names

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
    ET.SubElement(request_desc, "REPORTNAME").text = "All Masters"
    static_variables = ET.SubElement(request_desc, "STATICVARIABLES")
    ET.SubElement(static_variables, "SVCURRENTCOMPANY").text = "Techsolvo"

    # Create REQUESTDATA
    request_data = ET.SubElement(import_data, "REQUESTDATA")

    # Iterate over the rows to create TALLYMESSAGE elements
    for _, row in df.iterrows():
        account_name = saxutils.escape(str(row.get('Account Name', '')).strip())
        parent_account = str(row.get('Parent Account', '    ')).strip()  # Keep as raw string
        is_group = str(row.get('Is Group', '')).strip()  # Check if group

        # Generate a unique GUID
        guid = str(uuid.uuid4())

        # Skip if account_name is empty
        if not account_name:
            print(f"Skipping row due to missing Account Name: {row}")
            continue

        # Create TALLYMESSAGE element
        tally_message = ET.SubElement(request_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})

        # Determine tag based on whether it's a group or ledger
        account_tag = "GROUP"

        # Create GROUP or LEDGER based on is_group
        account = ET.SubElement(tally_message, account_tag, {
            "NAME": account_name,
            "RESERVEDNAME": account_name
        })
        
        # Populate fields according to the provided template
        ET.SubElement(account, "GUID").text = guid

        parent_account = row.get('Parent Account', '')
        # Convert to a string and check if it's empty or "nan"
        if str(parent_account).lower() == 'nan' or parent_account == '':
            ET.SubElement(account, "PARENT").text = '\t'  # Use a tab character if empty or 'nan'
        else:
            ET.SubElement(account, "PARENT").text = str(parent_account)

        ET.SubElement(account, "GRPDEBITPARENT").text = ""
        ET.SubElement(account, "GRPCREDITPARENT").text = ""
        ET.SubElement(account, "ISBILLWISEON").text = "No"
        ET.SubElement(account, "ISCOSTCENTRESON").text = "No"
        ET.SubElement(account, "ISADDABLE").text = "No"
        ET.SubElement(account, "ISUPDATINGTARGETID").text = "No"
        ET.SubElement(account, "ASORIGINAL").text = "Yes"
        ET.SubElement(account, "ISSUBLEDGER").text = "No"
        ET.SubElement(account, "ISREVENUE").text = "No"
        ET.SubElement(account, "AFFECTSGROSSPROFIT").text = "No"
        ET.SubElement(account, "ISDEEMEDPOSITIVE").text = "No"
        ET.SubElement(account, "TRACKNEGATIVEBALANCES").text = "No"
        ET.SubElement(account, "ISCONDENSED").text = "No"
        ET.SubElement(account, "AFFECTSSTOCK").text = "No"
        ET.SubElement(account, "ISGROUPFORLOANRCPT").text = "No"
        ET.SubElement(account, "ISGROUPFORLOANPYMNT").text = "No"
        ET.SubElement(account, "ISRATEINCLUSIVEVAT").text = "No"
        ET.SubElement(account, "ISINVDETAILSENABLE").text = "No"
        ET.SubElement(account, "SORTPOSITION").text = "30"
        ET.SubElement(account, "ALTERID").text = "4"
        ET.SubElement(account, "SERVICETAXDETAILS.LIST").text = "       "
        ET.SubElement(account, "VATDETAILS.LIST").text = "      "
        ET.SubElement(account, "SALESTAXCESSDETAILS.LIST").text = "     "
        ET.SubElement(account, "GSTDETAILS.LIST").text = "      "
        # Add language name list as in template
        language_name = ET.SubElement(account, "LANGUAGENAME.LIST")
        name_list = ET.SubElement(language_name, "NAME.LIST", {"TYPE": "String"})
        ET.SubElement(name_list, "NAME").text = account_name
        ET.SubElement(language_name, "LANGUAGEID").text = "1033"

        # Add empty lists for remaining tags
        for tag in ["XBRLDETAIL.LIST", "AUDITDETAILS.LIST", 
                    "SCHVIDETAILS.LIST", "EXCISETARIFFDETAILS.LIST", "TCSCATEGORYDETAILS.LIST", 
                    "TDSCATEGORYDETAILS.LIST", "GSTCLASSFNIGSTRATES.LIST", 
                    "EXTARIFFDUTYHEADDETAILS.LIST"]:
            ET.SubElement(account, tag).text = "        "

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
        unique_filename = f'chart_of_accounts_output_{uuid.uuid4().hex[:8]}.xml'
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