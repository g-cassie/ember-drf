from rest_framework.parsers import JSONParser

from inflection import pluralize, underscore

def remove_id_suffixes(string):
    print string
    if string[-3:] == '_id':
        return string[:-3]
    elif string[-4:] == '_ids':
        return pluralize(string[:-4])
    return string

def normalize_active_model_json(data):
    if isinstance(data, list):
        return [normalize_active_model_json(item) for item in data]
    elif isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            new_dict[remove_id_suffixes(key)] = normalize_active_model_json(value)
        return new_dict
    return data

def convert_to_snake_case(data):
    """Convert all dictionary keys to snake_case."""
    if isinstance(data, dict):
        snake_dict = {}
        for key, value in data.items():
            snake_dict[underscore(key)] = convert_to_snake_case(value)
        return snake_dict
    if isinstance(data, (list, tuple)):
        return [convert_to_snake_case(i) for i in data]
    return data


class ActiveModelJSONParser(JSONParser):
    """Parse strings output by Ember Data's ActiveModelSerializer."""

    def parse(self, stream, media_type=None, renderer_context=None):
        obj = super(ActiveModelJSONParser, self).parse(
            stream, media_type, renderer_context)
        return normalize_active_model_json(obj)


class EmberJSONParser(JSONParser):
    """Parse strings output by Ember Data's JSONSerializer."""

    def parse(self, stream, media_type=None, renderer_context=None):
        obj = super(EmberJSONParser, self).parse(
            stream, media_type, renderer_context)
        return convert_to_snake_case(obj)
