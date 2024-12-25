class EmptyBasketException(Exception):
    """Raised when the basket is empty during payment processing."""

    def __init__(self, message="The basket is empty. Please add items to proceed with checkout."):
        self.message = message
        super().__init__(self.message)


class MissingShippingAddressException(Exception):
    """Raised when no shipping address is provided for an order requiring shipping."""

    def __init__(self, message="A shipping address is required to complete this transaction."):
        self.message = message
        super().__init__(self.message)


class MissingShippingMethodException(Exception):
    """Raised when no shipping method is selected for an order requiring shipping."""

    def __init__(self, message="Please select a shipping method before proceeding."):
        self.message = message
        super().__init__(self.message)


class InvalidBasket(Exception):
    """
    Raised when the user's basket can't be submitted (e.g., it has zero cost or contains invalid items).

    The message of this exception is shown to the customer.
    """

    def __init__(self, message="This basket cannot be processed. Please review your items."):
        self.message = message
        super().__init__(self.message)


class RazorpayError(Exception):
    """Generic exception for Razorpay-related errors."""

    def __init__(self, message="An error occurred with Razorpay. Please try again later.", error_code=None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class PaymentProcessingException(RazorpayError):
    """Raised when there's an issue with processing the payment."""

    def __init__(self, message="Payment processing failed.", error_code=None):
        super().__init__(message, error_code)


class PaymentCaptureFailedException(RazorpayError):
    """Raised when payment capture fails after authorization."""

    def __init__(self, message="Payment capture failed. Please try again or contact support.", error_code=None):
        super().__init__(message, error_code)


class PaymentAuthorizationFailedException(RazorpayError):
    """Raised when payment authorization fails."""

    def __init__(self, message="Payment authorization failed. Please check your payment details.", error_code=None):
        super().__init__(message, error_code)


class TransactionLimitExceededException(RazorpayError):
    """Raised when the transaction exceeds allowed limits."""

    def __init__(self, message="The transaction amount exceeds the allowed limit.", error_code=None):
        super().__init__(message, error_code)
