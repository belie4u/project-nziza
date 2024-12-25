from __future__ import unicode_literals
from uuid import uuid4
import logging

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import RazorpayTransaction as Transaction
from .exceptions import (
    RazorpayError, PaymentCaptureFailedException,
    TransactionLimitExceededException
)

import razorpay

# Initialize Razorpay client
rz_client = razorpay.Client(
    auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET)
)

logger = logging.getLogger('razorpay')

# Facade Functions


def start_razorpay_txn(basket, amount, user=None, email=None):
    """
    Initialize a Razorpay transaction and save it to the database.
    """
    currency = basket.currency or getattr(settings, 'RAZORPAY_CURRENCY', 'INR')
    transaction = Transaction(
        user=user,
        amount=amount,
        currency=currency,
        status="initiated",
        basket_id=basket.id,
        txnid=uuid4().hex[:28],
        email=email
    )
    transaction.save()
    return transaction


def update_transaction_details(rz_id, txn_id):
    """
    Update transaction details from Razorpay's API.
    """
    try:
        payment = rz_client.payment.fetch(rz_id)
    except razorpay.errors.RazorpayError as e:
        logger.error(
            "Failed to fetch Razorpay transaction %s: %s", rz_id, str(e))
        raise RazorpayError("Unable to fetch transaction details.")

    try:
        txn = Transaction.objects.select_for_update().get(txnid=txn_id)
    except Transaction.DoesNotExist:
        logger.error("Transaction %s not found in the database.", txn_id)
        raise RazorpayError("Transaction not found.")

    if int(txn.amount * 100) != payment["amount"] or txn.currency != payment["currency"]:
        logger.warning("Mismatch in details for txn %s: %s", txn, payment)
        raise RazorpayError("Transaction details mismatch.")

    txn.status = payment["status"]
    txn.rz_id = rz_id
    txn.save()
    return txn


def capture_transaction(rz_id):
    """
    Capture a Razorpay payment.
    """
    try:
        txn = Transaction.objects.select_for_update().get(rz_id=rz_id)
        rz_client.payment.capture(rz_id, int(txn.amount * 100))
        txn.status = "captured"
        txn.save()
        return txn
    except razorpay.errors.RazorpayError as e:
        logger.error("Failed to capture payment %s: %s", rz_id, str(e))
        raise PaymentCaptureFailedException("Capture failed.", e.error.code)
    except Transaction.DoesNotExist:
        logger.error("Transaction %s not found for capture.", rz_id)
        raise RazorpayError("Transaction not found.")


def refund_transaction(rz_id, amount, currency):
    """
    Refund a transaction partially or fully.
    """
    try:
        txn = Transaction.objects.select_for_update().get(rz_id=rz_id)
        if amount > int(txn.amount * 100):
            raise TransactionLimitExceededException(
                "Refund amount exceeds transaction amount.")
        if currency != txn.currency:
            raise RazorpayError("Currency mismatch for refund.")

        rz_client.payment.refund(rz_id, amount)
        txn.status = "refunded"
        txn.save()
        logger.info("Refund processed for transaction %s.", rz_id)
        return txn
    except razorpay.errors.RazorpayError as e:
        logger.error("Refund failed for %s: %s", rz_id, str(e))
        raise RazorpayError("Refund failed.")
    except Transaction.DoesNotExist:
        logger.error("Transaction %s not found for refund.", rz_id)
        raise RazorpayError("Transaction not found.")

