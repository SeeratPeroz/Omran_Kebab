# Omran Kebab — Project Documentation

_Written 2026-10-03 as a snapshot of the project state before continuing development._

## 1. Overview

Django website for **Omran Kebab**, a Turkish restaurant. One-page marketing site plus:

- Online food ordering with modular product options (sauce, size, extras)
- Payment by Stripe (card) or cash on delivery/pickup
- Order tracking by order number
- Table reservations
- Staff dashboard and kitchen screen (login required)
- Events section (private/individual celebrations)

UI language is **German**; order status codes are English uppercase.
Deployed on Render (`omran-kebab.onrender.com`), served with Gunicorn + WhiteNoise.

## 2. Tech stack

| Area | Choice |
|---|---|
| Backend | Django (Python 3.13 per `.pyc` files) |
| DB | SQLite (`db.sqlite3`, committed to git); `psycopg2-binary` is in requirements for a possible Postgres move |
| Static files | WhiteNoise (`CompressedManifestStaticFilesStorage`), `STATIC_ROOT=staticfiles/` |
| Payments | Stripe (Checkout Sessions + webhook) |
| Images | Pillow, uploads in `media/products/`, `media/events/` |
| Frontend | Django templates, Bootstrap 5, Bootstrap Icons, AOS (BootstrapMade-style template in `static/assets/`) |
| Server | Gunicorn |

`requirements.txt`: Django, gunicorn, whitenoise, psycopg2-binary, Pillow, stripe.

## 3. Folder structure

```
Omran_Kebab/
├── manage.py
├── requirements.txt
├── db.sqlite3                      # dev DB (tracked in git, currently modified)
├── OK_Onlie_Food_Ordering/         # Django project (settings, urls, wsgi, asgi)
├── FoodOrdering/                   # the single app
│   ├── models.py  views.py  forms.py  admin.py  urls.py  tests.py
│   ├── migrations/0001 … 0007
│   └── management/commands/seed_omran_wolt.py
├── templates/
│   ├── index.html                  # home, composes sections/
│   ├── cart.html  order_success.html  track_order.html
│   ├── login.html  admin.html  kitchen.html  starter-page.html
│   ├── includes/  base.html header.html footer.html
│   └── sections/  startseite, speisekarte, ueber_uns, events, galerie, kontakt
├── static/assets/                  # css (main.css, style.css), js (main.js), img, vendor libs
├── media/products/                 # uploaded product images (.avif)
├── .github/copilot-instructions.md # detailed architecture notes (kept in sync with this doc)
└── django_app/                     # UNRELATED, untracked — see §10
```

## 4. Data model (`FoodOrdering/models.py`)

**Menu**
- `Category` — name, slug, is_active, sort_order
- `Product` — category (PROTECT), name, slug, description, price, image, is_available
- `OptionGroup` — reusable group (e.g. Sauce, Size, Extras) with default rules: `is_required`, `min_select`, `max_select` (1 = radio, >1 = checkboxes)
- `Option` — belongs to a group, `price_delta`
- `ProductOptionGroup` — attaches a group to a product, with optional per-product overrides; `effective_is_required/min_select/max_select()` fall back to the group's defaults

**Orders**
- `Order` — status `CART → PLACED → PREPARING → DELIVERING → COMPLETED / CANCELLED`; customer/address fields; `payment_method` (`CASH`/`STRIPE`), `is_paid`, Stripe session / payment-intent ids; `order_number` (`OK-YYYYMMDD-6HEX`, via `ensure_order_number()`). A `CART`-status order *is* the shopping cart.
- `OrderItem` — product, quantity, `price_at_time` (snapshot). No unique(order, product): same product with different options = separate lines.
- `OrderItemOption` — chosen options with `price_delta_at_time` snapshot.

**Other**
- `TableReservation` — name, email, phone, date, time, people, message, status (`new/confirmed/cancelled`)
- `Event` — title, slug, description, price, image, is_active, sort_order

All registered in `admin.py` (Product admin has option-group inline and image preview).

## 5. URLs / views (`FoodOrdering/urls.py`, `views.py`)

| URL | View | Purpose |
|---|---|---|
| `/` | `home` | Landing page (menu, events, gallery, contact, reservation form) |
| `/login/`, `/logout/` | `login_page`, `logout_user` | Staff auth |
| `/dashboard/` | `admin_panel` | Staff overview of orders & reservations (login required) |
| `/dashboard/order/<id>/status/` | `update_order_status` | POST status change |
| `/dashboard/reservation/<id>/status/` | `update_reservation_status` | POST status change |
| `/kitchen/`, `/kitchen/poll/` | `kitchen_view`, `kitchen_poll` | Kitchen screen, polled for new orders (JSON) |
| `/cart/` | `cart_detail` | View cart |
| `/cart/add/<product_id>/` | `add_to_cart` | Atomic; validates option rules; AJAX → JSON, else redirect |
| `/cart/remove/<product_id>/` | `remove_from_cart` | Remove line |
| `/cart/count/` | `get_cart_count` | Badge count |
| `/checkout/` | `checkout` | Summary |
| `/checkout/save-info/` | `save_checkout_info` | POST address/phone, validated by `_validate_checkout_fields` |
| `/checkout/create-session/` | `create_stripe_checkout_session` | Builds Stripe line items (cents) |
| `/checkout/success/`, `/checkout/cancel/` | `checkout_success`, `checkout_cancel` | Stripe return pages |
| `/stripe/webhook/` | `stripe_webhook` | CSRF-exempt, verifies signature, marks order PLACED/paid |
| `/checkout/cash/` | `place_cash_order` | Status PLACED, `is_paid=False` |
| `/order/success/<order_number>/` | `order_success` | Confirmation |
| `/order/track/` | `track_order` | Look up by order number |
| `/reservation/create/` | `create_reservation` | POST, `TableReservationForm` (1–50 people) |
| `/admin/` | Django admin | |

Commented-out routes (menu, category, product detail, cart update) are unused — menu lives on the home page.

## 6. Key workflows

**Cart / order:** session holds `cart_id`; `get_cart()` guarantees a valid CART-status order. `add_to_cart` reads form keys `group_<id>` (radio) or `group_<id>[]` (checkbox), enforces required/min/max, and deletes the new OrderItem if invalid.

**Card payment:** `save_checkout_info` → `create_stripe_checkout_session` → Stripe → webhook marks paid/PLACED; `checkout_success` is the browser return.
Stripe line item name format: `ProductName | Group: Option | Group: Option`.

**Cash payment:** `place_cash_order` sets PLACED, unpaid.

**Staff:** log in → `/dashboard/` to manage orders/reservations, `/kitchen/` for live kitchen view.

## 7. Seed data

```bash
python manage.py seed_omran_wolt
```
Idempotent (`get_or_create`, `@transaction.atomic`). Creates categories, products, and option groups "Soße deiner Wahl", "Käse deiner Wahl", "Portion deiner Wahl" etc.

## 8. Running locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_omran_wolt        # optional
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/.

## 9. Conventions

- German UI text; English uppercase status codes
- `@transaction.atomic` for multi-step writes
- Always `prefetch_related("products__product_option_groups__group__options")` when rendering menus (avoids N+1 in option modals)
- Django `messages` for user feedback
- Don't delete orders; transition status instead
- Slugs auto-generated with `slugify()`, unique

## 10. Known issues / to-do (found during review)

**Security / config — fix before real production use**
1. `settings.py` has a hard-coded `SECRET_KEY` and `DEBUG = True`. Move to environment variables.
2. Stripe keys are placeholders (`sk_live_or_test_...`, `whsec_...`) in settings. Load from env vars; never commit real keys.
3. `ALLOWED_HOSTS` is hard-coded; no `CSRF_TRUSTED_ORIGINS` for the Render domain (may be needed for POSTs on HTTPS).
4. `db.sqlite3` is tracked in git and has uncommitted changes — it contains real orders/users. Consider `.gitignore` + a real database (Postgres on Render; SQLite files are wiped on Render redeploys).
5. Uploaded media (`media/`) is served by Django only when `DEBUG=True`; on Render the disk is ephemeral → use persistent storage (S3/Cloudinary) for production.

**Repo hygiene**
6. No `.gitignore`: `__pycache__/*.pyc`, `.DS_Store` files are committed.
7. `README.md` is just a title.
8. `STATICFILES_STORAGE` is deprecated in newer Django (use `STORAGES`).
9. `TIME_ZONE = 'UTC'`, `LANGUAGE_CODE = 'en-us'` — restaurant is German; consider `Europe/Berlin` / `de`.
10. `tests.py` is essentially empty — no automated tests for the cart option validation or Stripe webhook.
11. Typo in project package name `OK_Onlie_Food_Ordering` ("Onlie") — harmless, renaming is invasive.
12. `django_app/` (untracked) is a separate, unrelated project ("NovaTik" Three.js landing page with its own `manage.py`). It does not belong in this repo; move or delete it.

## 11. Git state at time of writing

Branch `main`, 18 commits; latest: "Logo", "fix static files config", "add requirements", "Allow Hosts". Uncommitted: modified `db.sqlite3`, untracked `django_app/`.

---

_Next steps: to be decided — continue the project from here._
