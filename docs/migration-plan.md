# Documentation Migration Plan

## Current Documentation State

### Phase Documentation Files
- `PHASE_4_7_INTERACTIVE_REPORTS.md` - Interactive dashboard documentation
- `EMBEDDING_STORAGE_DESIGN.md` - Embedding storage system design
- `JSON_CITATION_FORMAT.md` - Citation data format specification
- `LOCAL_EXECUTION.md` - Local development setup
- Various README files in subdirectories

### Results Documentation
- `results/README.md` - Analysis results overview
- Individual README files in analysis subdirectories
- CLI help text embedded in command implementations

## Migration Strategy

### Phase 1: Consolidate Core Documentation

#### Move Phase-Specific Documentation
```bash
# Interactive dashboards
mv PHASE_4_7_INTERACTIVE_REPORTS.md docs/visualization/interactive-dashboards.md

# Embedding system
mv EMBEDDING_STORAGE_DESIGN.md docs/analysis/embedding-system.md

# Data formats
mv JSON_CITATION_FORMAT.md docs/api/data-formats.md

# Development setup
mv LOCAL_EXECUTION.md docs/development/setup.md
```

#### Reorganize Results Documentation
- Keep `results/README.md` as analysis results overview
- Move methodology documentation to `docs/analysis/`
- Create cross-references between results and methodology docs

### Phase 2: Extract CLI Documentation

#### Generate CLI Reference
```python
# Extract from existing CLI help text
for command in cli_commands:
    help_text = extract_help_text(command)
    generate_markdown_docs(help_text, f"docs/cli/{command}.md")
```

#### Create Workflow Guides
- **Getting Started**: Basic usage examples
- **Analysis Workflows**: Step-by-step analysis procedures
- **Automation Setup**: Pipeline configuration guides
- **Troubleshooting**: Common issues and solutions

### Phase 3: MkDocs Implementation

#### Configuration
```yaml
# mkdocs.yml
site_name: Dataset Citations Analysis
theme:
  name: material
  palette:
    primary: blue
    accent: orange
nav:
  - Home: index.md
  - CLI Reference:
    - Overview: cli/README.md
    - Analysis Commands: cli/analysis-commands.md
    - Visualization Commands: cli/visualization-commands.md
  - Analysis Methods:
    - Network Analysis: analysis/network-analysis.md
    - Temporal Analysis: analysis/temporal-analysis.md
    - Confidence Scoring: analysis/confidence-scoring.md
  - Visualization:
    - Interactive Dashboards: visualization/interactive-dashboards.md
    - External Tools: visualization/external-tools.md
  - API Reference:
    - Data Formats: api/data-formats.md
    - Core Modules: api/core-modules.md
```

#### Enhanced Features
- **Code Examples**: Embedded command examples with expected outputs
- **Search Functionality**: Full-text search across all documentation
- **Cross-References**: Links between related concepts and commands
- **Version Control**: Documentation versioning aligned with releases

## Implementation Timeline

### Week 1: Content Migration
- [ ] Move existing markdown files to new structure
- [ ] Update internal links and references
- [ ] Create comprehensive CLI reference from help text
- [ ] Consolidate methodology documentation

### Week 2: MkDocs Setup
- [ ] Install and configure MkDocs with Material theme
- [ ] Create navigation structure and landing pages
- [ ] Add code examples and usage scenarios
- [ ] Implement search and cross-referencing

### Week 3: Integration and Testing
- [ ] Link documentation from CLI help commands
- [ ] Add documentation build to CI/CD pipeline
- [ ] Test documentation completeness and accuracy
- [ ] Create contribution guidelines for documentation

## Benefits of Reorganization

### For Users
- **Single Source of Truth**: All documentation in organized, searchable format
- **Workflow-Oriented**: Documentation organized by tasks, not implementation details
- **Examples and Tutorials**: Practical guides with real-world scenarios
- **Up-to-Date Information**: Documentation integrated with development workflow

### For Developers
- **Maintainable Structure**: Clear organization reduces maintenance overhead
- **Automated Generation**: CLI reference generated from actual help text
- **Version Control**: Documentation changes tracked with code changes
- **Contribution Guidelines**: Clear process for documentation updates

## File Structure After Migration

```
docs/
├── index.md                          # Project overview and getting started
├── cli/
│   ├── README.md                     # CLI overview
│   ├── analysis-commands.md          # Network, temporal, UMAP analysis
│   ├── visualization-commands.md     # Dashboards, exports, networks
│   ├── data-management.md            # Discovery, updates, migrations
│   └── automation.md                 # Pipeline and scheduling commands
├── analysis/
│   ├── README.md                     # Analysis methodology overview
│   ├── network-analysis.md           # Co-citation, bridge analysis methods
│   ├── temporal-analysis.md          # Citation timeline methodology
│   ├── confidence-scoring.md         # Citation quality assessment
│   ├── embedding-system.md           # UMAP and similarity analysis
│   └── research-themes.md            # Theme identification and clustering
├── visualization/
│   ├── README.md                     # Visualization overview
│   ├── interactive-dashboards.md     # Dashboard usage and customization
│   ├── external-tools.md             # Gephi, Cytoscape integration
│   ├── network-layouts.md            # Network visualization options
│   └── customization.md              # Styling and configuration
├── api/
│   ├── README.md                     # API overview
│   ├── data-formats.md               # JSON schemas and data structures
│   ├── core-modules.md               # Core analysis module reference
│   ├── cli-modules.md                # CLI implementation details
│   └── database-schema.md            # Neo4j graph schema
└── development/
    ├── setup.md                      # Local development environment
    ├── contributing.md               # Contribution guidelines
    ├── testing.md                    # Testing procedures
    └── deployment.md                 # Production deployment guides

# Legacy files to be integrated
results/README.md                     # Keep as analysis results index
plan.md                              # Keep as development roadmap
```

This structure provides comprehensive, organized documentation while maintaining backward compatibility with existing result files and development workflows.