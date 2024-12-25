from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from apps.catalogue.models import Category
from oscar.apps.dashboard.catalogue.views import CategoryListMixin
from django.views import generic
from .forms import CategoryForm  # Use the updated CategoryForm with clean_image logic

class CategoryCreateView(CategoryListMixin, generic.CreateView):
    template_name = "oscar/dashboard/catalogue/category_form.html"
    model = Category
    form_class = CategoryForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Add a new category")
        return ctx

    def get_success_url(self):
        messages.info(self.request, _("Category created successfully"))
        return super().get_success_url()

    def get_initial(self):
        # Set child category if specified in the URL kwargs
        initial = super().get_initial()
        if "parent" in self.kwargs:
            initial["_ref_node_id"] = self.kwargs["parent"]
        return initial

    def form_valid(self, form):
        # Explicitly call clean_image to ensure validation occurs
        try:
            form.clean_image()
        except forms.ValidationError as e:
            form.add_error("image", e)
            return self.form_invalid(form)
        return super().form_valid(form)


class CategoryUpdateView(CategoryListMixin, generic.UpdateView):
    template_name = "oscar/dashboard/catalogue/category_form.html"
    model = Category
    form_class = CategoryForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = _("Update category '%s'") % self.object.name
        return ctx

    def get_success_url(self):
        messages.info(self.request, _("Category updated successfully"))
        action = self.request.POST.get("action")
        if action == "continue":
            return reverse(
                "dashboard:catalogue-category-update", kwargs={"pk": self.object.id}
            )
        return super().get_success_url()

    def form_valid(self, form):
        # Explicitly call clean_image to ensure validation occurs
        try:
            form.clean_image()
        except forms.ValidationError as e:
            form.add_error("image", e)
            return self.form_invalid(form)
        return super().form_valid(form)
