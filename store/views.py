from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.mail import send_mail
from .models import Order, OrderItem, Product, Category
from .utils import generate_jazzcash_hash


# 1. Product List & Category Filtering
def product_list(request):
    category_slug = request.GET.get('category')
    products = Product.objects.all()

    if category_slug:
        cat = category_slug.lower().strip()
        
        # Main Men Section (All Men Shoes & Subcategories)
        if cat == 'men':
            products = products.filter(
                Q(category__name__icontains='men') | 
                Q(name__icontains='men') |
                Q(category__name__icontains='peshawari') |
                Q(category__name__icontains='chappal') |
                Q(category__name__icontains='sandal') |
                Q(category__name__icontains='sneaker') |
                Q(category__name__icontains='loafer') |
                Q(category__name__icontains='formal')
            )
        
        # Individual Sub-Categories Filtering
        elif cat in ['chappals', 'chappal']:
            products = products.filter(
                Q(category__name__icontains='chappal') | Q(name__icontains='chappal')
            )
        elif cat in ['sandals', 'sandal']:
            products = products.filter(
                Q(category__name__icontains='sandal') | Q(name__icontains='sandal')
            )
        elif cat in ['peshawari', 'pashawari']:
            products = products.filter(
                Q(category__name__icontains='peshawari') | Q(name__icontains='peshawari') |
                Q(category__name__icontains='pashawari') | Q(name__icontains='pashawari')
            )
        elif cat in ['sneakers', 'sports', 'sneakers / sports', 'sneaker']:
            products = products.filter(
                Q(category__name__icontains='sneaker') | Q(name__icontains='sneaker') |
                Q(category__name__icontains='sport') | Q(name__icontains='sport')
            )
        elif cat in ['loafers', 'loafer']:
            products = products.filter(
                Q(category__name__icontains='loafer') | Q(name__icontains='loafer')
            )
        elif cat in ['formals', 'formal']:
            products = products.filter(
                Q(category__name__icontains='formal') | Q(name__icontains='formal')
            )
        elif cat == 'women':
            products = products.filter(
                Q(category__name__icontains='women') | Q(name__icontains='women')
            )
        elif cat == 'luxury':
            products = products.filter(
                Q(category__name__icontains='luxury') | Q(is_featured=True)
            )
        else:
            products = products.filter(
                Q(category__name__icontains=cat) | Q(name__icontains=cat)
            )

    context = {
        'products': products,
        'current_category': category_slug,
    }
    return render(request, 'store/product_list.html', context)


# 2. Home View Redirect
def home(request):
    return product_list(request)


# 3. Product Details Page
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'store/product_detail.html', {'product': product})


# 4. Cart Management
def cart(request):
    cart_session = request.session.get('cart', {})
    cart_items = []
    total = 0

    for product_id, item_data in cart_session.items():
        subtotal = item_data['price'] * item_data['quantity']
        total += subtotal
        cart_items.append({
            'product_id': product_id,
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'subtotal': subtotal,
            'image': item_data.get('image', '')
        })

    context = {
        'cart_items': cart_items,
        'total': total
    }
    return render(request, 'store/cart.html', context)


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})

    str_id = str(product_id)
    if str_id in cart:
        cart[str_id]['quantity'] += 1
    else:
        cart[str_id] = {
            'name': product.name,
            'price': float(product.price),
            'quantity': 1,
            'image': product.image.url if product.image else ''
        }

    request.session['cart'] = cart
    return redirect('cart')

# 5. Checkout & Order Processing
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('product_list')

    if request.method == 'POST':
        # Form values extract karein
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        payment_method = request.POST.get('payment_method')

        valid_products = Product.objects.filter(id__in=cart.keys())
        if not valid_products.exists():
            request.session['cart'] = {}
            return redirect('product_list')

        total_price = 0
        items_summary = ""

        for product in valid_products:
            item_data = cart[str(product.id)]
            subtotal = float(item_data['price']) * item_data['quantity']
            total_price += subtotal
            items_summary += f"- {product.name} (Qty: {item_data['quantity']}) - Rs. {subtotal}\n"

        # Order Create Karein
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            total_amount=total_price,
            status='Pending'
        )

        for product in valid_products:
            item_data = cart[str(product.id)]
            OrderItem.objects.create(
                order=order,
                product=product,
                price=item_data['price'],
                quantity=item_data['quantity']
            )

        # CLIENT KO EMAIL BHEJNA
        if email:
            subject = f"Order Placed - #{order.id} | D.9 Shoes"
            message = f"""
Hello {full_name},

Thank you for your order at D.9 Shoes!

--- Order Details ---
Order ID: #{order.id}
Payment Method: {payment_method.upper()}

Items:
{items_summary}
Total Amount: Rs. {total_price}

Shipping Address:
{address}, {city}
Phone: {phone}

We will contact you shortly to confirm your dispatch details.

Regards,
D.9 Shoes Team
"""
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Email error: {e}")

        # Checkout Flow Routing
        request.session['cart'] = {}

        if payment_method == 'jazzcash':
            return redirect('initiate_jazzcash_payment', order_id=order.id)
        else:
            return redirect('order_success', order_id=order.id)

    total = sum(float(item['price']) * item['quantity'] for item in cart.values())
    return render(request, 'store/checkout.html', {'total': total})

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'store/order_success.html', {'order': order})


# 6. JazzCash Payment Gateway Logic
def initiate_jazzcash_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    txn_ref_no = f"T{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pp_expiry_date = datetime.now().strftime('%Y%m%d%H%M%S')
    
    post_data = {
        'pp_Version': '1.1',
        'pp_TxnType': '',
        'pp_Language': 'EN',
        'pp_MerchantID': settings.JAZZCASH_MERCHANT_ID,
        'pp_SubMerchantID': '',
        'pp_Password': settings.JAZZCASH_PASSWORD,
        'pp_BankID': 'TBANK',
        'pp_ProductID': 'REFILL',
        'pp_TxnRefNo': txn_ref_no,
        'pp_Amount': str(int(order.total_amount * 100)),
        'pp_TxnCurrency': 'PKR',
        'pp_TxnDateTime': datetime.now().strftime('%Y%m%d%H%M%S'),
        'pp_BillReference': str(order.id),
        'pp_Description': f'Order #{order.id} Payment',
        'pp_TxnExpiryDateTime': pp_expiry_date,
        'pp_ReturnURL': settings.JAZZCASH_RETURN_URL,
        'pp_SecureHash': '',
        'ppmpf_1': str(order.id),
    }

    post_data['pp_SecureHash'] = generate_jazzcash_hash(post_data)

    return render(request, 'store/jazzcash_redirect.html', {
        'post_data': post_data,
        'jazzcash_url': settings.JAZZCASH_API_URL
    })


@csrf_exempt
def jazzcash_callback(request):
    if request.method == 'POST':
        response_data = request.POST.dict()
        response_code = response_data.get('pp_ResponseCode')
        order_id = response_data.get('pp_BillReference') or response_data.get('ppmpf_1')

        if response_code == '000':
            if order_id:
                order = Order.objects.get(id=order_id)
                order.is_paid = True
                order.status = 'Shipped'
                order.save()
            return render(request, 'store/order_success.html', {'order': order, 'message': 'Payment Successful!'})
        else:
            return render(request, 'store/order_failed.html', {'message': response_data.get('pp_ResponseMessage', 'Payment Failed')})

    return redirect('home')


# 7. User Auth Handlers
def user_login(request):
    return redirect('home')

def user_logout(request):
    return redirect('home')

def user_register(request):
    return redirect('home')