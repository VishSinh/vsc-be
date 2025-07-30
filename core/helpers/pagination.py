from typing import Any, Dict

from django.core.paginator import Paginator


class PaginationHelper:
    @staticmethod
    def paginate_queryset(
        queryset,
        page: int,
        page_size: int,
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Paginate a queryset and return data and pagination info as tuple.

        Args:
            queryset: Django QuerySet to paginate
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (data_dict, pagination_dict) for use with @forge decorator
        """
        paginator = Paginator(queryset, page_size)
        total_pages = paginator.num_pages

        # Check if the requested page is valid
        if page > total_pages and total_pages > 0:
            from core.exceptions import BadRequest

            raise BadRequest(f"Page {page} does not exist. Total pages: {total_pages}")

        page_obj = paginator.get_page(page)

        pagination_info = {
            "current_page": page,
            "page_size": page_size,
            "total_items": page_obj.paginator.count,
            "total_pages": page_obj.paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
        }

        return page_obj, pagination_info
