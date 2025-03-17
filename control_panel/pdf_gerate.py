from datetime import datetime
import io
import os
from django.conf import settings
import requests
from PyPDF2 import PdfMerger
from PIL import Image
from django.core.files.storage import default_storage


from fpdf import FPDF

# def create_details_pdf(details):
#     pdf = FPDF()
#     pdf.add_page()
#     pdf.set_font("Arial", size=12)
    
#     for key, value in details.items():
#         pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
    
#     pdf_bytes = io.BytesIO()
#     pdf.output(pdf_bytes)
#     pdf_bytes.seek(0)
    
#     return pdf_bytes
def create_details_pdf(details):
    pdf = FPDF()
    pdf.add_page()

    # Define A4 size in mm
    A4_WIDTH, A4_HEIGHT = 210, 297

    # Set font for details
    pdf.set_font("Arial", size=12)

    # Extract profile image URL if available
    profile_image_url = details.get('profile_image')

    # Add the profile image if provided
    if profile_image_url:
        # Load the image
        response = requests.get(profile_image_url)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            
            # Save image to a temporary location
            # temp_image_path = '/tmp/temp_image.jpg'
            # image.save(temp_image_path)

            # Set the position and size for the image
            image_x = A4_WIDTH - 50  # Position image 50mm from the right
            image_y = 10  # Position image 10mm from the top
            image_w = 40  # Image width
            image_h = 40  # Image height

            # Add image to PDF
            pdf.image(image, x=image_x, y=image_y, w=image_w, h=image_h)

    # Define table position
    table_x = 10  # X position of the table
    table_y = 60  # Y position of the table (below the image)

    # Set X and Y position for the table
    pdf.set_xy(table_x, table_y)
    
    # Set font for the table headers
    pdf.set_font("Arial", size=12)
    
    # Define column widths
    col_width = (A4_WIDTH - 20) / 2  # Adjusted to account for margins
    row_height = 10
    pdf.set_fill_color(200, 220, 255)  # Header background color
    
    # Draw table headers
    pdf.cell(col_width * 2, row_height, "Admin Details", border=1, fill=True,align='C')
    # pdf.cell(col_width, row_height, "Value", border=1, fill=True)
    pdf.ln(row_height)
    
    # Set font for the table content
    pdf.set_font("Arial", size=10)

    # Add table rows
    for key, value in details.items():
        if key != 'profile_image':  # Skip profile image URL key
            # Draw key cell
            pdf.cell(col_width, row_height, txt=key, border=1)
            # Draw value cell
            pdf.cell(col_width, row_height, txt=str(value), border=1)
            pdf.ln(row_height)
    
    pdf_bytes = io.BytesIO()
    pdf.output(pdf_bytes)
    pdf_bytes.seek(0)
    
    return pdf_bytes


def merge_files_from_urls(file_urls, request, admin_id, details):
    merger = PdfMerger()

    # Add stamp files first
    for url in file_urls:
        if not url:
            continue  # Skip if URL is None or empty

        response = requests.get(url)
        if response.status_code == 200:
            content_type = response.headers['Content-Type']
            if 'pdf' in content_type:
                # If the file is a PDF
                file = io.BytesIO(response.content)
                merger.append(file)
            elif 'image' in content_type:
                # If the file is an image
                image = Image.open(io.BytesIO(response.content))
                pdf_image = convert_image_to_pdf(image)
                merger.append(pdf_image)

    # Add details as a new PDF page
    details_pdf = create_details_pdf(details)
    merger.append(details_pdf)

    # Merge all PDFs
    merged_pdf = io.BytesIO()
    merger.write(merged_pdf)
    merger.close()
    merged_pdf.seek(0)

    # Save the merged PDF to the media directory
    filename = f"admin_{admin_id}_details_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    with default_storage.open(file_path, 'wb') as out_file:
        out_file.write(merged_pdf.read())

    pdf_relative_path = os.path.join('pdf_files', filename)
    # pdf_url = os.path.join(settings.MEDIA_URL, pdf_relative_path)
    # scheme = "https" if request.is_secure() else "http"
    # pdf_url = f"{scheme}://{request.get_host()}{file_path}"
    
    # # Get the absolute URL of the merged PDF
    # merged_pdf_url = request.build_absolute_uri(settings.MEDIA_URL + filename)

    # return merged_pdf_url

    pdf_relative_path = f"/{pdf_relative_path}"
    
    return pdf_relative_path

# def merge_files_from_urls(file_urls,request,admin_id):
#     merger = PdfMerger()

#     for url in file_urls:
#         response = requests.get(url)
#         if response.status_code == 200:
#             content_type = response.headers['Content-Type']
#             if 'pdf' in content_type:
#                 # If the file is a PDF
#                 file = io.BytesIO(response.content)
#                 merger.append(file)
#             elif 'image' in content_type:
#                 # If the file is an image
#                 image = Image.open(io.BytesIO(response.content))
#                 pdf_image = convert_image_to_pdf(image)
#                 merger.append(pdf_image)

#     merged_pdf = io.BytesIO()
#     merger.write(merged_pdf)
#     merger.close()
#     merged_pdf.seek(0)

#     # Save the merged PDF to the media directory
#     filename = f"admin_{admin_id}_details_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
#     file_path = os.path.join(settings.MEDIA_ROOT, filename)
#     with default_storage.open(file_path, 'wb') as out_file:
#         out_file.write(merged_pdf.read())

#     pdf_relative_path= os.path.join('pdf_files', filename)

#     pdf_url=os.path.join(settings.MEDIA_URL,pdf_relative_path)
#     scheme = "https" if request.is_secure()  else "http"
#     file_path =  pdf_url.replace('\\', '/')
#     pdf_url = f"{scheme}://{request.get_host()}{file_path}"
    
#     # Get the absolute URL of the merged PDF
#     merged_pdf_url = request.build_absolute_uri(settings.MEDIA_URL + filename)

#     return  merged_pdf_url

# def convert_image_to_pdf(image):
#     # Define A4 size in points (1 point = 1/72 inch)
#     A4_WIDTH, A4_HEIGHT = 595.2, 841.8

#     # Resize the image to fit A4 size while maintaining aspect ratio
#     image.thumbnail((A4_WIDTH, A4_HEIGHT))

#     # Create a new PDF-sized image with a white background
#     pdf_image = Image.new('RGB', (int(A4_WIDTH), int(A4_HEIGHT)), 'white')
#     pdf_image.paste(image, (int((A4_WIDTH - image.width) / 2), int((A4_HEIGHT - image.height) / 2)))

#     pdf_bytes = io.BytesIO()
#     pdf_image.save(pdf_bytes, format='PDF')
#     pdf_bytes.seek(0)
#     return pdf_bytes



def convert_image_to_pdf(image):
    # Define A4 size in points (1 point = 1/72 inch)
       # Define A4 size in points (1 point = 1/72 inch)
    A4_WIDTH, A4_HEIGHT = 595.2, 841.8
    image.thumbnail((A4_WIDTH, A4_HEIGHT))

    # Create a PDF object
    pdf = FPDF()
    pdf.add_page()
    pdf_image = Image.new('RGB', (int(A4_WIDTH), int(A4_HEIGHT)), 'white')
    pdf_image.paste(image, (int((A4_WIDTH - image.width) / 2), int((A4_HEIGHT - image.height) / 2)))
    # Convert image to A4 size
    pdf.image(pdf_image, x=0, y=0)
    
    pdf_bytes = io.BytesIO()
    pdf.output(pdf_bytes)
    pdf_bytes.seek(0)
    
    return pdf_bytes