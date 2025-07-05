"""
DISCLAIMER:
This script is provided "AS IS" for educational and demonstration purposes only.
It is not production-ready and comes with no warranties, express or implied.
You are responsible for reviewing, testing, and securing this code before using it in any live environment.

We strongly recommend using this script only in a **sandbox/test environment** (e.g., with Stripe test keys and test payment methods).
Do not run this script against a live production account without appropriate safeguards.

For full documentation and best practices, visit: https://stripe.com/docs/api
"""

import stripe

# Set your Stripe secret key (use environment variables or secret manager in production)
stripe.api_key = "rk_test_..."  #  NEVER hard-code secret keys in real applications

# ================================
# 1. CREATE PRODUCT
# ================================

# A Product in Stripe represents a service you're selling – in this case, a flat-rate streaming subscription
product_plan_a = stripe.Product.create(
    name="Streaming Unlimited Plan A",                   # Product name shown to customers
    description="Unlimited monthly access to streaming service"  # Product description
)

# ================================
# 2. CREATE PRICE
# ================================

# Create a recurring monthly price of $24.99 for the product above
price_plan_a = stripe.Price.create(
    unit_amount=2499,                  # Price in cents ($24.99)
    currency="usd",                    # Currency code
    recurring={"interval": "month"},   # Charge monthly
    product=product_plan_a.id,         # Associate price with the product
)

# ================================
# 3. CREATE CUSTOMER
# ================================

# Create a test customer with a default payment method (Stripe test card)
customer = stripe.Customer.create(
    email="testuserA@steamingexample.com",  # Test email
    name="Test User A",                     # Customer name
    payment_method="pm_card_visa"           # Built-in Stripe test card (auto-approves in sandbox)
)

# ================================
# 4. ATTACH PAYMENT METHOD
# ================================

# Fetch available payment methods associated with the customer
customer_payment_methods = stripe.Customer.list_payment_methods(customer.id)

# Attach the first available payment method to the customer account
stripe.PaymentMethod.attach(
    customer_payment_methods.data[0].id,
    customer=customer.id
)

# ================================
# 5. SET DEFAULT PAYMENT METHOD
# ================================

# Set the attached payment method as the default for invoices
stripe.Customer.modify(
    customer.id,
    invoice_settings={
        "default_payment_method": customer_payment_methods.data[0].id
    },
)

# ================================
# 6. CREATE SUBSCRIPTION
# ================================

# Create the subscription for the customer using the flat monthly plan
subscription = stripe.Subscription.create(
    customer=customer.id,
    items=[{"price": price_plan_a.id}],                # Add flat-rate price as a subscription item
    expand=["latest_invoice.payment_intent"],          # Expand invoice payment details inline
)

# ================================
# END OF SCRIPT
# ================================


# Notes:
# - Use `sk_test_...` API keys and `pm_card_visa` for testing only.
# - Do NOT use in production without securing keys, adding error handling, and validating inputs.
# - Consider listening to `invoice.payment_succeeded` webhook to handle post-payment actions.
