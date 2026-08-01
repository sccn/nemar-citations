"""HTML header component."""


def generate_header(
    title: str = "Dataset Citations Analysis Dashboard", data_file: str | None = None
) -> str:
    """Generate HTML header with all required scripts and styles."""

    lazy_load_script = ""
    if data_file:
        lazy_load_script = f"""
    <!-- Lazy Loading Script -->
    <script>
        // Load data asynchronously
        fetch('{data_file}')
            .then(response => response.json())
            .then(data => {{
                window.analysisData = data.analysisData;
                console.log('Data loaded successfully');
            }})
            .catch(error => console.error('Error loading data:', error));
    </script>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <!-- Plotly.js -->
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <!-- Cytoscape.js -->
    <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    
    <!-- Dashboard Templates & Styles -->
    <!-- Templates embedded in HTML -->
    <link href="dashboard_styles.css" rel="stylesheet">
    {lazy_load_script}
"""
