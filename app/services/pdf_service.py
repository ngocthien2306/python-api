from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

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

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )

        # Title
        title = Paragraph("BIÊN LAI THANH TOÁN", title_style)
        elements.append(title)
        elements.append(Spacer(1, 10*mm))

        # Company info
        company_info = f"""
        <b>Task Management AI</b><br/>
        Email: taskmanagement.agent@gmail.com<br/>
        Ngày: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}
        """
        elements.append(Paragraph(company_info, normal_style))
        elements.append(Spacer(1, 10*mm))

        # Customer info section
        elements.append(Paragraph("THÔNG TIN KHÁCH HÀNG", heading_style))

        customer_data = [
            ['Tên khách hàng:', user_data.get('username', 'N/A')],
            ['Email:', user_data.get('email', 'N/A')],
            ['User ID:', payment_data.get('user_id', 'N/A')]
        ]

        customer_table = Table(customer_data, colWidths=[60*mm, 90*mm])
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        elements.append(customer_table)
        elements.append(Spacer(1, 10*mm))

        # Payment details section
        elements.append(Paragraph("CHI TIẾT THANH TOÁN", heading_style))

        payment_details = [
            ['Mã giao dịch:', payment_data.get('transaction_id', 'N/A')],
            ['Gói đăng ký:', plan_data.get('name', 'N/A')],
            ['Số tiền:', f"{payment_data.get('amount', 0):,.0f} {payment_data.get('currency', 'VND')}"],
            ['Phương thức:', 'Stripe - Thẻ tín dụng/ghi nợ'],
            ['Ngày thanh toán:', payment_data.get('completed_at', datetime.utcnow()).strftime('%d/%m/%Y %H:%M')],
            ['Trạng thái:', 'Đã thanh toán ✓']
        ]

        payment_table = Table(payment_details, colWidths=[60*mm, 90*mm])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d1fae5')),
        ]))

        elements.append(payment_table)
        elements.append(Spacer(1, 10*mm))

        # Subscription details section
        elements.append(Paragraph("CHI TIẾT GÓI ĐĂNG KÝ", heading_style))

        features = plan_data.get('features', [])
        features_text = '<br/>'.join([f'• {feature}' for feature in features])

        subscription_info = f"""
        <b>Gói:</b> {plan_data.get('name', 'N/A')}<br/>
        <b>Thời hạn:</b> {plan_data.get('duration_days', 'N/A')} ngày<br/>
        <b>Giới hạn tokens:</b> {plan_data.get('tokens_limit', 0):,}<br/>
        <b>Giới hạn requests:</b> {plan_data.get('requests_limit', 0):,}<br/>
        <br/>
        <b>Tính năng:</b><br/>
        {features_text}
        """

        elements.append(Paragraph(subscription_info, normal_style))
        elements.append(Spacer(1, 15*mm))

        # Total amount box
        total_data = [[f"TỔNG CỘNG: {payment_data.get('amount', 0):,.0f} {payment_data.get('currency', 'VND')}"]]
        total_table = Table(total_data, colWidths=[150*mm])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
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
            alignment=TA_CENTER
        )

        footer_text = """
        Cảm ơn quý khách đã sử dụng dịch vụ!<br/>
        Biên lai này được tạo tự động bởi hệ thống.<br/>
        Nếu có thắc mắc, vui lòng liên hệ: taskmanagement.agent@gmail.com
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
