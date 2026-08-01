def cart_count(request):
    cart = request.session.get('cart', {})
    total_count = sum(item['quantity'] for item in cart.values())
    return {'cart_count': total_count}