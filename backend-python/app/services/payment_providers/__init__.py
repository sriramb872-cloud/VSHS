# backend-python/app/services/payment_providers/__init__.py
"""Payment providers for the subscription domain.

``MockPaymentProvider`` (INTERNAL) is imported eagerly; ``RazorpayProvider``
is imported lazily by ``PaymentService.get_provider`` so environments that
only ever run the mock never need the Razorpay SDK installed.
"""

from app.services.payment_providers.base import (  # noqa: F401
    OrderRequest,
    PaymentOrder,
    PaymentProvider,
    PaymentProviderError,
    RefundResult,
    VerificationResult,
    to_paise,
)
