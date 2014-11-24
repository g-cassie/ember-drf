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
        fields = fields.child
    for field in fields:
        assert isinstance(field, BoundField), field
        if field._proxy_class is ManyRelatedField:
            key = [prefix] + field.name.split('.')
            convert = singularize(key[-1]) + '_ids'
            ret.append(([prefix] + field.name.split('.'), convert))
        elif field._proxy_class is RelatedField:
            key = [prefix] + field.name.split('.')
            convert = key + '_id'
            ret.append(([prefix] + field.name.split('.'), convert))
        if isinstance(field, NestedBoundField):
            ret.extend(find_related_fields(field, prefix=prefix))
    return ret

def rename_related_fields(data, fields, parents=[]):
    root_fields = [(f[0][0], f[1]) for f in fields if len(f[0]) == 1]
    nest_fields = [f for f in fields if len(f[0]) > 1]

    print 'fields'
    print fields
    print 'root fields'
    print root_fields
    print 'nest_fields'
    print nest_fields

    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            found_match = False
            for field, convert in root_fields:
                print 'Checking:'
                print key
                print field
                if key == field:
                    new_dict[convert] = value
                    found_match = True
                    break
            if found_match:
                continue
            for field in nest_fields:
                if key == field[0][0]:
                    new_fields = [(field[0][1:], field[1]) for field in nest_fields]
                    print 'Shortening Fields'
                    print fields
                    print new_fields
                    new_dict[key] = rename_related_fields(value, new_fields)
                    found_match = True
                    break
            if not found_match:
                new_dict[key] = value
        return new_dict
    elif isinstance(data, list):
        return [rename_related_fields(i, fields, parents=parents) for i in data]


def convert_to_active_model_json(data):
    try:
        serializer = data.serializer
    except:
        raise ValueError(
            'You must pass in a ReturnDict or ReturnList with `.serializer`'
            'set.'
        )
    related_fields = []
    if isinstance(serializer, (SideloadSerializer, SideloadListSerializer)):
        for key, value in data.items():
            assert hasattr(value, 'serializer'), (
                'Each root key must nest a `ReturnDict` or `ReturnList` with '
                '`.serializer` set.'
            )
            related_fields.extend(find_related_fields(value.serializer, prefix=key))
    return rename_related_fields(data, related_fields)


# def convert_to_active_model_json(data, serializer=None):
#     """Convert all related keys to ActiveModelJSONSerializer format."""
#     # Standard usage should result in all viewset methods returning a
#     # `ReturnDict` or `ReturnList` object which has a serializer property.
#     # Some custom API endpoints will return a normal python list or dictionary.
#     if not serializer:
#         try:
#             serializer = data.serializer
#         except AttributeError:
#             serializer = None
#     print data.__class__
#     # If we have reached a normal DRF serializer then we iterate over the
#     # keys and format them ActiveModel style.
#     if serializer and isinstance(serializer, ListSerializer):
#         child = serializer.child
#         if hasattr(child, 'base_serializer'):
#             child = child.base_serializer
#         return [convert_to_active_model_json(i, serializer=child) for i in data]

#     elif serializer and not isinstance(serializer,
#             (SideloadSerializer, SideloadListSerializer)):
#         # when a normal serializer is reached we rename each related key
#         for field in [f for f in serializer.fields.values() if f.field_name in \
#                       data]:
#             name = field.field_name

#             print name
#             print field.__class__
#             print data[name].__class__

#             # convert belongs to id field
#             if isinstance(field, PrimaryKeyRelatedField):
#                 data[name + '_id'] = data[name]
#                 del data[name]

#             # convert has many id field
#             elif isinstance(field, (ListSerializer, ManyRelatedField)) \
#                     and any([isinstance(getattr(field, f , None), \
#                     PrimaryKeyRelatedField) for f in \
#                     ['child', 'child_relation']]):
#                 data[singularize(name) + '_ids'] = data[name]
#                 del data[name]

#             # convert embedded records
#             elif hasattr(data[name], 'serializer'):
#                 convert_to_active_model_json(data[name])
#         return data
#     else:
#         if isinstance(data, dict):
#             new_dict = {}
#             for key, value in data.items():
#                 new_dict[key] = convert_to_active_model_json(value)
#             return new_dict
#         elif isinstance(data, list):
#             return [convert_to_active_model_json(i) for i in data]

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
