from ember_drf.renderers import EmberJSONRenderer
from rest_framework.renderers import JSONRenderer

def test_ember_json_renderer():
    obj = {
        'under_score': [
            {'nested_underscore': 'some_thing'},
            {'nested_underscore': 'some_thing'},
            {'nested_underscore': 'some_thing'},
        ]
    }
    expected = {
        'underScore': [
            {'nestedUnderscore': 'some_thing'},
            {'nestedUnderscore': 'some_thing'},
            {'nestedUnderscore': 'some_thing'},
        ]
    }
    assert EmberJSONRenderer().render(obj) == \
        JSONRenderer().render(expected)
