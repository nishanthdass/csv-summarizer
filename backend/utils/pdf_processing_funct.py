import os
from rich import print as rprint
import pymupdf4llm
from langchain_core.documents import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


# Intialize variables for character text splitters
headers = ['#', '##', '###', '####', '#####', '######']

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    ("####", "Header 4"),
    ("#####", "Header 5"),
    ("######", "Header 6"),
]

separators = [
    "\n\n",
    "\n", 
    " ",
]
 
# Intialize variables for text splitters
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on,
    strip_headers=False
)

recur_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=40,
    length_function=len,
    is_separator_regex=False,
)


def finalize_paragraph(build_paragraph, page_lines):
    """
    Helper function to finalize a paragraph and add it to the page_lines list.
    """
    if build_paragraph:
        joined_paragraph = ' '.join(build_paragraph)
        page_lines.append(joined_paragraph)
        build_paragraph.clear()


def split_into_paragraphs(words, text):
    """
    Split text into paragraphs based on block information from words.
    """
    word_count = 0
    page_lines = []
    build_paragraph = []
    block = None

    for line in text.split('\n'):
        if word_count < len(words):
            if block != words[word_count][5] and build_paragraph:
                finalize_paragraph(build_paragraph, page_lines)
                block = words[word_count][5]
        else:
            if len(build_paragraph) > 0:
                finalize_paragraph(build_paragraph, page_lines)
                block = None

        for word in line.split(' '):
            if word_count >= len(words) and word.strip():
                build_paragraph.append(word)
            elif word in headers:
                build_paragraph.append(word)
            elif word.strip():
                build_paragraph.append(word)
                word_count += 1

    return page_lines

def recursive_chunk_splitter(md_lines):
    '''
    Convert page lines to markdown.
    '''
    chunks_with_metadata = [] # use this to accumlate chunk records

    for item in md_lines: # pull these keys from the json
        item_text = item.page_content
        item_metadata = item.metadata
        item_text_chunks = recur_text_splitter.split_text(item_text) # split the text into chunks
        chunk_seq_id = 0

        for chunk in item_text_chunks:# only take the first 20 chunks
            item_metadata['chunk_seq_id'] = chunk_seq_id
            item_metadata['line_id'] = f'{item.metadata["pdf_file_name"]}-{item.metadata["page_number"]}-{item.metadata["line_number"]}-chunk{chunk_seq_id:04d}'
            copy_metadata = item_metadata.copy()
            chunks_with_metadata.append(Document(page_content=chunk, metadata=copy_metadata))
            chunk_seq_id += 1

    return chunks_with_metadata


def markdown_chunk_splitter(page_lines):
    '''
    Convert page lines to markdown.
    '''
    md_lines = []
    for line in page_lines:
        md_header_splits = markdown_splitter.split_text(line)
        
        md_lines.append(md_header_splits[0])
    return md_lines


def insert_metadata(markdown_lines, page_obj, has_images, pdf_file_name, prev_header):
    '''
    Insert line number, page number into metadata.
    '''

    title = page_obj['metadata']['title']
    page_count = page_obj['metadata']['page_count']
    toc_items = page_obj['toc_items']
    if toc_items:
        toc_items = toc_items[0]
        chapter_name = toc_items[1]
        chapter_number = toc_items[0]
    else:
        chapter_name = "__Unknown__"
        chapter_number = "__Unknown__"

    last_meta = None
    line_count = 0

    for line in markdown_lines:
        line_count += 1
        intial_meta = line.metadata.copy()
        has_header = len(intial_meta.keys()) > 0
        has_prev_header = len(prev_header.keys())

        if has_header and not has_prev_header:
            prev_header = intial_meta
        elif prev_header != intial_meta and has_header:
            prev_header = intial_meta

        if len(prev_header.values()) > 0:
            list_val = list(prev_header.values())[0]
        else:
            list_val = "__Unknown__"
        line.metadata = {}
        line.metadata['source'] = list_val
        line.metadata['pdf_file_name'] = pdf_file_name
        line.metadata['toc'] = toc_items
        line.metadata['line_number'] = line_count
        line.metadata['page_number'] = page_obj['metadata']['page']
        line.metadata['has_images'] = has_images
        line.metadata['alt_title'] = title
        line.metadata['page_count'] = page_count
        line.metadata['chapter_name'] = chapter_name
        line.metadata['chapter_number'] = chapter_number
        line.metadata['page_id'] = f'{pdf_file_name}-{page_obj["metadata"]["page"]}'

    return markdown_lines, prev_header


def save_pdf_imgs(pdf_file, page_index_input, output_folder_path, file_name_minus_ext):
    """
    Extract images from a PDF file.
    """
    # print(f"Extracting images from page {page_index_input}")
    image_found = False

    for page_index in range(len(pdf_file)):
        page = pdf_file.load_page(page_index)
        image_list = page.get_images(full=True)

        for image_index, img in enumerate(image_list, start=1):
            if page_index == page_index_input-1:
                image_found = True

                xref = img[0]
                base_image = pdf_file.extract_image(xref)
                image_bytes = base_image["image"]

                # get the image extension
                image_ext = base_image["ext"]

                # save the image
                image_name = f"{file_name_minus_ext}_{page_index+1}_{image_index}.{image_ext}"

                image_path = os.path.join(output_folder_path, image_name)
                
                with open(image_path, "wb") as image_file:
                    image_file.write(image_bytes)
                    # print(f"[+] Image saved as {image_name}")
    
    return image_found


def process_pdf(pdf_file, file_path, page_nums=None, output_folder_path=None, file_name_minus_ext=None):
    '''
    Process a single page of a PDF file.
    '''

    book_array = []
    prev_header = {}
    has_images = False

    # Initialize splitter tools
    md_output = pymupdf4llm.to_markdown(
        file_path, 
        pages=page_nums,
        page_chunks=True, 
        extract_words=True
    )

    for page in md_output:
        # rprint(f"Processing page {page}")
        # Extract images
        if len(page['images']) > 0:
            has_images = save_pdf_imgs(pdf_file, page['metadata']['page'], output_folder_path, file_name_minus_ext)

        # Variables for processing text
        text = page['text']
        words = page['words']

        # Split text by using block information from words(pymupdf4llm output)
        page_lines = split_into_paragraphs(words, text)
        # Convert page lines to markdown
        md_lines = markdown_chunk_splitter(page_lines)

        # Insert line number, page number into metadata
        md_lines, prev_header = insert_metadata(md_lines, page, has_images, file_name_minus_ext, prev_header)
        # Split markdown into chunks
        md_lines_chunked = recursive_chunk_splitter(md_lines)

        book_array.extend(md_lines_chunked)
        has_images = False

    return book_array


def param_insert(pdf_obj_instance):
    '''
    Format params for Neo4j query
    '''
    params = {
        'chunkParam': {
            'source': pdf_obj_instance.metadata['source'],
            'pdfFileName': pdf_obj_instance.metadata['pdf_file_name'],
            'toc': pdf_obj_instance.metadata['toc'],
            'lineNumber': pdf_obj_instance.metadata['line_number'],
            'pageNumber': pdf_obj_instance.metadata['page_number'],
            'hasImages': pdf_obj_instance.metadata['has_images'],
            'altTitle': pdf_obj_instance.metadata['alt_title'],
            'pageCount': pdf_obj_instance.metadata['page_count'],
            'chapterName': pdf_obj_instance.metadata['chapter_name'],
            'chapterNumber': pdf_obj_instance.metadata['chapter_number'],
            'pageId': pdf_obj_instance.metadata['page_id'],
            'lineId': pdf_obj_instance.metadata['line_id'],
            'chunkSeqId': pdf_obj_instance.metadata['chunk_seq_id'],
            'text': pdf_obj_instance.page_content
        }
    }

    return params