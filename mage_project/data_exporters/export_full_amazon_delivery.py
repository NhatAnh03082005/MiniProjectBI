if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

from mage_project.amazon_delivery_repository import assert_export_output, export_amazon_delivery


@data_exporter
def export_full_amazon_delivery(payload, *args, **kwargs):
    """Populate or reconcile current-state staging through the shared upsert."""
    return export_amazon_delivery(payload)


@test
def test_output(output, *args):
    assert_export_output(output)
