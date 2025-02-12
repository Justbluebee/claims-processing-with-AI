from flask import Flask, request, render_template, send_file, jsonify
import pandas as pd
import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the files are in the request
    if 'treaty' not in request.files or 'bordereaux' not in request.files or 'statement' not in request.files:
        return jsonify({'error': 'Missing one or more required files: Treaty, Bordereaux, or Statement.'}), 400
    
    # Get files
    treaty_file = request.files['treaty']
    bordereaux_file = request.files['bordereaux']
    statement_file = request.files['statement']
    
    # Validate file types (PDF for treaty and statement, Excel for bordereaux)
    allowed_pdf = {'pdf'}
    allowed_excel = {'xls', 'xlsx'}
    
    if not (allowed_file(treaty_file.filename, allowed_pdf) and 
            allowed_file(bordereaux_file.filename, allowed_excel) and
            allowed_file(statement_file.filename, allowed_pdf)):
        return jsonify({'error': 'Invalid file format. Treaty and Statement should be PDF, and Bordereaux should be Excel.'}), 400
    
    try:
        # Extract data from PDF and Excel files
        treaty_text = extract_text_from_pdf(treaty_file)
        bordereaux_df = pd.read_excel(bordereaux_file)
        statement_text = extract_text_from_pdf(statement_file)
    
        # Identify common fields
        common_fields = identify_common_fields(bordereaux_df, statement_text, treaty_text)
    
        # Perform comparisons
        discrepancies = compare_bordereaux_statement(bordereaux_df, statement_text, common_fields)
        treaty_discrepancies = compare_bordereaux_treaty(bordereaux_df, treaty_text, common_fields)
        premium_discrepancies = compare_premium_prices(bordereaux_df, statement_text, common_fields)
        
        # Flag potentially fraudulent claims
        fraud_flags = flag_fraudulent_claims(bordereaux_df)
        
        # Detect duplicate data in Bordereaux
        duplicate_data = detect_duplicate_data(bordereaux_df)
    
        # Generate report
        report = generate_report(discrepancies, treaty_discrepancies, premium_discrepancies, fraud_flags, duplicate_data)
    
        # Generate PDF from the report
        pdf_buffer = generate_pdf_report(report)
    
        # Return PDF for download
        return send_file(pdf_buffer, as_attachment=True, download_name='discrepancy_report.pdf', mimetype='application/pdf')
    
    except Exception as e:
        # Log the error and send a response with the error message
        print(f"Error occurred: {e}")
        return jsonify({'error': f"An error occurred while processing the files: {str(e)}"}), 500

def allowed_file(filename, allowed_extensions):
    """Utility function to check file extensions"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_text_from_pdf(file):
    """Extract text from a PDF using pdfplumber"""
    with pdfplumber.open(file) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text()
    return text

def identify_common_fields(bordereaux_df, statement_text, treaty_text):
    """Identify common fields between Bordereaux, Statement, and Treaty"""
    common_fields = []
    for column in bordereaux_df.columns:
        if column in statement_text and column in treaty_text:
            common_fields.append(column)
    return common_fields

def compare_bordereaux_statement(bordereaux_df, statement_text, common_fields):
    """Compare Bordereaux with Statement based on common fields"""
    discrepancies = []
    for index, row in bordereaux_df.iterrows():
        for field in common_fields:
            value = str(row[field])
            if value not in statement_text:
                discrepancies.append({
                    'Policy Holder ID': row.get('Policy Holder ID', 'Unknown'),
                    'Field': field,
                    'Value': value,
                    'Issue': f'{value} not found in statement under field {field} (Row {index+1})'
                })
    return discrepancies

def compare_bordereaux_treaty(bordereaux_df, treaty_text, common_fields):
    """Compare Bordereaux with Treaty based on common fields"""
    treaty_discrepancies = []
    for index, row in bordereaux_df.iterrows():
        for field in common_fields:
            value = str(row[field])
            if value not in treaty_text:
                treaty_discrepancies.append({
                    'Policy Holder ID': row.get('Policy Holder ID', 'Unknown'),
                    'Field': field,
                    'Value': value,
                    'Issue': f'{value} not found in treaty under field {field} (Row {index+1})'
                })
    return treaty_discrepancies

def compare_premium_prices(bordereaux_df, statement_text, common_fields):
    """Compare Premium prices between Bordereaux and Statement"""
    premium_discrepancies = []
    for index, row in bordereaux_df.iterrows():
        for field in common_fields:
            if 'Premium' in field:
                value = str(row[field])
                if value not in statement_text:
                    premium_discrepancies.append({
                        'Policy Holder ID': row.get('Policy Holder ID', 'Unknown'),
                        'Field': field,
                        'Value': value,
                        'Issue': f'{value} not found in statement under field {field} (Row {index+1})'
                    })
    return premium_discrepancies

def flag_fraudulent_claims(bordereaux_df):
    """Flag potentially fraudulent claims based on certain conditions"""
    fraud_flags = []
    for index, row in bordereaux_df.iterrows():
        claim_amount = row.get('Claim Amount', None)
        premium_amount = row.get('Premium Amount', None)
        if pd.notnull(claim_amount) and pd.notnull(premium_amount):
            if claim_amount > (2 * premium_amount):  # Example threshold for potential fraud
                fraud_flags.append({
                    'Policy Holder ID': row.get('Policy Holder ID', 'Unknown'),
                    'Claim Amount': claim_amount,
                    'Premium Amount': premium_amount,
                    'Issue': f'Potential fraud: Claim Amount ({claim_amount}) significantly higher than Premium Amount ({premium_amount}) (Row {index+1})'
                })
    return fraud_flags

def detect_duplicate_data(bordereaux_df):
    """Detect duplicate entries in the Bordereaux"""
    duplicate_data = bordereaux_df[bordereaux_df.duplicated(subset=['Policy Holder ID'], keep=False)]
    duplicates = []
    for index, row in duplicate_data.iterrows():
        duplicates.append({
            'Policy Holder ID': row['Policy Holder ID'],
            'Issue': f'Duplicate Policy Holder ID found in bordereaux (Row {index+1})'
        })
    return duplicates

def generate_report(discrepancies, treaty_discrepancies, premium_discrepancies, fraud_flags, duplicate_data):
    """Generate a comprehensive report of discrepancies"""
    report = {
        'Statement Discrepancies': discrepancies,
        'Treaty Discrepancies': treaty_discrepancies,
        'Premium Discrepancies': premium_discrepancies,
        'Fraudulent Claims': fraud_flags,
        'Duplicate Entries': duplicate_data
    }
    
    # Handle NaN values in discrepancies
    for category in report.values():
        for discrepancy in category:
            for key, value in discrepancy.items():
                if pd.isnull(value):
                    discrepancy[key] = 'Unknown'
    
    return report

def generate_pdf_report(report):
    """Generate a PDF report from discrepancies"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Header
    c.drawString(100, 750, "Discrepancy Report")
    y = 720
    
    # Debug print for report
    print("Generated Report: ", report)  # For debugging
    
    # Check if report has data
    if not any(report.values()):  # If all lists are empty
        c.drawString(100, y, "No discrepancies found.")
        c.save()
        buffer.seek(0)
        return buffer
    
    # Iterate through report categories and discrepancies
    for category, discrepancies in report.items():
        if discrepancies:  # Check if there are discrepancies in the current category
            c.drawString(100, y, f'{category}:')
            y -= 20
            
            for discrepancy in discrepancies:
                c.drawString(100, y, f"Policy Holder ID: {discrepancy['Policy Holder ID']}")
                y -= 15
                c.drawString(100, y, f"Issue: {discrepancy['Issue']}")
                y -= 30

                # Ensure there's enough space on the current page
                if y < 100:  # Create a new page if there's no space
                    c.showPage()
                    y = 750  # Reset Y-coordinate for new page
    
    # Save and return PD
    c.save()
    buffer.seek(0)
    return buffer

if __name__ == '__main__':
    app.run(debug=True)