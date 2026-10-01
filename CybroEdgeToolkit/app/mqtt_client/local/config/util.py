from typing import List, Optional, Dict


def strip_split(value: str, separator: str = ",") -> List[str]:
    """Splits string by separator and strips whitespaces from resulting
    strings.

    :param value: Value to split.
    :param separator: String by which to split value, default is ",".
    :return: List of strings.
    """
    return [v.strip() for v in value.split(separator) if v != '']


def split_var_flatten(values: Optional[List[str]]) -> List[str]:
    """Splits a comma separated strings form list into chunks and resulting
    list of lists is flattened into one dimensional list of strings.

    :param values: Values to process.
    :return: List of strings.
    """
    if values is None:
        return []
    else:
        return [
            chunk
            for line in values
            for chunk in strip_split(line)
        ]


def split_map_dict(values: Optional[List[str]]) -> Dict[str, List[str]]:
    """Splits a comma separated strings from list into chunks where first chunk
    is key and rest of chunks are value for the resulting dictionary object.

    :param values: List of strings to process.
    :return: Dictionary of processed values.
    """
    if values is None:
        return {}
    else:
        return {
            v[0]: v[1:] for v in (strip_split(line) for line in values)
        }


def split_map_dict_one(values: Optional[List[str]]) -> Dict[str, str]:
    """Splits a comma separated string from list into chunks where first chunk
    is key and second value for the resulting dictionary object.

    :param values: List of strings to process.
    :return: Dictionary of processed values.
    """
    if values is None:
        return {}
    else:
        d = {}

        for v in (strip_split(line) for line in values):
            if len(v) > 2:
                raise ValueError(
                    f"Multiple values found for tag '{v[0]}': {v[1:]}"
                )
            d[v[0]] = v[1]

        return d
