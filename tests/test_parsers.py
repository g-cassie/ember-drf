from ember_drf.parsers import ActiveModelJSONParser, EmberJSONParser
from django.utils.six.moves import StringIO


def test_active_model_parser():
    stream = StringIO('{"child": {"parent_id": 1, "child_ids": [1, 2, 3], '
                      '"text_attribute": "something_id"}}')
    expected = {'child': {'parent': 1, 'children': [1, 2, 3],
                'text_attribute': 'something_id'}}
    assert ActiveModelJSONParser().parse(stream) == expected

def test_ember_json_parser():
    stream = StringIO('{"childObject": {"parent": 1, "childIds": [1, 2, 3], '
                      '"textAttribute": "something_id"}}')
    expected = {'child_object': {'parent': 1, 'child_ids': [1, 2, 3],
                'text_attribute': 'something_id'}}
    assert EmberJSONParser().parse(stream) == expected
