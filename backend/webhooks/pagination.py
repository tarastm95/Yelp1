from rest_framework.pagination import PageNumberPagination

class FivePerPagePagination(PageNumberPagination):
    """Default pagination size for API responses."""

    # Increase page size from 5 to 20 so that API endpoints return
    # larger result sets per request. This helps reduce the number of
    # requests required on the frontend while still keeping the data
    # set manageable.
    page_size = 20
