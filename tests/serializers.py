from rest_framework import serializers

from drf_ember.serializers import SideloadSerializer

from tests.models import ChildModel, ParentModel, OptionalChildModel


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildModel

class OptionalChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionalChildModel

class ParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentModel
        fields = ('id', 'text', 'children', 'old_children')


class ChildSideloadSerializer(SideloadSerializer):
    class Meta:
        sideload_fields = ['parent', 'old_parent']
        base_serializer = ChildSerializer
        sideloads = [
            (ParentModel, ParentSerializer)
        ]


class OptionalChildSideloadSerializer(SideloadSerializer):
    class Meta:
        sideload_fields = ['parent']
        base_serializer = OptionalChildSerializer
        sideloads = [
            (ParentModel, ParentSerializer)
        ]