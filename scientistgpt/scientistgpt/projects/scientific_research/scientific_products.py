from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, Set, List

from scientistgpt.conversation.stage import Stage
from scientistgpt.projects.scientific_research.scientific_stage import ScientificStages
from scientistgpt.run_gpt_code.types import CodeAndOutput
from scientistgpt.utils.nice_list import NiceList
from scientistgpt.base_steps.types import DataFileDescriptions, Products, NameDescriptionStageGenerator
from scientistgpt.servers.crossref import CrossrefCitation


CODE_STEPS_TO_STAGES: Dict[str, Stage] = {
    'data_exploration': ScientificStages.EXPLORATION,
    'data_preprocessing': ScientificStages.PREPROCESSING,
    'data_analysis': ScientificStages.CODE,
}


@dataclass
class ScientificProducts(Products):
    """
    Contains the different scientific outcomes of the research.
    These outcomes are gradually populated, where in each step we get a new product based on previous products.
    """
    data_file_descriptions: DataFileDescriptions = field(default_factory=DataFileDescriptions)
    codes_and_outputs: Dict[str, CodeAndOutput] = field(default_factory=dict)
    research_goal: Optional[str] = None
    analysis_plan: Optional[str] = None
    tables: List[str] = None
    numeric_values: Dict[str, str] = field(default_factory=dict)
    results_summary: Optional[str] = None
    paper_sections: Dict[str, str] = field(default_factory=dict)
    cited_paper_sections_and_citations: Dict[str, Tuple[str, Set[CrossrefCitation]]] = field(default_factory=dict)
    ready_to_be_tabled_paper_sections: Dict[str, str] = field(default_factory=dict)

    @property
    def citations(self) -> NiceList[CrossrefCitation]:
        """
        Return the citations of the paper.
        """
        citations = set()
        for section_content, section_citations in self.cited_paper_sections_and_citations.values():
            citations.update(section_citations)
        return NiceList(citations, separator='\n\n')

    @property
    def cited_paper_sections(self) -> Dict[str, str]:
        """
        Return the actual cited paper sections.
        """
        return {section_name: section_content
                for section_name, (section_content, _) in self.cited_paper_sections_and_citations.items()}

    @property
    def tabled_paper_sections(self) -> Dict[str, str]:
        """
        Return the actual tabled paper sections.
        """
        return {section_name: self.add_tables_to_paper_section(section_content)
                for section_name, section_content in self.ready_to_be_tabled_paper_sections.items()}

    def add_tables_to_paper_section(self, section_content: str) -> str:
        """
        Insert the tables into the ready_to_be_tabled_paper_sections.
        """
        updated_section = section_content
        if self.tables is not None:
            for table in self.tables:
                table_label_start = table.find('label{') + len('label{')  # find the start of the label
                table_label_end = table.find('}', table_label_start)  # find the end of the label
                table_label = table[table_label_start:table_label_end]  # extract the label
                # find the sentence that contains the table reference
                table_reference_sentence = None
                for sentence in updated_section.split('. '):
                    if table_label in sentence:
                        table_reference_sentence = sentence
                        break
                if table_reference_sentence is None:
                    # add the table at the end of the section
                    updated_section += table
                else:
                    # add the table after the table reference sentence
                    updated_section = updated_section.replace(table_reference_sentence,
                                                              table_reference_sentence + table)
        return updated_section

    @property
    def most_updated_paper_sections(self) -> Dict[str, str]:
        section_names_to_content = {}
        for section_name, section in self.paper_sections.items():
            if section_name in self.cited_paper_sections:
                section = self.cited_paper_sections[section_name]
            if section_name in self.ready_to_be_tabled_paper_sections:
                section = self.tabled_paper_sections[section_name]
            section_names_to_content[section_name] = section
        return section_names_to_content

    def get_paper(self, product_field: str) -> str:
        """
        Compose the paper from the different paper sections.
        product_field can be one of the following:
            'paper_sections'
            'cited_paper_sections'
            'tabled_paper_sections'
            'most_updated_paper_sections'
        """
        paper_sections = getattr(self, product_field)
        paper = ''
        for section_name, section_content in paper_sections.items():
            paper += f"``{section_name}``\n\n{section_content}\n\n\n"
        return paper

    def _get_generators(self) -> Dict[str, NameDescriptionStageGenerator]:
        return {
            'data_file_descriptions': NameDescriptionStageGenerator(
                'Dataset',
                'DESCRIPTION OF DATASET\n\nWe have the following {}',
                ScientificStages.DATA,
                lambda: self.data_file_descriptions,
            ),

            'research_goal': NameDescriptionStageGenerator(
                'Research Goal',
                'Here is our Research Goal\n\n{}',
                ScientificStages.GOAL,
                lambda: self.research_goal,
            ),

            'analysis_plan': NameDescriptionStageGenerator(
                'Data Analysis Plan',
                'Here is our Data Analysis Plan:\n\n{}',
                ScientificStages.PLAN,
                lambda: self.analysis_plan,
            ),

            'code:{}': NameDescriptionStageGenerator(
                '{code_name} Code',
                'Here is our {code_name} Code:\n```python\n{code}\n```\n',
                lambda code_step: CODE_STEPS_TO_STAGES[code_step],
                lambda code_step: {'code': self.codes_and_outputs[code_step].code,
                                   'code_name': self.codes_and_outputs[code_step].name},
            ),

            'output:{}': NameDescriptionStageGenerator(
                'Output of the {code_name} Code',
                'Here is the output of our {code_name} code:\n```\n{output}\n```\n',
                lambda code_step: CODE_STEPS_TO_STAGES[code_step],
                lambda code_step: {'output': self.codes_and_outputs[code_step].output,
                                   'code_name': self.codes_and_outputs[code_step].name},
            ),

            'code_and_output:{}': NameDescriptionStageGenerator(
                'Data Analysis Code and Output',
                '{}\n\n{}',
                lambda code_step: CODE_STEPS_TO_STAGES[code_step],
                lambda code_step: (self["code:" + code_step].description, self["output:" + code_step].description)
            ),

            'results_summary': NameDescriptionStageGenerator(
                'Results Summary',
                'Here is our Results Summary:\n\n{}',
                ScientificStages.INTERPRETATION,
                lambda: self.results_summary,
            ),

            'title_and_abstract': NameDescriptionStageGenerator(
                'Title and Abstract',
                "Here are the title and abstract of the paper:\n\n{}\n\n{}",
                ScientificStages.WRITING,
                lambda: (self.paper_sections['title'], self.paper_sections['abstract']),
            ),

            'paper_sections': NameDescriptionStageGenerator(
                'Paper Sections',
                '{}',
                ScientificStages.WRITING,
                lambda: self.get_paper("paper_sections")
            ),

            'cited_paper_sections_and_citations': NameDescriptionStageGenerator(
                'Cited Paper Sections and Citations',
                '{}\n\n\n``Citations``\n\n{}',
                ScientificStages.CITATIONS,
                lambda: (self.get_paper("cited_paper_sections"), self.citations),
            ),

            'tabled_paper_sections': NameDescriptionStageGenerator(
                'Paper Sections with Tables',
                '{}',
                ScientificStages.TABLES,
                lambda: self.get_paper("tabled_paper_sections")
            ),

            'most_updated_paper_sections': NameDescriptionStageGenerator(
                'Most Updated Paper Sections',
                '{}',
                ScientificStages.WRITING,
                lambda: self.get_paper("most_updated_paper_sections")
            ),

            'paper_sections:{}': NameDescriptionStageGenerator(
                'The {section_name} Section of the Paper',
                'Here is the {section_name} section of the paper:\n\n{content}',
                ScientificStages.WRITING,
                lambda section_name: {'section_name': section_name.title(),
                                      'content': self.paper_sections[section_name],
                                      },
            ),

            'cited_paper_sections_and_citations:{}': NameDescriptionStageGenerator(
                'The {section_name} Section of the Paper with Citations',
                'Here is the cited {section_name} section of the paper:\n\n{content}\n\n``Citations``\n\n{citations}',
                ScientificStages.CITATIONS,
                lambda section_name: {'section_name': section_name.title(),
                                      'content': self.cited_paper_sections[section_name],
                                      'citations': self.citations[section_name],
                                      },
            ),

            'tabled_paper_sections:{}': NameDescriptionStageGenerator(
                'The {section_name} Section of the Paper with Tables',
                'Here is the {section_name} section of the paper with tables:\n\n{content}',
                ScientificStages.TABLES,
                lambda section_name: {'section_name': section_name.title(),
                                      'content': self.tabled_paper_sections[section_name],
                                      },
            ),

            'most_updated_paper_sections:{}': NameDescriptionStageGenerator(
                'The most-updated {section_name} Section of the Paper',
                'Here is the most-updated {section_name} section of the paper:\n\n{content}',
                ScientificStages.TABLES,
                lambda section_name: {'section_name': section_name.title(),
                                      'content': self.most_updated_paper_sections[section_name],
                                      },
            ),

            'tables': NameDescriptionStageGenerator(
                'The Tables of the Paper',
                'Here are the tables of the paper:\n\n{}',
                ScientificStages.TABLES,
                lambda: NiceList([f"Table {i+1}:\n\n {table}"
                                  for i, table in enumerate(self.tables)],
                                 separator='\n\n'), ),

            'numeric_values': NameDescriptionStageGenerator(
                'The Numeric Values of the Paper',
                'Here are the numeric values of the paper:\n\n{}',
                ScientificStages.INTERPRETATION,
                lambda: NiceList([f"Numeric Value {i+1}, {numeric_value_name}:\n\n {numeric_value_content}"
                                  for i, (numeric_value_name, numeric_value_content) in
                                  enumerate(self.numeric_values.items())], separator='\n\n'), ),

            'tables_and_numeric_values': NameDescriptionStageGenerator(
                'The Tables and Numeric Values of the Paper',
                '{tables}\n\n{numeric_values}',
                ScientificStages.INTERPRETATION,
                lambda: {'tables': self['tables'].description,
                         'numeric_values': self['numeric_values'].description,
                         },
            ),
        }
