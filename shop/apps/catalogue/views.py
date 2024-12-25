from urllib.parse import quote
from django.conf import settings
from django.contrib import messages
from django.core.paginator import InvalidPage
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, TemplateView


from oscar.apps.catalogue.signals import product_viewed
from oscar.apps.catalogue.views import CatalogueView as CoreCatalogueView

from oscar.core.loading import get_class, get_model

Product = get_model("catalogue", "product")
Category = get_model("catalogue", "category")
ProductAlert = get_model("customer", "ProductAlert")
ProductAlertForm = get_class("customer.forms", "ProductAlertForm")
get_product_search_handler_class = get_class(
    "catalogue.search_handlers", "get_product_search_handler_class"
)




class CatalogueView(TemplateView):
    """
    Browse all products in the catalogue
    """

    context_object_name = "products"
    template_name = "oscar/catalogue/browse.html"

    def get(self, request, *args, **kwargs):
        try:
            products_per_page = request.GET.get(
                'products_per_page', settings.OSCAR_PRODUCTS_PER_PAGE)
            try:
                products_per_page = int(products_per_page)
                if products_per_page not in [6, 16, 20, 24, 28]:
                    products_per_page = settings.OSCAR_PRODUCTS_PER_PAGE
            except ValueError:
                products_per_page = settings.OSCAR_PRODUCTS_PER_PAGE

            self.search_handler = self.get_search_handler(
                request.GET, request.get_full_path(), [], products_per_page=products_per_page
            )
            response = super().get(request, *args, **kwargs)
        except InvalidPage:
            messages.error(request, _("the given page number was invalid. "))
            return redirect("catalogue:index")
        return response

    def get_search_handler(self, *args, **kwargs):
        return get_product_search_handler_class()(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = {}
        ctx["summary"] = _("All products")
        search_context = self.search_handler.get_search_context_data(
            self.context_object_name
        )
        ctx.update(search_context)
        return ctx
