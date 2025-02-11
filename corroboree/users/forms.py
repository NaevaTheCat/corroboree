from django import forms

from wagtail.users.forms import UserEditForm, UserCreationForm

from corroboree.config.models import Member

class CustomUserEditForm(UserEditForm):
    member = forms.ModelChoiceField(queryset=Member.objects, required=False, label="Associated Member")
    class Meta(UserEditForm.Meta):
        fields = UserEditForm.Meta.fields | {"member"}

class CustomUserCreationForm(UserCreationForm):
    member = forms.ModelChoiceField(queryset=Member.objects, required=False, label="Associated Member")
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields | {"member"}