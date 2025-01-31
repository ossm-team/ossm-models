import abc
import os
from pprint import pprint

from ap_models.exceptions import DescriptionError

import xmlschema

from ap_models.validators import validate_model_dict


def parse_description_xml(model_description_xml: str):
    schema = xmlschema.XMLSchema("../schema.xsd")

    try:
        model = schema.to_dict(model_description_xml)
    except xmlschema.XMLSchemaValidationError as e:
        raise DescriptionError(f"The model description does not follow the description language: {e.reason}")

    return model

class Model(abc.ABC):

    @property
    @abc.abstractmethod
    def model_name(self) -> str: ...

    @property
    @abc.abstractmethod
    def model_version(self) -> str: ...

    @property
    @abc.abstractmethod
    def model_author(self) -> str: ...

    @property
    @abc.abstractmethod
    def coverage(self) -> dict: ...

    @property
    @abc.abstractmethod
    def plausibility(self) -> dict: ...

    def __repr__(self):
        return f"{self.model_name} v{self.model_version} by {self.model_author}"


class ModelFromXML(Model):

    def __init__(self, model_description_xml: str):
        self.model = parse_description_xml(model_description_xml)

        for key, value in self.model:
            if key[0] == "@":
                setattr(self, key[1:], value)


class ModelFromDict(Model):

    def __init__(self, model: dict):
        self.model = model
        validate_model_dict(self.model)


if __name__ == "__main__":
    model = ModelFromXML("../model-sample/model.xml")

    print(model.coverage)
    print(model)
