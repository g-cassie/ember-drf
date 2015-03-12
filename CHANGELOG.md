## 0.1.8
+ Fix compatability issues with DRF 3.0.1
+ Fix bug with serializers passing in parent context

## 0.1.7
+ Fix additional compatability issues with DRF 3.0.2.
+ Remove install requirements to prevent emberdrf from upgrading django
  on install.

## 0.1.6
+ Fix compatability issues with DRF 3.0.2.

## 0.1.5
+ Fix compatability issues with DRF 3.0.1. Closes https://github.com/g-cassie/ember-drf/issues/6
+ Updates to Readme

## 0.1.4
+ Use flexible version numbers in requirements.txt

## 0.1.3
+ Pass context into `.base_serializer()`. See https://github.com/g-cassie/ember-drf/pull/3
+ Remove unnecessary use of `._field`

## 0.1.2
+ Fix bug due to renaming of ManyRelation to ManyRelatedField in DRF 3.0
  (See https://github.com/tomchristie/django-rest-framework/commit/fd97d9bff82b96b9362930686b9008ba78326115)
+ Refactor ActiveModelJSONRenderer to remove reliance upon nested
  ReturnDict and ReturnList instances.

## 0.1.0
+ Implement SideloadSerializer and SideloadListSerializer for
  read operations.
+ Implement EmberJSONRenderer
+ Implement ActiveModelJSONRenderer
