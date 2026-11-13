if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader

from mage_project.amazon_delivery_loader import load_amazon_delivery


@data_loader
def full_load_amazon_delivery(*args, **kwargs):
    """Read one source file and create a dynamic full-load batch context."""
    return load_amazon_delivery('FULL_LOAD', kwargs)
