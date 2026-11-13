if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

from mage_project.amazon_delivery_contract import validate_and_prepare


@transformer
def validate_full_amazon_delivery(payload, *args, **kwargs):
    """Apply the same technical contract used by incremental loads."""
    return validate_and_prepare(payload)
