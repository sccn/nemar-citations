/**
 * Dashboard Templates and Standardized Components
 * NEMAR Dataset Citation Analysis
 * 
 * This file provides reusable templates and configurations for dashboard visualizations
 */

// ============================================================================
// Color Scheme Configuration
// ============================================================================
const NEMARTheme = {
    colors: {
        primaryBlue: '#083d94',
        accentGold: '#e1d295',
        textGray: '#555555',
        lightGray: '#f8f9fa',
        borderGray: '#dee2e6',
        darkBlue: '#052963',
        linkBlue: '#0056b3',
        white: '#ffffff',
        lightBlue: '#e8f0ff',
        success: '#28a745',
        warning: '#ffc107',
        danger: '#dc3545'
    },
    
    // Plotly color scales
    colorScales: {
        qualitative: ['#083d94', '#e1d295', '#555555', '#0056b3', '#052963'],
        sequential: ['#e8f0ff', '#083d94'],
        diverging: ['#dc3545', '#ffffff', '#28a745']
    },
    
    // Chart specific colors
    chartColors: {
        primary: '#083d94',
        secondary: '#e1d295',
        tertiary: '#555555',
        quaternary: '#0056b3',
        quinary: '#052963'
    }
};

// ============================================================================
// Standard Chart Configurations
// ============================================================================
const ChartTemplates = {
    /**
     * Base layout configuration for all Plotly charts
     */
    baseLayout: {
        font: {
            family: 'Open Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif',
            color: NEMARTheme.colors.textGray
        },
        plot_bgcolor: NEMARTheme.colors.white,
        paper_bgcolor: NEMARTheme.colors.white,
        margin: { t: 40, r: 20, b: 60, l: 60 },
        hovermode: 'closest',
        showlegend: true,
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: -0.3,
            xanchor: 'center',
            x: 0.5,
            bgcolor: 'rgba(255,255,255,0.9)',
            bordercolor: NEMARTheme.colors.borderGray,
            borderwidth: 1
        },
        xaxis: {
            gridcolor: NEMARTheme.colors.borderGray,
            zerolinecolor: NEMARTheme.colors.borderGray
        },
        yaxis: {
            gridcolor: NEMARTheme.colors.borderGray,
            zerolinecolor: NEMARTheme.colors.borderGray
        }
    },
    
    /**
     * Configuration for bar charts
     */
    barChart: {
        type: 'bar',
        marker: {
            color: NEMARTheme.colors.primaryBlue,
            line: {
                color: NEMARTheme.colors.darkBlue,
                width: 1
            }
        },
        hovertemplate: '%{y}<br>%{x}<extra></extra>'
    },
    
    /**
     * Configuration for line charts
     */
    lineChart: {
        type: 'scatter',
        mode: 'lines+markers',
        line: {
            color: NEMARTheme.colors.primaryBlue,
            width: 2
        },
        marker: {
            color: NEMARTheme.colors.primaryBlue,
            size: 8,
            line: {
                color: NEMARTheme.colors.white,
                width: 2
            }
        },
        hovertemplate: '%{y}<br>%{x}<extra></extra>'
    },
    
    /**
     * Configuration for pie charts
     */
    pieChart: {
        type: 'pie',
        marker: {
            colors: NEMARTheme.colorScales.qualitative,
            line: {
                color: NEMARTheme.colors.white,
                width: 2
            }
        },
        textposition: 'auto',
        textinfo: 'label+percent',
        hovertemplate: '%{label}<br>%{value} (%{percent})<extra></extra>'
    },
    
    /**
     * Configuration for scatter plots
     */
    scatterChart: {
        type: 'scatter',
        mode: 'markers',
        marker: {
            color: NEMARTheme.colors.primaryBlue,
            size: 10,
            opacity: 0.7,
            line: {
                color: NEMARTheme.colors.darkBlue,
                width: 1
            }
        },
        hovertemplate: '%{text}<br>X: %{x}<br>Y: %{y}<extra></extra>'
    }
};

// ============================================================================
// Loading and Error State Templates
// ============================================================================
const StateTemplates = {
    /**
     * Generate loading state HTML
     */
    loading: (message = 'Loading data...') => `
        <div class="d-flex justify-content-center align-items-center" style="min-height: 300px;">
            <div class="text-center">
                <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem; border-color: ${NEMARTheme.colors.primaryBlue};">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">${message}</p>
            </div>
        </div>
    `,
    
    /**
     * Generate error state HTML
     */
    error: (message = 'An error occurred') => `
        <div class="alert alert-danger d-flex align-items-center" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <div>${message}</div>
        </div>
    `,
    
    /**
     * Generate empty state HTML
     */
    empty: (message = 'No data available') => `
        <div class="text-center text-muted py-5">
            <i class="fas fa-inbox fa-3x mb-3" style="color: ${NEMARTheme.colors.borderGray};"></i>
            <p>${message}</p>
        </div>
    `,
    
    /**
     * Generate success state HTML
     */
    success: (message = 'Operation completed successfully') => `
        <div class="alert alert-success d-flex align-items-center" role="alert">
            <i class="fas fa-check-circle me-2"></i>
            <div>${message}</div>
        </div>
    `
};

// ============================================================================
// Reusable Visualization Functions
// ============================================================================
const VisualizationHelpers = {
    /**
     * Create a standardized Plotly chart
     */
    createChart: function(elementId, data, layout, config = {}) {
        try {
            // Merge with base layout
            const finalLayout = {
                ...ChartTemplates.baseLayout,
                ...layout
            };
            
            // Default config
            const finalConfig = {
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['pan2d', 'lasso2d'],
                ...config
            };
            
            // Create the plot
            Plotly.newPlot(elementId, data, finalLayout, finalConfig);
            
            // Add resize observer for better responsiveness
            if (window.ResizeObserver) {
                const resizeObserver = new ResizeObserver(() => {
                    Plotly.Plots.resize(elementId);
                });
                const element = document.getElementById(elementId);
                if (element) {
                    resizeObserver.observe(element);
                }
            }
            
            return true;
        } catch (error) {
            console.error(`Error creating chart ${elementId}:`, error);
            const element = document.getElementById(elementId);
            if (element) {
                element.innerHTML = StateTemplates.error(`Failed to create chart: ${error.message}`);
            }
            return false;
        }
    },
    
    /**
     * Update existing chart data
     */
    updateChart: function(elementId, data, layout = null) {
        try {
            if (layout) {
                Plotly.react(elementId, data, layout);
            } else {
                Plotly.restyle(elementId, data);
            }
            return true;
        } catch (error) {
            console.error(`Error updating chart ${elementId}:`, error);
            return false;
        }
    },
    
    /**
     * Add loading state to element
     */
    showLoading: function(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = StateTemplates.loading(message);
        }
    },
    
    /**
     * Add error state to element
     */
    showError: function(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = StateTemplates.error(message);
        }
    },
    
    /**
     * Add empty state to element
     */
    showEmpty: function(elementId, message) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = StateTemplates.empty(message);
        }
    },
    
    /**
     * Format numbers with commas
     */
    formatNumber: function(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },
    
    /**
     * Format dates consistently
     */
    formatDate: function(date) {
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        return new Date(date).toLocaleDateString('en-US', options);
    },
    
    /**
     * Create tooltip content
     */
    createTooltip: function(data) {
        let html = '<div class="custom-tooltip">';
        for (const [key, value] of Object.entries(data)) {
            html += `<div><strong>${key}:</strong> ${value}</div>`;
        }
        html += '</div>';
        return html;
    }
};

// ============================================================================
// Network Visualization Templates
// ============================================================================
const NetworkTemplates = {
    /**
     * Base Cytoscape configuration
     */
    baseCytoscapeConfig: {
        layout: {
            name: 'preset',
            padding: 50,
            animate: true,
            animationDuration: 500
        },
        style: [
            {
                selector: 'node',
                style: {
                    'background-color': NEMARTheme.colors.primaryBlue,
                    'label': 'data(label)',
                    'color': NEMARTheme.colors.textGray,
                    'text-valign': 'bottom',
                    'text-halign': 'center',
                    'font-size': '12px',
                    'font-family': 'Open Sans, Arial, sans-serif',
                    'border-width': 2,
                    'border-color': NEMARTheme.colors.darkBlue,
                    'width': 'mapData(value, 0, 100, 20, 60)',
                    'height': 'mapData(value, 0, 100, 20, 60)'
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': NEMARTheme.colors.borderGray,
                    'target-arrow-color': NEMARTheme.colors.borderGray,
                    'curve-style': 'bezier',
                    'opacity': 0.7
                }
            },
            {
                selector: 'node:selected',
                style: {
                    'background-color': NEMARTheme.colors.accentGold,
                    'border-color': NEMARTheme.colors.darkBlue,
                    'border-width': 3
                }
            }
        ],
        minZoom: 0.5,
        maxZoom: 3,
        wheelSensitivity: 0.2
    },
    
    /**
     * Create network visualization with standard configuration
     */
    createNetwork: function(elementId, elements, customConfig = {}) {
        try {
            const container = document.getElementById(elementId);
            if (!container) {
                throw new Error(`Container ${elementId} not found`);
            }
            
            const config = {
                container: container,
                elements: elements,
                ...this.baseCytoscapeConfig,
                ...customConfig
            };
            
            const cy = cytoscape(config);
            
            // Add pan/zoom controls
            cy.on('tap', 'node', function(evt) {
                const node = evt.target;
                console.log('Node clicked:', node.data());
            });
            
            // Fit to viewport
            cy.fit();
            
            return cy;
        } catch (error) {
            console.error(`Error creating network ${elementId}:`, error);
            VisualizationHelpers.showError(elementId, `Network visualization error: ${error.message}`);
            return null;
        }
    }
};

// ============================================================================
// Data Formatting Standards
// ============================================================================
const DataFormats = {
    /**
     * Standard format for time series data
     */
    timeSeries: {
        x: [], // Array of dates
        y: [], // Array of values
        name: '', // Series name
        metadata: {} // Additional metadata
    },
    
    /**
     * Standard format for categorical data
     */
    categorical: {
        categories: [], // Array of category names
        values: [], // Array of values
        colors: [], // Optional array of colors
        metadata: {} // Additional metadata
    },
    
    /**
     * Standard format for network data
     */
    network: {
        nodes: [
            {
                id: '', // Unique identifier
                label: '', // Display label
                value: 0, // Node size/importance
                group: '', // Category/cluster
                metadata: {} // Additional properties
            }
        ],
        edges: [
            {
                source: '', // Source node ID
                target: '', // Target node ID
                weight: 0, // Edge weight/strength
                type: '', // Edge type
                metadata: {} // Additional properties
            }
        ]
    },
    
    /**
     * Validate and format data
     */
    validate: function(data, format) {
        // Implementation of validation logic
        return true;
    }
};

// ============================================================================
// Export for use in dashboard
// ============================================================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        NEMARTheme,
        ChartTemplates,
        StateTemplates,
        VisualizationHelpers,
        NetworkTemplates,
        DataFormats
    };
}