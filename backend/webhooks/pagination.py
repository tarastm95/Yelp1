from rest_framework.pagination import PageNumberPagination

class FivePerPagePagination(PageNumberPagination):
    """Default pagination size for API responses."""

    # Return smaller result sets to keep the list pages lightweight.
    # Frontend is expected to request additional pages as needed.
    page_size = 5
