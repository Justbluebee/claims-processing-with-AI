from flask import Flask, request, render_template, send_file
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
    if 'treaty' not in request.files or 'bordereaux' not in request.files or 'statement' not in request.files:
        return "Missing file(s)"
    
    treaty_file = request.files['treaty']
    bordereaux_file = request.files['bordereaux']
    statement_file = request.files['statement']
    
    # Extract data from files
    treaty_text = extract_text_from_pdf(treaty_file)
    bordereaux_df = pd.read_excel(bordereaux_file)
    statement_text = extract_text_from_pdf(statement_file)
    
    # Identify common fields
    common_fields = identify_common_fields(bordereaux_df, statement_text, treaty_text)
    
    # Perform comparisons
    discrepancies = compare_bordereaux_statement(bordereaux_df, statement_text, common_fields)
    treaty_discrepancies = compare_bordereaux_treaty(bordereaux_df, treaty_text, common_fields)
    premium_discrepancies = compare_premium_prices(bordereaux_df, statement_text, common_fields)
    
    # Generate report
    report = generate_report(discrepancies, treaty_discrepancies, premium_discrepancies)
    
    # Generate PDF
    pdf_buffer = generate_report(report)
    
    return send_file(pdf_buffer, as_attachment=True, download_name='discrepancy_report.pdf', mimetype='application/pdf')

def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = ''
        for page in pdf.pages:
            text += page.extract_text()
    return text

def identify_common_fields(bordereaux_df, statement_text, treaty_text):
    common_fields = []
    for column in bordereaux_df.columns:
        if column in statement_text and column in treaty_text:
            common_fields.append(column)
    return common_fields

def compare_bordereaux_statement(bordereaux_df, statement_text, common_fields):
    discrepancies = []
    for index, row in bordereaux_df.iterrows():
        for field in common_fields:
            value = str(row[field])
            if value not in statement_text:
                discrepancies.append({
                    'Policy Holder ID': row['Policy Holder ID'],
                    'Field': field,
                    'Value': value,
                    'Issue': f'{field} not found in statement'
                })
    return discrepancies

def compare_bordereaux_treaty(bordereaux_df, treaty_text, common_fields):
    treaty_discrepancies = []
    for index, row in bordereaux_df.iterrows():
        for field in common_fields:
            value = str(row[field])
            if value not in treaty_text:
                treaty_discrepancies.append({
                    'Policy Holder ID': row['Policy Holder ID'],
                    'Field': field,
                    'Value': value,
                    'Issue': f'{field} not found in treaty'
                })
    return treaty_discrepancies

def compare_premium_prices(bordereaux_df, statement_text, common_fields):
    premium_discrepancies = []
    for index, row in bordereaux_df.iterrows():
        for field in common_fields:
            if 'Premium' in field:
                value = str(row[field])
                if value not in statement_text:
                    premium_discrepancies.append({
                        'Policy Holder ID': row['Policy Holder ID'],
                        'Field': field,
                        'Value': value,
                        'Issue': f'{field} discrepancy'
                    })
    return premium_discrepancies

def generate_report(discrepancies, treaty_discrepancies, premium_discrepancies):
    report = {
        'Statement Discrepancies': discrepancies,
        'Treaty Discrepancies': treaty_discrepancies,
        'Premium Discrepancies': premium_discrepancies
    }
    
    # Handle NaT values
    for discrepancy in report['Statement Discrepancies']:
        if pd.isnull(discrepancy['Policy Holder ID']):
            discrepancy['Policy Holder ID'] = 'Unknown'
        if pd.isnull(discrepancy['Value']):
            discrepancy['Value'] = 'Unknown'
    
    for discrepancy in report['Treaty Discrepancies']:
        if pd.isnull(discrepancy['Policy Holder ID']):
            discrepancy['Policy Holder ID'] = 'Unknown'
        if pd.isnull(discrepancy['Value']):
            discrepancy['Value'] = 'unknown'