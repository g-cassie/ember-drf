from inflection import camelize, singularize

from rest_framework.relations import PrimaryKeyRelatedField, ManyRelation
from rest_framework.renderers import JSONRenderer
from rest_framework.serializers import ListSerializer, ModelSerializer, Serializer

from drf_ember.serializers import SideloadListSerializer, SideloadSerializer

def convert_to_camel_case(data):
    """Convert all dictionary keys to camel case."""
    if isinstance(data, dict):
        camel_dict = {}
        for key, value in data.items():
            camel_dict[camelize(key, False)] = convert_to_camel_case(value)
        return camel_dict
    if isinstance(data, (list, tuple)):
        return [convert_to_camel_case(i) for i in data]
    return data

def convert_related_keys(data):
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
                if hasattr(data, name):
                    data[name + '_id'] = data[name]
                    del data[name]
            elif (isinstance(field, ListSerializer) and \
                    isinstance(field.child, PrimaryKeyRelatedField)) or \
                    isinstance(field, ManyRelation):
                name = field.field_name
                if hasattr(data, name):
                    data[singularize(name) + '_ids'] = data[name]
                    del data[name]
        return data
    else:
        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                new_dict[key] = convert_related_keys(value)
            return new_dict
        elif isinstance(data, list):
            return [convert_related_keys(i) for i in data]


class EmberJSONRenderer(JSONRenderer):
    """Render string compatible with Ember Data's JSONSerializer."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """Convert underscores to camel case."""
        data = convert_to_camel_case(data)
        return super(EmberJSONRenderer, self).render(
            data, accepted_media_type, renderer_context)


class ActiveModelJSONRenderer(JSONRenderer):
    """Render string compatible with Ember Data's ActiveModelSerializer."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = convert_related_keys(data)
        return super(ActiveModelJSONRenderer, self).render(
            data, accepted_media_type, renderer_context)
