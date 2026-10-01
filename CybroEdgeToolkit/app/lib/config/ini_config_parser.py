import json
import re
from typing import List, Dict, Optional, NewType

KeyDataType = NewType("KeyDataType", List[str])
SectionDataType = NewType("SectionDataType", List[Dict[str, KeyDataType]])


class IniConfigParserError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class IniConfigParserValueError(IniConfigParserError):
    def __init__(self):
        super().__init__("Value and default is None")


class IniConfigParser:
    COMMENT_PREFIXES = ('#', ";")
    DEFAULT_SECTION = None
    MULTISECTION_DELIMITER = "[]"
    KEY_VALUE_DELIMITER = "="

    def __init__(self):
        self._data: Dict[Optional[str], SectionDataType] = {
            None: [{}]
        }
        self._section_pattern = re.compile(r'\[(.+)\]')

    def __repr__(self):
        return json.dumps(self._data, indent=2)

    def _require_one_section(self, section: Optional[str]):
        if len(self._data[section]) > 1:
            raise IniConfigParserError("Multiple sections found")

    def section_names(self) -> List[str]:
        return [x for x in self._data.keys() if x is not None]

    def section_count(self, name: str) -> int:
        return len(self._data[name])

    def parse(self, filename: str):
        with open(filename, "r") as f:
            self._parse_lines(f.readlines())

    def parse_string(self, data: str):
        self._parse_lines(data.splitlines())

    def get_multisect_multival(self,
                               section: Optional[str],
                               section_idx: int,
                               key: str) -> List[str]:
        if key in self._data[section][section_idx]:
            return self._data[section][section_idx][key]
        else:
            return []

    def get_multival(self,
                     section: Optional[str],
                     key: str) -> List[str]:
        r = []
        for s in self._data[section]:
            if key in s:
                r += s[key]
        return r

    def get_multisect_optional(
        self,
        section: Optional[str],
        section_idx: int,
        key: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        v = self.get_multisect_multival(section, section_idx, key)
        if len(v) == 0:
            return default
        elif len(v) > 1:
            raise IniConfigParserError("Multiple values found")
        else:
            return v[0]

    def get_int_multisect_optional(
        self,
        section: Optional[str],
        section_idx: int,
        key: str,
        default: Optional[int] = None
    ) -> Optional[int]:
        v = self.get_multisect_optional(section, section_idx, key)
        return int(v) if v is not None else default

    def get_float_multisect_optional(
        self,
        section: Optional[str],
        section_idx: int,
        key: str,
        default: Optional[float] = None
    ) -> Optional[float]:
        v = self.get_multisect_optional(section, section_idx, key)
        return float(v) if v else default

    def get_boolean_multisect_optional(
        self,
        section: Optional[str],
        section_idx: int,
        key: str,
        default: Optional[bool] = None
    ) -> Optional[bool]:
        v = self.get_multisect_optional(section, section_idx, key)
        if v is None:
            return default

        v = v.lower()
        if v in ["true", "1", "yes", "on"]:
            return True
        elif v in ["false", "0", "no", "off"]:
            return False
        else:
            raise IniConfigParserError(f"Invalid boolean value: {v}")

    def get_multisect(self,
                      section: Optional[str],
                      section_idx: int,
                      key: str,
                      default: Optional[str] = None) -> str:
        v = self.get_multisect_optional(
            section, section_idx, key, default
        )
        if v is None:
            raise IniConfigParserValueError()
        else:
            return v

    def get_int_multisect(self,
                          section: Optional[str],
                          section_idx: int,
                          key: str,
                          default: Optional[int] = None) -> int:
        v = self.get_int_multisect_optional(
            section, section_idx, key, default
        )
        if v is None:
            raise IniConfigParserValueError()
        else:
            return v

    def get_float_multisect(self,
                            section: Optional[str],
                            section_idx: int,
                            key: str,
                            default: Optional[float] = None) -> float:
        v = self.get_float_multisect_optional(
            section, section_idx, key, default
        )
        if v is None:
            raise IniConfigParserValueError()
        else:
            return v

    def get_boolean_multisect(self,
                              section: Optional[str],
                              section_idx: int,
                              key: str,
                              default: Optional[bool] = None
                              ) -> bool:
        v = self.get_boolean_multisect_optional(
            section, section_idx, key, default
        )
        if v is None:
            raise IniConfigParserValueError()
        else:
            return v

    def get_optional(self,
                     section: Optional[str],
                     key: str,
                     default: Optional[str] = None) -> Optional[str]:
        self._require_one_section(section)
        return self.get_multisect_optional(section, 0, key, default)

    def get_int_optional(self,
                         section: Optional[str],
                         key: str,
                         default: Optional[int] = None) -> Optional[int]:
        self._require_one_section(section)
        return self.get_int_multisect_optional(section, 0, key, default)

    def get_float_optional(
        self,
        section: Optional[str],
        key: str,
        default: Optional[float] = None
    ) -> Optional[float]:
        self._require_one_section(section)
        return self.get_float_multisect_optional(section, 0, key, default)

    def get_boolean_optional(self,
                             section: Optional[str],
                             key: str,
                             default: Optional[bool] = None) -> Optional[bool]:
        self._require_one_section(section)
        return self.get_boolean_multisect_optional(
            section, 0, key, default
        )

    def get(self,
            section: Optional[str],
            key: str,
            default: Optional[str] = None) -> str:
        self._require_one_section(section)
        return self.get_multisect(section, 0, key, default)

    def get_int(self,
                section: Optional[str],
                key: str,
                default: Optional[int] = None) -> int:
        self._require_one_section(section)
        return self.get_int_multisect(section, 0, key, default)

    def get_float(self,
                  section: Optional[str],
                  key: str,
                  default: Optional[float] = None) -> float:
        self._require_one_section(section)
        return self.get_float_multisect(section, 0, key, default)

    def get_boolean(self,
                    section: Optional[str],
                    key: str,
                    default: Optional[bool] = None) -> bool:
        self._require_one_section(section)
        return self.get_boolean_multisect(section, 0, key, default)

    def items(self, section: Optional[str]) -> Dict[str, List[str]]:
        self._require_one_section(section)
        return self._data[section][0].items()

    def _last_value_index(self,
                          section: Optional[str],
                          section_idx: int,
                          key: str) -> int:
        return len(self._data[section][section_idx][key]) - 1

    def _parse_lines(self, lines: List[str]):
        curr_sect = self.DEFAULT_SECTION
        cs_idx = 0
        last_key = None

        for i, raw_line in enumerate(lines):
            line = raw_line.strip()

            # skip comments
            if line == '' or line.startswith(self.COMMENT_PREFIXES):
                continue

            # handle sections
            section = self._section_pattern.match(line)
            if section is not None:
                curr_sect = section.group(1)
                if curr_sect not in self._data:
                    self._data[curr_sect] = [{}]
                    cs_idx = 0
                else:
                    self._data[curr_sect].append({})
                    cs_idx = len(self._data[curr_sect]) - 1
                continue

            # remove inline comments
            comment = line.find(" ; ")
            line_without_comment = line if comment == -1 else line[:comment]

            # handle key-value lines
            delimiter_idx = line.find(self.KEY_VALUE_DELIMITER)
            if delimiter_idx == -1:
                if last_key is None:
                    raise IniConfigParserError(f"No key found for value on "
                                               f"line {i}")

                lv_idx = self._last_value_index(
                    curr_sect, cs_idx, last_key
                )
                self._data[curr_sect][cs_idx][last_key][lv_idx] += \
                    line_without_comment.strip()
            else:
                last_key = line_without_comment[:delimiter_idx].strip()
                self._data[curr_sect][cs_idx] \
                    .setdefault(last_key, []).append(
                    line_without_comment[delimiter_idx + 1:].strip()
                )
