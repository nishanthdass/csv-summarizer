from PyPDF2 import PdfReader, PdfWriter

def remove_pdf_pages(input_pdf_path, output_pdf_path, pages_to_keep):
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()
    for page_num in range(len(reader.pages)):
        if page_num in pages_to_keep:
            writer.add_page(reader.pages[page_num])
    with open(output_pdf_path, 'wb') as output_pdf_file:
        writer.write(output_pdf_file)

if __name__ == "__main__":
    input_pdf_path = "New York City For Dummies.pdf"
    output_pdf_path = "output.pdf"
    pages_to_keep = [i for i in range(0, 1)]
    print(pages_to_keep)
    remove_pdf_pages(input_pdf_path, output_pdf_path, pages_to_keep)
    print(f"Pages removed, new PDF saved to {output_pdf_path}")