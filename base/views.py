from django.shortcuts import render,  redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import FlashcardDeck, Flashcard
from .forms import FlashcardDeckForm, FlashcardForm

def home_view(request):
    """
    Render the home page
    """
    return render(request, 'base/base.html')

def study_sessions_view(request):
    """
    Render the study sessions page
    """
    return render(request, 'base/study_sessions.html')

def resources_view(request):
    """
    Render the resources page
    """
    return render(request, 'base/resources.html')

def about_view(request):
    """
    Render the about page
    """
    return render(request, 'base/about.html')

def flashcards_view(request):
    """
    Main flashcards page to list all decks
    """
    decks = FlashcardDeck.objects.all()
    return render(request, 'base/flashcards.html', {
        'decks': decks
    })


def create_deck_view(request):
    if request.method == 'POST':
        form = FlashcardDeckForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('deck_list')  # Or wherever you want to redirect
    else:
        form = FlashcardDeckForm()
    return render(request, 'base/create_deck.html', {'form': form})


def deck_detail_view(request, deck_id):
    """
    View to display a deck and its flashcards and handle the addition of a new flashcard.
    """
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    cards = deck.flashcards.all()  # Use the related_name 'flashcards'

    if request.method == 'POST':
        form = FlashcardForm(request.POST)
        if form.is_valid():
            flashcard = form.save(commit=False)
            flashcard.deck = deck  # Associate the flashcard with the current deck
            flashcard.save()  # Save the flashcard to the database
            return redirect('deck_detail', deck_id=deck.id)  # Redirect to the deck details page
    else:
        form = FlashcardForm()

    return render(request, 'base/deck_detail.html', {'deck': deck, 'cards': cards, 'form': form})


def study_flashcards_view(request, deck_id):
    """
    View to study flashcards by flipping through the questions and answers.
    """
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    cards = deck.flashcards.all()

    # Get the current card index from the URL, default to 0 if not provided
    current_card_index = int(request.GET.get('card', 0))

    # Get the current flashcard
    if current_card_index < len(cards):
        current_card = cards[current_card_index]
    else:
        current_card = cards[0]
        current_card_index = 0

    # Determine next and previous card indices
    next_card_index = current_card_index + 1 if current_card_index + 1 < len(cards) else 0
    prev_card_index = current_card_index - 1 if current_card_index - 1 >= 0 else len(cards) - 1

    current_card_index_plus_one = current_card_index + 1

    return render(request, 'base/study_flashcards.html', {
        'deck': deck,
        'current_card': current_card,
        'next_card_index': next_card_index,
        'prev_card_index': prev_card_index,
        'current_card_index': current_card_index,
        'current_card_index_plus_one': current_card_index_plus_one,
        'total_cards': len(cards),
    })
