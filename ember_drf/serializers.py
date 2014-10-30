
from collections import defaultdict
from inflection import pluralize, underscore

from rest_framework.serializers import ReturnDict, \
    ListSerializer, Serializer
from rest_framework.relations import PrimaryKeyRelatedField

class SideloadSerializerMixin(object):

    def get_sideload_key_name(self, model, singular=False):
        """
        Gets the dictionary key to nest a model's instances under.
        """
        name = model.__name__
        if not singular:
            name = pluralize(name)
        return underscore(name)

    def get_sideload_config(self):
        """
        Gets a dictionary with the configuration for the serializer.

        Expects that the `Meta` class has a `sideloads` property that contains
        a list of tuples in the format `(ModelClass, SerializerClass)`.
        """
        result = {}
        if hasattr(self, 'child'):
            conf = getattr(self.child.Meta, 'sideloads', [])
        else:
            conf = getattr(self.Meta, 'sideloads', [])
        for (model, serializer) in conf:
            result[self.get_sideload_key_name(model)] = {
                'model': model,
                'serializer': serializer
            }
        return result

    def get_sideload_objects(self, data):
        """
        Gets a dictionary of objects to sideload.

        Args:
            data (list): the list of objects that are being serialized and
                for which sideloaded data is required.
        Returns:
            dict: Dictionary where each key represents a model type and each
                value is a list of instances of that model type.
        """
        sideloads = self.get_sideload_ids(data)
        ret = defaultdict(set)
        for key, ids in sideloads.items():
            try:
                conf = self.get_sideload_config()[key]
            except KeyError:
                raise ValueError(
                    'You must provide a tuple in the following format for '
                    'each sideloaded model: '
                    '(\'<model name>\', <serializer class>)')
            ret[key] = conf['serializer'](
                conf['model'].objects.filter(pk__in=ids), many=True).data
        return ret


class SideloadListSerializer(SideloadSerializerMixin, ListSerializer):

    def get_sideload_ids(self, data):
        """
        Gets a dictionary of all object ids that are to be sideloaded.

        Args:
            data (list): the list of objects that are being serialized and
                for which sideloaded data is required.
        Returns:
            dict: Dictionary where each key represents a model type and each
                value is a list of ids for that model type.

        """
        sideload_list = []
        for item in data:
            sideload_list.append(self.child.get_sideload_ids(item))
        sideloads = defaultdict(set)
        for sideload_dict in sideload_list:
            for key, value in sideload_dict.items():
                sideloads[key].update(value)
        return sideloads

    def to_representation(self, data):
        """
        Overrides the DRF method to add a root key and sideloads.
        """
        ret = ReturnDict(serializer=self)
        base_serializer = getattr(self.child.Meta, 'base_serializer')
        model = getattr(base_serializer.Meta, 'model')

        # TODO: Consider whether to support a SideloadListSerializer
        # serializing details to be nested.
        ret = ReturnDict(serializer=self)
        key = self.get_sideload_key_name(model)
        ret[key] = base_serializer(data, many=True).data
        ret.update(self.get_sideload_objects(data))
        return ret


class SideloadSerializer(SideloadSerializerMixin, Serializer):

    def __new__(cls, *args, **kwargs):
        # We override this method in order to automagically create
        # `SideloadListSerializer` classes instead when `many=True` is set.
        if kwargs.pop('many', False):
            kwargs['child'] = cls()
            return SideloadListSerializer(*args, **kwargs)
        return super(Serializer, cls).__new__(cls, *args, **kwargs)

    def get_sideload_ids(self, instance):
        """
        Returns a dictionary of model ids to sideload.
        """
        base_serializer = getattr(self.Meta, 'base_serializer')
        sideload_fields = getattr(self.Meta, 'sideload_fields', [])
        fields = [field for field in base_serializer().fields.values()
                  if field.source in sideload_fields]

        sideloads = defaultdict(set)
        for field in fields:
            # we cannot use field.get_attribute as that will give us a back
            # a `PKOnlyObject`.
            attribute = getattr(instance, field.source)
            if isinstance(field, PrimaryKeyRelatedField):
                key = self.get_sideload_key_name(attribute.__class__)
                sideloads[key].add(attribute.id)
            elif isinstance(field, ListSerializer):
                key = self.get_sideload_key_name(attribute.model)
                sideloads[key].update(
                    set(attribute.values_list('id', flat=True)))
            else:
                raise ValueError(
                    'Encountered an unexpected field class %s.  Did '
                    'you specify a field in `sideload_fields` that is '
                    'not a relation?')
        return sideloads

    def to_representation(self, instance):
        """
        Overrides the DRF method to add a root key and sideloads.
        """
        base_serializer = getattr(self.Meta, 'base_serializer')
        model = getattr(base_serializer.Meta, 'model')
        is_nested = hasattr(self, 'parent') and self.parent
        base_result = base_serializer(instance).data
        if is_nested:
            return base_result

        ret = ReturnDict(serializer=self)
        key = self.get_sideload_key_name(model, singular=True)
        ret[key] = base_result
        ret.update(self.get_sideload_objects(instance))
        return ret
