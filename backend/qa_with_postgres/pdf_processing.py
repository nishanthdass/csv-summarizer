import pymupdf
import pymupdf4llm
from langchain.docstore.document import Document
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter, CharacterTextSplitter
from rich import print as rprint
import re

# Initialize output dictionary
book_array = []
page_obj = {}

# Intialize variables for character text splitters
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    ("####", "Header 4"),
    ("#####", "Header 5"),
    ("######", "Header 6"),
]

headers = ['#', '##', '###', '####', '#####', '######']

separators = [
    "\n\n",
    "\n", 
    " ",
]

# Initialize splitter tools
output = pymupdf4llm.to_markdown(
    "Hands-On Machine Learning with Scikit.pdf", 
    pages=[62], 
    write_images=True,
    page_chunks=True, 
    extract_words=True
)

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on,
    strip_headers=False
)

recur_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=30,
    length_function=len,
    separators=separators,
    is_separator_regex=True,
    keep_separator=True
)

# Helper function
def finalize_paragraph(build_paragraph, page_lines):
    """
    Helper function to finalize a paragraph and add it to the page_lines list.
    """
    if build_paragraph:
        joined_paragraph = ' '.join(build_paragraph)
        page_lines.append(joined_paragraph)
        build_paragraph.clear()


# Add metadata and image information for page
info = output[0]
page_obj['metadata'] = {
    'title': info['metadata']['title'],
    'page_count': info['metadata']['page_count'],
    'page': info['metadata']['page'],
    'toc_items': info['toc_items'],}
page_obj['images'] = info['images']

# Variables for processing
text = output[0]['text']
words = output[0]['words']

# Initialize functional variables
word_count = 0
page_lines = []
build_paragraph = []
block = None

# Split text by using block information from words(pymupdf4llm output)
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


md_lines = []

# Convert page lines to markdown
for line in page_lines:
    md_header_splits = markdown_splitter.split_text(line)
    md_lines.append(md_header_splits[0])


last_meta = None
line_count = 0

# Insert line number, page number and is_image into metadata
for line in md_lines:
    match = re.match(r'!\[\]\([^)]*\)', line.page_content)
    line_count += 1
    if len(line.metadata.keys()) > 0:
        line.metadata['line_number'] = line_count
        line.metadata['page_number'] = page_obj['metadata']['page']
        line.metadata['is_image'] = match
        last_meta = line.metadata.copy()
    else:
        if last_meta:
            line.metadata = last_meta.copy()
        line.metadata['line_number'] = line_count
        line.metadata['page_number'] = page_obj['metadata']['page']
        line.metadata['is_image'] = match


rprint(md_lines)
# chunk page_content larger that 200 words
chunks = recur_text_splitter.split_documents(md_lines)
