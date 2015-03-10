"""
This module provides support for backwards compatibility with older
versions of django-rest-framework.
"""


def get_related_model(relation_info):
    """`RelationInfo.related_model` was called `RelationInfo.related`
    prior to DRF 3.1.
    """
    try:
        return relation_info.related_model
    except AttributeError:
        return relation_info.related
