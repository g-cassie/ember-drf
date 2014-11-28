from collections import namedtuple
from inflection import camelize, singularize, pluralize, underscore

from rest_framework.relations import PrimaryKeyRelatedField, ManyRelatedField
from rest_framework.serializers import ListSerializer
from rest_framework.utils.serializer_helpers import BoundField

from ember_drf.serializers import SideloadListSerializer, SideloadSerializer

def convert_to_ember_json(data):
    """Convert all dictionary keys to camel case."""
    if isinstance(data, dict):
        camel_dict = {}
        for key, value in data.items():
            camel_dict[camelize(key, False)] = convert_to_ember_json(value)
        return camel_dict
    if isinstance(data, (list, tuple)):
        return [convert_to_ember_json(i) for i in data]
    return data

def convert_from_ember_json(data):
    """Convert all dictionary keys to snake_case."""
    if isinstance(data, dict):
        snake_dict = {}
        for key, value in data.items():
            snake_dict[underscore(key)] = convert_from_ember_json(value)
        return snake_dict
    if isinstance(data, (list, tuple)):
        return [convert_from_ember_json(i) for i in data]
    return data

RelatedFieldRename = namedtuple('RelatedFieldRename', ['index', 'new_name'])

def find_related_fields_to_rename(fields, prefix=[]):
    """
    Find all related fields on a Serializer or NestedBoundField.
    Args:
        fields: an object whose `.__iter__()` method returns instances of
            `BoundField` (e.g. a `Serializer` or `NestedBoundField`)
        prefix: a list of parent keys that map to the current list of
            fields.  (e.g. `{'one': {'two': {'three': 'value'}}}` will have
                `prefix=['one', 'two'] when `{'three': 'value'})` is passed
                into the function.
    Returns:
        list: list of RelatedFieldRename instances.
    """
    ret = []
    if isinstance(fields, ListSerializer):
        fields = fields.child.__class__()

    # this is selfish hack to support something I am doing
    # hopefully I can factor this out soon
    if isinstance(fields, BoundField):
        fields = fields._field

    # iterate over each field to determine if it is related
    for field in fields:
        assert isinstance(field, BoundField), (
            'Fields must be an iterator that returns `BoundField` instances.'
        )
        key = prefix + field.name.split('.')
        # iterate over any nested lists
        if field._proxy_class is ListSerializer:
            ret.extend(
                find_related_fields_to_rename(field.child, prefix=key)
            )
        # any nested dicts should be iterated over
        # this could check if `field` is an instance of `NestedBoundField`
        # but that would break my hack above
        elif hasattr(field, 'fields'):
            ret.extend(find_related_fields_to_rename(field, prefix=key))
        # the field is a list of pks and should be renamed
        elif field._proxy_class is ManyRelatedField:
            new_name = singularize(key[-1]) + '_ids'
            ret.append(RelatedFieldRename(key, new_name))
        # the field is a single pk and should be renamed
        elif field._proxy_class is PrimaryKeyRelatedField:
            new_name = key[-1] + '_id'
            ret.append(RelatedFieldRename(key, new_name))
    return ret

def rename_related_fields(data, fields):
    """
    Rename related fields to ActiveModel json style.

    Args:
        data (dict or list): object to be traversed and renamed.
        fields (list): list of `RelatedFieldRename` instances.
    Returns:
        dict or list: with all related keys in `fields` renamed as specified.
    """

    root_fields = [(f.index[0], f.new_name) for f in fields if len(f.index) == 1]
    nested_fields = [f for f in fields if len(f.index) > 1]

    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            found_match = False

            # check if any immediate children fields are related fields
            for field, new_name in root_fields:
                if key == field:
                    new_dict[new_name] = value
                    found_match = True
                    break
            if found_match:
                continue

            # check if any nested fields contain related fields
            for field in nested_fields:
                if key == field.index[0]:
                    new_fields = [
                        RelatedFieldRename(field.index[1:], field.new_name)
                        for field in nested_fields
                    ]
                    new_dict[key] = rename_related_fields(value, new_fields)
                    found_match = True
                    break

            # copy the existing key/value pair for non related fields
            if not found_match:
                new_dict[key] = value
        return new_dict
    elif isinstance(data, list):
        return [rename_related_fields(i, fields) for i in data]

def convert_to_active_model_json(data):
    try:
        serializer = data.serializer
    except AttributeError:
        # do nothing if we are not given a ReturnDict with `.serializer` set.
        return data
    related_fields = []
    if isinstance(serializer, (SideloadSerializer, SideloadListSerializer)):
        for key, value in data.items():
            assert hasattr(value, 'serializer'), (
                'Each root key must nest a `ReturnDict` or `ReturnList` with '
                '`.serializer` set.'
            )
            related_fields.extend(
                find_related_fields_to_rename(value.serializer, prefix=[key])
            )
    return rename_related_fields(data, related_fields)

def remove_id_suffixes(string):
    if string[-3:] == '_id':
        return string[:-3]
    elif string[-4:] == '_ids':
        return pluralize(string[:-4])
    return string

def convert_from_active_model_json(data):
    if isinstance(data, list):
        return [convert_from_active_model_json(item) for item in data]
    elif isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            new_dict[remove_id_suffixes(key)] = \
                convert_from_active_model_json(value)
        return new_dict
    return data
