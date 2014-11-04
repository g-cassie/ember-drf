from rest_framework.parsers import JSONParser

from ember_drf.utils import (
    convert_from_ember_json, convert_from_active_model_json
)


class ActiveModelJSONParser(JSONParser):
    """Parse strings output by Ember Data's ActiveModelSerializer."""

    def parse(self, stream, media_type=None, renderer_context=None):
        obj = super(ActiveModelJSONParser, self).parse(
            stream, media_type, renderer_context)
        return convert_from_active_model_json(obj)


class EmberJSONParser(JSONParser):
    """Parse strings output by Ember Data's JSONSerializer."""

    def parse(self, stream, media_type=None, renderer_context=None):
        obj = super(EmberJSONParser, self).parse(
            stream, media_type, renderer_context)
        return convert_from_ember_json(obj)
