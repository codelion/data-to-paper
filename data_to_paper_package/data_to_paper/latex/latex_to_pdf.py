import os
import re
import shutil
import subprocess

from typing import Set, Optional

from data_to_paper.servers.types import Citation
from data_to_paper.utils.file_utils import run_in_temp_directory

from .exceptions import LatexCompilationError, TooWideTableOrText

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

BIB_FILENAME: str = 'citations.bib'


def evaluate_latex_num_command(latex_str):
    """
    Evaluates all expressions of the form \num{...} in the given latex string and replaces them with the result.
    """
    pattern = r'\\num{(.+?)}'
    matches = re.findall(pattern, latex_str)
    for match in matches:
        try:
            result = round(eval(match), 10)
            latex_str = latex_str.replace(f'\\num{{{match}}}', str(result))
        except (SyntaxError, NameError):
            pass
    return latex_str


def check_latex_compilation(latex_content: str, file_stem: str = 'test', output_directory: Optional[str] = None,
                            tolerance_for_too_wide_in_pts: Optional[float] = None):
    with open(os.path.join(THIS_FOLDER, 'compilation_template.tex'), 'r') as f:
        latex_document = f.read().replace('@@@content@@@', latex_content)
    save_latex_and_compile_to_pdf(latex_document, file_stem, output_directory,
                                  tolerance_for_too_wide_in_pts=tolerance_for_too_wide_in_pts)


def save_latex_and_compile_to_pdf(latex_content: str, file_stem: str, output_directory: Optional[str] = None,
                                  references: Set[Citation] = None,
                                  tolerance_for_too_wide_in_pts: Optional[float] = None):
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

        output = pdflatex_output.stdout.decode('utf-8')
        if r'Overfull \hbox' in output:
            overflow_in_pt = float(re.search(r'Overfull \\hbox \((.*?)pt too wide\)', output).group(1))
            print('Overflow in pt: ', overflow_in_pt)
            if tolerance_for_too_wide_in_pts is not None and overflow_in_pt > tolerance_for_too_wide_in_pts:
                move_latex_and_pdf_to_output_directory(file_stem, output_directory, latex_file_name)
                raise TooWideTableOrText(latex_content=latex_content,
                                         pdflatex_output=pdflatex_output.stdout.decode('utf-8'))

        if should_compile_with_bib:
            try:
                subprocess.run(['bibtex', file_stem], check=True)
                subprocess.run(pdflatex_params, check=True)
                subprocess.run(pdflatex_params, check=True)
            except subprocess.CalledProcessError:
                move_latex_and_pdf_to_output_directory(file_stem, output_directory, latex_file_name)
                raise
        move_latex_and_pdf_to_output_directory(file_stem, output_directory, latex_file_name)


def move_latex_and_pdf_to_output_directory(file_stem: str, output_directory: str = None, latex_file_name: str = None):
    # Move the pdf and the latex and the citation file to the original directory:

    def move_if_exists(file_name):
        if os.path.exists(file_name):
            shutil.move(file_name, output_directory)

    if output_directory is not None:
        move_if_exists(file_stem + '.pdf')
        move_if_exists(latex_file_name)
        move_if_exists('citations.bib')