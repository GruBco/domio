from typing import Dict

from lib.config.ini_config_parser import IniConfigParser, IniConfigParserError


class AliasConfig:
    aliases: Dict[str, str]
    _reversed: Dict[str, str]

    def __init__(self, aliases: Dict[str, str]):
        for val in aliases.values():
            if not val.replace("_", "").isalnum():
                raise ValueError(f"Alias name can contain only alphanumeric "
                                 f"characters: '{val}'")
        self.aliases = aliases
        self._reversed = {v: k for k, v in aliases.items()}

    @property
    def reversed(self) -> Dict[str, str]:
        return self._reversed

    def props(self) -> Dict[str, str]:
        return self.aliases

    @classmethod
    def load(cls, icp: IniConfigParser, default: 'AliasConfig'):
        section = "ALIAS"

        aliases = default.props()

        try:
            aliases_from_conf: Dict[str, str] = {
                k: v[0] for k, v in icp.items(section)
            }
        except IniConfigParserError:
            aliases_from_conf = aliases

        return cls(aliases_from_conf)
