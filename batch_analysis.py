"""Multi-jib batch analysis for crane fleet/selection."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import numpy as np
from loader import load_model
from crane_calc import run_analysis
from models import Section, PointLoad, LoadCase, TrussConfig, DiagonalConfig


@dataclass
class JibConfig:
    """Single jib configuration."""
    name: str
    jib_length: float
    counterjib_length: float = 15.0
    jib_height: float = 0.0
    sections: List = field(default_factory=list)
    point_loads: List = field(default_factory=list)
    udls: List = field(default_factory=list)


@dataclass
class BatchResult:
    """Results from batch analysis."""
    config_name: str
    max_moment: float
    max_shear: float
    max_stress: float
    max_utilization: float
    tip_deflection: float
    worst_load_case: str
    passed: bool


class BatchAnalyzer:
    """Analyze multiple jib configurations."""
    
    def __init__(self, base_model=None):
        self.base_model = base_model
        self.results: List[BatchResult] = []
        self.worst_case: Optional[BatchResult] = None
    
    def add_config(self, config: JibConfig):
        """Add a jib configuration to analyze."""
        # Modify base model with new config
        model = self.base_model
        if model:
            model.jib_length = config.jib_length
            model.jib_height_position = config.jib_height
            if config.sections:
                model.sections = config.sections
            if config.point_loads:
                model.point_loads = config.point_loads
            if config.udls:
                model.udls = config.udls
        
        # Run analysis
        result = run_analysis(model)
        
        # Extract key metrics
        max_moment = float(np.max(np.abs(result.M)))
        max_shear = float(np.max(np.abs(result.V)))
        max_stress = float(np.max(result.sigma))
        
        # Calculate utilization
        max_util = 0.0
        for sec in model.sections:
            util = max_stress / sec.yield_strength if sec.yield_strength > 0 else 0
            max_util = max(max_util, util)
        
        # Tip deflection
        tip_defl = float(result.delta[-1])
        
        # Find worst load case
        worst_lc = max(model.load_cases, key=lambda lc: lc.coef('payload')).name
        
        passed = max_util < 1.0 and tip_defl < model.jib_length / 250
        
        batch_result = BatchResult(
            config_name=config.name,
            max_moment=max_moment,
            max_shear=max_shear,
            max_stress=max_stress,
            max_utilization=max_util * 100,
            tip_deflection=tip_defl,
            worst_load_case=worst_lc,
            passed=passed,
        )
        
        self.results.append(batch_result)
        
        # Track worst case
        if self.worst_case is None or max_moment > self.worst_case.max_moment:
            self.worst_case = batch_result
    
    def generate_comparison_table(self) -> str:
        """Generate comparison table for all configurations."""
        if not self.results:
            return "No results"
        
        header = f"{'Config':<15} {'Length':<8} {'Max M':<12} {'Max V':<10} {'Stress':<10} {'Util%':<8} {'Defl (mm)':<12} {'Pass':<6}"
        separator = "-" * len(header)
        
        lines = [header, separator]
        
        for r in self.results:
            status = "✓" if r.passed else "✗"
            lines.append(f"{r.config_name:<15} {self.base_model.jib_length if self.base_model else 0:<8.1f} "
                        f"{r.max_moment:<12.1f} {r.max_shear:<10.1f} "
                        f"{r.max_stress:<10.1f} {r.max_utilization:<8.1f} "
                        f"{r.tip_deflection:<12.1f} {status:<6}")
        
        return "\n".join(lines)
    
    def find_worst_utilization(self) -> BatchResult:
        """Find configuration with highest utilization."""
        return max(self.results, key=lambda r: r.max_utilization)
    
    def find_worst_deflection(self) -> BatchResult:
        """Find configuration with highest deflection."""
        return max(self.results, key=lambda r: r.tip_deflection)


def run_batch_analysis(configs: List[Dict], input_file: str = None) -> BatchAnalyzer:
    """
    Run batch analysis on multiple jib configurations.
    
    Args:
        configs: List of jib configurations to analyze
        input_file: Base input YAML file
    
    Returns:
        BatchAnalyzer with results
    """
    # Load base model
    base_model = load_model(input_file) if input_file else None
    
    analyzer = BatchAnalyzer(base_model)
    
    for config in configs:
        jib_config = JibConfig(
            name=config['name'],
            jib_length=config['jib_length'],
            jib_height=config.get('jib_height', 0.0),
            point_loads=config.get('point_loads', []),
            udls=config.get('udls', []),
        )
        analyzer.add_config(jib_config)
    
    return analyzer


# Example usage
if __name__ == '__main__':
    # Example: Analyze different jib lengths
    configs = [
        {'name': '50m', 'jib_length': 50.0, 'jib_height': 0.0},
        {'name': '55m', 'jib_length': 55.0, 'jib_height': 0.0},
        {'name': '60m', 'jib_length': 60.0, 'jib_height': 0.0},
        {'name': '65m', 'jib_length': 65.0, 'jib_length': 0.0},
    ]
    
    analyzer = run_batch_analysis(configs, 'examples/working_60m/input.yaml')
    
    print("=" * 80)
    print("BATCH ANALYSIS RESULTS")
    print("=" * 80)
    print(analyzer.generate_comparison_table())
    print()
    print(f"Worst case: {analyzer.worst_case.config_name}")
    print(f"  Max Moment: {analyzer.worst_case.max_moment:.1f} kN·m")
    print(f"  Max Stress: {analyzer.worst_case.max_stress:.1f} MPa")
    print(f"  Utilization: {analyzer.worst_case.max_utilization:.1f}%")

def load_batch_config(config_file: str) -> dict:
    """
    Load batch analysis configuration from YAML file.
    
    Returns dict with:
    - analysis_name: str
    - base: dict with input_file
    - jibs: list of jib configs
    - options: dict
    - selection_criteria: dict
    """
    import yaml
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def run_batch_from_config(config_file: str) -> BatchAnalyzer:
    """
    Run batch analysis from YAML config file.
    
    Args:
        config_file: Path to batch configuration YAML
    
    Returns:
        BatchAnalyzer with results for all jib configurations
    """
    config = load_batch_config(config_file)
    
    # Load base model
    base_input = config.get('base', {}).get('input_file', 'examples/working_60m/input.yaml')
    base_model = load_model(base_input)
    
    analyzer = BatchAnalyzer(base_model)
    
    # Process each jib config
    for jib in config.get('jibs', []):
        # Create a copy of base model
        model = load_model(base_input)
        
        # Override parameters
        if 'jib_length' in jib:
            model.jib_length = jib['jib_length']
        if 'jib_height_position' in jib:
            model.jib_height_position = jib['jib_height_position']
        
        # Custom sections
        if 'sections' in jib:
            model.sections = _parse_sections(jib['sections'])
        elif 'section_scaling' in jib:
            # Scale existing sections
            scale = jib['section_scaling']
            for sec in model.sections:
                sec.end = sec.start + (sec.end - sec.start) * scale
        
        # Custom point loads
        if 'point_loads' in jib:
            model.point_loads = _parse_point_loads(jib['point_loads'])
        
        # Custom load cases
        if 'load_cases' in jib:
            model.load_cases = _parse_load_cases(jib['load_cases'])
        
        # Run analysis
        result = run_analysis(model)
        
        # Extract results
        max_moment = float(np.max(np.abs(result.M)))
        max_shear = float(np.max(np.abs(result.V)))
        max_stress = float(np.max(result.sigma))
        
        max_util = 0.0
        for sec in model.sections:
            util = max_stress / sec.yield_strength if sec.yield_strength > 0 else 0
            max_util = max(max_util, util)
        
        tip_defl = float(result.delta[-1])
        worst_lc = max(model.load_cases, key=lambda lc: lc.coef('payload')).name if model.load_cases else 'default'
        
        passed = max_util < 1.0
        
        batch_result = BatchResult(
            config_name=jib['name'],
            max_moment=max_moment,
            max_shear=max_shear,
            max_stress=max_stress,
            max_utilization=max_util * 100,
            tip_deflection=tip_defl,
            worst_load_case=worst_lc,
            passed=passed,
        )
        
        analyzer.results.append(batch_result)
        
        if analyzer.worst_case is None or max_moment > analyzer.worst_case.max_moment:
            analyzer.worst_case = batch_result
    
    return analyzer


def _parse_sections(sections_data: list) -> list:
    """Parse section data from YAML."""
    from models import Section, TrussConfig
    sections = []
    for s in sections_data:
        sec = Section(
            name=s['name'],
            start=s['start'],
            end=s['end'],
            weight_per_length=s['weight_per_length'],
            area=s['area'],
            moment_of_inertia=s['moment_of_inertia'],
            height=s['height'],
            yield_strength=s.get('yield_strength', 345.0),
        )
        if 'truss' in s:
            sec.truss = _parse_truss(s['truss'])
        sections.append(sec)
    return sections


def _parse_truss(truss_data: dict) -> TrussConfig:
    """Parse truss config from YAML."""
    from models import TrussConfig, DiagonalConfig
    diagonals = [DiagonalConfig(d['angle'], d.get('present', True)) for d in truss_data.get('diagonals', [])]
    return TrussConfig(
        cross_section=truss_data.get('cross_section', 'triangle'),
        height=truss_data.get('height', 1.5),
        width=truss_data.get('width', 0.0),
        diagonals=diagonals,
    )


def _parse_point_loads(loads_data: list) -> list:
    """Parse point loads from YAML."""
    from models import PointLoad
    return [PointLoad(name=p['name'], position=p['position'], magnitude=p['magnitude']) for p in loads_data]


def _parse_load_cases(lc_data: list) -> list:
    """Parse load cases from YAML."""
    from models import LoadCase
    cases = []
    for lc in lc_data:
        case = LoadCase(
            name=lc['name'],
            coefficients=lc.get('coefficients', {}),
            wind_pressure=lc.get('wind_pressure', 0.0),
        )
        cases.append(case)
    return cases

