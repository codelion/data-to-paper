import os
import re
import shutil
import subprocess

from typing import Optional, Collection

import numpy as np

from data_to_paper.servers.custom_types import Citation
from data_to_paper.utils.file_utils import run_in_temp_directory
from PyPDF2 import PdfWriter, PdfReader

from .exceptions import LatexCompilationError, TooWideTableOrText

BIB_FILENAME: str = 'citations.bib'
WATERMARK_PATH: str = os.path.join(os.path.dirname(__file__), 'watermark.pdf')


def evaluate_latex_num_command(latex_str):
    """
    Evaluates all expressions of the form \num{...} in the given latex string and replaces them with the result.
    """
    pattern = r'\\num{(.+?)}'
    matches = re.findall(pattern, latex_str)
    for match in matches:
        try:
            result = eval(match,
                          {'exp': np.exp, 'log': np.log, 'sin': np.sin, 'cos': np.cos, 'tan': np.tan, 'pi': np.pi,
                           'e': np.e, 'sqrt': np.sqrt, 'log2': np.log2, 'log10': np.log10})
            latex_str = latex_str.replace(f'\\num{{{match}}}', '{:.4g}'.format(result))
        except (SyntaxError, NameError):
            pass
    return latex_str


def add_watermark_to_pdf(pdf_path: str, watermark_path: str, output_path: str = None):
    """
    Add watermark to pdf
    :param pdf_path: path to pdf file
    :param output_path: path to output file
    :param watermark_path: path to watermark file
    """
    if output_path is None:
        output_path = pdf_path
    with open(pdf_path, "rb") as input_file, open(watermark_path, "rb") as watermark_file:
        input_pdf = PdfReader(input_file, strict=False)
        output = PdfWriter()
        for i in range(len(input_pdf.pages)):
            watermark_pdf = PdfReader(watermark_file, strict=False)
            watermark_page = watermark_pdf.pages[0]
            pdf_page = input_pdf.pages[i]
            watermark_page.merge_page(pdf_page)
            output.add_page(watermark_page)
        with open(output_path, "wb") as merged_file:
            output.write(merged_file)


def save_latex_and_compile_to_pdf(latex_content: str, file_stem: str, output_directory: Optional[str] = None,
                                  references: Collection[Citation] = None,
                                  raise_on_too_wide: bool = True) -> str:
    latex_content = evaluate_latex_num_command(latex_content)
    references = references or set()
    should_compile_with_bib = len(references) > 0
    latex_file_name = file_stem + '.tex'
    pdflatex_params = ['pdflatex', '--shell-escape', '-interaction', 'nonstopmode', latex_file_name]
    with run_in_temp_directory():

        # Create the bib file:
        if should_compile_with_bib:
            references_bibtex = [reference.bibtex for reference in references]
            with open(BIB_FILENAME, 'w') as f:
                f.write('\n\n'.join(references_bibtex))

        with open(latex_file_name, 'w') as f:
            f.write(latex_content)
        try:
            pdflatex_output = subprocess.run(pdflatex_params,
                                             check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise LatexCompilationError(latex_content=latex_content, pdflatex_output=e.stdout.decode('utf-8'))

        pdflatex_output = pdflatex_output.stdout.decode('utf-8')

        if should_compile_with_bib:
            try:
                subprocess.run(['bibtex', file_stem], check=True)
                subprocess.run(pdflatex_params, check=True)
                subprocess.run(pdflatex_params, check=True)
            except subprocess.CalledProcessError:
                _move_latex_and_pdf_to_output_directory(file_stem, output_directory, latex_file_name)
                raise

        add_watermark_to_pdf(file_stem + '.pdf', WATERMARK_PATH)

        _move_latex_and_pdf_to_output_directory(file_stem, output_directory, latex_file_name)

        if r'Overfull \hbox' in pdflatex_output and raise_on_too_wide:
            raise TooWideTableOrText(latex_content=latex_content,
                                     pdflatex_output=pdflatex_output)

        return pdflatex_output


def _move_latex_and_pdf_to_output_directory(file_stem: str, output_directory: str = None, latex_file_name: str = None):
    # Move the pdf and the latex and the citation file to the original directory:

    def move_if_exists(file_name):
        if os.path.exists(file_name):
            shutil.move(file_name, output_directory)

    if output_directory is not None:
        move_if_exists(file_stem + '.pdf')
        move_if_exists(latex_file_name)
        move_if_exists('citations.bib')
