from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.db.models import Q, Prefetch
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.http import HttpResponse
from .models import Order, OrderItem, Product, Category
from .utils import generate_jazzcash_hash


# 0. Main Home View (Dynamic 7 Sections Page)
def index(request):
    featured_products = Product.objects.all()[:10]

    target_categories = [
        'Sleeper', 'Shoe', 'Peshawari chapal', 
        'Pumpy', 'Loafers', 'Naurozi', 'Sandals'
    ]

    categories_sections = Category.objects.filter(
        name__in=target_categories
    ).prefetch_related(
        Prefetch('products', queryset=Product.objects.all(), to_attr='category_products')
    )

    context = {
        'featured_products': featured_products,
        'categories_sections': categories_sections,
    }
    return render(request, 'store/index.html', context)


# 1. Product List & Category Filtering (Dedicated Filter Page)
def product_list(request):
    category_slug = request.GET.get('category')
    products = Product.objects.all()

    if category_slug:
        cat = category_slug.lower().strip()
        
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
        elif cat in ['chappals', 'chappal']:
            products = products.filter(
                Q(category__name__icontains='chappal') | Q(name__icontains='chappal')
            )
        elif cat in ['sandals', 'sandal']:
            products = products.filter(
                Q(category__name__icontains='sandal') | Q(name__icontains='sandal')
            )
        elif cat in ['peshawari', 'pashawari', 'peshawari chapal', 'peshawari-chapal']:
            products = products.filter(
                Q(category__name__icontains='peshawari') | Q(name__icontains='peshawari') |
                Q(category__name__icontains='pashawari') | Q(name__icontains='pashawari') |
                Q(category__name__icontains='chapal') | Q(name__icontains='chapal')
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
        elif cat in ['formals', 'formal', 'shoe', 'shoes']:
            products = products.filter(
                Q(category__name__icontains='formal') | Q(name__icontains='formal') |
                Q(category__name__icontains='shoe') | Q(name__icontains='shoe')
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


# 2. Home View Redirect Handler
def home(request):
    return index(request)


# 3. Product Details Page
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'store/product_detail.html', {'product': product})


# 4. Cart Management Functions
def add_to_cart(request, product_id):
    if request.method == 'POST':
        size = request.POST.get('size', '')
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        product = get_object_or_404(Product, id=product_id)
        final_price = float(product.discount_price) if product.discount_price else float(product.price)

        cart = request.session.get('cart', {})
        item_key = f"{product_id}_{size}" if size else str(product_id)

        if item_key in cart:
            cart[item_key]['quantity'] = quantity
            cart[item_key]['price'] = final_price
        else:
            cart[item_key] = {
                'product_id': product.id,
                'name': product.name,
                'price': final_price,
                'size': size,
                'quantity': quantity,
            }

        request.session['cart'] = cart
        request.session.modified = True

    return redirect('cart')


@never_cache
def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0.0

    for key, item in cart.items():
        subtotal = item['price'] * item['quantity']
        total_price += subtotal
        
        cart_items.append({
            'key': key,
            'name': item.get('name', 'Product'),
            'price': item.get('price', 0),
            'size': item.get('size', '-'),
            'quantity': item.get('quantity', 1),
            'subtotal': subtotal,
        })

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    
    # Rendering with strict anti-cache headers to completely resolve back-button issue
    response = render(request, 'store/cart.html', context)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


# 5. Checkout & Order Processing
# 5. Checkout & Order Processing
@never_cache
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('product_list')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        city = request.POST.get('city', '')
        payment_method = request.POST.get('payment_method', 'cod')

        total_price = 0
        items_summary = ""

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            total_amount=0,
            payment_method=payment_method,
            status='Pending'
        )

        for item_key, item_data in cart.items():
            product_id = item_data['product_id']
            product = get_object_or_404(Product, id=product_id)
            subtotal = float(item_data['price']) * item_data['quantity']
            total_price += subtotal
            
            size_info = f" (Size: {item_data['size']})" if item_data.get('size') else ""
            items_summary += f"- {product.name}{size_info} x {item_data['quantity']} = Rs. {subtotal}\n"

            OrderItem.objects.create(
                order=order,
                product=product,
                price=item_data['price'],
                quantity=item_data['quantity']
            )

        order.total_amount = total_price
        order.save()

        print(f"DEBUG: Form submitted with Email -> '{email}'")

        if email:
            subject = f"Order Confirmation - #{order.id} | D.9 Shoes"
            message = f"""
Hello {full_name},

Thank you for your order at D.9 Shoes!

--- Order Details ---
Order ID: #{order.id}
Payment Method: {str(payment_method).upper()}

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
                    [email,aliksks827@gmail.com],
                    fail_silently=False
                )
                print("DEBUG: Email sent successfully!")
            except Exception as e:
                print(f"CRITICAL EMAIL ERROR: {e}")
        else:
            print("DEBUG: Email field is empty or not captured from form!")

        # Clear Session Cart Safely
        request.session['cart'] = {}
        request.session.modified = True

        if payment_method == 'jazzcash':
            return redirect('initiate_jazzcash_payment', order_id=order.id)
        else:
            return redirect('order_success', order_id=order.id)

    total = sum(float(item['price']) * item['quantity'] for item in cart.values())
    response = render(request, 'store/checkout.html', {'total': total})
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'store/order_success.html', {'order': order})


# 6. JazzCash Payment Gateway Logic
def initiate_jazzcash_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    now = datetime.now()
    txn_ref_no = f"T{now.strftime('%Y%m%d%H%M%S')}"
    pp_expiry_date = (now + timedelta(hours=1)).strftime('%Y%m%d%H%M%S')
    
    post_data = {
        'pp_Version': '1.1',
        'pp_TxnType': '',
        'pp_Language': 'EN',
        'pp_MerchantID': getattr(settings, 'JAZZCASH_MERCHANT_ID', ''),
        'pp_SubMerchantID': '',
        'pp_Password': getattr(settings, 'JAZZCASH_PASSWORD', ''),
        'pp_BankID': 'TBANK',
        'pp_ProductID': 'REFILL',
        'pp_TxnRefNo': txn_ref_no,
        'pp_Amount': str(int(order.total_amount * 100)),
        'pp_TxnCurrency': 'PKR',
        'pp_TxnDateTime': now.strftime('%Y%m%d%H%M%S'),
        'pp_BillReference': str(order.id),
        'pp_Description': f'Order #{order.id} Payment',
        'pp_TxnExpiryDateTime': pp_expiry_date,
        'pp_ReturnURL': getattr(settings, 'JAZZCASH_RETURN_URL', ''),
        'pp_SecureHash': '',
        'ppmpf_1': str(order.id),
    }

    post_data['pp_SecureHash'] = generate_jazzcash_hash(post_data)

    return render(request, 'store/jazzcash_redirect.html', {
        'post_data': post_data,
        'jazzcash_url': getattr(settings, 'JAZZCASH_API_URL', 'https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform')
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
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'store/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('home')

def user_register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('home')
        else:
            messages.error(request, "Registration failed. Please correct the errors.")
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    return redirect('cart')