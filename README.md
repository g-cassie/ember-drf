## DRF 3.0 Installation
Until DRF 3.0 is released it will be need to be installed using the following
command:
```
 pip install https://github.com/tomchristie/django-rest-framework/archive/version-3.0.zip
```

## Usage

Give these models:
```python
class Basket(models.Model):
    pass

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
        {id: 1},
        {id: 2},
    ]
}

```