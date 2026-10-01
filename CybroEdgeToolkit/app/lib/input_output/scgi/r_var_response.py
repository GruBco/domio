from dataclasses import dataclass


@dataclass
class RVarResponse:
    name: str
    nad: str
    var_name: str
    var_type: str
    var_description: str

    @classmethod
    def create(cls,
               name: str,
               nad: str,
               var_name: str,
               var_type: str,
               var_description: str):
        return cls(name=name, nad=nad, var_name=var_name, var_type=var_type,
                   var_description=var_description)
