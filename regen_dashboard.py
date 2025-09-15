from dataset_citations.dashboard.core import DashboardGenerator
from pathlib import Path

gen = DashboardGenerator(
    results_dir=Path("dashboard_data"), output_dir=Path("interactive_reports")
)

output_path = gen.generate_dashboard(dashboard_type="nemar", lazy_load=True)
print(f"Dashboard generated: {output_path}")
