from django.apps import AppConfig
from oscar.core.application import OscarDashboardConfig
from django.urls import path, re_path
from oscar.core.loading import get_class


class RzDashboardConfig(OscarDashboardConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.razor_pay.rz_dashboard'
    namespace = 'razor_pay_dashboard'
    default_permissions = ['is_staff']
    def ready(self):
        super().ready()
        self.razorpay_list_view = get_class(
            'rz_dashboard.views', 'TransactionListView')
        self.razorpay_detail_view = get_class(
            'rz_dashboard.views', 'TransactionDetailView')

    def get_urls(self):
        urls = super().get_urls()
        urls += [
            path('transactions/', self.razorpay_list_view.as_view(),
                 name='razorpay-list'),
            re_path(r'^transactions/(?P<pk>\d+)/$',
                    self.razorpay_detail_view.as_view(), name='razorpay-detail'),
        ]
        return self.post_process_urls(urls)
