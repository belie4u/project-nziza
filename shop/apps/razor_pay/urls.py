from django.urls import path

from . import views

urlpatterns = [
    path('preview/<int:basket_id>/',
         views.SuccessResponseView.as_view(),
         name='razorpay-success-response'),
    path('cancel/<int:basket_id>/',
         views.CancelResponseView.as_view(),
         name='razorpay-cancel-response'),
    path('payment/',
         views.PaymentView.as_view(),
         name='razorpay-direct-payment'),
]
