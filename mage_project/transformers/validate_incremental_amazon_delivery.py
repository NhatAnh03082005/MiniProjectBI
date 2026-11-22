if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

from mage_project.amazon_delivery_contract import validate_and_prepare


@transformer
def validate_incremental_amazon_delivery(payload, *args, **kwargs):
    """Validate technical rules and compute raw hashes for an incremental run."""
    from etl_monitoring import runtime
    if runtime.enabled():
        runtime.start_step(runtime.context(payload['monitoring_context']), 'validate', 'MAGE')
        return runtime.validation_completed(payload, validate_and_prepare(payload))
    return validate_and_prepare(payload)
