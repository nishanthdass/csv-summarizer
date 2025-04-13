import os
from rich import print as rprint
import pymupdf
import pymupdf4llm
import re
from statistics import median
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from itertools import groupby
from operator import itemgetter


def markdown_format(page_lines, page_num):
    '''
    Convert page lines to markdown and insert metadata.
    '''
    md_lines = []
    for line in page_lines:
        text = line["text"]
        block_num = line["block"]
        is_header = line["is_header"]

        # Instead of splitting, just wrap the whole text as Document
        doc = Document(
            page_content=text,
            metadata={
                "page_number": page_num,
                "block_number": block_num,
                "is_header": is_header
            }
        )
        md_lines.append(doc)
    return md_lines


recur_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=40,
    length_function=len,
    is_separator_regex=False,
)

def recursive_chunk_splitter(md_lines):
    '''
    Convert page lines to markdown.
    '''
    chunks_with_metadata = [] # use this to accumlate chunk records

    for item in md_lines: # pull these keys from the json
        item_text = item.page_content
        item_metadata = item.metadata
        item_text_chunks = recur_text_splitter.split_text(item_text) # split the text into chunks
        chunk_seq_index = 0

        for chunk in item_text_chunks:# only take the first 20 chunks
            item_metadata['chunk_seq_index'] = chunk_seq_index
            item_metadata['block_id'] = f'{item.metadata["pdf_file_name"]}-{item.metadata["page_number"]}-{item.metadata["block_number"]}-chunk{chunk_seq_index:04d}'
            copy_metadata = item_metadata.copy()
            chunks_with_metadata.append(Document(page_content=chunk, metadata=copy_metadata))
            chunk_seq_index += 1

    return chunks_with_metadata


def insert_additional_metadata(md, page, file_path, page_nums):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    
    title = page['metadata']['title'] if page['metadata']['title'] else file_name
    page_count = page['metadata']['page_count']
    toc_items = page.get('toc_items', [])

    # Handle TOC gracefully
    if toc_items and toc_items[0].strip() != "":
        toc_item = toc_items[0]
        chapter_name = toc_item[1] if toc_item[1].strip() != "" else "__Unknown__"
        chapter_number = toc_item[0] if toc_item[0].strip() != "" else "__Unknown__"
    else:
        chapter_name = "__Unknown__"
        chapter_number = "__Unknown__"

    # Default source is page number
    source = None

    for line in md:
        initial_meta = line.metadata.copy()

        # Update source if header
        if initial_meta.get("is_header") is True:
            source = line.page_content

        # Rebuild metadata
        line.metadata = {}
        line.metadata['source'] = source
        line.metadata['is_header'] = initial_meta.get("is_header")
        line.metadata['pdf_file_name'] = file_name
        line.metadata['toc'] = toc_items
        line.metadata['block_number'] = initial_meta.get("block_number", -1)
        line.metadata['section_block_number'] = 0
        line.metadata['page_number'] = page['metadata']['page']
        line.metadata['has_images'] = False
        line.metadata['alt_title'] = title
        line.metadata['page_count'] = page_count
        line.metadata['chapter_name'] = chapter_name
        line.metadata['chapter_number'] = chapter_number
        line.metadata['page_id'] = f'{file_name}-{page["metadata"]["page"]}'

    return md


def span_is_header(span, size_median):
    size = span["size"]
    flags = span["flags"]
    text  = span["text"].strip()
    font  = span["font"].lower()

    # Header detection logic
    is_header = False
    if size > 1.5 * size_median:
        is_header = True
    if size >= 18:
        is_header = True
    if flags == 20:
        is_header = True

    line_obj = {
        "is_header": is_header,
        "line": span["line"],
        "block": span["block"],
        "text": span["text"]
    }

    return line_obj
    

def make_header_detector():
    returns_list = []

    def my_header_detector(span, page=None):
        ret_val = ""
        returns_list.append(span)
        return ret_val
        
    return my_header_detector, returns_list

    


def process_pdf(pdf_file, file_path, page_nums=None):
    '''
    Process a single page of a PDF file.
    '''

    book_array = []
    prev_header = {}
    has_images = False

    for num in range(len(pdf_file)):
        detector_func, page_spans = make_header_detector()

        # Initialize splitter tools
        md_output = pymupdf4llm.to_markdown(
            file_path,
            page_chunks=True,
            pages = [num],
            extract_words=True,
            hdr_info=detector_func
        )
        
        # intialize structures to hold words/lines
        text_array = []

        # Calculate median size
        sizes = [span["size"] for span in page_spans if span["size"] > 0]
        size_median = median(sizes) if sizes else 9

        # Assess if line is a header and build text_array of objs
        text_array = [span_is_header(span, size_median) for span in page_spans]

        # sort by block and line
        sorted_lines = sorted(text_array, key=lambda x: (x["block"], x["line"]))

        # rprint(sorted_lines)


        # merge lines into their respective blocks
        merged_blocks = []
        for block_num, group in groupby(sorted_lines, key=lambda x: x["block"]):
            block_lines = list(group)
            merged_text = " ".join(line["text"] for line in block_lines)
            is_header = any(line["is_header"] for line in block_lines)

            split_sentence = merged_text.split(" ")
            length_sentence = len(split_sentence)
            if length_sentence >= 10:
                is_header = False

            merged_blocks.append({
                "block": block_num,
                "is_header": is_header,
                "text": merged_text
            })

        intitial_md = markdown_format(merged_blocks, num)
        
        final_md = insert_additional_metadata(intitial_md, md_output[0], file_path, num)
            
        # Split markdown into chunks
        md_lines_chunked = recursive_chunk_splitter(final_md)

        book_array.extend(md_lines_chunked)

    return book_array


def post_process_pdf(processed_pdf):
    last_source = None

    
    # If secttion name not available use page number as identifier
    for doc in processed_pdf:
        if doc.metadata['source'] is not None:
            last_source = doc.metadata['source']
        if doc.metadata['source'] is None:
            if last_source is not None:
                doc.metadata['source'] = last_source
            else:
                doc.metadata['source'] = "__Page__" + str( doc.metadata['page_number'])
                
    section = None
    count = 0
    is_header = None

    # Add sources or paragraph header to each block
    for doc in processed_pdf:
        if doc.metadata['is_header'] is True:
            is_header 
            section = doc.metadata['source']
            count = 0
            doc.metadata['section_block_number'] = count
            
        elif doc.metadata['is_header'] is False and section == doc.metadata['source'] and doc.metadata['chunk_seq_index'] == 0:
            count += 1
            doc.metadata['section_block_number'] = count
        elif doc.metadata['is_header'] is False and section == doc.metadata['source'] and doc.metadata['chunk_seq_index'] > 0:
            doc.metadata['section_block_number'] = count


    counter = 0
    prev_block_number = None
    
    for doc in processed_pdf:
        block_number = doc.metadata['block_number']
        
        if block_number != prev_block_number:
            doc.metadata['block_number'] = counter
            counter += 1
    
    return processed_pdf
                