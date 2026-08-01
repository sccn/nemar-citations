"""Hero section component."""

from typing import Any


def generate_hero_section(cards: list[dict[str, Any]]) -> str:
    """Generate hero section with statistics cards."""

    stat_cards_html = ""
    for card in cards:
        detail_text = (
            card["detail"].replace("*", "") if "*" in card["detail"] else card["detail"]
        )
        has_asterisk = "*" in card["detail"]

        stat_cards_html += f"""
                        <div class="col-md-3">
                            <div class="card stat-card" onclick="showDetailModal('{card["id"]}')" 
                                 title="Click for details">
                                <div class="card-body text-center">
                                    <h3><i class="{card["icon"]} me-2"></i>{card["value"]}</h3>
                                    <p class="mb-0">{card["label"]}</p>
                                    <small class="text-muted">{"*" if has_asterisk else ""}{detail_text}</small>
                                </div>
                            </div>
                        </div>"""

    datasets_count = cards[0]["value"] if cards else 302

    return f"""
    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <div class="jumbotron bg-light p-5 rounded">
                    <h1 class="display-4">
                        <i class="fas fa-chart-network me-3"></i>
                        NEMAR Dataset Citation Analysis
                    </h1>
                    <p class="lead">
                        Comprehensive analysis of citation patterns, research themes, and network relationships 
                        across {datasets_count} BIDS datasets on NEMAR with confidence-filtered citations.
                    </p>
                    <hr class="my-4">
                    <div class="row">
                        {stat_cards_html}
                    </div>
                </div>
            </div>
        </div>
    </div>"""
