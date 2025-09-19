"""
Modal HTML and JavaScript generation for NEMAR dashboard.
"""

import json
from typing import Any, Dict


class ModalHandler:
    """Generate modal HTML and JavaScript for dashboard."""

    @staticmethod
    def generate_modal_html() -> str:
        """Generate the Bootstrap modal HTML structure."""
        return """
        <!-- Detail Modal -->
        <div class="modal fade" id="detailModal" tabindex="-1" aria-labelledby="detailModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="detailModalLabel">Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="modalContent">
                        <!-- Content will be populated dynamically -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
        """

    @staticmethod
    def generate_modal_javascript(modals: Dict[str, Any]) -> str:
        """Generate JavaScript for modal functionality."""
        # Format the JSON with proper indentation to avoid parser issues
        modal_json = json.dumps(modals, indent=2) if modals else "{}"

        return f"""
        // Modal data from server - ensure it's in window scope
        window.modalData = {modal_json};
        
        // Modal handler - ensure it's in window scope
        window.showDetailModal = function(type) {{
            const modal = new bootstrap.Modal(document.getElementById('detailModal'));
            const modalTitle = document.getElementById('detailModalLabel');
            const modalContent = document.getElementById('modalContent');
            
            const data = window.modalData[type] || {{}};
            let content = '';
            
            switch(type) {{
                case 'datasets': {{
                    {ModalHandler._generate_datasets_case()}
                    break;
                }}
                    
                case 'citations': {{
                    {ModalHandler._generate_citations_case()}
                    break;
                }}
                    
                case 'bridges': {{
                    {ModalHandler._generate_bridges_case()}
                    break;
                }}
                    
                case 'threshold': {{
                    {ModalHandler._generate_threshold_case()}
                    break;
                }}
                    
                default:
                    modalTitle.textContent = 'Information';
                    content = '<p>No additional information available.</p>';
            }}
            
            modalContent.innerHTML = content;
            modal.show();
        }}
        """

    @staticmethod
    def _generate_datasets_case() -> str:
        """Generate JavaScript case for datasets modal."""
        return """
                    modalTitle.textContent = data.title || 'Dataset Analysis Details';
                    const datasets = data.content?.top_datasets || [];
                    let datasetList = '';
                    
                    // Generate list of top 20 datasets
                    datasets.slice(0, 20).forEach(ds => {
                        const dsId = ds.dataset_id || '';
                        const dsName = ds.dataset_name || 'Unknown';
                        const highConf = ds.high_confidence_citations || 0;
                        const total = ds.total_citations || 0;
                        const conf = (parseFloat(ds.avg_confidence) || 0).toFixed(2);
                        
                        datasetList += `
                            <div class="mb-3 p-2 border-bottom">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div>
                                        <strong><a href="https://nemar.org/dataexplorer/detail?dataset_id=${dsId}" 
                                                target="_blank" class="text-primary">${dsId}</a></strong>
                                        <span class="text-muted ms-2">${highConf} high-conf citations</span>
                                    </div>
                                </div>
                                <div class="text-muted small">${dsName}</div>
                                <div class="text-muted small">${total} total (${highConf} ≥0.4, ${total - highConf} <0.4)</div>
                            </div>
                        `;
                    });
                    
                    content = `
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <div class="card border-primary">
                                    <div class="card-body text-center">
                                        <h2 class="text-primary">${data.content?.total_datasets || 0}</h2>
                                        <p class="mb-0 text-dark">Total Datasets</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card border-success">
                                    <div class="card-body text-center">
                                        <h2 class="text-success">${data.content?.with_citations || 0}</h2>
                                        <p class="mb-0 text-dark">With High-Conf Citations</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card border-warning">
                                    <div class="card-body text-center">
                                        <h2 class="text-warning">${data.content?.coverage || '100%'}</h2>
                                        <p class="mb-0 text-dark">Coverage</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <h6 class="mb-3"><i class="fas fa-database me-2"></i>About the Analysis</h6>
                        <p>${data.content?.description || 'Datasets are analyzed from the BIDS repository.'}</p>
                        
                        <h6 class="mb-3"><i class="fas fa-star me-2"></i>Top 20 Datasets by High-Confidence Citations</h6>
                        <div class="list-group" style="max-height: 400px; overflow-y: auto;">
                            ${datasetList || '<p class="text-muted">No dataset data available</p>'}
                        </div>
                    `;
        """

    @staticmethod
    def _generate_citations_case() -> str:
        """Generate JavaScript case for citations modal."""
        return """
                    modalTitle.textContent = 'High-Confidence Citations Details';
                    const highConf = data.content?.high_confidence || 0;
                    const lowConf = data.content?.low_confidence || 0;
                    const total = data.content?.total || 0;
                    const percentage = data.content?.percentage || 0;
                    const threshold = data.content?.threshold || 0.4;
                    const qualityRate = data.content?.quality_rate || percentage;
                    const topCitations = data.content?.top_citations || [];
                    
                    // Generate top citations list
                    let citationsList = '';
                    topCitations.forEach(citation => {
                        const title = citation.citation_title || 'Unknown';
                        const authors = citation.citation_author || 'Unknown';
                        const year = citation.citation_year || '';
                        const impact = citation.citation_impact || 0;
                        const confidence = (parseFloat(citation.confidence_score) * 100 || 0).toFixed(1);
                        
                        citationsList += `
                            <div class="mb-3 p-2 border-bottom">
                                <div class="d-flex justify-content-between">
                                    <div class="flex-grow-1">
                                        <a href="https://scholar.google.com/scholar?q=${encodeURIComponent(title)}" 
                                           target="_blank" class="text-primary fw-bold">${title}</a>
                                        <div class="text-muted small">${authors}</div>
                                        <div class="text-muted small">Confidence: ${confidence}%</div>
                                    </div>
                                    <div class="text-end">
                                        <span class="badge bg-info">${impact} citations</span>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    
                    content = `
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <h5><i class="fas fa-chart-line me-2"></i>Citation Statistics</h5>
                                <table class="table">
                                    <tr><td>High-Confidence Citations</td><td class="text-end fw-bold">${highConf}</td></tr>
                                    <tr><td>Confidence Threshold</td><td class="text-end">≥${threshold}</td></tr>
                                    <tr><td>Quality Rate</td><td class="text-end">${qualityRate.toFixed(1)}%</td></tr>
                                </table>
                                
                                <h6 class="mt-3"><i class="fas fa-cog me-2"></i>Confidence Scoring</h6>
                                <p class="small">Citations are scored using sentence-transformer embeddings comparing dataset descriptions with citation abstracts. Only citations with confidence ≥${threshold} are included in analysis.</p>
                            </div>
                            <div class="col-md-6">
                                <h5><i class="fas fa-trophy me-2"></i>Highest Impact Citations</h5>
                                <div style="max-height: 300px; overflow-y: auto;">
                                    ${citationsList || '<p class="text-muted">No citation data available</p>'}
                                </div>
                            </div>
                        </div>
                    `;
        """

    @staticmethod
    def _generate_bridges_case() -> str:
        """Generate JavaScript case for bridge papers modal."""
        return r"""
                    modalTitle.textContent = data.title || 'Research Bridge Papers';
                    const papers = data.content?.top_papers || [];
                    let paperList = '';
                    
                    // Generate list of top 20 bridge papers
                    papers.slice(0, 20).forEach(paper => {
                        const title = paper.bridge_paper_title || 'Unknown Title';
                        const authors = paper.bridge_paper_author || 'Unknown Authors';
                        const year = paper.bridge_paper_year || '';
                        const numDatasets = paper.num_datasets_bridged || 0;
                        const datasets = paper.datasets_bridged ?
                            (Array.isArray(paper.datasets_bridged) ?
                                paper.datasets_bridged.slice(0, 3).join(', ') :
                                paper.datasets_bridged.replace(/[\[\]']/g, '').split(', ').slice(0, 3).join(', '))
                            : '';
                        
                        paperList += `
                            <div class="list-group-item">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div class="flex-grow-1">
                                        <h6 class="mb-1">
                                            <a href="https://scholar.google.com/scholar?q=${encodeURIComponent(title)}" 
                                               target="_blank" class="text-primary">${title}</a>
                                        </h6>
                                        <p class="mb-1 text-muted small">${authors} ${year ? `(${year})` : ''}</p>
                                        <span class="badge bg-secondary">${numDatasets} datasets</span>
                                        ${datasets ? `<div class="text-muted small mt-1">Datasets: ${datasets}</div>` : ''}
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    
                    content = `
                        <h6 class="mb-3"><i class="fas fa-link me-2"></i>What are Bridge Papers?</h6>
                        <p>${data.content?.description || 'Bridge papers cite multiple BIDS datasets.'}</p>
                        
                        <div class="row mb-3 justify-content-center">
                            <div class="col-md-6">
                                <div class="card border-primary">
                                    <div class="card-body text-center">
                                        <h2 class="text-primary">${data.content?.total || 0}</h2>
                                        <p class="mb-0 text-dark">Total Bridge Papers</p>
                                        <small class="text-muted">Papers citing multiple datasets</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <h6><i class="fas fa-list me-2"></i>Top 20 Bridge Papers</h6>
                        <div class="list-group" style="max-height: 400px; overflow-y: auto;">
                            ${paperList || '<p class="text-muted">No bridge paper data available</p>'}
                        </div>
                    `;
        """

    @staticmethod
    def _generate_threshold_case() -> str:
        """Generate JavaScript case for threshold modal."""
        return """
                    modalTitle.textContent = data.title || 'Confidence Threshold Information';
                    const thresholdValue = data.content?.threshold || 0.4;
                    const qualityRate = data.content?.quality_rate || 0;
                    const highQuality = qualityRate.toFixed(1);
                    const lowQuality = (100 - qualityRate).toFixed(1);
                    
                    content = `
                        <div class="row">
                            <div class="col-md-6">
                                <h5><i class="fas fa-brain me-2"></i>Confidence Scoring Method</h5>
                                <div class="card bg-light mb-3">
                                    <div class="card-body">
                                        <h4 class="text-info">≥${thresholdValue} Threshold</h4>
                                        <p>${data.content?.description || 'Citations must have a confidence score of 0.4 or higher to be included in analysis.'}</p>
                                        <ul class="small">
                                            <li><strong>0.7-1.0:</strong> High confidence</li>
                                            <li><strong>0.4-0.7:</strong> Medium confidence</li>
                                            <li><strong>0.0-0.4:</strong> Low confidence (excluded)</li>
                                        </ul>
                                    </div>
                                </div>
                                
                                <h5 class="mt-3"><i class="fas fa-chart-pie me-2"></i>Quality Distribution</h5>
                                <div class="row">
                                    <div class="col-6">
                                        <div class="card bg-success text-white">
                                            <div class="card-body text-center">
                                                <h4>${highQuality}%</h4>
                                                <small>High Quality (≥${thresholdValue})</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="card bg-warning text-white">
                                            <div class="card-body text-center">
                                                <h4>${lowQuality}%</h4>
                                                <small>Low Quality (<${thresholdValue})</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h5><i class="fas fa-microchip me-2"></i>Technical Implementation</h5>
                                <div class="card bg-light mb-3">
                                    <div class="card-body">
                                        <p><strong>Model:</strong> ${data.content?.model || 'Qwen3-Embedding-0.6B'}</p>
                                        <p><strong>Method:</strong> ${data.content?.method || 'Sentence-transformer similarity'}</p>
                                        <p><strong>Comparison:</strong> ${data.content?.comparison || 'Dataset descriptions vs citation abstracts'}</p>
                                        <p><strong>Validation:</strong> ${data.content?.validation || 'Manual review sample'}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="alert alert-info mt-3">
                            <i class="fas fa-info-circle me-2"></i>
                            The ${thresholdValue} threshold was chosen based on empirical validation against manually reviewed citation-dataset pairs,
                            balancing precision and recall for research applications.
                        </div>
                    `;
        """
