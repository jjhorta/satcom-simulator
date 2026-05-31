# Stripe Setup — Quick Reference

**Constellation Simulator — Billing Configuration**

---

## Env vars to fill in `.env`

```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO=price_xxx_pro_monthly
STRIPE_PRICE_PRO_YEAR=price_xxx_pro_yearly
STRIPE_PRICE_ENT=price_xxx_ent_monthly
STRIPE_PRICE_ENT_YEAR=price_xxx_ent_yearly
APP_URL=https://hortahome.duckdns.org
```

## Products to create in Stripe Dashboard

| Product | Price | Stripe ID placeholder |
|---------|-------|----------------------|
| ConstellaSim Pro (monthly) | €299/mês | `price_pro_monthly` |
| ConstellaSim Pro (annual) | €2.990/ano | `price_pro_annual` |
| ConstellaSim Enterprise (monthly) | €999/mês | `price_enterprise_monthly` |
| ConstellaSim Enterprise (annual) | €9.990/ano | `price_enterprise_annual` |

## Webhook events needed

- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

## Frontend Price IDs to replace

File: `web/frontend/src/pages/BillingPage.tsx`
- Line ~96: `price_pro_monthly`
- Line ~126: `price_enterprise_monthly`
- Line ~155: `price_pro_annual`
- Line ~157: `price_enterprise_annual`

After updating → `npm run build` + `docker cp dist/. web-frontend-1:/app/dist/` + restart.

## Files involved

- `web/.env` — Stripe keys & price IDs
- `web/backend/app/stripe_integration.py` — Webhook + Checkout logic
- `web/backend/app/api/billing_routes.py` — Billing API endpoints
- `web/frontend/src/pages/BillingPage.tsx` — Pricing UI
- `web/backend/app/tier_config.py` — Tier limits & price mapping
- `web/backend/app/config.py` — Env var loading

## Full guide

See `documentation/stripe_configuration.md`
