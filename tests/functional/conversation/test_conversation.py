import os.path

import openai

from data_to_paper import Conversation, Message, Role
from data_to_paper.servers.chatgpt import OPENAI_SERVER_CALLER, try_get_chatgpt_response


def test_failed_gpt_response(conversation, openai_exception):
    with OPENAI_SERVER_CALLER.mock(['I am okay.', openai_exception]):
        assert try_get_chatgpt_response(conversation) == 'I am okay.'
        assert isinstance(try_get_chatgpt_response(conversation), openai.error.InvalidRequestError)


@OPENAI_SERVER_CALLER.record_or_replay()
def test_conversation_gpt_response(conversation):
    response = try_get_chatgpt_response(conversation)
    assert isinstance(response, str) and len(response)


@OPENAI_SERVER_CALLER.record_or_replay()
def test_conversation_gpt_response_without_appending(conversation):
    response = try_get_chatgpt_response(conversation)
    assert len(response)
    assert len(conversation) == 4


def test_conversation_save_load(conversation, tmpdir):
    filename = os.path.join(tmpdir, 'test_conversation_save.txt')
    conversation.save(filename)
    new_conversation = Conversation()
    new_conversation.load(filename)

    assert new_conversation == conversation


def test_conversation_from_file(conversation, tmpdir):
    filename = os.path.join(tmpdir, 'test_conversation_save.txt')
    conversation.save(filename)
    new_conversation = Conversation.from_file(filename)

    assert new_conversation == conversation


def test_conversation_print(conversation):
    conversation.print_all_messages()


def test_conversation_get_last_response(conversation):
    conversation.append(Message(Role.ASSISTANT, 'Hello!'))
    assert conversation.get_last_response() == 'Hello!'


def test_conversation_delete_last_response(conversation):
    conversation.append(Message(Role.ASSISTANT, 'Hello!'))
    original_len = len(conversation)
    conversation.delete_last_response()
    assert len(conversation) == original_len - 1


def test_conversation_ignores_ignored_messages():
    conversation = Conversation()
    conversation.append(Message(Role.USER,
                                'This is a fun message just for the conversation to look nice!', ignore=True))
    conversation.append(Message(Role.USER, 'This is a real message', ignore=False))
    indices_and_messages = conversation.get_chosen_indices_and_messages()
    indices = [index for index, _ in indices_and_messages]
    assert indices == [1]
