# Omran Kebab - AI Agent Instructions

## Project Overview
Omran Kebab is a Django-based food ordering and reservation system for a Turkish restaurant. It features dynamic menu options (modular product extras), Stripe payment integration, order tracking, and table reservations.

## Architecture & Key Components

### Data Model Hierarchy
- **Category** → **Product** → **ProductOptionGroup** → **Option**
  - Products belong to categories (Döner, Specials, Vegetarian, etc.)
  - Options are flexible add-ons (sauce, size, extras) organized in groups
  - `ProductOptionGroup` allows per-product override of option rules (required, min/max selections)

- **Order** (cart/placed) → **OrderItem** (line items with snapshot prices) → **OrderItemOption** (chosen options with price deltas at purchase time)
  - Critical: OrderItem does NOT have `unique_together(order, product)` because same product with different options = separate lines
  - Price snapshots prevent issues if option prices change later

### Key Files & Responsibilities
- [FoodOrdering/models.py](FoodOrdering/models.py): All data models including Order workflow and payment tracking
- [FoodOrdering/views.py](FoodOrdering/views.py): Order workflow (add to cart, checkout), Stripe webhook, reservation handling
- [FoodOrdering/forms.py](FoodOrdering/forms.py): TableReservationForm with people count validation
- [FoodOrdering/urls.py](FoodOrdering/urls.py): Routes for cart, checkout, payment, order tracking
- [OK_Onlie_Food_Ordering/settings.py](OK_Onlie_Food_Ordering/settings.py): Stripe API keys, static/media paths

### Option Group Rules
When attaching option groups to products:
- `effective_is_required()`, `effective_min_select()`, `effective_max_select()` on `ProductOptionGroup` inherit from `OptionGroup` if null
- Examples: Sauce (required, max 1 = radio), Extras (optional, max 3 = checkboxes)
- Validation happens in `add_to_cart`: rejects if selected options violate constraints, deletes invalid OrderItem

## Critical Workflows

### Cart & Order Flow
1. **add_to_cart** (`views.add_to_cart`): Creates OrderItem + validates option selections per ProductOptionGroup rules
   - Form keys: `group_<id>` for radio (single), `group_<id>[]` for checkbox (multiple)
   - Uses `@transaction.atomic` to ensure atomicity
   - Returns JSON if AJAX (`x-requested-with` header), else redirects to home

2. **Checkout → Payment**:
   - `checkout`: Display cart summary
   - `save_checkout_info`: Save address/phone before payment
   - `create_stripe_checkout_session`: Convert OrderItems to Stripe line_items (amounts in cents)
   - Stripe webhook processes payment, marks order as PLACED/PAID
   - `checkout_success`: Redirect after successful Stripe session

3. **Order Number Generation**: Format `OK-YYYYMMDD-6HEX` (example: OK-20260113-7F3A2B)

### Seed Command
- **seed_omran_wolt.py**: Populates categories, products, option groups, and options
- Run: `python manage.py seed_omran_wolt`
- Uses `@transaction.atomic`, `get_or_create` for idempotency

## Performance Patterns

### Prefetch & Select Related
Always prefetch option groups + options when displaying menus or carts:
```python
categories = (
    Category.objects.filter(is_active=True)
    .prefetch_related("products__product_option_groups__group__options")
)
```
Prevents N+1 queries when rendering modals with options.

### Cart Retrieval
- Session-based: `request.session.get("cart_id")`
- Always call `get_cart()` to ensure valid CART-status Order exists
- Use `select_related` + `prefetch_related` for cart items display

## Language & Conventions
- German UI text (exceptions: order status values in English uppercase: CART, PLACED, PREPARING, etc.)
- Email validation for reservations and orders
- Timestamps: `auto_now_add` for creation, `auto_now` for updates
- Slugs: auto-generated from names using `slugify()`, required unique

## Payment Integration
- **Stripe API**: Secret key in settings.STRIPE_SECRET_KEY, public in STRIPE_PUBLISHABLE_KEY
- **Line items for Stripe**: Include product name + options concatenated (format: "ProductName | Group: Option | Group: Option")
- **Webhook**: Validates Stripe signature, updates order status on successful payment
- **Alternative**: Cash orders use `place_cash_order` (status=PLACED, is_paid=False)

## Testing & Validation
- Form validation: `TableReservationForm.clean_people()` ensures 1–50 people
- Option selection: Enforces min/max constraints before creating OrderItem
- CSRF protection: Enabled for all POST endpoints (Stripe webhook uses CSRF exemption)

## Common Patterns to Maintain
1. **Atomic transactions**: Use `@transaction.atomic` for multi-step data writes (e.g., create OrderItem + options)
2. **Error handling**: Use Django messages framework for user feedback; delete invalid OrderItems on constraint violations
3. **Status choices**: Define in model Meta or inline tuples; always reference as constants
4. **Soft delete**: No deletion of orders/items in production—use status transitions instead
5. **Prefetch for templates**: Frontend modal rendering requires prefetched option groups; missing prefetch = performance regression
