from typing import List, Optional, Union, Dict
from xml.etree.cElementTree import Element, SubElement, tostring, fromstring

from lib.input_output.scgi.r_var_response import RVarResponse
from lib.input_output.scgi.r_response import RResponse
from lib.services.alias_service import AliasService


class RRResponsesXmlSerializer:
    @classmethod
    def to_xml(cls,
               responses: List[Union[RResponse, RVarResponse]],
               alias_error_tags: List[str],
               reply_with_description: bool,
               alias_service: AliasService) -> str:
        data = Element("data")

        if len(responses) == 0:
            response = RResponse(
                "",
                "?",
                "",
                "",
                False,
                RResponse.Code.DEVICE_NOT_FOUND,
                False
            )
            responses.append(response)

        var_responses: Dict[str, List[RVarResponse]] = {}

        for response in responses:
            if type(response) is RVarResponse:
                var_responses.setdefault(response.nad, []).append(response)
            else:
                cls.process_response(data,
                                     response,
                                     alias_error_tags,
                                     reply_with_description,
                                     alias_service)

        if var_responses:
            cls.process_var_responses(data,
                                      var_responses,
                                      alias_service)

        content = tostring(data)

        return "<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>" + \
            content.decode("iso-8859-1")

    @classmethod
    def process_response(cls,
                         data: Element,
                         response: RResponse,
                         alias_error_tags: List[str],
                         reply_with_description: bool,
                         alias_service: AliasService):
        var = SubElement(data, "var")
        SubElement(var, "name").text = \
            alias_service.to_alias_name(response.name) \
                if response.name not in alias_error_tags else response.name

        value_sub_element = SubElement(var, "value")

        if isinstance(response.value, list):
            for item in response.value:
                SubElement(value_sub_element, "item").text = item
        else:
            value_sub_element.text = (
                str(response.value) if response.valid else "?"
            )

        if reply_with_description:
            SubElement(var, "description").text = response.description

        if response.code != RResponse.Code.NO_ERROR:
            SubElement(var, "error_code").text = \
                str(response.code.value)

    @classmethod
    def process_var_responses(cls,
                              data: Element,
                              responses: Dict[str, List[RVarResponse]],
                              alias_service: AliasService):
        for k in responses.keys():
            name = alias_service.to_alias_name(k)

            for response in responses[k]:
                var = SubElement(data, "var")
                SubElement(var, "name").text = \
                    f"{name}.{response.var_name}"
                SubElement(var, "type").text = response.var_type
                SubElement(var, "description").text = \
                    response.var_description

    @classmethod
    def from_xml(
        cls,
        data: str,
        alias_service: Optional[AliasService] = None
    ) -> List[RResponse]:
        root: Element = fromstring(data)
        if root.tag != 'data':
            raise ValueError("No data tag found in xml")

        responses: List[RResponse] = []

        for var in root.findall("var"):
            if var.tag != 'var':
                raise ValueError("No var tag found in xml")

            parts = var.findtext('name').split(".")
            value = var.findtext('value')
            code = var.findtext('error_code')

            responses.append(RResponse(
                alias_service.to_nad(parts[0]) if alias_service else parts[0],
                ".".join(parts[1:]),
                value,
                var.findtext('description'),
                value != "?",
                RResponse.Code(int(code)) if code else None,
                False
            ))

        return responses
