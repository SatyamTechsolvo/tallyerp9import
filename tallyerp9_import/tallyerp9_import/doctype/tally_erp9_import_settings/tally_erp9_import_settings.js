frappe.ui.form.on('Tally ERP9 Import Settings', {
    convert_and_download_xml: function(frm) {
        const csv_file = frm.doc.attach_csv;

        if (!csv_file) {
            frappe.msgprint({
                title: __('Error'),
                message: __('Please upload a CSV file first.'),
                indicator: 'red'
            });
            return;
        }

        // Dynamic method and filename based on selected type
        const methodMap = {
            'Customer': 'tallyerp9_import.customer.convert_csv_to_xml',
            'Supplier': 'tallyerp9_import.supplier.convert_csv_to_xml',
            'Sales Order': 'tallyerp9_import.sales_order.convert_csv_to_xml',
            'Purchase Order': 'tallyerp9_import.purchase_order.convert_csv_to_xml',
            'Journal Entry': 'tallyerp9_import.journal_entry.convert_csv_to_xml',
            'Payment Entry': 'tallyerp9_import.payment_entry.convert_csv_to_xml',
            'Item Master': 'tallyerp9_import.item_master.convert_csv_to_xml',
            'Chart of Accounts': 'tallyerp9_import.coa.convert_csv_to_xml'
        };

        const filenameMap = {
            'Customer': 'Customer_Output.xml',
            'Supplier': 'Supplier_Output.xml',
            'Sales Order': 'Sales_Order_Output.xml',
            'Purchase Order': 'Purchase_Order_Output.xml',
            'Journal Entry': 'Journal_Entry_Output.xml',
            'Payment Entry': 'Payment_Entry_Output.xml',
            'Item': 'Item_Master_Output.xml'
        };

        const selectedType = frm.doc.select_type;
        const method = methodMap[selectedType];
        const defaultFilename = filenameMap[selectedType] || 'Output.xml';

        if (!method) {
            frappe.msgprint({
                title: __('Error'),
                message: __('XML conversion is not supported for the selected type.'),
                indicator: 'red'
            });
            return;
        }
        frappe.call({
            method: method,
            args: {
                doctype: frm.doctype,
                docname: frm.doc.name,
                csv_file: csv_file
            },
            callback: function(r) {
                frappe.hide_progress();

                if (r.message) {
                    if (r.message.file_url) {
                        // Construct full URL
                        const full_url = window.location.origin + r.message.file_url;
                        
                        // Create a link to download the XML file
                        const link = document.createElement('a');
                        link.href = full_url;
                        link.download = r.message.file_name || defaultFilename;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);

                        frappe.msgprint({
                            title: __('Success'),
                            message: __(`XML file for ${selectedType} generated successfully`),
                            indicator: 'green'
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: __('Invalid file response'),
                            indicator: 'red'
                        });
                    }
                } else {
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Error in generating XML file'),
                        indicator: 'red'
                    });
                }
            },
            error: function(err) {
                frappe.hide_progress();
                console.error('XML Generation Error:', err);
                frappe.msgprint({
                    title: __('Error'),
                    message: __('An error occurred while generating the XML file. Please check the console for details.'),
                    indicator: 'red'
                });
            }
        });
    }
});