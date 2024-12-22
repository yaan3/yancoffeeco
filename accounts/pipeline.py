from accounts   .models import User
from social_core.pipeline.partial import partial

@partial
def save_user_details(strategy, details, user=None, *args, **kwargs):
    if user:
        return {'is_new': False}

    fields = {
        'first_name': details.get('first_name'),
        'last_name': details.get('last_name'),
        'email': details.get('email'),
    }
    
    if not all(fields.values()):
        return strategy.redirect('/some-error-page/') 

    user = User.objects.create_user(
        email=fields['email'],
        first_name=fields['first_name'],
        last_name=fields['last_name'],
        phone_number=details.get('phone_number', ''), 
    )
    return {
        'is_new': True,
        'user': user
    }

def set_user_phone_number(backend, user, response, *args, **kwargs):
    phone_number = response.get('phone_number')
    if phone_number and not user.phone_number:
        user.phone_number = phone_number
        user.save()

def activate_user(user, *args, **kwargs):
    user.is_active = True
    user.save()

def check_if_user_blocked(user, *args, **kwargs):
    if user.is_blocked:
        return {
            'is_blocked': True,
            'user': user
        }
    return {
        'is_blocked': False,
        'user': user
    }