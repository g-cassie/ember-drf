from inflection import camelize
from rest_framework.renderers import JSONRenderer


def convert_to_camel_case(data):
    if isinstance(data, dict):
        camel_dict = {}
        for key, value in data.items():
            camel_dict[camelize(key, False)] = convert_to_camel_case(value)
        return camel_dict
    if isinstance(data, (list, tuple)):
        return [convert_to_camel_case(i) for i in data]
    return data


class EmberJSONRenderer(JSONRenderer):
    """
    Convert underscores to camelcase.
    """
    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = convert_to_camel_case(data)
        return super(EmberJSONRenderer, self).render(
            data, accepted_media_type, renderer_context)
