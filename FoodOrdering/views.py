from decimal import Decimal
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Prefetch
from .models import (
    Product, Order, OrderItem, Category,
    ProductOptionGroup, Option, OrderItemOption
)


def home(request):
    # Speed: prefetch everything needed for modals (products + option groups + options)
    categories = (
        Category.objects.filter(is_active=True)
        .prefetch_related(
            "products",
            "products__product_option_groups__group__options",
        )
    )
    return render(request, "index.html", {"categories": categories})


def get_cart(request):
    cart_id = request.session.get("cart_id")
    cart = None

    if cart_id:
        cart = Order.objects.filter(id=cart_id, status="CART").first()

    if not cart:
        cart = Order.objects.create(full_name="", phone="", status="CART")
        request.session["cart_id"] = cart.id

    return cart


def _parse_quantity(request):
    try:
        q = int(request.POST.get("quantity", "1"))
        return max(1, q)
    except (TypeError, ValueError):
        return 1


@transaction.atomic
def add_to_cart(request, product_id):
    """
    Expects POST from modal.

    POST format we use:
    - quantity
    - For RADIO groups (max_select == 1):   group_<group_id> = <option_id>
    - For CHECKBOX groups (max_select > 1): group_<group_id>[] = [<option_id>, ...]
    """
    product = get_object_or_404(Product, id=product_id, is_available=True)

    if request.method != "POST":
        messages.error(request, "Bitte wähle Optionen aus und füge dann zum Warenkorb hinzu.")
        return redirect("home")

    cart = get_cart(request)
    quantity = _parse_quantity(request)

    # Create a new line item always (because same product can have different options)
    item = OrderItem.objects.create(
        order=cart,
        product=product,
        quantity=quantity,
        price_at_time=product.price,
    )

    # Load option groups attached to this product
    pogs = (
        ProductOptionGroup.objects
        .select_related("group")
        .filter(product=product)
        .order_by("sort_order", "group__sort_order", "group__name")
    )

    # Validate + save selected options
    for pog in pogs:
        group = pog.group

        min_select = pog.effective_min_select()
        max_select = pog.effective_max_select()
        is_required = pog.effective_is_required()

        # If required but min_select is 0, we treat it as 1 (sane UX)
        if is_required and min_select == 0:
            min_select = 1

        radio_key = f"group_{group.id}"
        checkbox_key = f"group_{group.id}[]"

        if max_select and max_select > 1:
            raw_ids = request.POST.getlist(checkbox_key)
        else:
            v = request.POST.get(radio_key)
            raw_ids = [v] if v else []

        raw_ids = [x for x in raw_ids if x]  # drop empty
        count = len(raw_ids)

        # Rules
        if count < min_select:
            item.delete()
            messages.error(request, f"Bitte wähle mindestens {min_select} Option(en) bei: {group.name}")
            return redirect("home")

        if max_select and count > max_select:
            item.delete()
            messages.error(request, f"Zu viele Optionen gewählt bei: {group.name} (max. {max_select})")
            return redirect("home")

        # Fetch options and verify they belong to THIS group and are active
        opts = list(
            Option.objects.filter(
                id__in=raw_ids,
                group=group,
                is_active=True,
            )
        )
        if len(opts) != count:
            item.delete()
            messages.error(request, f"Ungültige Auswahl bei: {group.name}")
            return redirect("home")

        # Save snapshots
        for opt in opts:
            OrderItemOption.objects.create(
                order_item=item,
                option=opt,
                price_delta_at_time=opt.price_delta,
            )

 # ✅ Return JSON for AJAX, otherwise redirect back to menu
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "message": "Zum Warenkorb hinzugefügt."})

    return redirect("home")

def cart_detail(request):
    cart = get_cart(request)
    cart_items = cart.items.select_related("product").prefetch_related("chosen_options__option__group")
    return render(request, "cart.html", {"cart": cart, "cart_items": cart_items})



def remove_from_cart(request, product_id):
    """
    Your old behavior: removes ALL cart lines of that product.
    Better UX is removing by item_id; keep this for now.
    """
    cart = get_cart(request)
    OrderItem.objects.filter(order=cart, product_id=product_id).delete()
    return redirect("cart_detail")


def checkout(request):
    cart = get_cart(request)
    cart_items = (
        cart.items.select_related("product")
        .prefetch_related("chosen_options__option__group")
    )
    return render(request, "checkout.html", {"cart": cart, "cart_items": cart_items})


# Stripe integration views Payement
stripe.api_key = settings.STRIPE_SECRET_KEY


def _order_line_items_for_stripe(cart):
    """
    Stripe wants amounts in cents.
    """
    line_items = []
    for item in cart.items.select_related("product").prefetch_related("chosen_options__option__group"):
        # Build name including options
        option_parts = []
        for cho in item.chosen_options.all():
            option_parts.append(f"{cho.option.group.name}: {cho.option.name}")
        option_text = " | ".join(option_parts)

        product_name = item.product.name
        full_name = product_name if not option_text else f"{product_name} ({option_text})"

        unit_amount_eur = item.unit_total()  # Decimal
        unit_amount_cents = int((unit_amount_eur * 100).quantize(Decimal("1")))

        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": full_name},
                "unit_amount": unit_amount_cents,
            },
            "quantity": item.quantity,
        })
    return line_items


def create_stripe_checkout_session(request):
    cart = get_cart(request)

    if not cart.phone or not cart.address_line or not cart.postal_code or not cart.city:
        return JsonResponse({"ok": False, "message": "Bitte zuerst Name/Telefon/Adresse eingeben."}, status=400)

    if cart.items.count() == 0:
        return JsonResponse({"ok": False, "message": "Warenkorb ist leer."}, status=400)

    success_url = request.build_absolute_uri(reverse("checkout_success"))
    cancel_url = request.build_absolute_uri(reverse("checkout_cancel"))

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=_order_line_items_for_stripe(cart),
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"order_id": str(cart.id)},
    )

    cart.payment_method = "STRIPE"
    cart.stripe_session_id = session["id"]
    cart.save(update_fields=["payment_method", "stripe_session_id"])

    return JsonResponse({"ok": True, "checkout_url": session.url})


def checkout_success(request):
    cart = get_cart(request)
    session_id = request.GET.get("session_id")

    # If we have session_id, verify it:
    if session_id:
        session = stripe.checkout.Session.retrieve(session_id)
        if session and session.get("payment_status") == "paid":
            cart.ensure_order_number()
            cart.status = "PLACED"
            cart.is_paid = True
            cart.placed_at = timezone.now()
            cart.stripe_payment_intent_id = session.get("payment_intent", "") or ""
            cart.save(update_fields=["status", "is_paid", "placed_at", "stripe_payment_intent_id", "order_number"])

            # optional: clear cart session so next order starts fresh
            request.session.pop("cart_id", None)

    return render(request, "checkout_success.html", {"cart": cart})


def checkout_cancel(request):
    return render(request, "checkout_cancel.html")


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        return HttpResponse(status=400)

    # Handle successful payment
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")

        if order_id:
            order = Order.objects.filter(id=order_id).first()
            if order:
                order.status = "PLACED"
                order.is_paid = True
                order.payment_method = "STRIPE"
                order.placed_at = timezone.now()
                order.stripe_session_id = session.get("id", "")
                order.stripe_payment_intent_id = session.get("payment_intent", "") or ""
                order.ensure_order_number()
                order.save()

    return HttpResponse(status=200)


# Save checkout info (name, phone, address)
@require_POST
def save_checkout_info(request):
    cart = get_cart(request)

    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    street = (request.POST.get("street") or "").strip()
    postal_code = (request.POST.get("postal_code") or "").strip()
    city = (request.POST.get("city") or "").strip()

    # Required validation
    if not last_name or not phone or not street or not postal_code or not city:
        messages.error(request, "Bitte füllen Sie alle Pflichtfelder aus (Nachname, Telefon, Adresse).")
        return redirect("cart_detail")

    # Save into Order
    cart.full_name = f"{first_name} {last_name}".strip()
    cart.phone = phone
    cart.address_line = street
    cart.postal_code = postal_code
    cart.city = city
    cart.save(update_fields=["full_name", "phone", "address_line", "postal_code", "city"])

    messages.success(request, "Daten gespeichert. Bitte wählen Sie nun eine Zahlungsart.")
    return redirect("cart_detail")




@require_POST
def place_cash_order(request):
    cart = get_cart(request)

    # 1) Must have items
    if cart.items.count() == 0:
        messages.error(request, "Ihr Warenkorb ist leer.")
        return redirect("cart_detail")

    # 2) Read fields from POST (from hidden inputs in cart.html)
    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    street = (request.POST.get("street") or "").strip()
    postal_code = (request.POST.get("postal_code") or "").strip()
    city = (request.POST.get("city") or "").strip()

    # 3) Validate required fields
    if not last_name or not phone or not street or not postal_code or not city:
        messages.error(request, "Bitte füllen Sie alle Pflichtfelder (*) aus.")
        return redirect("cart_detail")

    # 4) Save customer info into cart (Order)
    cart.full_name = f"{first_name} {last_name}".strip()
    cart.phone = phone
    cart.address_line = street
    cart.postal_code = postal_code
    cart.city = city

    # 5) Mark payment + place order (sent to restaurant)
    cart.payment_method = "CASH"
    cart.is_paid = False
    cart.status = "PLACED"
    cart.placed_at = timezone.now()

    # 6) Generate order number BEFORE saving
    cart.ensure_order_number()

    # 7) Save everything in one DB save
    cart.save(update_fields=[
        "full_name", "phone", "address_line", "postal_code", "city",
        "payment_method", "is_paid", "status", "placed_at", "order_number"
    ])

    # 8) Clear session cart (new cart next time)
    request.session.pop("cart_id", None)

    # ✅ Option A (recommended): redirect to success page that shows order number
    return redirect("order_success", order_number=cart.order_number)

    # ✅ Option B (if you prefer redirect home):
    # messages.success(request, f"✅ Bestellung aufgegeben! Bestellnummer: {cart.order_number}")
    # return redirect("home")


# Order success and track order views
def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, "order_success.html", {"order": order})



def track_order(request):
    order = None
    error = None

    if request.method == "POST":
        order_number = (request.POST.get("order_number") or "").strip()
        order = Order.objects.filter(order_number=order_number).first()
        if not order:
            error = "Order number not found. Please check and try again."

    return render(request, "track_order.html", {"order": order, "error": error})
