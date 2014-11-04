from inflection import camelize, singularize, pluralize, underscore

from rest_framework.relations import PrimaryKeyRelatedField, ManyRelation
from rest_framework.serializers import ListSerializer

from drf_ember.serializers import SideloadListSerializer, SideloadSerializer

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


def convert_to_active_model_json(data):
    """Convert all relat keys to ActiveModelJSONSerializer format."""
    # Standard usage should result in all viewset methods returning a
    # `ReturnDict` or `ReturnList` object which has a serializer property.
    # Some custom API endpoitns will return a normal python list or dictionary.
    try:
        serializer = data.serializer
    except AttributeError:
        serializer = None

    # If we have reached a normal DRF serializer then we iterate over the
    # keys and format them ActiveModel style.
    if serializer and not isinstance(serializer,
            (SideloadSerializer, SideloadListSerializer, ListSerializer)):
        # when a normal serializer is reached we rename each related key
        for field in serializer.fields.values():
            if isinstance(field, (PrimaryKeyRelatedField)):
                name = field.field_name
                if name in data:
                    data[name + '_id'] = data[name]
                    del data[name]
            elif (isinstance(field, ListSerializer) and \
                    isinstance(field.child, PrimaryKeyRelatedField)) or \
                    isinstance(field, ManyRelation):
                name = field.field_name
                if name in data:
                    data[singularize(name) + '_ids'] = data[name]
                    del data[name]
        return data
    else:
        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                new_dict[key] = convert_to_active_model_json(value)
            return new_dict
        elif isinstance(data, list):
            return [convert_to_active_model_json(i) for i in data]

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
