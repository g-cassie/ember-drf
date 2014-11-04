from rest_framework import filters


class CoallesceIDsFilterBackend(filters.BaseFilterBackend):
    """
    Filter class to support ED's "coalesce find requqests" option.

    See http://emberjs.com/blog/2014/08/18/ember-data-1-0-beta-9-released.html
    for more detail.
    """
    def filter_queryset(self, request, queryset, view):
        ids = dict(request.QUERY_PARAMS).get('ids[]')
        if ids:
            queryset = queryset.filter(id__in=ids)
        return queryset
