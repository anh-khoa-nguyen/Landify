from rest_framework import pagination

class GeneralPaginator(pagination.PageNumberPagination):
	page_size = 10