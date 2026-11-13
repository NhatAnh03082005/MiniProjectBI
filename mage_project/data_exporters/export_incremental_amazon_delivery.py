if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

from mage_project.amazon_delivery_repository import assert_export_output, export_amazon_delivery


@data_exporter
def export_incremental_amazon_delivery(payload, *args, **kwargs):
    """Upsert current-state staging by Order_ID and raw row hash."""
    return export_amazon_delivery(payload)


@test
def test_output(output, *args):
    assert_export_output(output)
