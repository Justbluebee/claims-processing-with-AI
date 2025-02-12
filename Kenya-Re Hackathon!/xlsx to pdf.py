import pandas as pd
from openpyxl import load_workbook
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
# Load the XLSX file
file_path = '"C:\Users\hp\Downloads\OneDrive_1_9-25-2024\3rd quota.xlsx"pip'
df = pd.read_excel(file_path)

# Create a PDF file
pdf_file = 'output_file.pdf'
c = canvas.Canvas(pdf_file, pagesize=landscape(letter))
width, height = landscape(letter)

# Add content to the PDF
text = c.beginText(40, height - 40)
text.setFont("Helvetica", 10)

# Convert DataFrame to string and add to PDF
for row in df.itertuples():
    text.textLine(str(row))

c.drawText(text)
c.save()
