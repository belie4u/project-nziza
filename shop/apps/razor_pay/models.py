from __future__ import unicode_literals
from uuid import uuid4

from django.db import models
from oscar.core.compat import AUTH_USER_MODEL


def generate_id():
    return uuid4().hex[:28]


class RazorpayTransaction(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='razorpay_transactions'
    )
    email = models.EmailField(null=True, blank=True)
    txnid = models.CharField(
        max_length=32, db_index=True, default=generate_id
    )
    basket_id = models.CharField(
        max_length=12, null=True, blank=True, db_index=True
    )

    amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, null=True, blank=True)

    INITIATED, AUTHORIZED, CAPTURED, CAPTURE_FAILED, AUTH_FAILED = (
        "initiated", "authorized", "captured", "capture_failed", "auth_failed"
    )
    STATUS_CHOICES = (
        (INITIATED, 'Initiated'),
        (AUTHORIZED, 'Authorized'),
        (CAPTURED, 'Captured'),
        (CAPTURE_FAILED, 'Capture Failed'),
        (AUTH_FAILED, 'Auth Failed'),
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES)

    rz_id = models.CharField(
        max_length=32, null=True, blank=True, db_index=True
    )

    error_code = models.CharField(max_length=32, null=True, blank=True)
    error_message = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        ordering = ('-date_created',)
        app_label = 'razor_pay'

    @property
    def is_successful(self):
        return self.status == self.CAPTURED

    @property
    def is_pending(self):
        return self.status == self.AUTHORIZED

    @property
    def is_failed(self):
        return self.status not in (self.CAPTURED, self.AUTHORIZED, self.INITIATED)

    def __str__(self):
        return f'razorpay payment: {self.rz_id or "No ID"}'

    def mark_as_abandoned(self):
        if self.status == self.INITIATED:
            self.status = self.AUTH_FAILED
            self.save()
