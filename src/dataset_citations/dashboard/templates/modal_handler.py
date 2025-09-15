"""
Modal HTML and JavaScript generation for NEMAR dashboard.
"""

from typing import Dict, Any
import json


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
        return f"""
        // Modal data from server
        const modalData = {json.dumps(modals) if modals else "{}"};
        
        // Modal handler
        function showDetailModal(type) {{
            const modal = new bootstrap.Modal(document.getElementById('detailModal'));
            const modalTitle = document.getElementById('detailModalLabel');
            const modalContent = document.getElementById('modalContent');
            
            const data = modalData[type] || {{}};
            let content = '';
            
            switch(type) {{
                case 'datasets':
                    {ModalHandler._generate_datasets_case()}
                    break;
                    
                case 'citations':
                    {ModalHandler._generate_citations_case()}
                    break;
                    
                case 'bridges':
                    {ModalHandler._generate_bridges_case()}
                    break;
                    
                case 'threshold':
                    {ModalHandler._generate_threshold_case()}
                    break;
                    
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
                                <div class="card bg-primary text-white">
                                    <div class="card-body text-center">
                                        <h2>${data.content?.total_datasets || 0}</h2>
                                        <p class="mb-0">Total Datasets</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card bg-success text-white">
                                    <div class="card-body text-center">
                                        <h2>${data.content?.with_citations || 0}</h2>
                                        <p class="mb-0">With Citations</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card bg-info text-white">
                                    <div class="card-body text-center">
                                        <h2>${data.content?.coverage || '100%'}</h2>
                                        <p class="mb-0">Coverage</p>
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
                    modalTitle.textContent = data.title || 'Citation Analysis';
                    const highConf = data.content?.high_confidence || 0;
                    const lowConf = data.content?.low_confidence || 0;
                    const total = data.content?.total || 0;
                    const percentage = data.content?.percentage || 0;
                    const threshold = data.content?.threshold || 0.4;
                    
                    content = `
                        <div class="row mb-4">
                            <div class="col-md-4">
                                <div class="card bg-success text-white">
                                    <div class="card-body text-center">
                                        <h2>${highConf}</h2>
                                        <p class="mb-0">High-Confidence</p>
                                        <small>≥${threshold} score</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card bg-warning text-white">
                                    <div class="card-body text-center">
                                        <h2>${lowConf}</h2>
                                        <p class="mb-0">Low-Confidence</p>
                                        <small><${threshold} score</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card bg-primary text-white">
                                    <div class="card-body text-center">
                                        <h2>${total}</h2>
                                        <p class="mb-0">Total Citations</p>
                                        <small>${percentage}% high-conf</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <h6 class="mb-3"><i class="fas fa-info-circle me-2"></i>Citation Confidence Scoring</h6>
                        <p>Citations are collected from Google Scholar and analyzed using AI-based semantic similarity matching.</p>
                        
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <div class="alert alert-success mb-2">
                                    <strong>High Confidence (≥${threshold}):</strong><br>
                                    Papers that directly reference the dataset with clear mentions in title, abstract, or methods.
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="alert alert-warning mb-2">
                                    <strong>Low Confidence (<${threshold}):</strong><br>
                                    Papers with indirect or unclear references, excluded from primary analysis.
                                </div>
                            </div>
                        </div>
                        
                        <div class="alert alert-info">
                            <i class="fas fa-chart-line me-2"></i>
                            <strong>Coverage Analysis:</strong> ${total} total citations discovered, with ${highConf} (${percentage}%) 
                            meeting the confidence threshold for inclusion in the analysis.
                        </div>
                    `;
        """

    @staticmethod
    def _generate_bridges_case() -> str:
        """Generate JavaScript case for bridge papers modal."""
        return """
                    modalTitle.textContent = data.title || 'Research Bridge Papers';
                    const papers = data.content?.top_papers || [];
                    let paperList = '';
                    
                    // Generate list of top 20 bridge papers
                    papers.slice(0, 20).forEach(paper => {
                        const title = paper.bridge_paper_title || 'Unknown Title';
                        const authors = paper.bridge_paper_author || 'Unknown Authors';
                        const year = paper.bridge_paper_year || '';
                        const numDatasets = paper.num_datasets_bridged || 0;
                        const datasets = paper.datasets_bridged ? paper.datasets_bridged.replace(/[\[\]']/g, '').split(', ').slice(0, 3).join(', ') : '';
                        
                        paperList += `
                            <div class="list-group-item">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div class="flex-grow-1">
                                        <h6 class="mb-1">
                                            <a href="https://scholar.google.com/scholar?q=${encodeURIComponent(title)}" 
                                               target="_blank" class="text-primary">${title}</a>
                                        </h6>
                                        <p class="mb-1 text-muted small">${authors} ${year ? `(${year})` : ''}</p>
                                        <span class="badge bg-info">${numDatasets} datasets</span>
                                        ${datasets ? `<div class="text-muted small mt-1">Datasets: ${datasets}</div>` : ''}
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    
                    content = `
                        <h6 class="mb-3"><i class="fas fa-link me-2"></i>What are Bridge Papers?</h6>
                        <p>${data.content?.description || 'Bridge papers cite multiple BIDS datasets.'}</p>
                        
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <div class="card bg-primary text-white">
                                    <div class="card-body text-center">
                                        <h2>${data.content?.total || 0}</h2>
                                        <p class="mb-0">Total Bridge Papers</p>
                                        <small>Citing multiple datasets</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card bg-info text-white">
                                    <div class="card-body text-center">
                                        <h2>${papers.length || 0}</h2>
                                        <p class="mb-0">High-Impact Papers</p>
                                        <small>Top papers by dataset count</small>
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
                    content = `
                        <div class="row">
                            <div class="col-md-6">
                                <h6><i class="fas fa-brain me-2"></i>Confidence Scoring Method</h6>
                                <div class="card bg-light mb-3">
                                    <div class="card-body">
                                        <h4 class="text-info">≥${data.content?.threshold || 0.4} Threshold</h4>
                                        <p>${data.content?.description || 'Citations are scored using AI-based relevance matching.'}</p>
                                        <ul class="small">
                                            <li><strong>0.7-1.0:</strong> High confidence - Clear dataset reference</li>
                                            <li><strong>0.4-0.7:</strong> Medium confidence - Likely reference</li>
                                            <li><strong>0.0-0.4:</strong> Low confidence - Excluded from analysis</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h6><i class="fas fa-robot me-2"></i>AI Model Details</h6>
                                <div class="card bg-light mb-3">
                                    <div class="card-body">
                                        <p><strong>Model:</strong> Sentence-BERT</p>
                                        <p><strong>Method:</strong> Semantic similarity matching</p>
                                        <p><strong>Input:</strong> Citation text + dataset metadata</p>
                                        <p><strong>Output:</strong> Confidence score (0-1)</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>Why ${data.content?.threshold || 0.4}?</strong> This threshold balances precision and recall, 
                            ensuring we capture relevant citations while filtering out noise.
                        </div>
                    `;
        """
