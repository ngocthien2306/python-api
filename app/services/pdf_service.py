from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from io import BytesIO
import logging
import os

logger = logging.getLogger(__name__)

# Register Vietnamese-compatible fonts
try:
    # Get font directory path
    font_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'fonts')
    font_normal = os.path.join(font_dir, 'DejaVuSans.ttf')
    font_bold = os.path.join(font_dir, 'DejaVuSans-Bold.ttf')

    # Register DejaVu Sans fonts
    pdfmetrics.registerFont(TTFont('DejaVuSans', font_normal))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_bold))
    FONT_NAME = 'DejaVuSans'
    FONT_NAME_BOLD = 'DejaVuSans-Bold'
    logger.info(f"Using DejaVu Sans font for Vietnamese support from {font_dir}")
except Exception as e:
    # Fallback to default fonts (will have encoding issues with Vietnamese)
    logger.warning(f"Could not load DejaVu fonts: {e}. Using Helvetica as fallback.")
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'

class PDFReceiptService:
    """Service to generate payment receipt PDF"""

    def generate_receipt(self, payment_data: dict, user_data: dict, plan_data: dict) -> BytesIO:
        """
        Generate PDF receipt for payment

        Args:
            payment_data: Payment information
            user_data: User information
            plan_data: Subscription plan details

        Returns:
            BytesIO: PDF file in memory
        """
        buffer = BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30*mm,
            leftMargin=30*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        # Container for elements
        elements = []
        styles = getSampleStyleSheet()

        # Custom styles with Vietnamese font support
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=FONT_NAME_BOLD
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=12,
            fontName=FONT_NAME_BOLD
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            fontName=FONT_NAME
        )

        # Title
        title = Paragraph("PAYMENT RECEIPT", title_style)
        elements.append(title)
        elements.append(Spacer(1, 10*mm))

        # Company info
        from datetime import timezone
        company_info = f"""
        <b>Task Management AI</b><br/>
        Email: taskmanagement.agent@gmail.com<br/>
        Date: {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}
        """
        elements.append(Paragraph(company_info, normal_style))
        elements.append(Spacer(1, 10*mm))

        # Customer info section
        elements.append(Paragraph("CUSTOMER INFORMATION", heading_style))

        customer_data = [
            ['Customer Name:', user_data.get('username', 'N/A')],
            ['Email:', user_data.get('email', 'N/A')],
            ['Customer ID:', payment_data.get('user_id', 'N/A')]
        ]

        customer_table = Table(customer_data, colWidths=[60*mm, 90*mm])
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), FONT_NAME_BOLD),
            ('FONTNAME', (1, 0), (1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elements.append(customer_table)
        elements.append(Spacer(1, 10*mm))

        # Payment details section
        elements.append(Paragraph("PAYMENT DETAILS", heading_style))

        payment_details = [
            ['Transaction ID:', payment_data.get('transaction_id', 'N/A')],
            ['Subscription Plan:', plan_data.get('name', 'N/A')],
            ['Amount:', f"{payment_data.get('amount', 0):,.0f} {payment_data.get('currency', 'VND')}"],
            ['Payment Method:', 'Stripe - Credit/Debit Card'],
            ['Payment Date:', payment_data.get('completed_at', datetime.now(timezone.utc)).strftime('%B %d, %Y at %H:%M UTC')],
            ['Status:', 'PAID ✓']
        ]

        payment_table = Table(payment_details, colWidths=[60*mm, 90*mm])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), FONT_NAME_BOLD),
            ('FONTNAME', (1, 0), (1, -1), FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d1fae5')),
        ]))

        elements.append(payment_table)
        elements.append(Spacer(1, 10*mm))

        # Subscription details section
        elements.append(Paragraph("SUBSCRIPTION DETAILS", heading_style))

        features = plan_data.get('features', [])
        features_text = '<br/>'.join([f'• {feature}' for feature in features])

        subscription_info = f"""
        <b>Plan:</b> {plan_data.get('name', 'N/A')}<br/>
        <b>Duration:</b> {plan_data.get('duration_days', 'N/A')} days<br/>
        <b>Token Limit:</b> {plan_data.get('tokens_limit', 0):,} tokens<br/>
        <b>Request Limit:</b> {plan_data.get('requests_limit', 0):,} requests<br/>
        <br/>
        <b>Features:</b><br/>
        {features_text}
        """

        elements.append(Paragraph(subscription_info, normal_style))
        elements.append(Spacer(1, 15*mm))

        # Total amount box
        total_data = [[f"TOTAL AMOUNT: {payment_data.get('amount', 0):,.0f} {payment_data.get('currency', 'VND')}"]]
        total_table = Table(total_data, colWidths=[150*mm])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
        ]))

        elements.append(total_table)
        elements.append(Spacer(1, 15*mm))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER,
            fontName=FONT_NAME
        )

        footer_text = """
        Thank you for your business!<br/>
        This receipt was generated automatically by the system.<br/>
        If you have any questions, please contact: taskmanagement.agent@gmail.com
        """
        elements.append(Paragraph(footer_text, footer_style))

        # Build PDF
        doc.build(elements)

        # Get PDF data
        buffer.seek(0)
        logger.info(f"Generated PDF receipt for payment {payment_data.get('_id')}")

        return buffer

    def save_receipt(self, buffer: BytesIO, filename: str) -> str:
        """Save PDF buffer to file"""
        try:
            with open(filename, 'wb') as f:
                f.write(buffer.getvalue())
            logger.info(f"Saved PDF receipt to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving PDF: {str(e)}")
            raise
