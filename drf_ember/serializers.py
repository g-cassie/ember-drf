from collections import defaultdict
from inflection import pluralize, underscore

from rest_framework.relations import PrimaryKeyRelatedField, ManyRelation
from rest_framework.serializers import (
    ReturnDict, ListSerializer, Serializer, ValidationError
)
from rest_framework.utils.model_meta import get_field_info

from drf_ember.exceptions import ActiveModelValidationError


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
        sideload_fields = getattr(meta, 'sideload_fields', [])
        self.models, self.sideload_key_names = {}, {}
        relations_info = get_field_info(self.base_serializer.Meta.model).relations
        for key, value in relations_info.items():
            self.models[key] = value.related
            self.sideload_key_names[value.related.__name__] = \
                self.get_sideload_key_name(value.related)

        self.sideload_fields =  [
            field for field in self.base_serializer.fields.values()
            if field.source in sideload_fields]


    def get_base_key(self, singular=False):
        meta = self.child.Meta if hasattr(self, 'child') else self.Meta
        key = getattr(meta, 'base_key', None)
        if key and not singular:
            key = pluralize(key)
        if not key:
            model = self.base_serializer.Meta.model
            key = self.get_sideload_key_name(model, singular=singular)
        return key


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
        key = self.get_base_key()
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
        is_nested = hasattr(self, 'parent') and self.parent
        base_result = self.base_serializer.to_representation(instance)
        if is_nested:
            return base_result

        ret = ReturnDict(serializer=self)
        key = self.get_base_key(singular=True)
        ret[key] = base_result
        ret.update(self.get_sideload_objects(instance))
        return ret

    def to_internal_value(self, data):
        key = self.get_base_key(singular=True)
        if not key in data:
            raise ValidationError(
                'You must nest the attributes for the new object '
                'under a root key: %s' % key)
        return self.base_serializer.to_internal_value(data[key])

    def create(self, validated_data):
        return self.base_serializer.create(validated_data)

    def update(self, instance, validated_data):
        return self.base_serializer.update(instance, validated_data)

    def is_valid(self, raise_exception=False):
        """
        Override builtin DRF method to reformat errors and use HTTP 422.

        This is kind of hacky, hopefully there will be a better way to do this
        soon.
        """
        try:
            result = super(SideloadSerializer, self).is_valid(raise_exception)
        except ValidationError:
            errors = ReturnDict({'errors': self._errors}, serializer=self)
            raise ActiveModelValidationError(errors)
        self._errors = ReturnDict({'errors': self._errors}, serializer=self) \
            if self._errors else {}
        return not bool(self._errors)
