from rest_framework.renderers import JSONRenderer

from ember_drf.utils import (
    convert_to_active_model_json, convert_to_ember_json
)


class EmberJSONRenderer(JSONRenderer):
    """Render string compatible with Ember Data's JSONSerializer."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """Convert underscores to camel case."""
        data = convert_to_ember_json(data)
        return super(EmberJSONRenderer, self).render(
            data, accepted_media_type, renderer_context)


class ActiveModelJSONRenderer(JSONRenderer):
    """Render string compatible with Ember Data's ActiveModelSerializer."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = convert_to_active_model_json(data)
        return super(ActiveModelJSONRenderer, self).render(
            data, accepted_media_type, renderer_context)
