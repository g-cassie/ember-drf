# Overview

This project aims to create a python package that makes it simple to build an
API that is compatible with
[Ember Data](https://github.com/emberjs/data)
out of the box. While initially the user will still be required to configure
their urls and serializers in a certain way for them to work properly, the 
goal is to make this as pluggable as possible.

## Structure
There are currently two parts to the project:
1. Serializer
2. Renderer
These components should be sufficient to match all of Ember Data's
specifications other than it's url scheme which the user must currently
configure manually in their router.py file.  We will look at ways to take
care of this as well soon.

## Serializer

`drf_ember` uses Serializers to make structural modifications to the default
DRF responses (as opposed to purely aesthetic modifications that are handled by
renderers).  The primary structural difference between Ember Data and
out of the box DRF are as follows:

1. Responses from the api are nested under a root key.

2. Related records can be sideloaded under other root keys.

`drf_ember` supports the above structural changes by providing the
SideloadSerializer base class.  This must be used in conjunction with
one or more typical `ModelSerializers`.  Despite the name, SideloadSerializer
may be used without any sideloading options in order to simply nest the
api response under a root key.

### Serializer Example

Give these models:
```python
class Basket(models.Model):
    text = models.CharField(max_length=200, default='Fruit Basket')

class Fruit(models.Model):
    basket = models.ForeignKey(Basket)
    previous_basket = models.ForeignKey(Basket, related_name='former_fruits')
```
And these serializers:
```python
class BasketSerializer(models.Model):
    class Meta:
        model = Basket

class Fruit(models.Model):
    class Meta:
        model = Fruit
```

You can create a fruit serializer that sideloads baskets in the correct format
for Ember Data as follows:
```python
class FruitSideloadSerializer(SideloadSerializer):
    class Meta:
        sideload_fields = ['basket', 'previous_basket']
        base_serializer = FruitSerializer
        sideloads = [
            (Basket, BasketSerializer)
        ]

```
This will produce output in the following format:

```json
{
    fruits: [
        {id: 1, basket: 1, previous_basket: 2},
        {id: 2, basket: 2, previous_basket: 1},
        {id: 3, basket: 1, previous_basket: 1},
    ],
    baskets: [
        {id: 1, title: 'Fruit Basket'},
        {id: 2, title: 'Fruit Basket'},
    ]
}
```
Note that the serializer does not convert the underscored attributes to camel
case. That functionality is decoupled and put in the EmberJSONRenderer.

## Renderers

This project uses renderers to make changes that are purely aesthetic (as opposed to structural).  There are two renders:

1. EmberJSONRenderer: For use with Ember Data's built in JSONSerializer.

2. Active ModelJSONRenderer: For use with Ember Data's built in
    ActiveModelSerializer.


Details on how to use renders can be found
[here](http://www.django-rest-framework.org/api-guide/renderers)

# Notes

## DRF 3.0 Installation
Until DRF 3.0 is released it will need to be installed using
the following command:
```
 pip install https://github.com/tomchristie/django-rest-framework/archive/version-3.0.zip
```
