"""
DISCLAIMER:
This script is provided "AS IS" for educational and demonstration purposes only.
It is not production-ready and comes with no warranties, express or implied.
You are responsible for reviewing, testing, and securing this code before using it in any live environment.

We strongly recommend using this script only in a **sandbox/test environment** (e.g., with Stripe test keys and test payment methods).
Do not run this script against a live production account without appropriate safeguards.

Use of this script with your Stripe account is at your own risk.
Ensure API keys are stored securely (e.g., environment variables) and sensitive data is handled appropriately.

For full documentation, refer to: https://stripe.com/docs/api
"""

import stripe

# Set your Stripe secret key
stripe.api_key = "rk_test_..."  # Use environment variables for this in production

# ================================
# 1. CREATE PRODUCT
# ================================

# Define the product for your streaming service with metered billing
# Products are containers for pricing plans
product = stripe.Product.create(
    name="Streaming GB Metered Plan B",  # Plan name as seen by customers
    description="Metered plan: $10.99 for 100GB, then $1.00 per 10GB"  # Clear explanation
)

# ================================
# 2. CREATE BASE FLAT RATE PRICE
# ================================

# This flat price covers the initial base allowance (e.g., first 100 GB)
flat_price = stripe.Price.create(
    product=product.id,          # Link to the product above
    currency="usd",              # Price in USD
    unit_amount=1099,            # $10.99 (Stripe uses cents)
    billing_scheme="per_unit",   # Charges a fixed price per unit (1 unit = 1 subscription)
    recurring={
        "usage_type": "licensed",    # Licensed = flat rate; billed regardless of usage
        "interval": "month",         # Monthly recurring charge
    },
)

# ================================
# 3. CREATE METER & OVERAGE PRICE
# ================================

# Step 3.1 – Create a Meter to track usage (new Metering API)
# The meter tracks events named "streaming_per_gb" and maps the `value` to GB used
meter = stripe.billing.Meter.create(
    display_name="Streaming GB Usage",  # Friendly name for dashboard
    event_name="streaming_per_gb",      # Usage events must match this name
    #be aware this should be unique name in your account, you can use it to track difrent usage of 
    #difrent services in your streaming service ( HD VS FullHD ) and set difrent pricing for each
    
    default_aggregation={"formula": "sum"},  # Aggregate all events via summation
    customer_mapping={
        "event_payload_key": "stripe_customer_id",  # Map usage events to customer by ID
        "type": "by_id"
    },
    value_settings={
        "event_payload_key": "value"  # Where to read usage value (e.g., GB) from in the event payload
    },
)

print("Meter ID:", meter.id)  # Useful for reference or debugging

# Step 3.2 – Create a metered price using the Meter
# This will charge $1.00 per additional 10 GB over the initial 100 GB
overage_price = stripe.Price.create(
    product=product.id,
    currency="usd",
    billing_scheme="tiered",  # Use tiered pricing to handle base and overage logic
    recurring={
        "usage_type": "metered",       # Bill based on reported usage
        "interval": "month",
        "meter": meter.id              # Link this price to the Meter we just created
    },
    tiers_mode="graduated",  # Graduated means apply the pricing tier by tier (not flat-rate per tier)
    tiers=[
        {"up_to": 100, "unit_amount_decimal": "0"},    # (0 - 100 units) First 100 GB is charged $0, this translates to 100 units x 0.
        {"up_to": "inf", "unit_amount_decimal": "10"}, # ( 101 - infint units ) charge $1.00 per 10 GB beyond 100 GB, translates to $0.1 per 1 unit.
    ],
    nickname="GB Overage Meter"  # For display in the Stripe dashboard
)

# ================================
# 4. CREATE CUSTOMER
# ================================

# Create a new test customer
customer = stripe.Customer.create(
    email="testuserB@example.com",       # Test email
    name="Test User B",                  # Optional: set customer name
    payment_method="pm_card_visa"        # Stripe test card (automatically approved in test mode)
)

# ================================
# 5. ATTACH PAYMENT METHOD
# ================================

# Get the customer's payment methods (you can also skip this if manually attaching `pm_card_visa`)
customer_payment_methods = stripe.Customer.list_payment_methods(customer.id)

# Attach the first available payment method
stripe.PaymentMethod.attach(
    customer_payment_methods.data[0].id,
    customer=customer.id
)

# Set the payment method as the default for invoicing
stripe.Customer.modify(
    customer.id,
    invoice_settings={
        "default_payment_method": customer_payment_methods.data[0].id
    },
)

# ================================
# 6. CREATE SUBSCRIPTION
# ================================

# Create a subscription with two items:
# - The base flat monthly price ($10.99)
# - The usage-based price for GB overage
subscription = stripe.Subscription.create(
    customer=customer.id,
    items=[
        {"price": flat_price.id, "quantity": 1},  # Flat price charged monthly
        {"price": overage_price.id},             # Usage-based price tied to meter
    ],
    expand=["latest_invoice.payment_intent"],    # Expand to get payment info inline
)

# ================================
# 7. REPORT USAGE EVENT
# ================================

# Report usage of 150 GB for this billing cycle
# Stripe will use the meter logic to calculate the overage and bill accordingly:
# - First 100 GB is free (0 cost)
# - 50 GB overage = 5 x 10GB units = $5.00 charge
meter_event = stripe.billing.MeterEvent.create(
    event_name="streaming_per_gb",  # Must match the Meter's event_name
    payload={
        "value": "150",                # Reported usage in GB
        "stripe_customer_id": customer.id  # Must match the customer_mapping field in Meter
    }
)

# ================================
# END OF SCRIPT
# ================================

# Notes:
# - Stripe will bill the customer for both the flat monthly fee and metered overage on the next invoice.
# - You must call `MeterEvent.create()` periodically (e.g., daily, hourly, or real-time) to report usage.
# - You can track all usage and invoice details in your Stripe Dashboard under the customer/subscription.
