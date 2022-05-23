"""
Model for the data that is created and consumed by the user interface API.
"""
from typing import List, Union, Optional, Dict
from pydantic import BaseModel


class IndexedValue(BaseModel):
    index: List[List[Union[float, str]]]  # do not change order!
    value: List[Union[float, str]]  # do not change order!


class ScalarValue(BaseModel):
    value: Union[float, str]   # do not change order!


class Variable(BaseModel):
    display_name = ""
    description = ""
    units = ""
    readonly = False
    value: Optional[Union[IndexedValue, ScalarValue]]


class Block(BaseModel):
    display_name = ""
    description = ""
    category = "default"
    variables: Dict[str, Variable] = {}
    blocks: Dict[str, "Block"] = {}
    meta: Dict = {}


