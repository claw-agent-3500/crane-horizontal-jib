"""YAML input loader with truss config support."""

import yaml

from models import (
    CraneModel, Section, PointLoad, UDL, Trolley, LoadCase,
    TrussConfig, DiagonalConfig, DEFAULT_E,
)


def _parse_diagonal(data: dict) -> DiagonalConfig:
    return DiagonalConfig(
        angle=data['angle'],
        present=data.get('present', True),
    )


def _parse_truss(data: dict) -> TrussConfig:
    if not data:
        return None
    return TrussConfig(
        upper_chords=data.get('upper_chords', 2),
        lower_chords=data.get('lower_chords', 2),
        compression_diagonal=_parse_diagonal(data['compression_diagonal']) if 'compression_diagonal' in data else None,
        tension_diagonal=_parse_diagonal(data['tension_diagonal']) if 'tension_diagonal' in data else None,
        neutral_diagonal=_parse_diagonal(data['neutral_diagonal']) if 'neutral_diagonal' in data else None,
    )


def _parse_section(data: dict) -> Section:
    truss_data = data.pop('truss', None)
    truss = _parse_truss(truss_data) if truss_data else None
    wind_area = data.pop('wind_area', 0.0)
    cg_x = data.pop('cg_x', 0.0)
    cg_y = data.pop('cg_y', 0.0)
    cg_z = data.pop('cg_z', 0.0)
    return Section(**data, truss=truss, wind_area=wind_area, cg_x=cg_x, cg_y=cg_y, cg_z=cg_z)


def _parse_point_load(data: dict) -> PointLoad:
    wind_area = data.pop('wind_area', 0.0)
    cg_x = data.pop('cg_x', 0.0)
    cg_y = data.pop('cg_y', 0.0)
    cg_z = data.pop('cg_z', 0.0)
    return PointLoad(**data, wind_area=wind_area, cg_x=cg_x, cg_y=cg_y, cg_z=cg_z)


def _parse_udl(data: dict) -> UDL:
    wind_area = data.pop('wind_area', 0.0)
    cg_x = data.pop('cg_x', 0.0)
    cg_y = data.pop('cg_y', 0.0)
    cg_z = data.pop('cg_z', 0.0)
    return UDL(**data, wind_area=wind_area, cg_x=cg_x, cg_y=cg_y, cg_z=cg_z)


def load_model(path: str) -> CraneModel:
    with open(path) as f:
        data = yaml.safe_load(f)

    crane = data['crane']
    sections = [_parse_section(dict(s)) for s in data['sections']]
    point_loads = [_parse_point_load(dict(pl)) for pl in data.get('point_loads', [])]
    udls = [_parse_udl(dict(u)) for u in data.get('udls', [])]

    analysis = data.get('analysis', {})
    num_points = analysis.get('num_points', 500)
    E = crane.get('youngs_modulus', DEFAULT_E)

    ts_data = data.get('trolley')
    trolley = None
    if ts_data:
        trolley = Trolley(
            magnitude=ts_data['magnitude'],
            min_position=ts_data['min_position'],
            max_position=ts_data['max_position'],
            step=ts_data.get('step', 1.0),
            wind_area=ts_data.get('wind_area', 0.0),
            cg_x=ts_data.get('cg_x', 0.0),
            cg_y=ts_data.get('cg_y', 0.0),
            cg_z=ts_data.get('cg_z', 0.0),
        )

    # Load cases
    lc_data = data.get('load_cases', [])
    load_cases = []
    for lc in lc_data:
        # Parse coefficients: keys starting with "coef_"
        coefs = {k[5:]: v for k, v in lc.items() if k.startswith('coef_')}
        wind_pressure = lc.get('wind_pressure', 0.0)  # Pa
        load_cases.append(LoadCase(name=lc['name'], coefficients=coefs, wind_pressure=wind_pressure))

    # If no load cases defined, create a default one (all coef = 1.0, no wind)
    if not load_cases:
        load_cases.append(LoadCase(name='Default (All loads)', coefficients={}, wind_pressure=0.0))

    return CraneModel(
        name=crane['name'],
        jib_length=crane['jib_length'],
        jib_height_position=crane.get('jib_height_position', 0.0),
        sections=sections,
        point_loads=point_loads,
        udls=udls,
        youngs_modulus=E,
        num_points=num_points,
        trolley=trolley,
        load_cases=load_cases,
    )
