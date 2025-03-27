from django import forms
from .models import FlashcardDeck, Flashcard

class FlashcardForm(forms.ModelForm):
    class Meta:
        model = Flashcard
        fields = ['question', 'answer', 'tags']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tags': forms.TextInput(attrs={'class': 'form-control'}),
        }

class FlashcardDeckForm(forms.ModelForm):
    class Meta:
        model = FlashcardDeck
        fields = ['name', 'description']

