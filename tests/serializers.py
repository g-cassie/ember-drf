from rest_framework import serializers

from ember_drf.serializers import SideloadSerializer

from tests.models import ChildModel, ParentModel


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildModel


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