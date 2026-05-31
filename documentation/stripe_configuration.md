# 💳 Stripe Configuration Guide

**Constellation Simulator — Org-Level Billing**

---

## Overview

Billing is **org-level**. The Stripe Customer object is attached to the **organization**, not the individual user. When a subscription changes, the webhook:

1. Updates `organizations.subscription_tier`
2. Promotes org members to the max role allowed by their new tier

### Pricing & Tiers

| Tier | Price | RBAC Role | Features |
|------|-------|-----------|----------|
| **Free** | €0 | `viewer` | 3 trial heatmaps (watermark) |
| **Pro** | **€299/mês** or €2.990/ano | `creator` | 500 jobs/mês, AI, sweep, QGIS |
| **Enterprise** | **€999/mês** or €9.990/ano | `team_manager` | Unlimited everything, API |

---

## 1. Create Products in Stripe Dashboard

### Step 1: Log in to Stripe

1. Go to https://dashboard.stripe.com/
2. You're in **Test mode** by default (toggle at left: "View test data")
3. Keep it in Test mode until everything is verified

### Step 2: Create Products & Prices

For each product below:
1. Go to **Products** → **+ Add Product**
2. Fill name, description, and pricing

#### Product 1: Pro Monthly

| Field | Value |
|-------|-------|
| Name | `ConstellaSim Pro` |
| Description | `Monthly subscription — 500 simulations/month, AI insights, parametric sweep, QGIS export` |
| Pricing model | **Recurring** |
| Amount | **€299.00** |
| Currency | **EUR** |
| Billing period | **Monthly** |

→ Annotate the **Price ID** (starts with `price_1...`)

#### Product 2: Pro Annual

| Field | Value |
|-------|-------|
| Name | `ConstellaSim Pro (Annual)` |
| Description | `Annual subscription — 500 simulations/month, AI insights, sweep, QGIS export — save ~17%` |
| Pricing model | **Recurring** |
| Amount | **€2,990.00** |
| Currency | **EUR** |
| Billing period | **Yearly** |

→ Annotate the **Price ID**

#### Product 3: Enterprise Monthly

| Field | Value |
|-------|-------|
| Name | `ConstellaSim Enterprise` |
| Description | `Enterprise — unlimited simulations, team management, API access, SLA` |
| Pricing model | **Recurring** |
| Amount | **€999.00** |
| Currency | **EUR** |
| Billing period | **Monthly** |

→ Annotate the **Price ID**

#### Product 4: Enterprise Annual

| Field | Value |
|-------|-------|
| Name | `ConstellaSim Enterprise (Annual)` |
| Description | `Enterprise annual — unlimited everything, API, SLA — save ~17%` |
| Pricing model | **Recurring** |
| Amount | **€9,990.00** |
| Currency | **EUR** |
| Billing period | **Yearly** |

→ Annotate the **Price ID**

---

## 2. Get API Keys

1. Go to **Developers** → **API Keys**
2. Copy the **Secret key** (starts with `sk_test_...`)

---

## 3. Configure Environment Variables

Edit `/home/lusospace/constellation_simulator/web/.env`:

```bash
# Add these lines:

# Stripe
STRIPE_SECRET_KEY=sk_test_YOUR_SECRET_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE
STRIPE_PRICE_PRO=price_YOUR_PRO_MONTHLY_ID
STRIPE_PRICE_PRO_YEAR=price_YOUR_PRO_ANNUAL_ID
STRIPE_PRICE_ENT=price_YOUR_ENT_MONTHLY_ID
STRIPE_PRICE_ENT_YEAR=price_YOUR_ENT_ANNUAL_ID
APP_URL=https://hortahome.duckdns.org
```

> ⚠️ **Important:** The `.env` file path inside the container is at the docker-compose level. On the host it's at:
> `/home/lusospace/constellation_simulator/web/.env`

---

## 4. Set Up Webhook Endpoint

### Why Webhooks?

Stripe sends webhook events for subscription lifecycle changes:
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

Our backend uses these to update org subscription tiers and promote user roles.

### Option A: Stripe CLI (Recommended for Test Mode)

Install Stripe CLI on the server:

```bash
# Install Stripe CLI
curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg.key | gpg --dearmor | sudo tee /usr/share/keyrings/stripe-cli.gpg
echo "deb [signed-by=/usr/share/keyrings/stripe-cli.gpg] https://packages.stripe.dev/stripe-cli/debian ./" | sudo tee /etc/apt/sources.list.d/stripe-cli.list
sudo apt update && sudo apt install stripe -y

# Login (will open browser)
stripe login

# Forward webhooks to local API
stripe listen --forward-to localhost:8000/api/billing/webhook
```

The CLI will output a **webhook signing secret** (`whsec_...`). Copy this to `.env`:

```
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET
```

> **On Docker:** The API runs inside a container. To forward webhooks to it:
> ```bash
> stripe listen --forward-to http://web-api-1:8000/api/billing/webhook
> ```
> (Stripe CLI needs to be on the Docker network)

### Option B: Stripe Dashboard (Production)

1. Go to **Developers** → **Webhooks** → **+ Add endpoint**
2. Endpoint URL: `https://hortahome.duckdns.org/constellation-simulator/api/billing/webhook`
3. Events to listen to:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Click **Add endpoint**
5. Copy the **Signing secret** (`whsec_...`) to `.env`

---

## 5. Testing

### Step 1: Restart the API container

```bash
cd /home/lusospace/constellation_simulator/web
docker compose restart api
```

### Step 2: Verify env vars are read

```bash
# Check that Stripe keys are loaded
docker exec web-api-1 python3 -c "
from app.config import Settings
s = Settings()
print(f'Stripe key set: {bool(s.stripe_secret_key)}')
print(f'Webhook secret set: {bool(s.stripe_webhook_secret)}')
print(f'Pro price: {s.stripe_price_pro}')
print(f'APP_URL: {s.app_url}')
"
```

### Step 3: Test checkout flow

1. Open `https://hortahome.duckdns.org/constellation-simulator/billing`
2. Click **Upgrade to Pro**
3. Should redirect to Stripe Checkout (test mode)
4. Use Stripe test card: `4242 4242 4242 4242` with any future date and CVC
5. After payment, you should be redirected back to `/billing?success=true`
6. Check your role was upgraded to `creator`

### Step 4: Test with Stripe CLI

```bash
# Trigger test events
stripe trigger customer.subscription.created

# Check the webhook was received
docker logs web-api-1 --tail 20 | grep "webhook\|stripe"
```

### Step 5: Verify the subscription API

```bash
# Login and get subscription info
TOKEN=$(curl -s -X POST https://hortahome.duckdns.org/constellation-simulator/api/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@constellasim.com&password=CHANGE_ME_ADMIN_PASSWORD' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" \
  https://hortahome.duckdns.org/constellation-simulator/api/billing/subscription | python3 -m json.tool
```

Expected response:
```json
{
  "tier": "pro",
  "subscription_status": "active",
  "role": "creator",
  "jobs_used": 0,
  "jobs_limit": 500,
  ...
}
```

---

## 6. Frontend Price IDs

The frontend BillingPage uses **hardcoded placeholder price IDs**. After creating real prices in Stripe, edit:

**File:** `/home/lusospace/constellation_simulator/web/frontend/src/pages/BillingPage.tsx`

Search for these lines and replace the price IDs:

```typescript
// Line ~96: Pro Monthly
priceId: 'price_pro_monthly',            // → 'price_YOUR_PRO_MONTHLY_ID'

// Line ~126: Enterprise Monthly
priceId: 'price_enterprise_monthly',      // → 'price_YOUR_ENT_MONTHLY_ID'

// Line ~155: Pro Annual (when annual toggle is on)
? 'price_pro_annual'                     // → 'price_YOUR_PRO_ANNUAL_ID'

// Line ~157: Enterprise Annual
: 'price_enterprise_annual'              // → 'price_YOUR_ENT_ANNUAL_ID'
```

After updating, rebuild the frontend:

```bash
cd /home/lusospace/constellation_simulator/web/frontend
npm run build
docker cp dist/. web-frontend-1:/app/dist/
docker restart web-frontend-1
```

---

## 7. Going Live

When you're ready to accept real payments:

1. **Complete your Stripe account details** (business profile, bank account)
2. **Toggle Stripe to Live mode** (dashboard toggle)
3. **Create new Products & Prices** in Live mode (same steps as above)
4. **Update `.env`** with live `sk_live_...` keys and live `price_...` IDs
5. **Update webhook endpoint** in Stripe Dashboard to point to production URL
6. **Update `STRIPE_WEBHOOK_SECRET`** with the live webhook secret
7. **Test with a real card** (make a small test payment then refund)

> ⚠️ **Test vs Live:** Test keys start with `sk_test_`, live keys start with `sk_live_`. Test price IDs start with `price_1...` and are different from live price IDs. Never mix them.

---

## 8. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Checkout returns 500 | Stripe key is empty or invalid | Check `.env` has `STRIPE_SECRET_KEY` set |
| Webhook returns 400 | Invalid signature | Check `STRIPE_WEBHOOK_SECRET` matches Stripe Dashboard |
| User not upgraded after payment | Webhook not received | Check Stripe Dashboard webhook logs |
| `price_pro_monthly` error | Price ID placeholder used | Replace with real `price_xxx` ID |
| "No organization found" | User has no org | Admin must create an org (via Admin page or DB) |
| "billing:manage" permission denied | User role is too low | Only `admin`, `team_manager`, and `creator` can manage billing |

### Quick verification script

Run this inside the API container to verify Stripe connection:

```bash
docker exec web-api-1 python3 -c "
from app.config import Settings
import stripe

s = Settings()
stripe.api_key = s.stripe_secret_key

# Test: list products
products = stripe.Product.list(limit=5)
print(f'Products: {len(products.data)}')
for p in products.data:
    print(f'  - {p.name} (id: {p.id})')

# Test: list prices
prices = stripe.Price.list(limit=10)
print(f'Prices: {len(prices.data)}')
for p in prices.data:
    print(f'  - {p.id} | {p.nickname or \"unnamed\"} | {p.unit_amount/100:.0f}{p.currency.upper()}/{p.recurring.interval}')
"
```
