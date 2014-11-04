from collections import defaultdict, namedtuple
from inflection import pluralize, underscore

from rest_framework.serializers import (
    ReturnDict, ListSerializer, Serializer, ValidationError
)
from rest_framework.utils.model_meta import get_field_info

from ember_drf.exceptions import ActiveModelValidationError


def get_ember_json_key_for_model(model, singular=False):
    """
    Take a model a return the key that is records should be nested under.
    """
    name = model.__name__
    if not singular:
        name = pluralize(name)
    return underscore(name)

Sideload = namedtuple('Sideload', ['field', 'model', 'serializer', 'queryset',
                                   'key_name'])


class SideloadSerializerMixin(object):

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
        sideload_ids = self.get_sideload_ids(data)
        ret = defaultdict(set)
        for key, ids in sideload_ids.items():
            conf = self.sideloads[
                [t.key_name for t in self.sideloads].index(key)]
            ret[key] = conf.serializer(
                conf.queryset.filter(id__in=ids), many=True).data
        return ret

    def _configure_sideloads(self, meta):
        """
        Assemble configuration for each sideload.
        """
        self.base_serializer = meta.base_serializer()
        self.model = self.base_serializer.Meta.model
        self.sideloads = []
        self.base_key = getattr(meta, 'base_key', None)
        if not self.base_key:
            self.base_key = get_ember_json_key_for_model(self.model, True)

        configs = []
        for conf in meta.sideloads:
            assert isinstance(conf, tuple) and len(conf) >= 2 \
                and len(conf) <= 3, (
                '`Meta.sideloads` must be a list of tuples in the following '
                'format: (<model class>, <serializer class>, '
                '<queryset instance (optional)>)'
            )
            model, serializer = conf[:2]
            queryset = conf[0].objects.all() if (len(conf) == 2) else conf[2]
            configs.append((model, serializer, queryset))

        relations = get_field_info(self.base_serializer.Meta.model).relations
        fields = self.base_serializer.fields.values()
        for field_name, info in relations.items():
            try:
                conf = configs[[t[0] for t in configs].index(info.related)]
            except ValueError:
                continue
            field = fields[
                [f.source for f in fields].index(field_name)]
            self.sideloads.append(Sideload(
                field=field, model=conf[0], serializer=conf[1],
                queryset=conf[2], key_name=underscore(pluralize(conf[0].__name__))
            ))


class SideloadListSerializer(SideloadSerializerMixin, ListSerializer):

    def __init__(self, *args, **kwargs):
        self._configure_sideloads(kwargs['child'].Meta)
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
        sideload_ids = defaultdict(set)
        for sideload_dict in sideload_list:
            for key, value in sideload_dict.items():
                sideload_ids[key].update(value)
        return sideload_ids

    def to_representation(self, instance):
        """
        Overrides to nest the primary record and add sideloads.
        """
        ret = ReturnDict(serializer=self)
        ret[pluralize(self.base_key)] = self.base_serializer.__class__(instance, many=True).data
        ret.update(self.get_sideload_objects(instance))
        return ret


class SideloadSerializer(SideloadSerializerMixin, Serializer):

    def __init__(self, *args, **kwargs):
        """
        Setup the SideloadSerializer and configure it.

        A nested SideloadSerializer will have a parent SideloadListSerializer
        that already has the relevant configuration.
        """
        self.is_nested = hasattr(self, 'parent')
        if self.is_nested:
            self.base_serializer = self.parent.base_serializer
            self.sideloads = self.parent.sideloads
            self.base_key = self.parent.base_key
            self.base_key_plural = self.parent.base_key_plural
        else:
            self._configure_sideloads(self.Meta)
        return super(SideloadSerializer, self).__init__(*args, **kwargs)

    def __new__(cls, *args, **kwargs):
        """
        Automatically create a SideloadListSerializer when `many=True`.

        This copies the internal DRF pattern with `Serializer`/`ListSerializer`.
        """
        if kwargs.pop('many', False):
            kwargs['child'] = cls(*args, **kwargs)
            return SideloadListSerializer(*args, **kwargs)
        return super(Serializer, cls).__new__(cls, *args, **kwargs)

    def get_sideload_ids(self, instance):
        """
        Returns a dictionary of model ids to sideload.
        """
        sideload_ids = defaultdict(set)
        for config in self.sideloads:
            attribute = config.field.get_attribute(instance)
            if isinstance(attribute, list):
                sideload_ids[config.key_name].update([a.pk for a in attribute])
            else:
                sideload_ids[config.key_name].add(attribute.pk if attribute else None)
        return sideload_ids

    def to_representation(self, instance):
        """
        Overrides the DRF method to add a root key and sideloads.
        """
        base_result = self.base_serializer.to_representation(instance)
        if self.is_nested:
            return base_result

        ret = ReturnDict(serializer=self)
        key = self.base_key
        ret[key] = base_result
        ret.update(self.get_sideload_objects(instance))
        return ret

    def to_internal_value(self, data):
        """
        Overrides the DRF method to expect a root key.
        """
        if not self.base_key in data:
            raise ValidationError(
                'You must nest the attributes for the new object '
                'under a root key: %s' % self.base_key)
        return self.base_serializer.to_internal_value(data[self.base_key])

    def create(self, validated_data):
        """
        Proxy `create()` calls to `Meta.base_serializer`.
        """
        return self.base_serializer.create(validated_data)

    def update(self, instance, validated_data):
        """
        Proxy `update()` calls to `Meta.base_serializer`.
        """
        return self.base_serializer.update(instance, validated_data)

    def is_valid(self, raise_exception=False):
        """
        Override builtin DRF method to reformat errors and use HTTP 422.

        This is kind of hacky, hopefully there will be a better way to do this
        soon.
        """
        try:
            super(SideloadSerializer, self).is_valid(raise_exception)
        except ValidationError:
            errors = ReturnDict({'errors': self._errors}, serializer=self)
            raise ActiveModelValidationError(errors)
        self._errors = ReturnDict({'errors': self._errors}, serializer=self) \
            if self._errors else {}
        return not bool(self._errors)
