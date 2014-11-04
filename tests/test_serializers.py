from django.test import TestCase

from ember_drf.exceptions import ActiveModelValidationError
from ember_drf.serializers import SideloadListSerializer

from rest_framework.serializers import ValidationError

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

    def test_custom_basekey(self):
        serializer = ChildSideloadSerializer
        serializer.Meta.base_key = 'cats'
        result = serializer().to_representation(self.child)
        self.assertIn('cats', result)
        # for some reason this needs to be unset otherwise it will affect
        # other tests.
        serializer.Meta.base_key = None

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

class TestSideloadSerializerCreate(TestCase):

    def setUp(self):
        self.parent = ParentModel.objects.create()
        self.old_parent = ParentModel.objects.create()
        self.payload = {'child_model':
            {'parent': self.parent.pk, 'old_parent': self.old_parent.pk }}

    def test_deserialize_requires_root_key(self):
        with self.assertRaises(ValidationError):
            ChildSideloadSerializer().to_internal_value(
                self.payload['child_model'])

    def test_deserialize_field_validation_works(self):
        self.payload['child_model'].pop('parent')
        with self.assertRaises(ValidationError):
            ChildSideloadSerializer().to_internal_value(
                self.payload['child_model'])

    def test_deserialize(self):
        serializer = ChildSideloadSerializer(data=self.payload)
        self.assertTrue(serializer.is_valid)

    def test_create(self):
        serializer = ChildSideloadSerializer(data=self.payload)
        self.assertEqual(ChildModel.objects.count(), 0)
        serializer.is_valid()
        serializer.save()
        self.assertEqual(ChildModel.objects.count(), 1)


class TestSideloadSerializerUpdate(TestCase):

    def setUp(self):
        self.parent = ParentModel.objects.create()
        self.old_parent = ParentModel.objects.create()
        self.child = ChildModel.objects.create(
            parent=self.parent, old_parent=self.old_parent)
        # change `old_parent` to `self.parent`
        self.payload = {'child_model':
            {'id': self.child.pk, 'parent': self.parent.pk,
            'old_parent': self.parent.pk }}

    def test_deserialize_field_validation_works(self):
        self.payload['child_model'].pop('parent')
        serializer = ChildSideloadSerializer(
            data=self.payload, instance=self.child)
        self.assertFalse(serializer.is_valid())

    def test_errors_format(self):
        self.payload['child_model'].pop('parent')
        serializer = ChildSideloadSerializer(
            data=self.payload, instance=self.child)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors,
            {'errors': {'parent': ['This field is required.']}})

    def test_errors_status_code(self):
        self.payload['child_model'].pop('parent')
        serializer = ChildSideloadSerializer(
            data=self.payload, instance=self.child)
        with self.assertRaises(ActiveModelValidationError):
            serializer.is_valid(True)
        try:
            serializer.is_valid(True)
        except ActiveModelValidationError as e:
            self.assertEqual(e.status_code, 422)

    def test_deserialize(self):
        serializer = ChildSideloadSerializer(
            instance=self.child, data=self.payload)
        self.assertTrue(serializer.is_valid)

    def test_update(self):
        serializer = ChildSideloadSerializer(
            instance=self.child, data=self.payload)
        self.assertEqual(
            ChildModel.objects.get(pk=self.child.pk).old_parent, self.old_parent)
        serializer.is_valid()
        serializer.save()
        self.assertEqual(
            ChildModel.objects.get(pk=self.child.pk).old_parent, self.parent)


class TestSideloadListSerializer(TestCase):

    def setUp(self):
        self.parents = [ParentModel.objects.create() for x in range(3)]
        self.children = [
            ChildModel.objects.create(parent=self.parents[1], old_parent=self.parents[2]),
            ChildModel.objects.create(parent=self.parents[1], old_parent=self.parents[2]),
            ChildModel.objects.create(parent=self.parents[0], old_parent=self.parents[1])
        ]
        self.children.extend([ChildModel.objects.create(parent=self.parents[1], old_parent=self.parents[2]) for x in range(5)])

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
