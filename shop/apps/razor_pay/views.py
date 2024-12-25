import logging
from urllib.parse import urlencode

from django.views.generic import RedirectView, View
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext_lazy as _

from oscar.apps.payment.exceptions import UnableToTakePayment
from oscar.core.loading import get_class, get_model

from . import facade
from .exceptions import (
    EmptyBasketException, MissingShippingAddressException,
    MissingShippingMethodException, InvalidBasket, RazorpayError
)

# Load Oscar classes dynamically
PaymentDetailsView = get_class('checkout.views', 'PaymentDetailsView')
CheckoutSessionMixin = get_class('checkout.session', 'CheckoutSessionMixin')

ShippingAddress = get_model('order', 'ShippingAddress')
Country = get_model('address', 'Country')
Basket = get_model('basket', 'Basket')
Repository = get_class('shipping.repository', 'Repository')
Selector = get_class('partner.strategy', 'Selector')
Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
Applicator = get_class('offer.applicator', 'Applicator')

logger = logging.getLogger('razorpay')


class PaymentView(CheckoutSessionMixin, View):
    template_name = 'oscar/razor_pay/payment.html'

    def get(self, request, *args, **kwargs):
        try:
            basket = self.build_submission()['basket']
            if basket.is_empty:
                raise EmptyBasketException()
        except InvalidBasket as e:
            messages.warning(request, str(e))
            return HttpResponseRedirect(reverse('basket:summary'))
        except EmptyBasketException:
            messages.error(request, _("Your basket is empty"))
            return HttpResponseRedirect(reverse('basket:summary'))
        except MissingShippingAddressException:
            messages.error(request, _("A shipping address must be specified"))
            return HttpResponseRedirect(reverse('checkout:shipping-address'))
        except MissingShippingMethodException:
            messages.error(request, _("A shipping method must be specified"))
            return HttpResponseRedirect(reverse('checkout:shipping-method'))
        else:
            basket.freeze()
            logger.info("Starting payment for basket #%s", basket.id)
            context = self._start_razorpay_txn(basket)
            return render(request, self.template_name, context)

    def _start_razorpay_txn(self, basket):
        if basket.is_empty:
            raise EmptyBasketException()

        order_total = self.build_submission()['order_total']
        user = self.request.user
        amount = order_total.incl_tax
        email = user.email if user.is_authenticated else self.build_submission()[
            'order_kwargs']['guest_email']
        user = user if user.is_authenticated else None

        transaction = facade.start_razorpay_txn(basket, amount, user, email)
        return {
            "basket": basket,
            "amount": int(amount * 100),  # Convert to paisa
            "rz_key": settings.RAZORPAY_API_KEY,
            "email": email,
            "txn_id": transaction.txnid,
            "name": getattr(settings, "RAZORPAY_VENDOR_NAME", "My Store"),
            "description": getattr(settings, "RAZORPAY_DESCRIPTION", "Amazing Product"),
            "theme_color": getattr(settings, "RAZORPAY_THEME_COLOR", "#F37254"),
            "logo_url": getattr(settings, "RAZORPAY_VENDOR_LOGO", "https://via.placeholder.com/150x150"),
        }


class CancelResponseView(RedirectView):
    permanent = False

    def get(self, request, *args, **kwargs):
        basket = get_object_or_404(
            Basket, id=kwargs['basket_id'], status=Basket.FROZEN)
        basket.thaw()
        logger.info("Payment cancelled - basket #%s thawed", basket.id)
        messages.error(request, _("Razorpay transaction cancelled"))
        return super().get(request, *args, **kwargs)

    def get_redirect_url(self, **kwargs):
        return reverse('basket:summary')


@method_decorator(csrf_exempt, name='dispatch')
class SuccessResponseView(PaymentDetailsView):
    preview = True

    @property
    def pre_conditions(self):
        return []

    def get(self, request, *args, **kwargs):
        self.rz_id = request.GET.get('rz_id')
        self.txn_id = request.GET.get('txn_id')

        if not self.rz_id or not self.txn_id:
            logger.warning("Missing GET params on success response page")
            messages.error(request, _(
                "Unable to determine Razorpay transaction details"))
            return HttpResponseRedirect(reverse('basket:summary'))

        try:
            transaction = facade.update_transaction_details(
                self.rz_id, self.txn_id)
        except RazorpayError:
            messages.error(request, _(
                "A problem occurred communicating with Razorpay - please try again later"))
            return HttpResponseRedirect(reverse('basket:summary'))

        basket = self.load_frozen_basket(kwargs['basket_id'])
        if not basket:
            logger.warning(
                "Unable to load frozen basket with ID %s", kwargs['basket_id'])
            messages.error(request, _(
                "No basket was found that corresponds to your Razorpay transaction"))
            return HttpResponseRedirect(reverse('basket:summary'))

        logger.info("Basket #%s - showing preview payment id %s",
                    basket.id, self.rz_id)
        submission = self.build_submission(basket=basket)
        return self.submit(**submission)

    def load_frozen_basket(self, basket_id):
        try:
            basket = Basket.objects.get(id=basket_id, status=Basket.FROZEN)
        except Basket.DoesNotExist:
            return None

        if Selector:
            basket.strategy = Selector().strategy(self.request)

        Applicator().apply(request=self.request, basket=basket)
        return basket

    def handle_payment(self, order_number, total, **kwargs):
        try:
            confirm_transaction = facade.capture_transaction(kwargs["rz_id"])
        except RazorpayError:
            raise UnableToTakePayment()

        if not confirm_transaction.is_successful:
            raise UnableToTakePayment()

        source_type, _ = SourceType.objects.get_or_create(name='Razorpay')
        source = Source(
            source_type=source_type,
            currency=confirm_transaction.currency,
            amount_allocated=confirm_transaction.amount,
            amount_debited=confirm_transaction.amount,
        )
        self.add_payment_source(source)
        self.add_payment_event(
            'Settled', confirm_transaction.amount, reference=confirm_transaction.rz_id)
