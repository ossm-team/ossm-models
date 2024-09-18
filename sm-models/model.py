import abc
import os
from pprint import pprint

import xmlschema


def parse_description_xml(model_description_xml: str):
    schema = xmlschema.XMLSchema("../schema.xsd")
    model = schema.to_dict(model_description_xml)
    pprint(model)

    # model_description_xml: str = model_description_xml
    # with open(model_description_xml, "r") as f:
    #     model_description: ET.ElementTree = ET.parse(f)
    #
    # model = {}
    # model["name"] = model_description.getroot().attrib["name"]
    # model["version"] = model_description.getroot().attrib["version"]
    # model["author"] = model_description.getroot().attrib["author"]
    #
    # for descriptor in ["coverage", "plausibility"]:
    #     model[descriptor] = {
    #         element.tag: True if element.text == "true" else False
    #         for element in list(model_description.find(descriptor))
    #     }

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

    @property
    def model_name(self) -> str:
        return self.model["name"]

    @property
    def model_version(self) -> str:
        return self.model["version"]

    @property
    def model_author(self) -> str:
        return self.model["author"]

    @property
    def coverage(self) -> dict:
        return self.model["coverage"]

    @property
    def plausibility(self) -> dict:
        return self.model["plausibility"]


class ModelFromDict(Model):

    def __init__(self, model: dict):
        self.model = model

    @property
    def model_name(self) -> str:
        return self.model["name"]

    @property
    def model_version(self) -> str:
        return self.model["version"]

    @property
    def model_author(self) -> str:
        return self.model["author"]

    @property
    def coverage(self) -> dict:
        return self.model["coverage"]

    @property
    def plausibility(self) -> dict:
        return self.model["plausibility"]


if __name__ == "__main__":
    model = ModelFromXML("../model-sample/model.xml")

    print(model.coverage)
    print(model)
