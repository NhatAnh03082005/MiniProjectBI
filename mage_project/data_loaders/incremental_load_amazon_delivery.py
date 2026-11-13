if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader

from mage_project.amazon_delivery_loader import load_amazon_delivery


@data_loader
def incremental_load_amazon_delivery(*args, **kwargs):
    """Read one source file and create a dynamic incremental batch context."""
    return load_amazon_delivery('INCREMENTAL', kwargs)
