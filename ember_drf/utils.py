from inflection import camelize, singularize, pluralize, underscore

from rest_framework.relations import PrimaryKeyRelatedField, ManyRelatedField, RelatedField
from rest_framework.serializers import ListSerializer
from rest_framework.utils.serializer_helpers import NestedBoundField, BoundField

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

def find_related_fields(fields, prefix=None):
    ret = []
    if isinstance(fields, ListSerializer):
        fields = fields.child.__class__()

    for field in fields:
        assert isinstance(field, BoundField), field
        if field._proxy_class is ManyRelatedField:
            key = [prefix] + field.name.split('.')
            convert = singularize(key[-1]) + '_ids'
            ret.append(([prefix] + field.name.split('.'), convert))
        elif field._proxy_class is PrimaryKeyRelatedField:
            key = [prefix] + field.name.split('.')
            convert = key[-1] + '_id'
            ret.append(([prefix] + field.name.split('.'), convert))

        if isinstance(field, NestedBoundField):
            ret.extend(find_related_fields(field, prefix=prefix))
    return ret

def rename_related_fields(data, fields):
    root_fields = [(f[0][0], f[1]) for f in fields if len(f[0]) == 1]
    nest_fields = [f for f in fields if len(f[0]) > 1]


    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            found_match = False
            for field, convert in root_fields:
                if key == field:
                    new_dict[convert] = value
                    found_match = True
                    break
            if found_match:
                continue
            for field in nest_fields:
                if key == field[0][0]:
                    new_fields = [(field[0][1:], field[1]) for field in nest_fields]
                    new_dict[key] = rename_related_fields(value, new_fields)
                    found_match = True
                    break
            if not found_match:
                new_dict[key] = value
        return new_dict
    elif isinstance(data, list):
        return [rename_related_fields(i, fields) for i in data]

def convert_to_active_model_json(data):
    try:
        serializer = data.serializer
    except AttributeError:
        return data
    related_fields = []
    if isinstance(serializer, (SideloadSerializer, SideloadListSerializer)):
        for key, value in data.items():
            assert hasattr(value, 'serializer'), (
                'Each root key must nest a `ReturnDict` or `ReturnList` with '
                '`.serializer` set.'
            )
            related_fields.extend(find_related_fields(value.serializer, prefix=key))
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
