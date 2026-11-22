if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

from mage_project.amazon_delivery_contract import validate_and_prepare


@transformer
def validate_incremental_amazon_delivery(payload, *args, **kwargs):
    """Validate technical rules and compute raw hashes for an incremental run."""
    from etl_monitoring import runtime
    if runtime.enabled():
        ctx = runtime.context(payload['monitoring_context'])
        try:
            runtime.start_step(ctx, 'validate', 'MAGE')
            return runtime.validation_completed(payload, validate_and_prepare(payload))
        except Exception as error:
            runtime.fail(ctx, 'validate', error)
            raise
    return validate_and_prepare(payload)
