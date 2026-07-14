import os
import random
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

OUT_PATH = r"c:\Desktop\ALGONOX\PAY-IN-AUTOMATION\CRM_Ready_Oriental_RealData.pdf"

def add_header_footer(canvas, doc):
    canvas.saveState()
    # Header
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(colors.HexColor('#4B5563'))
    canvas.drawString(54, 750, "THE ORIENTAL INSURANCE COMPANY LIMITED")
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(doc.pagesize[0] - 54, 750, "Circular Ref: OICL/HO/MOTOR/2026/07")
    
    # Line below header
    canvas.setStrokeColor(colors.HexColor('#D1D5DB'))
    canvas.setLineWidth(0.5)
    canvas.line(54, 742, doc.pagesize[0] - 54, 742)
    
    # Footer
    canvas.line(54, 45, doc.pagesize[0] - 54, 45)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(54, 32, "Confidential - For Internal Broker Circulation Only")
    canvas.drawRightString(doc.pagesize[0] - 54, 32, f"Page {doc.page}")
    canvas.restoreState()

def build_pdf():
    # 0.75 inch margins (54 points)
    doc = SimpleDocTemplate(
        OUT_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#4B5563'),
        alignment=1, # Center
        spaceAfter=30
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=10
    )
    
    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=6
    )
    
    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1F2937')
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=1 # Center
    )

    story = []

    # =========================================================================
    # PAGE 1: COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 100))
    story.append(Paragraph("THE ORIENTAL INSURANCE COMPANY LIMITED", title_style))
    story.append(Paragraph("Head Office: A-25/27, Asaf Ali Road, New Delhi - 110002", subtitle_style))
    story.append(Spacer(1, 40))
    
    # Large Decorative block
    meta_table_data = [
        [Paragraph("<font color='white'><b>MOTOR DEPT. PAYOUT & COMMISSION GRID</b></font>", ParagraphStyle('MetaH', fontName='Helvetica-Bold', fontSize=14, leading=18, alignment=1))],
        [Paragraph("<b>Effective Date:</b> July 1, 2026 &nbsp;&nbsp;|&nbsp;&nbsp; <b>Line of Business:</b> Motor &nbsp;&nbsp;|&nbsp;&nbsp; <b>Insurer:</b> Oriental", ParagraphStyle('MetaB', fontName='Helvetica', fontSize=10, leading=14, alignment=1))]
    ]
    meta_table = Table(meta_table_data, colWidths=[doc.width])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F3F4F6')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E5E7EB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB'))
    ]))
    story.append(meta_table)
    
    story.append(Spacer(1, 60))
    story.append(Paragraph("<b>Notice:</b> This circular contains the payouts, commission rates, and reward guidelines for licensed brokers, corporate agents, and POSPs for the financial year 2026-27. All rates listed are net percentages of the Own Damage (OD) or Net Premium as specified in the respective tables.", body_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: LLM EXTRACTION RULES & INSTRUCTIONS
    # =========================================================================
    story.append(Paragraph("GENERAL DEFINITIONS AND MAPPING RULES FOR PARSING LLM", h1_style))
    story.append(Paragraph("To facilitate accurate data extraction and auto-population in the Algonox Broker Platform, the extraction LLM must enforce the following definitions, mapping constraints, and defaults when processing this document:", body_style))
    
    story.append(Paragraph("&bull; <b>Line of Business (LOB) Default</b>: Every rate, layout, and commission rule in this PDF belongs exclusively to the <b>Motor</b> Line of Business. The LOB field must always be set to 'Motor'.", bullet_style))
    
    story.append(Paragraph("&bull; <b>Insurance Company Mapping</b>: The insurer name for all records in this document is <b>Oriental</b>.", bullet_style))
    
    story.append(Paragraph("&bull; <b>File Type Rules</b>: File types are specified as 'New' (first-year policies), 'Renewal' (renewals of existing Oriental policies), or 'Rollover' (policies rolled over from another insurer). If a section does not explicitly state a file type restriction, it applies to 'ALL'.", bullet_style))
    
    story.append(Paragraph("&bull; <b>Vehicle Age Parsing</b>: Brand new vehicles (first year) have an age range of <b>0 to 1</b>. Do not represent first-year ranges as '1 to 1'. For vehicles older than 1 year, parse from/to values numerically as written (e.g. 1 to 5, 6 to 15).", bullet_style))
    
    story.append(Paragraph("&bull; <b>Make (Manufacturer) Rules</b>: Specific vehicle manufacturers (e.g. Maruti, Tata, Hyundai, Mahindra, Bajaj, Hero, Honda) mentioned in remarks, tables, or notes must be mapped to their standard uppercase name. If no manufacturer constraint is listed, it must default to 'ALL'.", bullet_style))
    
    story.append(Paragraph("&bull; <b>Model Rules</b>: Vehicle model names (e.g. Alto 800, Swift, Nexon, Activa, Splendor, Pulsar, Ace, Dost) mentioned in any description or remarks column must be parsed. If no model is specified, map to 'ALL'.", bullet_style))
    
    story.append(Paragraph("&bull; <b>CPA Status Extraction</b>: CPA (Compulsory Personal Accident) cover status must be mapped to 'YES' or 'NO'. Policies with remarks indicating 'CPA cover included' or 'with CPA' are set to 'YES'. Policies marked 'without CPA' or 'excl. CPA' are set to 'NO'.", bullet_style))
    
    story.append(Paragraph("&bull; <b>NCB Status Extraction</b>: NCB (No Claim Bonus) status must be mapped to 'YES' or 'NO'. Text showing 'NCB cases' or 'NCB >20%' maps to 'YES'. Text showing 'without NCB cases' or 'No NCB' maps to 'NO'.", bullet_style))
    
    story.append(Paragraph("&bull; <b>RTO & State Specificity</b>: State abbreviations (e.g., MH, GJ, AP, TN, KA, DL) and specific RTO codes (e.g., GJ-01, MH-12) mentioned in tables or notes must be extracted cleanly. If a state has no RTO mentioned, RTO defaults to 'ALL'.", bullet_style))
    
    story.append(Paragraph("&bull; <b>Sales Channel / Partner Type</b>: Channel names like POSP, MISP, Broker, and OEM Dealer must be mapped to the 'Partner Type' column. If none is listed, default to 'ALL'.", bullet_style))
    
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: PRIVATE CAR COMMISSION GRID
    # =========================================================================
    story.append(Paragraph("SECTION A: PRIVATE CAR COMMISSION SCHEDULE (OD & TP RATES)", h1_style))
    story.append(Paragraph("The following table represents the payout structure for Private Cars (Passenger Carrying Vehicles). All rates are Net OD or Net Net as specified. Slabs are defined by Engine Cubic Capacity (cc).", body_style))
    story.append(Spacer(1, 5))

    # Column Headers for Private Car Table
    pc_headers = ["Product", "CC Slab\n(From - To)", "File\nType", "Fuel\nType", "State", "OD\nRate", "TP\nRate", "Remarks / Rules for LLM Extraction"]
    
    # 5 rows of real data for Private Car
    pc_rows = [
        ["Private Car", "0 - 1000 cc", "New", "Petrol", "MH", "15.0%", "0.0%", "Maruti Alto 800 only, CPA cover included, Broker channel, RTO MH-12"],
        ["Private Car", "1001 - 1500 cc", "New", "Petrol", "MH", "17.5%", "0.0%", "Maruti Swift and Hyundai i20 only, CPA cover included, Broker channel, RTO MH-12"],
        ["Private Car", "1501 - 999999 cc", "Renewal", "Diesel", "GJ", "20.0%", "2.5%", "Tata Nexon and Creta only, without NCB cases, POSP channel, RTO GJ-01"],
        ["Private Car", "1001 - 1500 cc", "Rollover", "Petrol", "KA", "22.5%", "0.0%", "Hyundai vehicles only, NCB cases (NCB >20%), MISP channel, RTO KA-01"],
        ["Private Car", "0 - 1000 cc", "New", "Petrol", "TN", "15.0%", "0.0%", "Maruti vehicles only, CPA cover included, OEM Dealer channel, RTO TN-01"]
    ]
    
    # Build Table
    table_data = [[Paragraph(h.replace('\n', '<br/>'), table_header_style) for h in pc_headers]]
    for r in pc_rows:
        row_cells = []
        for idx, val in enumerate(r):
            align_right = idx in (5, 6)
            style = ParagraphStyle(
                f'Col_{idx}',
                parent=table_text_style,
                alignment=2 if align_right else 0
            )
            row_cells.append(Paragraph(val, style))
        table_data.append(row_cells)
        
    pc_table = Table(table_data, colWidths=[65, 55, 38, 38, 30, 30, 30, 218])
    pc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F9FAFB')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor('#F9FAFB')),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#FFFFFF'))
    ]))
    story.append(pc_table)
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Footnote Rules for LLM Extraction:</b>", ParagraphStyle('FootH', parent=body_style, fontName='Helvetica-Bold')))
    story.append(Paragraph("1. For Row 1 and 2: The LLM must extract <b>Make = MARUTI</b>, <b>Model = ALTO 800</b> / <b>SWIFT</b>, and <b>CPA Status = YES</b> (from remarks 'CPA cover included').", bullet_style))
    story.append(Paragraph("2. For Row 3: The LLM must extract <b>Make = TATA</b> / <b>HYUNDAI</b>, <b>Model = NEXON</b> / <b>CRETA</b>, and <b>NCB Status = NO</b> (from remarks 'without NCB cases').", bullet_style))
    story.append(Paragraph("3. For Row 4: The LLM must extract <b>Make = HYUNDAI</b>, <b>NCB Status = YES</b> (from remarks 'NCB cases'), and RTO as <b>KA-01</b>.", bullet_style))
    
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: TWO WHEELER & COMMERCIAL VEHICLE COMMISSION GRID
    # =========================================================================
    story.append(Paragraph("SECTION B: TWO WHEELER & COMMERCIAL VEHICLES GRID", h1_style))
    story.append(Paragraph("The following table represents the payout structure for Two Wheelers and Goods Carrying Commercial Vehicles (GCV). Slabs are defined by Engine cc for 2W, and Gross Vehicle Weight (gvw) in kg for GCV.", body_style))
    story.append(Spacer(1, 5))

    # Column Headers for 2W/GCV Table
    other_headers = ["Product", "Slab Range\n(cc or gvw)", "File\nType", "Fuel\nType", "State", "OD\nRate", "TP\nRate", "Remarks / Rules for LLM Extraction"]
    
    # 6 rows of real data for 2W & GCV (making it 11 total rows)
    other_rows = [
        ["Two Wheeler", "0 - 75 cc", "New", "Petrol", "AP", "25.0%", "0.0%", "Bajaj Activa only, CPA cover included, MISP channel, RTO AP-02"],
        ["Two Wheeler", "76 - 150 cc", "New", "Petrol", "AP", "30.0%", "0.0%", "Hero Splendor only, CPA cover included, Broker channel, RTO AP-02"],
        ["Two Wheeler", "151 - 350 cc", "Renewal", "Petrol", "TN", "20.0%", "5.0%", "Royal Enfield Classic 350, without NCB cases, POSP channel, RTO TN-01"],
        ["GCV LCV", "0 - 3500 kg", "New", "Diesel", "GJ", "35.0%", "0.0%", "Tata Ace only, CPA cover included, Direct Retail channel, RTO GJ-01"],
        ["GCV LCV", "3501 - 7500 kg", "New", "Diesel", "MH", "40.0%", "0.0%", "Mahindra Bolero Maxi only, CPA cover included, POSP channel, RTO MH-12"],
        ["PCV 3W", "0 - 6 seats", "New", "Electric", "DL", "30.0%", "10.0%", "Electric rickshaws only (e-cart, e-rickshaw), Broker channel, RTO DL-01"]
    ]
    
    # Build Table
    table_data = [[Paragraph(h.replace('\n', '<br/>'), table_header_style) for h in other_headers]]
    for r in other_rows:
        row_cells = []
        for idx, val in enumerate(r):
            align_right = idx in (5, 6)
            style = ParagraphStyle(
                f'Col2_{idx}',
                parent=table_text_style,
                alignment=2 if align_right else 0
            )
            row_cells.append(Paragraph(val, style))
        table_data.append(row_cells)
        
    other_table = Table(table_data, colWidths=[65, 55, 38, 38, 30, 30, 30, 218])
    other_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F9FAFB')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor('#F9FAFB')),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,6), (-1,6), colors.HexColor('#F9FAFB'))
    ]))
    story.append(other_table)
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Footnote Rules for LLM Extraction:</b>", ParagraphStyle('FootH2', parent=body_style, fontName='Helvetica-Bold')))
    story.append(Paragraph("1. For Row 1 and 2: The LLM must extract vehicle type as <b>Two Wheeler</b>, <b>Make = BAJAJ / HERO</b>, and <b>Model = ACTIVA / SPLENDOR</b>.", bullet_style))
    story.append(Paragraph("2. For Row 3: The LLM must extract <b>Make = RE</b>, <b>Model = CLASSIC 350</b>, and <b>NCB Status = NO</b>.", bullet_style))
    story.append(Paragraph("3. For Row 4 and 5: The LLM must extract LOB as <b>Motor</b>, vehicle type as <b>GCV LCV</b>, <b>Make = TATA / MAHINDRA</b>, and <b>Model = ACE / BOLERO MAXI</b>.", bullet_style))
    story.append(Paragraph("4. For Row 6: The LLM must extract <b>Fuel Type = ELECTRIC</b> (from remarks 'Electric rickshaws only').", bullet_style))

    # Build document
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"Successfully generated Oriental PDF at: {OUT_PATH}")

if __name__ == '__main__':
    build_pdf()
