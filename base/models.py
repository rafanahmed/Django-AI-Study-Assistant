from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now


class FlashcardDeck(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Flashcard(models.Model):
    question = models.TextField()
    answer = models.TextField()
    deck = models.ForeignKey(FlashcardDeck, on_delete=models.CASCADE, related_name='flashcards')
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.CharField(max_length=255, blank=True, null=True)  # Example field for tags

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    stars = models.IntegerField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review by {self.user.username if self.user else 'Anonymous'}"
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    
    
    def __str__(self):
        return self.user.username 
