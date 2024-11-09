import frappe
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import io, os
import xml.sax.saxutils as saxutils
import re

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
    
    # Extract unique UOMs from the CSV
    unique_uoms = df['stock_uom'].dropna().unique()
    
    # Create the XML root
    envelope = ET.Element("ENVELOPE")
    
    # Add HEADER and BODY sections
    # HEADER
    header = ET.SubElement(envelope, "HEADER")
    tally_request = ET.SubElement(header, "TALLYREQUEST")
    tally_request.text = "Import Data"
    
    # BODY
    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")
    
    # REQUESTDESC
    request_desc = ET.SubElement(import_data, "REQUESTDESC")
    report_name = ET.SubElement(request_desc, "REPORTNAME")
    report_name.text = "All Masters"
    static_variables = ET.SubElement(request_desc, "STATICVARIABLES")
    sv_company = ET.SubElement(static_variables, "SVCURRENTCOMPANY")
    sv_company.text = "Techsolvo"
    
    # REQUESTDATA
    request_data = ET.SubElement(import_data, "REQUESTDATA")
    
    # Create UOM entries as per your exact requirements
    for uom in unique_uoms:
        count = 0
        uom_name = saxutils.escape(str(uom).strip())
        tally_message = ET.SubElement(request_data, "TALLYMESSAGE", xmlns="TallyUDF")
        unit = ET.SubElement(tally_message, "UNIT", NAME=uom_name, RESERVEDNAME="")
    
        # Set the specific attributes and child elements as per your required XML format
        name = ET.SubElement(unit, "NAME")
        name.text = uom_name
        guid = ET.SubElement(unit, "GUID")
        guid.text = "1e84c8a2-7b56-4823-a1f6-cc4b4e3a8f40-00000001"  # Adjust GUID as needed
        is_updating_target_id = ET.SubElement(unit, "ISUPDATINGTARGETID")
        is_updating_target_id.text = "No"
        as_original = ET.SubElement(unit, "ASORIGINAL")
        as_original.text = "Yes"
        is_gst_excluded = ET.SubElement(unit, "ISGSTEXCLUDED")
        is_gst_excluded.text = "No"
        is_simple_unit = ET.SubElement(unit, "ISSIMPLEUNIT")
        is_simple_unit.text = "Yes"
        alter_id = ET.SubElement(unit, "ALTERID")
        alter_id.text = str(count + 1)
    
    count += 1
    # Proceed with adding stock groups and items as in the original script...
    created_stock_items = set()
    existing_stock_groups = set()
    
    def normalize_name(name):
        return re.sub(r'\s+', '', name).lower()
    
    for _, row in df.iterrows():
        stock_group_name = saxutils.escape(str(row.get('item_group', 'Primary')).strip())
        item_name = saxutils.escape(str(row.get('item_name', '')).strip())
        normalized_item_name = item_name.replace(" ", "").lower()
    
        if normalized_item_name in created_stock_items:
            continue
    
        # Create TALLYMESSAGE for the stock group if it doesn't exist
        if stock_group_name not in existing_stock_groups:
            group_message = ET.Element("TALLYMESSAGE", xmlns="TallyUDF")
            # STOCKGROUP with all fields as specified
            stock_group = ET.SubElement(group_message, "STOCKGROUP", NAME=stock_group_name, RESERVEDNAME="")
            # Adding required elements with placeholder text or empty as needed
            ET.SubElement(stock_group, "GUID").text = "56bc34aa-e52d-4342-8654-2daf966384be-000000a7"
            ET.SubElement(stock_group, "PARENT").text = ""
            ET.SubElement(stock_group, "BASEUNITS").text = "Nos"
            ET.SubElement(stock_group, "ADDITIONALUNITS").text = ""
            ET.SubElement(stock_group, "ISBATCHWISEON").text = "No"
            ET.SubElement(stock_group, "ISPERISHABLEON").text = "No"
            ET.SubElement(stock_group, "ISADDABLE").text = "No"
            ET.SubElement(stock_group, "ISUPDATINGTARGETID").text = "No"
            ET.SubElement(stock_group, "ASORIGINAL").text = "Yes"
            ET.SubElement(stock_group, "IGNOREPHYSICALDIFFERENCE").text = "No"
            ET.SubElement(stock_group, "IGNORENEGATIVESTOCK").text = "No"
            ET.SubElement(stock_group, "TREATSALESASMANUFACTURED").text = "No"
            ET.SubElement(stock_group, "TREATPURCHASESASCONSUMED").text = "No"
            ET.SubElement(stock_group, "TREATREJECTSASSCRAP").text = "No"
            ET.SubElement(stock_group, "HASMFGDATE").text = "No"
            ET.SubElement(stock_group, "ALLOWUSEOFEXPIREDITEMS").text = "No"
            ET.SubElement(stock_group, "IGNOREBATCHES").text = "No"
            ET.SubElement(stock_group, "IGNOREGODOWNS").text = "No"
            ET.SubElement(stock_group, "ALTERID").text = str(_+1)
            
            # Adding empty LIST elements as specified
            ET.SubElement(stock_group, "SERVICETAXDETAILS.LIST")
            ET.SubElement(stock_group, "VATDETAILS.LIST")
            ET.SubElement(stock_group, "SALESTAXCESSDETAILS.LIST")
            ET.SubElement(stock_group, "GSTDETAILS.LIST")

            # LANGUAGENAME.LIST with nested elements
            language_name_list = ET.SubElement(stock_group, "LANGUAGENAME.LIST")
            name_list = ET.SubElement(language_name_list, "NAME.LIST", TYPE="String")
            ET.SubElement(name_list, "NAME").text = stock_group_name
            ET.SubElement(language_name_list, "LANGUAGEID").text = "1033"

            # Adding remaining LIST elements as empty
            ET.SubElement(stock_group, "SCHVIDETAILS.LIST")
            ET.SubElement(stock_group, "EXCISETARIFFDETAILS.LIST")
            ET.SubElement(stock_group, "TCSCATEGORYDETAILS.LIST")
            ET.SubElement(stock_group, "TDSCATEGORYDETAILS.LIST")
            ET.SubElement(stock_group, "GSTCLASSFNIGSTRATES.LIST")
            ET.SubElement(stock_group, "EXTARIFFDUTYHEADDETAILS.LIST")
            ET.SubElement(stock_group, "TEMPGSTITEMSLABRATES.LIST")

            # Append to request data and add to existing groups
            request_data.append(group_message)
            existing_stock_groups.add(stock_group_name)
    
        # Add stock item with exact XML structure
        tally_message = ET.SubElement(request_data, "TALLYMESSAGE", xmlns="TallyUDF")
        stock_item = ET.SubElement(tally_message, "STOCKITEM", NAME=item_name, RESERVEDNAME="")
    
        fields = {
            "GUID": "56bc34aa-e52d-4342-8654-2daf966384be-000000d1",
            "PARENT": stock_group_name,
            "CATEGORY": "",
            "TAXCLASSIFICATIONNAME": "",
            "BASEUNITS": saxutils.escape(str(row.get('stock_uom', 'Nos'))),
            "ADDITIONALUNITS": "",
            "EXCISEITEMCLASSIFICATION": "",
            "ISCOSTCENTRESON": "No",
            "ISBATCHWISEON": "No",
            "ISPERISHABLEON": "No",
            "ISENTRYTAXAPPLICABLE": "No",
            "ISCOSTTRACKINGON": "No",
            "ISUPDATINGTARGETID": "No",
            "ASORIGINAL": "Yes",
            "ISRATEINCLUSIVEVAT": "No",
            "IGNOREPHYSICALDIFFERENCE": "No",
            "IGNORENEGATIVESTOCK": "No",
            "TREATSALESASMANUFACTURED": "No",
            "TREATPURCHASESASCONSUMED": "No",
            "TREATREJECTSASSCRAP": "No",
            "HASMFGDATE": "No",
            "ALLOWUSEOFEXPIREDITEMS": "No",
            "IGNOREBATCHES": "No",
            "IGNOREGODOWNS": "No",
            "CALCONMRP": "No",
            "EXCLUDEJRNLFORVALUATION": "No",
            "ISMRPINCLOFTAX": "No",
            "ISADDLTAXEXEMPT": "No",
            "ISSUPPLEMENTRYDUTYON": "No",
            "GVATISEXCISEAPPL": "No",
            "REORDERASHIGHER": "No",
            "MINORDERASHIGHER": "No",
            "ISEXCISECALCULATEONMRP": "No",
            "INCLUSIVETAX": "No",
            "GSTCALCSLABONMRP": "No",
            "MODIFYMRPRATE": "No",
            "ALTERID": str(_+1),
            "DENOMINATOR": "1",
            "RATEOFVAT": "0"
        }
    
        for tag, text in fields.items():
            element = ET.SubElement(stock_item, tag)
            element.text = text
    
        # Add GST details as per XML
        gst_details = ET.SubElement(stock_item, "GSTDETAILS.LIST")
        ET.SubElement(gst_details, "APPLICABLEFROM").text = "20170701"
        ET.SubElement(gst_details, "CALCULATIONTYPE").text = "On Value"
        ET.SubElement(gst_details, "HSNCODE").text = str(row.get('gst_hsn_code'))
        ET.SubElement(gst_details, "ISREVERSECHARGEAPPLICABLE").text = "No"
        ET.SubElement(gst_details, "ISNONGSTGOODS").text = "No"
        ET.SubElement(gst_details, "GSTINELIGIBLEITC").text = "No"
        ET.SubElement(gst_details, "INCLUDEEXPFORSLABCALC").text = "No"
    
        # Add language name list
        language_name_list = ET.SubElement(stock_item, "LANGUAGENAME.LIST")
        name_list = ET.SubElement(language_name_list, "NAME.LIST", TYPE="String")
        ET.SubElement(name_list, "NAME").text = item_name
    
        # Empty lists for additional tags
        empty_tags = [
            "SERVICETAXDETAILS.LIST", "VATDETAILS.LIST", "SALESTAXCESSDETAILS.LIST",
            "SCHVIDETAILS.LIST", "EXCISETARIFFDETAILS.LIST", "TCSCATEGORYDETAILS.LIST",
            "TDSCATEGORYDETAILS.LIST", "EXCLUDEDTAXATIONS.LIST", "OLDAUDITENTRIES.LIST",
            "ACCOUNTAUDITENTRIES.LIST", "AUDITENTRIES.LIST", "MRPDETAILS.LIST",
            "VATCLASSIFICATIONDETAILS.LIST", "COMPONENTLIST.LIST", "ADDITIONALLEDGERS.LIST",
            "SALESLIST.LIST", "PURCHASELIST.LIST", "FULLPRICELIST.LIST", "BATCHALLOCATIONS.LIST",
            "TRADEREXCISEDUTIES.LIST", "STANDARDCOSTLIST.LIST", "STANDARDPRICELIST.LIST",
            "EXCISEITEMGODOWN.LIST", "MULTICOMPONENTLIST.LIST", "LBTDETAILS.LIST",
            "PRICELEVELLIST.LIST", "GSTCLASSFNIGSTRATES.LIST", "EXTARIFFDUTYHEADDETAILS.LIST",
            "TEMPGSTITEMSLABRATES.LIST"
        ]
    
        # Add empty tags and create them with the correct structure
        for tag in empty_tags:
            element = ET.SubElement(stock_item, tag)
            # Add empty text content to create the desired output
            element.text = "      "  # This adds spaces between the opening and closing tags
    
        # Assuming created_stock_items is defined and normalized_item_name is available
        created_stock_items.add(normalized_item_name)  
    
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
        unique_filename = f'item_master_output_{uuid.uuid4().hex[:8]}.xml'
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