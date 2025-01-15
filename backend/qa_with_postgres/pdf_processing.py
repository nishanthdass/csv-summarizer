from dotenv import load_dotenv
import os
import json
from rich import print as rprint
from pdf_processing_funct import process_pdf, param_insert
import pymupdf
from kg_init import (
    ask_question_window,
    create_section_relationships,
    connect_chunk_to_parent,
    return_all_chunks,
    match_nodes,
    view_labels,
    count_page_nodes,
    make_page_identifier_nodes,
    return_any_chunk,
    create_constraints,
    add_chunk_as_node,
    create_vector_index,
    create_embeddings,
)


load_dotenv()

# Initialize output dictionary
file_name = "auto-electric-can-opener-manual.pdf"
file_path = "pdfs/{file_name}".format(file_name=file_name)
file_name_minus_ext = file_name.split(".")[0]
output_folder_path = "pdfs/processsed_pdfs/{file_name_minus_ext}".format(file_name_minus_ext=file_name_minus_ext)


if not os.path.exists(output_folder_path):
    os.mkdir(output_folder_path)

pdf_file = pymupdf.open(file_path, filetype="pdf")


page_nums = None
pdf_obj = process_pdf(pdf_file, file_path, page_nums, output_folder_path, file_name_minus_ext)

rprint(pdf_obj)

create_constraints()
add_chunk_as_node(pdf_obj)

create_vector_index()
create_embeddings()

any_chunk = return_any_chunk()
page_info = any_chunk[0]["pageInfo"]

make_page_identifier_nodes(page_info)
page_nodes = count_page_nodes()

view_labels = view_labels()

all_chunks = return_all_chunks()
match_nodes(all_chunks)

connect_chunk_to_parent = connect_chunk_to_parent()
create_section_relationships = create_section_relationships()


# question_1 = ""What are the main steps a data scientist would go through to build a regression machine learning model?"
# question_2 = "What is the importance of verifying assumptions in a machine learning project, and how might misunderstanding downstream system requirements affect the framing of the task?"
# ask_question_window(question_2)
# question_3 = "what are the steps to use the electric can opener?"
# ask_question_window(question_3)

question_4 = "My electric can opener is not turning on, what should I do?"
ask_question_window(question_4)