"""NEMAR theme styles component."""


def get_nemar_styles() -> str:
    """Get NEMAR-specific inline styles."""
    return """
    <style>
        /* NEMAR Theme */
        :root {
            --nemar-primary-blue: #083d94;
            --nemar-text-gray: #555555;
            --nemar-accent-gold: #e1d295;
            --nemar-light-gray: #f8f9fa;
            --nemar-border-gray: #dee2e6;
            --nemar-white: #ffffff;
        }
        
        body {
            font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            color: var(--nemar-text-gray);
            font-size: 14px;
            line-height: 1.6;
        }
        
        h1 {
            color: var(--nemar-primary-blue);
            font-weight: 700;
            font-size: 2.2rem;
            border-bottom: 3px solid var(--nemar-accent-gold);
            padding-bottom: 0.75rem;
        }
        
        h2, h3, h4, h5, h6 {
            color: var(--nemar-primary-blue);
            font-weight: 600;
        }
        
        .stat-card {
            background: white;
            border: 2px solid var(--nemar-border-gray);
            border-radius: 8px;
            padding: 1.75rem 1.5rem;
            transition: all 0.3s ease;
            cursor: pointer;
            height: 100%;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        .stat-card:hover {
            border-color: var(--nemar-primary-blue);
            box-shadow: 0 6px 20px rgba(8, 61, 148, 0.12);
            transform: translateY(-3px);
        }
        
        .stat-card h3 {
            color: var(--nemar-primary-blue);
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .card-header {
            background-color: var(--nemar-primary-blue) !important;
            color: white !important;
            padding: 1.25rem;
            font-weight: 600;
            border-bottom: 3px solid var(--nemar-accent-gold) !important;
        }
        
        .card-header * {
            color: white !important;
        }
        
        .nav-pills .nav-link {
            color: var(--nemar-text-gray);
            background-color: white;
            border: 2px solid transparent;
            border-radius: 8px 8px 0 0;
            padding: 0.875rem 1.5rem;
            font-weight: 500;
            margin-right: 0.25rem;
        }
        
        .nav-pills .nav-link.active {
            background-color: var(--nemar-primary-blue);
            color: white;
        }
        
        .viz-container {
            min-height: 300px;
            background: white;
        }
        
        .network-container {
            background: #f8f9fa;
            border-radius: 8px;
            min-height: 500px;
        }
        
        footer {
            background: linear-gradient(to bottom, white, var(--nemar-light-gray));
            border-top: 3px solid var(--nemar-accent-gold);
            padding: 2rem 0 1.5rem;
            margin-top: 3rem;
        }
        
        footer a {
            color: var(--nemar-primary-blue);
            font-weight: 600;
        }
    </style>
</head>"""
