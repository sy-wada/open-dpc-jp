"""Contract-1 code dictionaries; source of truth is the legacy schema."""
from open_dpc.schemas import legacy_schema as _legacy_schema
_values = _legacy_schema()["variables"]
bool_dict = _values['bool_dict']
department_code_dict = _values['department_code_dict']
discharge_place_code_dict = _values['discharge_place_code_dict']
emergency_code_300_dict = _values['emergency_code_300_dict']
hour24_code_dict = _values['hour24_code_dict']
outcome_code_dict = _values['outcome_code_dict']
route_code_dict = _values['route_code_dict']
