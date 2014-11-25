import json

from django.test import TestCase

from rest_framework.compat import OrderedDict
from rest_framework.renderers import JSONRenderer
from rest_framework.serializers import ReturnDict

from ember_drf.renderers import EmberJSONRenderer, convert_to_active_model_json

from tests.serializers import (
    ChildSideloadSerializer, NestedChildSideloadSerializer,
    NestedParentSideloadSerializer, DeepNestedParentSideloadSerializer
)
from tests.models import ChildModel, ParentModel

class RendererTests(TestCase):

    def test_ember_json_renderer(self):
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

    def test_convert_related_keys_single(self):
        parent = ParentModel.objects.create()
        old_parent = ParentModel.objects.create()
        child = ChildModel.objects.create(parent=parent, old_parent=old_parent)
        obj = ChildSideloadSerializer(instance=child).data
        expected = {
            'child_model': OrderedDict([
                ('id', child.id,),
                ('parent_id', parent.id,),
                ('old_parent_id', old_parent.id)
            ]),
            'parent_models': [
                OrderedDict([('id', p.id), ('text', p.text), ('child_ids', p.child_ids),
                ('old_child_ids', p.old_child_ids)])
                for p in [parent, old_parent]
            ]
        }
        result = convert_to_active_model_json(obj)
        assert result == expected

    def test_convert_related_keys_on_nested_list(self):
        p = ParentModel.objects.create()
        c1 = ChildModel.objects.create(parent=p, old_parent=p)
        c2 = ChildModel.objects.create(parent=p, old_parent=p)
        serializer = NestedParentSideloadSerializer(instance=p)
        expected_children = [
            {'id': c.id, 'parent_id': c.parent.id,
            'old_parent_id': c.old_parent.id} for c in [c1, c2]
        ]
        expected = {
            'parent_model': {
                'id': p.id,
                'text': p.text,
                'children': expected_children,
                'old_children': expected_children
            }
        }
        data = serializer.data
        result = convert_to_active_model_json(data)
        assert result == expected

    def test_convert_related_keys_on_nested_dict(self):
        p = ParentModel.objects.create()
        c1 = ChildModel.objects.create(parent=p, old_parent=p)
        c2 = ChildModel.objects.create(parent=p, old_parent=p)
        serializer = DeepNestedParentSideloadSerializer(instance=p)
        nested_parent = {
            'id': p.id, 'text': p.text, 'child_ids': p.child_ids,
            'old_child_ids': p.old_child_ids
        }
        expected_children = [
            {'id': c.id, 'parent': nested_parent,
            'old_parent': nested_parent} for c in [c1, c2]
        ]
        expected = {
            'parent_model': {
                'id': p.id,
                'text': p.text,
                'children': expected_children,
                'old_children': expected_children
            }
        }
        data = serializer.data
        result = convert_to_active_model_json(data)
        assert result == expected

    def test_convert_nested_related_keys(self):
        p = ParentModel.objects.create()
        c = ChildModel.objects.create(parent=p, old_parent=p)
        serializer = NestedChildSideloadSerializer(c)
        expected_parent = {
            'id': p.id, 'text': p.text, 'child_ids': p.child_ids,
            'old_child_ids': p.old_child_ids
        }
        expected = {
            'child_model': {
                'id': c.id,
                'parent': expected_parent,
                'old_parent': expected_parent
            },
        }
        result = convert_to_active_model_json(serializer.data)
        assert result == expected

    def test_active_model_json_renderer(self):
        parents = [ParentModel.objects.create() for x in range(3)]
        children = [
            ChildModel.objects.create(parent=parents[1], old_parent=parents[2]),
            ChildModel.objects.create(parent=parents[1], old_parent=parents[2]),
            ChildModel.objects.create(parent=parents[0], old_parent=parents[1])
        ]
        obj = ChildSideloadSerializer(children, many=True).data
        expected = {
            'child_models': [
                OrderedDict([('id', c.id), ('parent_id', c.parent.id),
                ('old_parent_id', c.old_parent.id)]) for c in children
            ],
            'parent_models': [
                OrderedDict([('id', p.id), ('text', p.text),
                ('child_ids', p.child_ids), ('old_child_ids', p.old_child_ids)])
                for p in parents
            ]

        }
        result = convert_to_active_model_json(obj)
        assert result == expected
