from dataclasses import dataclass
from typing import Tuple, Optional

from data_to_paper.utils import dedent_triple_quote_str

from .base_products_conversers import BackgroundProductsConverser
from .result_converser import Rewind


@dataclass
class MultiChoiceBackgroundProductsConverser(BackgroundProductsConverser):
    """
    A base class for asking LLM to choose between multiple options.
    """

    LLM_PARAMETERS = {'temperature': 0.0, 'max_tokens': 30}

    mission_prompt: str = dedent_triple_quote_str("""
        Please choose one of the following options:
        1. Looks good. Choice 1.
        2. Something is wrong. Choice 2.

        {choice_instructions}
        """)

    choice_instructions: str = dedent_triple_quote_str("""
        Answer with just a single character, designating the option you choose {possible_choices}.
        """)

    possible_choices: Tuple[str, ...] = ('1', '2')

    default_rewind_for_result_error: Rewind = Rewind.AS_FRESH
    rewind_after_getting_a_valid_response: Optional[Rewind] = Rewind.AS_FRESH

    def _get_chosen_choice_from_response(self, response: str) -> str:
        choices_in_response = [choice for choice in self.possible_choices if choice in response]
        if len(choices_in_response) == 1:
            return choices_in_response[0]
        self._raise_self_response_error(self.choice_instructions)

    def _check_extracted_text_and_update_valid_result(self, extracted_text: str):
        chosen_choice = self._get_chosen_choice_from_response(extracted_text)
        self._update_valid_result(chosen_choice)
