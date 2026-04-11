from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from core.db import users_col
from bson.objectid import ObjectId

class PyMongoUser:
    def __init__(self, user_doc):
        self.user_doc = user_doc
        self.id = str(user_doc.get('_id'))
        
    @property
    def is_authenticated(self):
        return True

    @property
    def is_admin(self):
        # We also treat Django's superusers or staff as admins if applicable,
        # but for PyMongo users, we check the 'is_admin' field.
        return self.user_doc.get('is_admin', False)

    @property
    def email(self):
        return self.user_doc.get('email')

    @property
    def pk(self):
        return self.id

    def __str__(self):
        return self.email or self.id

class PyMongoJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user_id = validated_token.get('user_id')
        if not user_id:
            raise AuthenticationFailed('Token contained no recognizable user identification')
            
        try:
            # Check if user_id is a valid 24-character hexadecimal string
            if not isinstance(user_id, str) or len(user_id) != 24 or not all(c in '0123456789abcdefABCDEF' for c in user_id):
                raise AuthenticationFailed(f'Invalid user ID format: {user_id}', code='invalid_user_id')
                
            user_doc = users_col.find_one({"_id": ObjectId(user_id)})
            if not user_doc:
                import logging
                logger = logging.getLogger('django')
                logger.warning(f"❌ Auth Failure: User with ID {user_id} not found in users_col")
                raise AuthenticationFailed('User not found', code='user_not_found')
            return PyMongoUser(user_doc)
        except AuthenticationFailed:
            raise
        except Exception as e:
            raise AuthenticationFailed(f'Authentication error: {str(e)}', code='auth_error')
