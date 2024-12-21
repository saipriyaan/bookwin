import fitz  # PyMuPDF
import os

# Path to your PDF file
pdf_path = 'static/win.pdf'

# Directory where the images will be saved
output_dir = 'static/pdf_images/'

# Convert PDF to high-resolution images
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

pdf_document = fitz.open(pdf_path)

# Set the scaling factor for HD quality (2.0 for double the resolution)
scale = 2.0  # Adjust this value for higher or lower resolution
matrix = fitz.Matrix(scale, scale)

for page_num in range(len(pdf_document)):
    page = pdf_document.load_page(page_num)
    pix = page.get_pixmap(matrix=matrix)  # Apply scaling
    output_file = os.path.join(output_dir, f'page_{page_num + 1}.png')
    pix.save(output_file)

print("PDF pages converted to HD images and saved to:", output_dir)
