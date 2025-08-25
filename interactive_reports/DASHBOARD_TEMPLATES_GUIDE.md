# Dashboard Templates Guide

## Overview
The `dashboard_templates.js` file provides standardized, reusable components for creating consistent visualizations across the NEMAR Dataset Citation Analysis dashboard.

## Quick Start

### Including the Templates
```html
<script src="dashboard_templates.js"></script>
```

### Basic Usage

#### Creating a Chart
```javascript
// Standard bar chart
const data = [{
    x: ['Category A', 'Category B', 'Category C'],
    y: [10, 20, 15],
    type: 'bar'
}];

const layout = {
    title: 'Sample Bar Chart'
};

// Create the chart using the helper
VisualizationHelpers.createChart('chartElementId', data, layout);
```

#### Showing Loading States
```javascript
// Show loading indicator
VisualizationHelpers.showLoading('elementId', 'Fetching citation data...');

// Show error state
VisualizationHelpers.showError('elementId', 'Failed to load data');

// Show empty state
VisualizationHelpers.showEmpty('elementId', 'No citations found');
```

## Available Components

### 1. NEMARTheme
Provides consistent color scheme and design tokens:
- `colors`: Primary blue (#083d94), Accent gold (#e1d295), etc.
- `colorScales`: Qualitative, sequential, and diverging color palettes
- `chartColors`: Standardized colors for data visualization

### 2. ChartTemplates
Pre-configured Plotly chart templates:
- `baseLayout`: Standard layout for all charts
- `barChart`: Bar chart configuration
- `lineChart`: Line/time series configuration  
- `pieChart`: Pie/donut chart configuration
- `scatterChart`: Scatter plot configuration

### 3. StateTemplates
HTML templates for different states:
- `loading(message)`: Loading spinner with message
- `error(message)`: Error alert
- `empty(message)`: Empty state indicator
- `success(message)`: Success notification

### 4. VisualizationHelpers
Utility functions for chart management:
- `createChart(elementId, data, layout, config)`: Create standardized Plotly chart
- `updateChart(elementId, data, layout)`: Update existing chart
- `showLoading/Error/Empty(elementId, message)`: Display state templates
- `formatNumber(num)`: Add thousands separators
- `formatDate(date)`: Consistent date formatting
- `createTooltip(data)`: Generate tooltip HTML

### 5. NetworkTemplates
Cytoscape.js network visualization configuration:
- `baseCytoscapeConfig`: Standard network layout and styling
- `createNetwork(elementId, elements, config)`: Create network visualization

### 6. DataFormats
Standard data structure definitions:
- `timeSeries`: Format for temporal data
- `categorical`: Format for category data
- `network`: Format for network graphs

## Examples

### Time Series Chart
```javascript
const data = [{
    ...ChartTemplates.lineChart,
    x: ['2020', '2021', '2022', '2023'],
    y: [100, 150, 180, 220],
    name: 'Citations Over Time'
}];

const layout = {
    title: 'Citation Growth',
    xaxis: { title: 'Year' },
    yaxis: { title: 'Total Citations' }
};

VisualizationHelpers.createChart('timeSeriesChart', data, layout);
```

### Network Visualization
```javascript
const elements = {
    nodes: [
        { data: { id: 'n1', label: 'Dataset A', value: 50 } },
        { data: { id: 'n2', label: 'Dataset B', value: 30 } }
    ],
    edges: [
        { data: { source: 'n1', target: 'n2', weight: 5 } }
    ]
};

NetworkTemplates.createNetwork('networkContainer', elements);
```

### Error Handling
```javascript
VisualizationHelpers.showLoading('chartDiv', 'Processing data...');

fetch('/api/data')
    .then(response => response.json())
    .then(data => {
        if (data.length === 0) {
            VisualizationHelpers.showEmpty('chartDiv', 'No data available');
        } else {
            // Create chart with data
            VisualizationHelpers.createChart('chartDiv', data, layout);
        }
    })
    .catch(error => {
        VisualizationHelpers.showError('chartDiv', `Error: ${error.message}`);
    });
```

## Customization

### Extending Chart Templates
```javascript
// Create custom chart type
const customChart = {
    ...ChartTemplates.barChart,
    marker: {
        ...ChartTemplates.barChart.marker,
        color: NEMARTheme.colors.accentGold
    }
};
```

### Custom Color Schemes
```javascript
// Use theme colors in custom visualizations
const customColors = [
    NEMARTheme.colors.primaryBlue,
    NEMARTheme.colors.accentGold,
    NEMARTheme.colors.textGray
];
```

## Best Practices

1. **Always use theme colors** for consistency
2. **Handle all states** (loading, error, empty, success)
3. **Use standardized formatters** for numbers and dates
4. **Leverage base configurations** and extend as needed
5. **Maintain responsive design** with the responsive: true flag

## Data Structure Requirements

### Time Series Data
```javascript
{
    x: ['2020-01', '2020-02', ...],  // ISO date strings
    y: [10, 20, ...],                 // Numeric values
    name: 'Series Name',              // Display name
    metadata: { /* optional */ }      // Additional info
}
```

### Network Data
```javascript
{
    nodes: [
        { id: 'unique-id', label: 'Display Name', value: 100, group: 'category' }
    ],
    edges: [
        { source: 'node-id-1', target: 'node-id-2', weight: 1 }
    ]
}
```

## Migration from Direct Plotly Usage

### Before (Direct Plotly)
```javascript
Plotly.newPlot('myChart', data, layout, {responsive: true});
```

### After (Using Templates)
```javascript
VisualizationHelpers.createChart('myChart', data, layout);
```

The template version automatically:
- Merges with base layout configuration
- Adds resize observers for responsiveness
- Handles errors gracefully
- Applies NEMAR theme consistently

## Browser Compatibility
- Modern browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- Requires: Plotly.js, Cytoscape.js, Bootstrap 5
- Optional: jQuery for enhanced Bootstrap functionality

## Support
For questions or issues with dashboard templates, refer to the main project documentation or open an issue on GitHub.