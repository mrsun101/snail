from dataclasses import dataclass
from snail.view import View
from typing import Type

@dataclass
class Url:
    url: str
    view: Type[View]