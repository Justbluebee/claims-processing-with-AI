import os
import csv
import json
import io
import pandas as pd
import pdfplumber
import openai
from flask import jsonify,render_template_string
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tiktoken


def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_text_from_pdf(file):
    """Extract text from a PDF using pdfplumber"""
    try:
        with pdfplumber.open(file) as pdf:
            text = ''.join(page.extract_text() or '' for page in pdf.pages)
        print(f'Character count: {len(text)}')
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def save_text_file(text, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(text)

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""

def call_openai_api(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "system", "content": "You are an insurance data analyst."},
                      {"role": "user", "content": prompt}],
            max_tokens=1000,  # Reduce token limit
            temperature=0.4,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return ""

def clean_excel(input_file, output_file):
    try:
        df = pd.read_excel(input_file, sheet_name=None)
        with pd.ExcelWriter(output_file) as writer:
            for sheet_name, sheet_df in df.items():
                cleaned_df = sheet_df.dropna(how='all').dropna(axis=1, how='all')
                cleaned_df.to_excel(writer, sheet_name=sheet_name, index=False)
    except Exception as e:
        print(f"Error cleaning Excel file: {e}")

def generate_pdf_from_text(text, output_pdf_path):

    try:
        # Create a PDF canvas
        c = canvas.Canvas(output_pdf_path, pagesize=letter)
        width, height = letter

        # Set font
        c.setFont("Helvetica", 10)

        # Split text into lines that fit within the page width
        lines = text.split("\n")
        y_position = height - 50  # Start position

        for line in lines:
            if y_position < 50:  # New page if space runs out
                c.showPage()
                c.setFont("Helvetica", 10)
                y_position = height - 50

            c.drawString(50, y_position, line)
            y_position -= 15  # Move to next line

        # Save PDF
        c.save()
        print(f"PDF successfully saved at: {output_pdf_path}")

    except Exception as e:
        print(f"Error generating PDF: {e}")

def generate_pdf_from_csv(csv_filepath, output_pdf_path):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "CSV Report")
    y = 720
    try:
        with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                for key, value in row.items():
                    c.drawString(100, y, f"{key}: {value}")
                    y -= 15
                y -= 10
                if y < 100:
                    c.showPage()
                    y = 750
        c.save()
        buffer.seek(0)
        with open(output_pdf_path, 'wb') as f:
            f.write(buffer.getvalue())
        buffer.close()
        print(f"PDF report generated: {output_pdf_path}")
    except Exception as e:
        print(f"Error generating PDF: {e}")


def truncate_text_to_fit(text, max_tokens=9000, model="3.5-turbo"):
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]  # Truncate to fit within limits
    
    return enc.decode(tokens)  # Convert back to text

def process_files(treaty_file, bordereaux_file):
    allowed_pdf = {'pdf'}
    allowed_excel = {'xls', 'xlsx'}
    if not (allowed_file(treaty_file.filename, allowed_pdf) and allowed_file(bordereaux_file.filename, allowed_excel)):
        return jsonify({'error': 'Invalid file format. Treaty should be PDF, and Bordereaux should be Excel.'}), 400
    
    treaty_text = extract_text_from_pdf(treaty_file)
    treaty_output_path = "treatyoutput.txt"
    save_text_file(treaty_text, treaty_output_path)
    
    openai.api_key = 'eka hapa'
    prompt = "Create a summarized document highlighting key details."
    try:
        truncate_text_to_fit(treaty_output_path)
        max=50000
        final_treaty_text = call_openai_api((read_file(treaty_output_path)[max]) + "\n\n" + prompt)
        final_treaty_path = "final_treaty_document.txt"
        save_text_file(final_treaty_text, final_treaty_path)

    except Exception as e:
        print(f"Error in initial call : {e}")

    
    clean_bordereaux_output = 'clean_bordereaux.xlsx'
    clean_excel(bordereaux_file, clean_bordereaux_output)
    df = pd.read_excel(clean_bordereaux_output)
    df = df.iloc[:len(df) // 2]  # Selects the first half of rows
    final_bordereaux_csv = "final_bordereaux.csv"
    df.to_csv(final_bordereaux_csv, index=False)
    
    analysis_prompt = """
    The following files are an insurance boardereaux csv and insurance treaty text. 
    Search for insurance discrepancies related to claims processing in the boardereaux. 
    Compare it with the insurance treaty provided and search for any discrepancies related to treaty violations in the boardereaux. 
    Finally, generate an official report on your findings.
    """
    try:
        maxchars=50000
        report_text = call_openai_api((analysis_prompt +"\n\nBordereaux CSV:\n" + read_file(final_bordereaux_csv) + "\n\nTreaty text:\n" + final_treaty_text)[:maxchars])
    
    except Exception as e:
        print(f"Error in final call : {e}")
    print(report_text)
    try:
        report_json = json.loads(report_text)
        print(report_json)
        df = pd.DataFrame([report_json])
        final_report_csv = "Final_gpt_response.csv"
        df.to_csv(final_report_csv, index=False)
        print(f"CSV Report Saved: {final_report_csv}")
        
        output_pdf_path = 'AI_PDF_REPORT.pdf'
        generate_pdf_from_csv(final_report_csv, output_pdf_path)
    except Exception as e:
        print(f"Error in pdf from json/csv: {e}")

                
    return report_text
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
def generate_final_report(report):
    # HTML Template for the report
    html_template = f"""
    <html>
        <head>
            <title>AI Discrepancy Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 40px;
                }}
                h1 {{
                    color: #4CAF50;
                }}
                .report-content {{
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>AI Discrepancy Report</h1>
            <div class="report-content">
                <h2>Report Data:</h2>
                <p>{report}</p>
            </div>
        </body>
    </html>
    """
    return html_template
    
   