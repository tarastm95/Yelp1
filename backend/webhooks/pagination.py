from rest_framework.pagination import PageNumberPagination

class FivePerPagePagination(PageNumberPagination):
    page_size = 5
