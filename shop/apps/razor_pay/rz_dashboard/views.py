from django.views import generic

from apps.razor_pay import models


class TransactionListView(generic.ListView):
    model = models.RazorpayTransaction
    template_name = 'oscar/dashboard/transaction_list.html'
    context_object_name = 'transactions'


class TransactionDetailView(generic.DetailView):
    model = models.RazorpayTransaction
    template_name = 'oscar/dashboard/transaction_detail.html'
    context_object_name = 'txn'
