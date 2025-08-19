# Stripe billing for subscription and usage-based pricing
import stripe
from decimal import Decimal
from typing import Dict, Any
from backend.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class BillingManager:
    def __init__(self):
        self.pricing_tiers = {
            "starter": {"monthly": 29, "requests": 1000},
            "professional": {"monthly": 99, "requests": 10000},
            "enterprise": {"monthly": 299, "requests": 100000}
        }
    
    async def create_customer(self, email: str, name: str) -> str:
        """Create Stripe customer"""
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={"product": "NextAGI"}
        )
        return customer.id
    
    async def create_subscription(self, customer_id: str, tier: str) -> Dict:
        """Create subscription for user"""
        price_id = settings.STRIPE_PRICE_IDS[tier]
        
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            metadata={"tier": tier}
        )
        
        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end
        }
    
    async def track_usage(self, subscription_id: str, usage_count: int):
        """Track usage-based billing"""
        stripe.SubscriptionItem.create_usage_record(
            subscription_item=subscription_id,
            quantity=usage_count,
            timestamp=int(time.time())
        )