from collections import defaultdict, namedtuple
from inflection import pluralize, underscore

from django.db.models.query import QuerySet

from rest_framework.compat import OrderedDict
from rest_framework.fields import empty
from rest_framework.serializers import (
    ListSerializer, Serializer, ValidationError, LIST_SERIALIZER_KWARGS
)
from rest_framework.utils.model_meta import get_field_info
from rest_framework.utils.serializer_helpers import ReturnDict

from . import compat


def get_ember_json_key_for_model(model, singular=False):
    """
    Get the key that a model's records should be nested under.
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
            queryset = conf.queryset.filter(id__in=ids)
            serializer = conf.serializer(
                queryset,
                many=True,
                context=self.context
            )
            ret[key] = serializer.data
        return ret

    def _configure_sideloads(self, meta):
        """
        Assemble configuration for each sideload.
        """
        self.sideloads = []
        configs = []
        for conf in getattr(meta, 'sideloads', []):
            assert isinstance(conf, tuple) and len(conf) >= 2 \
                and len(conf) <= 3, (
                '`Meta.sideloads` must be a list of tuples in the following '
                'format: (<model class>, <serializer class>, '
                '<queryset instance (optional)>)'
            )
            model, serializer = conf[:2]
            queryset = conf[0].objects.all() if (len(conf) == 2) else conf[2]
            configs.append((model, serializer, queryset))

        relations = get_field_info(self.model).relations
        fields = self.base_serializer.fields.values()
        for field_name, relation_info in relations.items():
            try:
                related_model = compat.get_related_model(relation_info)
                conf = configs[
                    [t[0] for t in configs].index(related_model)
                ]
            except ValueError:
                continue
            field = fields[[f.source for f in fields].index(field_name)]
            key_name = getattr(conf[1].Meta, 'base_key',
                               underscore(conf[0].__name__))
            self.sideloads.append(Sideload(
                field=field, model=conf[0], serializer=conf[1],
                queryset=conf[2], key_name=pluralize(key_name)
            ))


class SideloadListSerializer(SideloadSerializerMixin, ListSerializer):

    def __init__(self, *args, **kwargs):
        super(SideloadListSerializer, self).__init__(*args, **kwargs)
        meta = self.child.Meta
        self.base_serializer = meta.base_serializer()
        self.model = self.base_serializer.Meta.model
        self.base_key = getattr(self.base_serializer.Meta, 'base_key',
                                get_ember_json_key_for_model(self.model, True))
        self._configure_sideloads(meta)

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
        ret = OrderedDict()
        base_data = self.base_serializer.__class__(
            instance,
            many=True,
            context=self.context
        ).data
        ret[pluralize(self.base_key)] = base_data
        ret.update(self.get_sideload_objects(instance))
        return ret

    @property
    def data(self):
        ret = super(ListSerializer, self).data
        return ReturnDict(ret, serializer=self)


class SideloadSerializer(SideloadSerializerMixin, Serializer):

    def __init__(self, instance=None, data=empty, **kwargs):
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
            base_serializer = self.Meta.base_serializer
            self.model = base_serializer.Meta.model
            self.base_key = getattr(
                base_serializer.Meta, 'base_key',
                get_ember_json_key_for_model(self.model, True))
            if data is not empty:
                if not isinstance(data, dict):
                    raise AssertionError('`data` must be a `dict`.')
                if self.base_key not in data:
                    raise AssertionError(
                        'You must nest the attributes for the new object '
                        'under a root key: %s' % self.base_key)
                data = data[self.base_key]
            self.base_serializer = base_serializer(
                instance=instance, data=data, **kwargs)
            self._configure_sideloads(self.Meta)
        super(SideloadSerializer, self).__init__(instance, data, **kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        """
        Override `.many_init()` to create a SideloadListSerializer instance.
        """
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {'child': child_serializer}
        list_kwargs.update(dict([
            (key, value) for key, value in kwargs.items()
            if key in LIST_SERIALIZER_KWARGS
        ]))
        return SideloadListSerializer(*args, **list_kwargs)

    def get_sideload_ids(self, instance):
        """
        Returns a dictionary of model ids to sideload.
        """
        sideload_ids = defaultdict(set)
        for config in self.sideloads:
            attribute = config.field.get_attribute(instance)
            if isinstance(attribute, (list, QuerySet)):
                sideload_ids[config.key_name].update([a.pk for a in attribute])
            else:
                sideload_ids[config.key_name].add(attribute.pk if attribute else None)
        return sideload_ids

    def to_representation(self, instance):
        """
        Overrides the DRF method to add a root key and sideloads.
        """
        # self.base_serializer.instance = instance
        base_result = self.base_serializer.data
        if self.is_nested:
            return base_result

        ret = OrderedDict()
        key = self.base_key
        ret[key] = base_result
        ret.update(self.get_sideload_objects(instance))
        return ret

    def to_internal_value(self, data):
        """
        Overrides the DRF method to expect a root key.
        """
        return self.base_serializer.to_internal_value(data=data)

    def create(self, validated_data):
        """Proxy `create()` calls to `Meta.base_serializer`. """
        return self.base_serializer.create(validated_data)

    def update(self, instance, validated_data):
        """Proxy `update()` calls to `Meta.base_serializer`. """
        return self.base_serializer.update(instance, validated_data)

    def is_valid(self, raise_exception=False):
        """Proxy `.is_valid()` to `Meta.base_serializer`. """
        return self.base_serializer.is_valid(raise_exception)

    def save(self, **kwargs):
        self.instance = self.base_serializer.save(**kwargs)
        return self.instance

    @property
    def errors(self):
        """Proxy `.errors` to `Meta.base_serializer`. """
        return self.base_serializer.errors

    @property
    def _validated_data(self):
        """Proxy `.errors` to `Meta.base_serializer`. """
        return self.base_serializer._validated_data
