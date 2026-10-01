from typing import Dict


class AliasError(ValueError):
    def __init__(self, nad: str):
        super().__init__(f"Alias for {nad} not used")


class AliasService:
    DELIMITER = "."

    def __init__(self,
                 aliases: Dict[str, str],
                 reversed_aliases: Dict[str, str]):
        self._aliases = aliases
        self._reversed = reversed_aliases

    @property
    def aliases(self):
        return self._aliases

    @property
    def reversed_aliases(self):
        return self._reversed

    def _get_alias(self, alias: str) -> str:
        return self._aliases.get(alias, alias)

    def _get_reversed(self, alias: str) -> str:
        return self._reversed.get(alias, alias)

    def to_nad(self, name: str) -> str:
        """Replaces configured alias name to NAD (e.g. alpha -> c10010).
        """
        return self._reversed.get(name, name)

    def to_alias(self, name: str) -> str:
        """Replaces NAD to configured alias name (e.g. c10010 -> alpha).
        """
        return self._aliases.get(name, name)

    def to_nad_name(self, name_var: str) -> str:
        """Replaces current alias name in NAD-variable combo with NAD (e.g.
        alpha.rtc_sec -> c10010.rtc_sec).
        """
        parts = name_var.split(self.DELIMITER)
        parts[0] = self._get_reversed(parts[0])
        return self.DELIMITER.join(parts)

    def to_alias_name(self, name_var: str) -> str:
        """Replaces current NAD in NAD-variable combo with alias name
        (e.g. c10010.rtc_sec -> alpha.rtc_sec).
        """
        parts = name_var.split(self.DELIMITER)
        parts[0] = self._get_alias(parts[0])
        return self.DELIMITER.join(parts)

    def to_nad_name_strict(self, name_var: str) -> str:
        """Version of to_nad_name method which enforces usage of aliases. It
        throws error if NAD is used for PLC with defined alias.
        """
        current = name_var.split(self.DELIMITER)[0]

        if current in self._aliases:
            raise AliasError(current)

        return self.to_nad_name(name_var)
