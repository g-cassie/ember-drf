from collections import defaultdict
from inflection import pluralize, underscore

from rest_framework.relations import PrimaryKeyRelatedField, ManyRelation
from rest_framework.serializers import ReturnDict, \
    ListSerializer, Serializer
from rest_framework.utils.model_meta import get_field_info


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
        for tup in conf:
            model, serializer = tup[:2]
            if len(tup) == 3:
                queryset = tup[2]
            else:
                queryset = model.objects.all()
            result[self.sideload_key_names[model.__name__]] = {
                'model': model,
                'serializer': serializer,
                'queryset': queryset
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
                    'Unable to find configuration for {}.  '
                    'You must provide a tuple in the following format for '
                    'each sideloaded model: '
                    '(\'<model name>\', <serializer class>)'.format(key))
            ret[key] = conf['serializer'](
                conf['queryset'].filter(id__in=ids), many=True).data
        return ret

    def set_config(self, meta):
        self.base_serializer = getattr(meta, 'base_serializer')()
        self.models, self.sideload_key_names = {}, {}
        relations_info = get_field_info(self.base_serializer.Meta.model).relations
        for key, value in relations_info.items():
            self.models[key] = value.related
            self.sideload_key_names[value.related.__name__] = \
                self.get_sideload_key_name(value.related)

        self.sideload_fields =  [
            field for field in self.base_serializer.fields.values()
            if field.source in meta.sideload_fields]


class SideloadListSerializer(SideloadSerializerMixin, ListSerializer):

    def __init__(self, *args, **kwargs):
        self.set_config(kwargs['child'].Meta)
        return super(SideloadListSerializer, self).__init__(*args, **kwargs)

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

    def to_representation(self, instance):
        """
        Overrides the DRF method to add a root key and sideloads.
        """
        ret = ReturnDict(serializer=self)
        model = self.base_serializer.Meta.model
        key = self.get_sideload_key_name(model)
        ret[key] = self.base_serializer.__class__(instance, many=True).data
        ret.update(self.get_sideload_objects(instance))
        return ret


class SideloadSerializer(SideloadSerializerMixin, Serializer):

    def __init__(self, *args, **kwargs):
        if hasattr(self, 'parent'):
            self.models = self.parent.models
            self.base_serializer = self.parent.base_serializer
            self.sideload_fields = self.parent.sideload_fields
        else:
            self.set_config(self.Meta)
        return super(SideloadSerializer, self).__init__(*args, **kwargs)

    def __new__(cls, *args, **kwargs):
        # We override this method in order to automagically create
        # `SideloadListSerializer` classes instead when `many=True` is set.
        if kwargs.pop('many', False):
            kwargs['child'] = cls(*args, **kwargs)
            return SideloadListSerializer(*args, **kwargs)
        return super(Serializer, cls).__new__(cls, *args, **kwargs)

    def get_sideload_ids(self, instance):
        """
        Returns a dictionary of model ids to sideload.
        """
        sideloads = defaultdict(set)
        for field in self.sideload_fields:
            # we cannot use field.get_attribute as that will give us a back
            # a `PKOnlyObject`.
            assert isinstance(field, (PrimaryKeyRelatedField, ManyRelation)), \
                ('Encountered an unexpected field class {}.  Did '
                'you specify a field in `sideload_fields` that is '
                'not a relation?'.format(field.__class__))
            model = self.models[field.source]
            key = self.sideload_key_names[model.__name__]
            attribute = field.get_attribute(instance)
            if isinstance(attribute, list):
                sideloads[key].update([a.pk for a in attribute])
            else:
                sideloads[key].add(attribute.pk if attribute else None)

        return sideloads

    def to_representation(self, instance):
        """
        Overrides the DRF method to add a root key and sideloads.
        """
        model = self.base_serializer.Meta.model
        is_nested = hasattr(self, 'parent') and self.parent
        base_result = self.base_serializer.to_representation(instance)
        if is_nested:
            return base_result

        ret = ReturnDict(serializer=self)
        key = self.get_sideload_key_name(model, singular=True)
        ret[key] = base_result
        ret.update(self.get_sideload_objects(instance))
        return ret
