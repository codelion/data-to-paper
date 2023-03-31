import re
from abc import abstractmethod, ABCMeta
from dataclasses import dataclass
from typing import Callable


class ScientistGPTException(Exception, metaclass=ABCMeta):
    @abstractmethod
    def __str__(self):
        pass


class RunCodeException(ScientistGPTException, metaclass=ABCMeta):
    pass


@dataclass
class FailedExtractingCode(RunCodeException):
    number_of_codes: int

    def __str__(self):
        if self.number_of_codes == 0:
            return "No code was found."
        return "More than one code snippet were found."


@dataclass
class FailedRunningCode(RunCodeException):
    exception: Exception

    def __str__(self):
        return f"Running the code resulted in the following exception:\n{self.exception}\n"


class FailedLoadingOutput(RunCodeException, FileNotFoundError):
    def __str__(self):
        return "Output file not found."


class UserRejectException(ScientistGPTException):
    def __str__(self):
        return "Output was disapproved by user."


@dataclass
class FailedRunningStep(ScientistGPTException):
    step: int
    func_name: str

    def __str__(self):
        return f"Failed running {self.func_name} (step {self.step})"


class DebuggingFailedException(ScientistGPTException):
    def __str__(self):
        return f"Failed debugging chatgpt code."