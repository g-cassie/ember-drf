from django.test import TestCase

from drf_ember.serializers import SideloadListSerializer

from tests.models import ChildModel, ParentModel, OptionalChildModel, \
    OneToOne, ReverseOneToOne
from tests.serializers import ChildSideloadSerializer, \
    OptionalChildSideloadSerializer, OneToOneSideloadSerializer, \
    ReverseOneToOneSideloadSerializer


class TestSideloadSerializer(TestCase):

    def setUp(self):
        self.parent = ParentModel.objects.create()
        self.old_parent = ParentModel.objects.create()
        self.child = ChildModel.objects.create(
            parent=self.parent, old_parent=self.old_parent)

    def test_get_sideload_ids(self):
        result = ChildSideloadSerializer().get_sideload_ids(self.child)
        expected = set([self.parent.id, self.old_parent.id])
        self.assertEqual(len(result), 1)
        self.assertEqual(result['parent_models'], expected)

    def test_get_sideload_objects(self):
        result = ChildSideloadSerializer().get_sideload_objects(self.child)
        expected = [
           {'id': p.id, 'text': p.text, 'children': p.child_ids,
            'old_children': p.old_child_ids}
            for p in ParentModel.objects.all()]
        self.assertEqual(len(result), 1)
        self.assertEqual(result['parent_models'], expected)

    def test_many_creates_list(self):
        result = ChildSideloadSerializer(many=True)
        self.assertTrue(isinstance(result, SideloadListSerializer))

    def test_serialization(self):
        with self.assertNumQueries(3):
            result = ChildSideloadSerializer(self.child).data
        expected = {
            'child_model': {
                'id': self.child.pk,
                'parent': self.parent.pk,
                'old_parent': self.old_parent.pk
            },
            'parent_models': [
                {'id': self.parent.pk, 'text': self.parent.text,
                 'children': [self.child.pk], 'old_children': []},
                {'id': self.old_parent.pk, 'text': self.old_parent.text,
                 'children': [], 'old_children': [self.child.pk]}
            ]
        }
        self.assertEqual(result, expected)

    def test_optional_foreign_key_serialization(self):
        child = OptionalChildModel.objects.create()
        result = OptionalChildSideloadSerializer(child).data
        expected = {
            'optional_child_model': {'id': child.pk, 'parent': None},
            'parent_models': []
        }
        self.assertEqual(result, expected)

    def test_one_to_one_field(self):
        reverse = ReverseOneToOne.objects.create()
        one = OneToOne.objects.create(reverse_one_to_one=reverse)
        result = OneToOneSideloadSerializer(one).data
        expected = {
            'one_to_one': {'id': one.pk, 'reverse_one_to_one': reverse.pk},
            'reverse_one_to_ones': [{'id': reverse.pk, 'one_to_one': one.pk}]
        }
        self.assertEqual(result, expected)

    def test_reverse_one_to_one_blank_field(self):
        reverse = ReverseOneToOne.objects.create()
        result = ReverseOneToOneSideloadSerializer(reverse).data
        expected = {
            'reverse_one_to_one': {'id': reverse.pk, 'one_to_one': None},
            'one_to_ones': []
        }
        self.assertEqual(result, expected)

class TestSideloadListSerailizer(TestCase):

    def setUp(self):
        self.parents = [ParentModel.objects.create() for x in range(3)]
        self.children = [
            ChildModel.objects.create(parent=self.parents[1], old_parent=self.parents[2]),
            ChildModel.objects.create(parent=self.parents[1], old_parent=self.parents[2]),
            ChildModel.objects.create(parent=self.parents[0], old_parent=self.parents[1])
        ]
        self.children.extend([ChildModel.objects.create(parent=self.parents[1], old_parent=self.parents[2]) for x in range(2000)])

    def test_get_sideload_ids(self):
        with self.assertNumQueries(1):
            result = ChildSideloadSerializer(many=True).get_sideload_ids(
                ChildModel.objects.all())
        self.assertEqual(len(result), 1)
        self.assertEqual(result['parent_models'],
                         set([p.id for p in self.parents]))

    def test_get_sideload_objects(self):
        with self.assertNumQueries(4):
            result = ChildSideloadSerializer(many=True).get_sideload_objects(
                ChildModel.objects.all())
        expected = [
            {'id': p.id, 'text': p.text, 'children': p.child_ids,
            'old_children': p.old_child_ids}
            for p in ParentModel.objects.all()]
        self.assertEqual(len(result), 1)
        self.assertEqual(result['parent_models'], expected)


    def test_serialization(self):
        with self.assertNumQueries(5):
            result = ChildSideloadSerializer(ChildModel.objects.all(), many=True).data
        expected = {
            'child_models': [{
                'id': c.pk,
                'parent': c.parent.pk,
                'old_parent': c.old_parent.pk
            } for c in self.children],
            'parent_models': [
                {'id': p.pk, 'text': p.text,
                'children': p.child_ids,
                'old_children': p.old_child_ids}
                for p in self.parents
            ]
        }
        self.assertEqual(result, expected)
