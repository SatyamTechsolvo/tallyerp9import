import frappe
import pandas as pd
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import xml.sax.saxutils as saxutils
import uuid

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
    ET.SubElement(request_desc, "REPORTNAME").text = "All Masters"
    static_variables = ET.SubElement(request_desc, "STATICVARIABLES")
    ET.SubElement(static_variables, "SVCURRENTCOMPANY").text = "Techsolvo"

    # Create REQUESTDATA
    request_data = ET.SubElement(import_data, "REQUESTDATA")

    # Iterate over rows to create TALLYMESSAGE elements
    for _, row in df.iterrows():
        # Extract required fields
        customer_name = saxutils.escape(str(row.get('customer_name', '')))
        email = saxutils.escape(str(row.get('email_id', '')))
        primary_address = saxutils.escape(str(row.get('customer_primary_address', '')))
        gstin = saxutils.escape(str(row.get('gstin', ''))) 
        pincode = saxutils.escape(str(row.get('pincode', '')))
        prior_state_name = saxutils.escape(str(row.get('state', ''))) 
        website = saxutils.escape(str(row.get('website', '')))  
        income_tax_number = saxutils.escape(str(row.get('income_tax_number', '')))  
        ledger_phone = saxutils.escape(str(row.get('ledger_phone', ''))) 
        ledger_fax = saxutils.escape(str(row.get('ledger_fax', ''))) 
        ledger_contact = saxutils.escape(str(row.get('ledger_contact', '')))  
        ledger_mobile = saxutils.escape(str(row.get('ledger_mobile', '')))  

        # Create a unique GUID for each entry
        guid = str(uuid.uuid4())

        # Create TALLYMESSAGE element for each customer
        tally_message = ET.SubElement(request_data, "TALLYMESSAGE", xmlns_UDF="TallyUDF")
        
        # Create LEDGER element
        ledger_element = ET.SubElement(tally_message, "LEDGER", {
            "NAME": customer_name,
            "RESERVEDNAME": ""
        })

        # Add mandatory fields
        address_list = ET.SubElement(ledger_element, "ADDRESS.LIST", TYPE="String")
        address = ET.SubElement(address_list, "ADDRESS")
        address.text = primary_address 

        mailing_name_list = ET.SubElement(ledger_element, "MAILINGNAME.LIST", TYPE="String")
        mailing_name = ET.SubElement(mailing_name_list, "MAILINGNAME")
        mailing_name.text = customer_name

        old_audit_entry_ids_list = ET.SubElement(ledger_element, "OLDAUDITENTRYIDS.LIST", TYPE="Number")
        old_audit_entry_ids = ET.SubElement(old_audit_entry_ids_list, "OLDAUDITENTRYIDS")
        old_audit_entry_ids.text = "-1"

        ET.SubElement(ledger_element, "GUID").text = guid
        ET.SubElement(ledger_element, "EMAIL").text = email
        ET.SubElement(ledger_element, "PRIORSTATENAME").text = primary_address
        ET.SubElement(ledger_element, "PINCODE").text = ''
        ET.SubElement(ledger_element, "WEBSITE").text = website
        pan = saxutils.escape(str(row.get('pan', '')))  
        ET.SubElement(ledger_element, "INCOMETAXNUMBER").text = pan
        ET.SubElement(ledger_element, "COUNTRYNAME").text = "India"
        ET.SubElement(ledger_element, "GSTREGISTRATIONTYPE").text = "Regular"
        ET.SubElement(ledger_element, "VATDEALERTYPE").text = "Regular" 
        ET.SubElement(ledger_element, "PARENT").text = "Sundry Debtors"
        ET.SubElement(ledger_element, "TAXCLASSIFICATIONNAME").text = ""
        ET.SubElement(ledger_element, "TAXTYPE").text = "Others"
        country = saxutils.escape(str(row.get('country', '')))
        ET.SubElement(ledger_element, "COUNTRYOFRESIDENCE").text = country
        mobile_no = saxutils.escape(str(row.get('mobile_no', '')))
        ET.SubElement(ledger_element, "LEDGERPHONE").text = mobile_no
        ET.SubElement(ledger_element, "LEDGERFAX").text = mobile_no
        ET.SubElement(ledger_element, "LEDGERCONTACT").text = customer_name
        ET.SubElement(ledger_element, "LEDGERMOBILE").text = mobile_no
        ET.SubElement(ledger_element, "GSTTYPE").text = ""
        ET.SubElement(ledger_element, "APPROPRIATEFOR").text = ""
        ET.SubElement(ledger_element, "EXCISELEDGERCLASSIFICATION").text = ""
        ET.SubElement(ledger_element, "EXCISEDUTYTYPE").text = ""
        ET.SubElement(ledger_element, "EXCISENATUREOFPURCHASE").text = ""
        ET.SubElement(ledger_element, "LEDGERFBTCATEGORY").text = ""
        ET.SubElement(ledger_element, "ISBILLWISEON").text = "Yes"
        ET.SubElement(ledger_element, "ISCOSTCENTRESON").text = "No"
        ET.SubElement(ledger_element, "ISINTERESTON").text = "No"
        ET.SubElement(ledger_element, "ALLOWINMOBILE").text = "No"
        ET.SubElement(ledger_element, "ISCOSTTRACKINGON").text = "No"
        ET.SubElement(ledger_element, "ISBENEFICIARYCODEON").text = "No"
        ET.SubElement(ledger_element, "PLASINCOMEEXPENSE").text = "No"
        ET.SubElement(ledger_element, "ISUPDATINGTARGETID").text = "No"
        ET.SubElement(ledger_element, "ASORIGINAL").text = "Yes"
        ET.SubElement(ledger_element, "ISCONDENSED").text = "No"
        ET.SubElement(ledger_element, "AFFECTSSTOCK").text = "No"
        ET.SubElement(ledger_element, "ISRATEINCLUSIVEVAT").text = "No"
        ET.SubElement(ledger_element, "FORPAYROLL").text = "No"
        ET.SubElement(ledger_element, "ISABCENABLED").text = "No"
        ET.SubElement(ledger_element, "ISCREDITDAYSCHKON").text = "No"
        ET.SubElement(ledger_element, "INTERESTONBILLWISE").text = "No"
        ET.SubElement(ledger_element, "OVERRIDEINTEREST").text = "No"
        ET.SubElement(ledger_element, "OVERRIDEADVINTEREST").text = "No"
        ET.SubElement(ledger_element, "USEFORVAT").text = "No"
        ET.SubElement(ledger_element, "IGNORETDSEXEMPT").text = "No"
        ET.SubElement(ledger_element, "ISTCSAPPLICABLE").text = "No"
        ET.SubElement(ledger_element, "ISTDSAPPLICABLE").text = "No"
        ET.SubElement(ledger_element, "ISFBTAPPLICABLE").text = "No"
        ET.SubElement(ledger_element, "ISGSTAPPLICABLE").text = "No"
        ET.SubElement(ledger_element, "ISEXCISEAPPLICABLE").text = "No"
        ET.SubElement(ledger_element, "ISTDSEXPENSE").text = "No"
        ET.SubElement(ledger_element, "ISEDLIAPPLICABLE").text = "No"
        ET.SubElement(ledger_element, "ISRELATEDPARTY").text = "No"
        ET.SubElement(ledger_element, "USEFORESIELIGIBILITY").text = "No"
        ET.SubElement(ledger_element, "ISINTERESTINCLLASTDAY").text = "No"
        ET.SubElement(ledger_element, "APPROPRIATETAXVALUE").text = "No"
        ET.SubElement(ledger_element, "ISBEHAVEASDUTY").text = "No"
        ET.SubElement(ledger_element, "INTERESTINCLDAYOFADDITION").text = "No"
        ET.SubElement(ledger_element, "INTERESTINCLDAYOFDEDUCTION").text = "No"
        ET.SubElement(ledger_element, "ISOTHTERRITORYASSESSEE").text = "No"
        ET.SubElement(ledger_element, "OVERRIDECREDITLIMIT").text = "No"
        ET.SubElement(ledger_element, "ISAGAINSTFORMC").text = "No"
        ET.SubElement(ledger_element, "ISCHEQUEPRINTINGENABLED").text = "Yes"
        ET.SubElement(ledger_element, "ISPAYUPLOAD").text = "No"
        ET.SubElement(ledger_element, "ISPAYBATCHONLYSAL").text = "No"
        ET.SubElement(ledger_element, "ISBNFCODESUPPORTED").text = "No"
        ET.SubElement(ledger_element, "ALLOWEXPORTWITHERRORS").text = "No"
        ET.SubElement(ledger_element, "CONSIDERPURCHASEFOREXPORT").text = "No"
        ET.SubElement(ledger_element, "ISTRANSPORTER").text = "No"
        ET.SubElement(ledger_element, "USEFORNOTIONALITC").text = "No"
        ET.SubElement(ledger_element, "ISECOMMOPERATOR").text = "No"
        ET.SubElement(ledger_element, "SHOWINPAYSLIP").text = "No"
        ET.SubElement(ledger_element, "USEFORGRATUITY").text = "No"
        ET.SubElement(ledger_element, "ISTDSPROJECTED").text = "No"
        ET.SubElement(ledger_element, "FORSERVICETAX").text = "No"
        ET.SubElement(ledger_element, "ISINPUTCREDIT").text = "No"
        ET.SubElement(ledger_element, "ISEXEMPTED").text = "No"
        ET.SubElement(ledger_element, "ISABATEMENTAPPLICABLE").text = "No"
        ET.SubElement(ledger_element, "ISSTXPARTY").text = "No"
        ET.SubElement(ledger_element, "ISSTXNONREALIZEDTYPE").text = "No"
        ET.SubElement(ledger_element, "ISUSEDFORCVD").text = "No"
        ET.SubElement(ledger_element, "LEDBELONGSTONONTAXABLE").text = "No"
        ET.SubElement(ledger_element, "ISEXCISEMERCHANTEXPORTER").text = "No"
        ET.SubElement(ledger_element, "ISPARTYEXEMPTED").text = "No"
        ET.SubElement(ledger_element, "ISSEZPARTY").text = "No"
        ET.SubElement(ledger_element, "TDSDEDUCTEEISSPECIALRATE").text = "No"
        ET.SubElement(ledger_element, "ISECHEQUESUPPORTED").text = "No"
        ET.SubElement(ledger_element, "ISEDDSUPPORTED").text = "No"
        ET.SubElement(ledger_element, "HASECHEQUEDELIVERYMODE").text = "No"
        ET.SubElement(ledger_element, "HASECHEQUEDELIVERYTO").text = "No"
        ET.SubElement(ledger_element, "HASECHEQUEPRINTLOCATION").text = "No"
        ET.SubElement(ledger_element, "HASECHEQUEPAYABLELOCATION").text = "No"
        ET.SubElement(ledger_element, "HASECHEQUEBANKLOCATION").text = "No"
        ET.SubElement(ledger_element, "HASEDDDELIVERYMODE").text = "No"
        ET.SubElement(ledger_element, "HASEDDDELIVERYTO").text = "No"
        ET.SubElement(ledger_element, "HASEDDPRINTLOCATION").text = "No"
        ET.SubElement(ledger_element, "HASEDDPAYABLELOCATION").text = "No"
        ET.SubElement(ledger_element, "HASEDDBANKLOCATION").text = "No"
        ET.SubElement(ledger_element, "ISEBANKINGENABLED").text = "No"
        ET.SubElement(ledger_element, "ISEXPORTFILEENCRYPTED").text = "No"
        ET.SubElement(ledger_element, "ISBATCHENABLED").text = "No"
        ET.SubElement(ledger_element, "ISPRODUCTCODEBASED").text = "No"
        ET.SubElement(ledger_element, "HASEDDCITY").text = "No"
        ET.SubElement(ledger_element, "HASECHEQUECITY").text = "No"
        ET.SubElement(ledger_element, "ISFILENAMEFORMATSUPPORTED").text = "No"
        ET.SubElement(ledger_element, "HASCLIENTCODE").text = "No"
        ET.SubElement(ledger_element, "PAYINSISBATCHAPPLICABLE").text = "No"
        ET.SubElement(ledger_element, "PAYINSISFILENUMAPP").text = "No"
        ET.SubElement(ledger_element, "ISSALARYTRANSGROUPEDFORBRS").text = "No"
        ET.SubElement(ledger_element, "ISEBANKINGSUPPORTED").text = "No"
        ET.SubElement(ledger_element, "ISSCBUAE").text = "No"
        ET.SubElement(ledger_element, "ISBANKSTATUSAPP").text = "No"
        ET.SubElement(ledger_element, "ISSALARYGROUPED").text = "No"
        ET.SubElement(ledger_element, "USEFORPURCHASETAX").text = "No"
        ET.SubElement(ledger_element, "AUDITED").text = "No"
        ET.SubElement(ledger_element, "SORTPOSITION").text = "1000"
        ET.SubElement(ledger_element, "ALTERID").text = str(_+1)
        language_name_list = ET.SubElement(ledger_element, "LANGUAGENAME.LIST")
        name_list = ET.SubElement(language_name_list, "NAME.LIST", TYPE="String")
        name = ET.SubElement(name_list, "NAME")
        name.text = customer_name

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
        unique_filename = f'customer_output_{uuid.uuid4().hex[:8]}.xml'
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