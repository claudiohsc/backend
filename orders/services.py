from decimal import Decimal

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404

from orders.models import Cart, CartItem, OrderStatus, Payment, PaymentStatus
from products.models import ProductVariation


def create_infinitepay_checkout(order, request):
    payment, _ = Payment.objects.get_or_create(
        order=order,
        defaults={"method": "CREDIT_CARD", "total_amount": order.total_amount},
    )

    items_data = []
    for item in order.items.select_related("variation", "variation__product"):
        items_data.append(
            {
                "quantity": item.quantity,
                "price": int(item.unit_price * 100),
                "description": item.product_name,
            }
        )

    if order.shipping_cost > 0:
        items_data.append(
            {
                "quantity": 1,
                "price": int(order.shipping_cost * 100),
                "description": "Frete",
            }
        )

    redirect_url = request.build_absolute_uri("/api/orders/pagamento-sucesso/")

    payload = {
        "handle": settings.INFINITEPAY_HANDLE,
        "redirect_url": redirect_url,
        "order_nsu": str(order.id),
        "items": items_data,
        "customer": {
            "name": order.user.name,
            "email": order.user.email,
            "phone_number": getattr(order.user.profile, "phone_number", "")
            if hasattr(order.user, "profile")
            else "",
        },
        "address": {
            "cep": order.shipping_zip_code,
            "street": order.shipping_street,
            "neighborhood": order.shipping_neighborhood,
            "number": order.shipping_number,
            "complement": order.shipping_complement or "",
        },
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(
        "https://api.checkout.infinitepay.io/links",
        json=payload,
        headers=headers,
        timeout=10,
    )

    response.raise_for_status()
    data = response.json()

    payment.status = PaymentStatus.PROCESSING
    payment.save()
    order.status = OrderStatus.AWAITING_PAYMENT
    order.save()

    return data.get("url")


def check_payment_status(order_nsu, transaction_nsu, slug):
    payload = {
        "handle": settings.INFINITEPAY_HANDLE,
        "order_nsu": order_nsu,
        "transaction_nsu": transaction_nsu,
        "slug": slug,
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(
        "https://api.checkout.infinitepay.io/payment_check",
        json=payload,
        headers=headers,
        timeout=10,
    )

    if response.status_code == 200:
        return response.json()
    return None


def get_or_create_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user, status="ACTIVE")
    return cart


def get_cart_data(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, status="ACTIVE").first()
        if not cart:
            return {"id": None, "items": [], "subtotal": Decimal("0.00")}

        items = []
        subtotal = Decimal("0.00")
        for item in cart.items.select_related("variation", "variation__product").all():
            total_price = item.quantity * item.unit_price
            subtotal += total_price
            items.append(
                {
                    "variation_id": item.variation.id,
                    "product_id": item.variation.product.id,
                    "product_name": item.variation.product.name,
                    "size": item.variation.size,
                    "sku": item.variation.sku,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": total_price,
                    "stock_quantity": item.variation.stock_quantity,
                }
            )
        return {
            "id": cart.id,
            "items": items,
            "subtotal": subtotal,
        }
    else:
        session_cart = request.session.get("cart", {})
        items = []
        subtotal = Decimal("0.00")
        invalid_variation_ids = []

        variation_ids = list(session_cart.keys())
        variations = ProductVariation.objects.filter(
            id__in=variation_ids
        ).select_related("product")
        variations_by_id = {str(v.id): v for v in variations}

        for var_id_str, item_data in session_cart.items():
            variation = variations_by_id.get(var_id_str)
            if not variation:
                invalid_variation_ids.append(var_id_str)
                continue

            quantity = item_data.get("quantity", 0)
            unit_price_str = item_data.get("unit_price")
            unit_price = (
                Decimal(unit_price_str)
                if unit_price_str
                else variation.product.base_price
            )

            total_price = quantity * unit_price
            subtotal += total_price

            items.append(
                {
                    "variation_id": variation.id,
                    "product_id": variation.product.id,
                    "product_name": variation.product.name,
                    "size": variation.size,
                    "sku": variation.sku,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "stock_quantity": variation.stock_quantity,
                }
            )

        if invalid_variation_ids:
            for iv_id in invalid_variation_ids:
                session_cart.pop(iv_id, None)
            request.session["cart"] = session_cart
            request.session.modified = True

        return {
            "id": None,
            "items": items,
            "subtotal": subtotal,
        }


def add_item_to_cart(request, variation_id, quantity):
    variation = get_object_or_404(
        ProductVariation.objects.select_related("product"), id=variation_id
    )

    if request.user.is_authenticated:
        cart = get_or_create_user_cart(request.user)
        cart_item, _ = CartItem.objects.get_or_create(
            cart=cart,
            variation=variation,
            defaults={"quantity": 0, "unit_price": variation.product.base_price},
        )

        new_quantity = cart_item.quantity + quantity
        if new_quantity > variation.stock_quantity:
            raise ValueError(
                f"Estoque insuficiente para {variation.product.name}. Disponível: {variation.stock_quantity}"
            )

        cart_item.quantity = new_quantity
        cart_item.unit_price = variation.product.base_price
        cart_item.save()
    else:
        session_cart = request.session.get("cart", {})
        var_id_str = str(variation.id)

        current_data = session_cart.get(var_id_str, {})
        current_quantity = current_data.get("quantity", 0)
        new_quantity = current_quantity + quantity

        if new_quantity > variation.stock_quantity:
            raise ValueError(
                f"Estoque insuficiente para {variation.product.name}. Disponível: {variation.stock_quantity}"
            )

        session_cart[var_id_str] = {
            "quantity": new_quantity,
            "unit_price": str(variation.product.base_price),
        }
        request.session["cart"] = session_cart
        request.session.modified = True


def update_item_quantity(request, variation_id, quantity):
    variation = get_object_or_404(
        ProductVariation.objects.select_related("product"), id=variation_id
    )

    if quantity > variation.stock_quantity:
        raise ValueError(
            f"Estoque insuficiente para {variation.product.name}. Disponível: {variation.stock_quantity}"
        )

    if request.user.is_authenticated:
        cart = get_or_create_user_cart(request.user)
        cart_item = get_object_or_404(CartItem, cart=cart, variation=variation)
        cart_item.quantity = quantity
        cart_item.unit_price = variation.product.base_price
        cart_item.save()
    else:
        session_cart = request.session.get("cart", {})
        var_id_str = str(variation.id)
        if var_id_str not in session_cart:
            raise KeyError("Item não está no carrinho.")

        session_cart[var_id_str]["quantity"] = quantity
        session_cart[var_id_str]["unit_price"] = str(variation.product.base_price)
        request.session["cart"] = session_cart
        request.session.modified = True


def remove_item_from_cart(request, variation_id):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, status="ACTIVE").first()
        if not cart:
            raise KeyError("Carrinho não encontrado.")
        cart_item = get_object_or_404(CartItem, cart=cart, variation_id=variation_id)
        cart_item.delete()
    else:
        session_cart = request.session.get("cart", {})
        var_id_str = str(variation_id)
        if var_id_str not in session_cart:
            raise KeyError("Item não está no carrinho.")
        session_cart.pop(var_id_str)
        request.session["cart"] = session_cart
        request.session.modified = True


def clear_cart(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, status="ACTIVE").first()
        if cart:
            cart.items.all().delete()
    else:
        request.session["cart"] = {}
        request.session.modified = True


def merge_session_cart_to_db(request, user):
    session_cart = request.session.get("cart", {})
    if not session_cart:
        return

    db_cart = get_or_create_user_cart(user)
    variation_ids = list(session_cart.keys())
    variations = ProductVariation.objects.filter(id__in=variation_ids).select_related(
        "product"
    )
    variations_by_id = {str(v.id): v for v in variations}

    for var_id_str, item_data in session_cart.items():
        variation = variations_by_id.get(var_id_str)
        if not variation:
            continue

        quantity = item_data.get("quantity", 0)
        cart_item, _ = CartItem.objects.get_or_create(
            cart=db_cart,
            variation=variation,
            defaults={"quantity": 0, "unit_price": variation.product.base_price},
        )

        new_quantity = cart_item.quantity + quantity
        if new_quantity > variation.stock_quantity:
            new_quantity = variation.stock_quantity

        cart_item.quantity = new_quantity
        cart_item.unit_price = variation.product.base_price
        cart_item.save()

    request.session.pop("cart", None)
    request.session.modified = True
