import requests
from odoo import models, fields, api
import logging
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import base64
import io

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    sc_name = fields.Char(string='SC Name')
    sc_idmedia = fields.Integer(string='SC ID Media')
    sc_active = fields.Boolean(string='SC Active')
    pdf_attachment = fields.Binary(string='PDF Attachment', attachment=True)
    _update_from_api_done = fields.Boolean(string='Update from API Done', default=False, store=False)

    def update_lead_from_api(self):
        _logger.info('Starting update_lead_from_api process')
        project_id = self.name or '8408224'  # Use the value from the name field or a default value
        url = f'https://api.sitecapture.com/customer_api/2_0/project/{project_id}'
        headers = {
            'API_KEY': 'IL398D2CR9S',
            'Content-Type': 'application/json'
        }
        auth = ('alexander.ionleed', 'alexander.ionleed')
        
        try:
            _logger.info('Sending GET request to API')
            response = requests.get(url, headers=headers, auth=auth)
            response.raise_for_status()  # Raise an exception for HTTP errors
            _logger.info('API request successful')
            data = response.json()
            if 'display_line1' in data and 'template_id' in data:
                self.write({
                    'sc_name': data.get('display_line1', self.sc_name),
                    'sc_idmedia': data.get('template_id', self.sc_idmedia),
                    'sc_active': bool(data.get('display_line1')),
                    '_update_from_api_done': True
                })
                _logger.info('Lead updated with data from API')
                self.create_pdf_attachment(data)
            else:
                _logger.warning('Expected keys not found in API response')
        except requests.exceptions.RequestException as e:
            _logger.error('Failed to fetch data from API: %s', e)
        except Exception as e:
            _logger.error('An unexpected error occurred: %s', e)

    def create_pdf_attachment(self, data):
        _logger.info('Creating PDF attachment')
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Track printed sections
        printed_sections = set()
        
        # Define styles
        styles = getSampleStyleSheet()
        section_style = styles['Heading1']
        section_style.fontSize = 20
        section_style.textColor = colors.black
        section_style.alignment = 1  # Center alignment
        section_style.fontName = 'Helvetica-Bold'
        
        key_style = styles['Normal']
        key_style.fontSize = 12
        key_style.textColor = colors.black
        
        # Margins
        left_margin = 50
        right_margin = 50
        available_width = letter[0] - left_margin - right_margin
        
        # Iterate over fields to create sections and add images
        y_position = 750
        for field in data.get('fields', []):
            section_key = field.get('section_key')
            if section_key and section_key not in printed_sections:
                p.showPage()
                p.setFont(section_style.fontName, section_style.fontSize)
                p.drawCentredString(letter[0] / 2, letter[1] / 2, section_key)
                printed_sections.add(section_key)
                p.showPage()  # Move to the next page for content
                y_position = 750
            
            # Print the key as a subtitle
            key = field.get('key')
            if key:
                # Check if there is enough space for the key and the image
                if y_position < 170:  # Adjust this value based on the height of the key and image
                    p.showPage()
                    y_position = 750
                p.setFont(key_style.fontName, key_style.fontSize)
                p.drawString(left_margin, y_position, key)
                y_position -= 20
            
            # Add images if available
            for media in field.get('media', []):
                media_id = media.get('id')
                if media_id:
                    image_url = f'https://api.sitecapture.com/customer_api/1_0/media/image/{media_id}'
                    try:
                        image_response = requests.get(image_url, headers={'API_KEY': 'IL398D2CR9S'}, auth=('alexander.ionleed', 'alexander.ionleed'))
                        image_response.raise_for_status()
                        image_data = image_response.content
                        image = ImageReader(io.BytesIO(image_data))
                        image_width, image_height = image.getSize()
                        aspect_ratio = image_height / image_width
                        image_height = available_width * aspect_ratio
                        if y_position < image_height + 50:  # Check if there is enough space for the image
                            p.showPage()
                            y_position = 750
                        p.drawImage(image, left_margin, y_position - image_height, width=available_width, height=image_height)
                        y_position -= (image_height + 20)  # Adjust y_position for the next image
                    except Exception as e:
                        _logger.error('Failed to load image from URL: %s', e)
        
        p.showPage()
        p.save()
        pdf_value = buffer.getvalue()
        buffer.close()

        pdf_name = data.get('display_line1', 'Lead_Details')  # Use display_line1 as the PDF name

        self.write({
            'pdf_attachment': base64.b64encode(pdf_value)
        })

        attachment = self.env['ir.attachment'].create({
            'name': f'{pdf_name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_value),
            'res_model': 'crm.lead',
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })
        _logger.info('PDF attachment created: %s', attachment)

    @api.model
    def create(self, vals):
        _logger.info('Creating a new lead')
        record = super(CrmLead, self).create(vals)
        if not vals.get('sc_idmedia'):
            record.update_lead_from_api()
        return record

    def write(self, vals):
        _logger.info('Updating an existing lead')
        return super(CrmLead, self).write(vals)