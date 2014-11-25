
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
