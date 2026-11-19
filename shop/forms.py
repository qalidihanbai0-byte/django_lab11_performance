from django import forms


class AskForm(forms.Form):
    question = forms.CharField(
        label='Сұрағыңыз',
        max_length=300,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Мысалы, Алматыда қанша клиент бар?',
        }),
        error_messages={
            'required': 'Сұрағыңызды жазыңыз.',
            'max_length': 'Сұрақ 300 таңбадан аспауы керек.',
        },
    )
