from base64 import b64decode

from app.data_processing import DataProcessor


def test_data_processor_generates_visualizations():
    records = [
        {"value": 10, "category": "A", "timestamp": "2024-01-01"},
        {"value": 20, "category": "B", "timestamp": "2024-01-02"},
        {"value": 15, "category": "A", "timestamp": "2024-01-03"},
        {"value": 30, "category": "C", "timestamp": "2024-01-04"},
        {"value": 25, "category": "B", "timestamp": "2024-01-05"},
    ]

    summary = DataProcessor().process(records)

    assert summary.visualizations, "Expected at least one visualization artifact"
    chart_types = {artifact.chart_type for artifact in summary.visualizations}
    assert "histogram" in chart_types
    assert any(artifact.column == "category" for artifact in summary.visualizations)
    assert any(artifact.column == "timestamp" for artifact in summary.visualizations)

    for artifact in summary.visualizations:
        decoded = b64decode(artifact.image_base64)
        assert decoded.startswith(b"\x89PNG"), "Visualization should be a PNG image"
