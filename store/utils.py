import hmac
import hashlib
from django.conf import settings

def generate_jazzcash_hash(post_data):
    # Alphabetical order mein keys ko sort karna hota hai
    sorted_keys = sorted(post_data.keys())
    
    # Hash string tayar karna
    hash_string = settings.JAZZCASH_INTEGERITY_SALT
    for key in sorted_keys:
        if post_data[key] != '' and post_data[key] is not None:
            hash_string += f"&{post_data[key]}"
    
    # HMAC-SHA256 Encryption
    secure_hash = hmac.new(
        settings.JAZZCASH_INTEGERITY_SALT.encode('utf-8'),
        hash_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()
    
    return secure_hash