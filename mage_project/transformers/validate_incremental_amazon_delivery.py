if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

from mage_project.amazon_delivery_contract import validate_and_prepare


@transformer
def validate_incremental_amazon_delivery(payload, *args, **kwargs):
    """Validate technical rules and compute raw hashes for an incremental run."""
    return validate_and_prepare(payload)
