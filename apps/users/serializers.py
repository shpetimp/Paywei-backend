from .models import CustomUser as User, APIKey, WhitelistAddress
from rest_framework import serializers
import re
from rest_registration.api.serializers import DefaultRegisterUserSerializer
from django.contrib.auth import get_user_model
from rest_registration.utils.users import get_user_setting


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email')


class RegisterUserSerializer(DefaultRegisterUserSerializer):
    email = serializers.EmailField(required=True)

    def validate_username(self, username):
        if len(username) <= 3:
            raise serializers.ValidationError(
                'Username must be more than 3 characters long')
        return username

    def validate_password(self, password):
        password = super(RegisterUserSerializer,
                         self).validate_password(password)
        pattern = re.compile(r'^(?=.*[a-z])(?=.*\d)(?=.*[A-Z])(?:.{8,})$')
        if not pattern.match(password):
            raise serializers.ValidationError(
                'Password must at least 8 characters long and contain an uppercase, lowercase, and number.')
        return password


class UserProfileSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        class MetaObj(object):
            pass

        from rest_registration.api.serializers import _get_field_names
        user_class = get_user_model()
        field_names = _get_field_names(allow_primary_key=True)
        read_only_field_names = _get_field_names(
            allow_primary_key=True,
            non_editable=True)
        self.Meta = MetaObj()
        self.Meta.model = user_class
        self.Meta.fields = field_names
        self.Meta.read_only_fields = read_only_field_names
        super().__init__(*args, **kwargs)

    def validate(self, data):
        data['username'] = self.instance.username
        data['email'] = self.instance.email
        return data


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = ('__all__')
        read_only = ('key',)


class WhitelistAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhitelistAddress
        fields = ('__all__')

    def update(self, instance, validated_data):
        for field in ['address', 'created_at', 'updated_at', 'revoked_at', 'user', 'status']:
            if field in validated_data:
                raise serializers.ValidationError({
                    field: 'You must not change this field'
                })
        return super().update(instance, validated_data)
