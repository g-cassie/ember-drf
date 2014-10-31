from inflection import camelize

from rest_framework.relations import PrimaryKeyRelatedField, ManyRelation
from rest_framework.renderers import JSONRenderer
from rest_framework.serializers import ListSerializer

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
    try:
        serializer = data.serializer
    except AttributeError:
        raise ValueError(
            'ActiveModelJSONRender requires a '
            '`rest_framework.serializers.ReturnDict` instance with the '
            '`serializer` attribute set.')
    if isinstance(serializer, (SideloadSerializer, SideloadListSerializer)):
        new_dict = {}
        for key, value in data.items():
            new_dict[key] = convert_related_keys(value)
        return new_dict
    elif isinstance(serializer, (ListSerializer)):
        return [convert_related_keys(i) for i in data]

    # when a normal serializer is reached we rename each related key
    for field in serializer.fields.values():
        if isinstance(field, (PrimaryKeyRelatedField)):
            name = field.field_name
            data[name + '_id'] = data[name]
            del data[name]
        elif (isinstance(field, ListSerializer) and \
                isinstance(field.child, PrimaryKeyRelatedField)) or \
                isinstance(field, ManyRelation):
            name = field.field_name
            data[name + '_ids'] = data[name]
            del data[name]
    return data


class EmberJSONRenderer(JSONRenderer):
    """Render string compatible with Ember Data's JSONSerializer."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """Convert underscores to camel case."""
        data = convert_to_camel_case(data)
        return super(EmberJSONRenderer, self).render(
            data, accepted_media_type, renderer_context)


class ActiveModelJSONRenderer(JSONRenderer):
    """
    Render string compatible with Ember Data's ActiveModelSerializer.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = convert_related_keys(data)
        return super(ActiveModelJSONRenderer, self).render(
            data, accepted_media_type, renderer_context)
