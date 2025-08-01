# Dataset Citations Documentation

This directory contains comprehensive documentation for the dataset citations analysis system.

## Documentation Structure

```
docs/
├── cli/                        # CLI command documentation
│   ├── README.md              # CLI overview and getting started
│   ├── analysis-commands.md   # Network and temporal analysis commands
│   ├── visualization-commands.md # Visualization and reporting commands
│   └── data-management.md     # Data loading and processing commands
├── analysis/                  # Analysis methodology documentation
│   ├── README.md              # Analysis overview
│   ├── network-analysis.md    # Network analysis methods
│   ├── temporal-analysis.md   # Temporal analysis methods
│   ├── confidence-scoring.md  # Citation confidence methodology
│   └── research-themes.md     # UMAP clustering and theme analysis
├── visualization/             # Visualization guides
│   ├── README.md              # Visualization overview
│   ├── interactive-dashboards.md # Interactive dashboard usage
│   ├── external-tools.md      # Gephi, Cytoscape integration
│   └── customization.md       # Styling and configuration options
└── api/                       # API reference documentation
    ├── README.md              # API overview
    ├── core-modules.md        # Core analysis modules
    ├── cli-modules.md         # CLI implementation details
    └── data-structures.md     # Data formats and schemas
```

## Migration Plan

### Phase 1: Documentation Consolidation
- Migrate content from `PHASE_4_7_INTERACTIVE_REPORTS.md` to `docs/visualization/interactive-dashboards.md`
- Move phase documentation content to appropriate sections
- Create comprehensive CLI reference from existing command help text

### Phase 2: MkDocs Implementation
- Set up MkDocs configuration with Material theme
- Create navigation structure following analysis workflow
- Add code examples and interactive tutorials
- Implement search functionality for CLI commands

### Phase 3: Integration
- Link documentation from CLI help commands
- Add documentation generation to CI/CD pipeline
- Create contribution guidelines for documentation updates

## Current Status
- **Analysis Results**: Documented in `results/README.md`
- **Phase Documentation**: Individual phase markdown files (to be consolidated)
- **CLI Help**: Available via `--help` flags (to be expanded)

## Future Enhancements
- Interactive code examples with embedded outputs
- Video tutorials for complex analysis workflows
- Integration with Jupyter notebooks for methodology documentation
- API documentation generation from docstrings