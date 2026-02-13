from rest_framework.pagination import PageNumberPagination

class ProductsPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "pageSize"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "items": data,
                "page": self.page.number,
                "pageSize": self.get_page_size(self.request),
                "total": self.page.paginator.count,
            }
        )