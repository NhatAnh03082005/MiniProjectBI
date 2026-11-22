if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

from mage_project.amazon_delivery_dbt import run_dbt_after_verification


@custom
def build_amazon_delivery_dds(verified, *args, **kwargs):
    """Final block: dbt build + DDS reconciliation; errors fail the Mage run."""
    return run_dbt_after_verification(verified)
