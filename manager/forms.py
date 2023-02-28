from django import forms
from support_bot.models import Developer


class DevForm(forms.ModelForm):
    class Meta:
        model = Developer
        fields = '__all__'