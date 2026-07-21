from PySide6.QtGui import QPdfWriter, QPainter, QFont, QColor, QImage, Qt, QPageSize
from PySide6.QtCore import QRect

def generate_pdf_report(output_path, manager_name, site_id, risk_data, timestamp):
    pdf = QPdfWriter(output_path)
    pdf.setPageSize(QPageSize(QPageSize.A4))
    painter = QPainter(pdf)

    # Header
    painter.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
    painter.drawText(QRect(0, 40, 595, 30), Qt.AlignmentFlag.AlignCenter, "Industrial Safety Report")
    
    painter.setFont(QFont("Helvetica", 10))
    painter.drawText(20, 100, f"Manager: {manager_name}")
    painter.drawText(20, 120, f"Site ID: {site_id}")
    painter.drawText(20, 140, f"Generated: {timestamp}")

    # Table Setup
    y = 180
    painter.drawRect(20, y, 550, 30)
    headers = ["Zone", "Risk Level", "Gas(PPM)", "Worker Status"]
    x = 25
    for h in headers:
        painter.drawText(x, y + 20, h)
        x += 130

    # Table Content
    y += 30
    for entry in risk_data:
        painter.drawRect(20, y, 550, 30)
        row = [entry['zone'], entry['level'], str(entry['gas']), entry['worker']]
        x = 25
        for cell in row:
            painter.drawText(x, y + 20, cell)
            x += 130
        y += 30

    painter.end()