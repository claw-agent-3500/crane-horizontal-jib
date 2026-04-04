"""Save and load load case sets to/from YAML files."""

import yaml
from pathlib import Path


def save_load_case_set(load_cases, output_path: str):
    """Save a list of load cases to a YAML file."""
    data = {'load_cases': []}
    for lc in load_cases:
        lc_dict = {'name': lc.name, 'wind_pressure': lc.wind_pressure}
        # Add all coefficients with coef_ prefix
        for k, v in lc.coefficients.items():
            lc_dict[f'coef_{k}'] = v
        data['load_cases'].append(lc_dict)
    
    Path(output_path).write_text(yaml.dump(data, default_flow_style=False))
    return output_path


def load_load_case_set(input_path: str) -> list:
    """Load load cases from a YAML file."""
    from models import LoadCase
    
    data = yaml.safe_load(Path(input_path).read_text())
    load_cases = []
    
    for lc_data in data.get('load_cases', []):
        coefficients = {k[5:]: v for k, v in lc_data.items() if k.startswith('coef_')}
        wind_pressure = lc_data.get('wind_pressure', 0.0)
        load_cases.append(LoadCase(
            name=lc_data['name'],
            coefficients=coefficients,
            wind_pressure=wind_pressure
        ))
    
    return load_cases
