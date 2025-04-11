import os
import google.generativeai as genai
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse

from .models import FlashcardDeck, Flashcard, Review, StudyGroup, AiInteraction
from .forms import (
    FlashcardDeckForm,
    FlashcardForm,
    ReviewForm,
    RegisterForm,
    StudyGroupForm,
    GroupMessageForm,
    QuestionnaireForm,
)

# --- Gemini API Configuration ---
try:
    model_name = "gemini-2.0-flash"
    model = genai.GenerativeModel(model_name)
    print(f"Successfully initialized Gemini model in views.py: {model_name}")
except Exception as e:
    print(f"ERROR: Failed to initialize Gemini model in views.py: {e}")
    model = None


def create_gemini_prompt(question, answer, desired_response_type):
    return f"""Context: A user is interacting with an educational web application.

Question asked to the user:
{question}

User's Answer:
{answer}

Task: Based *only* on the user's answer provided above in response to the question, provide {desired_response_type}. Keep the response concise and directly related to the answer."""


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('ai_features:home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'base/login.html', {'form': form})


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created! Please log in.")
            return redirect('ai_features:login')
    else:
        form = RegisterForm()
    return render(request, 'base/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect('ai_features:home')


def home_view(request):
    return render(request, 'base/base.html')


def study_sessions_view(request):
    return render(request, 'base/study_sessions.html')


def resources_view(request):
    return render(request, 'base/resources.html')


def about_view(request):
    return render(request, 'base/about.html')


@login_required
def flashcards_view(request):
    decks = FlashcardDeck.objects.all()
    return render(request, 'base/flashcards.html', {'decks': decks})


@login_required
def create_deck_view(request):
    if request.method == 'POST':
        form = FlashcardDeckForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('ai_features:flashcards')
    else:
        form = FlashcardDeckForm()
    return render(request, 'base/create_deck.html', {'form': form})


@login_required
def deck_detail_view(request, deck_id):
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    cards = deck.flashcards.all()
    form = FlashcardForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        flashcard = form.save(commit=False)
        flashcard.deck = deck
        flashcard.save()
        return redirect('ai_features:deck_detail', deck_id=deck.id)

    return render(request, 'base/deck_detail.html', {'deck': deck, 'cards': cards, 'form': form})


@login_required
def study_flashcards_view(request, deck_id):
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    cards = deck.flashcards.all()
    current_card_index = int(request.GET.get('card', 0))

    if not cards.exists():
        messages.warning(request, "This deck is empty. Add flashcards to study.")
        return redirect('ai_features:deck_detail', deck_id=deck.id)

    current_card = cards[current_card_index % len(cards)]
    next_card_index = (current_card_index + 1) % len(cards)
    prev_card_index = (current_card_index - 1) % len(cards)

    return render(request, 'base/study_flashcards.html', {
        'deck': deck,
        'current_card': current_card,
        'next_card_index': next_card_index,
        'prev_card_index': prev_card_index,
        'current_card_index': current_card_index,
        'total_cards': len(cards),
    })


@login_required
def delete_flashcard_view(request, deck_id, card_id):
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    flashcard = get_object_or_404(Flashcard, id=card_id, deck=deck)

    if request.method == 'POST':
        flashcard.delete()
        messages.success(request, 'Flashcard deleted successfully!')
    return redirect('ai_features:deck_detail', deck_id=deck.id)


@login_required
def delete_deck_view(request, deck_id):
    deck = get_object_or_404(FlashcardDeck, id=deck_id)

    if request.method == 'POST':
        deck.delete()
        messages.success(request, 'Deck deleted successfully!')
    return redirect('ai_features:flashcards')


def timer_page(request):
    return render(request, 'base/timer.html')


@login_required
def review_page(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.save()
            return redirect('ai_features:review_page')

    sort_by = request.GET.get('sort', 'date')
    reviews = Review.objects.all().order_by('-stars' if sort_by == 'rating' else '-created_at')
    form = ReviewForm()
    return render(request, 'base/reviews.html', {'form': form, 'reviews': reviews})


@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if review.user != request.user and not request.user.is_staff:
        messages.error(request, "You are not authorized to edit this review.")
        return redirect('ai_features:review_page')

    form = ReviewForm(request.POST or None, instance=review)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Review updated successfully!")
        return redirect('ai_features:review_page')

    return render(request, 'base/edit_review.html', {'form': form, 'review': review})


@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if review.user != request.user and not request.user.is_staff:
        messages.error(request, "You are not authorized to delete this review.")
        return redirect('ai_features:review_page')

    if request.method == 'POST':
        review.delete()
        messages.success(request, "Review deleted successfully!")
    return redirect('ai_features:review_page')


@login_required
def study_groups_view(request):
    return render(request, 'base/study_groups.html', {
        'user_groups': request.user.study_groups.all(),
        'all_groups': StudyGroup.objects.all()
    })


@login_required
def create_study_group(request):
    form = StudyGroupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        group = form.save(commit=False)
        group.created_by = request.user
        group.save()
        group.members.add(request.user)
        messages.success(request, f"Study group '{group.name}' created successfully!")
        return redirect('ai_features:study_group_detail', group_id=group.id)
    return render(request, 'base/create_study_group.html', {'form': form})


@login_required
def study_group_detail(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    messages_list = group.messages.all()
    form = GroupMessageForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        message = form.save(commit=False)
        message.group = group
        message.sender = request.user
        message.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': message.content,
                'username': request.user.username,
                'timestamp': message.created_at.isoformat(),
                'is_current_user': True
            })
        return redirect('ai_features:study_group_detail', group_id=group.id)

    return render(request, 'base/study_group_detail.html', {
        'group': group,
        'messages_list': messages_list,
        'message_form': GroupMessageForm()
    })


@login_required
def join_study_group(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    if request.user not in group.members.all():
        group.members.add(request.user)
        messages.success(request, f"You've joined '{group.name}'!")
    else:
        messages.info(request, f"You're already a member of '{group.name}'")
    return redirect('ai_features:study_group_detail', group_id=group.id)


@login_required
def leave_study_group(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    if request.user in group.members.all():
        group.members.remove(request.user)
        messages.info(request, f"You've left '{group.name}'")
    return redirect('ai_features:study_groups')


@login_required
def questionnaire_view(request, section_slug):
    section_details = {
        'online-tutorials': {
            'title': "Online Tutorials Feedback",
            'question': "What specific topic or concept from the online tutorials are you finding most challenging right now?",
            'response_type': "provide targeted feedback and suggest one specific online resource."
        },
        'study-guides': {
            'title': "Study Guide Clarification",
            'question': "Which concept or section from the study guides do you need further explanation on?",
            'response_type': "provide a concise and clear explanation."
        },
        'recommended-books': {
            'title': "Book Recommendations",
            'question': "Describe the type of book you're interested in.",
            'response_type': "suggest one relevant book title and author."
        },
        'mood-assessment': {
            'title': "Mood Assessment Reflection",
            'question': "Briefly describe how you're feeling about your studies.",
            'response_type': "offer a short supportive and encouraging comment."
        }
    }

    if section_slug not in section_details:
        messages.error(request, "Invalid AI interaction section.")
        return redirect('ai_features:home')

    question_text = section_details[section_slug]['question']
    response_type = section_details[section_slug]['response_type']
    title = section_details[section_slug]['title']

    form = QuestionnaireForm(request.POST or None, initial={'question_text': question_text, 'section': section_slug})

    if request.method == 'POST' and form.is_valid():
        if (form.cleaned_data['question_text'] != question_text or
                form.cleaned_data['section'] != section_slug):
            messages.error(request, "Form mismatch. Please try again.")
        else:
            prompt = create_gemini_prompt(question_text, form.cleaned_data['user_answer'], response_type)
            try:
                ai_response = model.generate_content(prompt).text if model else "Model unavailable"
            except Exception:
                ai_response = "Error generating response"
            AiInteraction.objects.create(
                user=request.user,
                section=section_slug,
                question_text=question_text,
                user_answer=form.cleaned_data['user_answer'],
                ai_response=ai_response
            )
            return redirect('ai_features:results_feed')

    return render(request, 'base/questionnaire_page.html', {
        'form': form,
        'question': question_text,
        'section_slug': section_slug,
        'section_title': title
    })


@login_required
def results_feed_view(request):
    interactions = AiInteraction.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'base/results_feed.html', {'interactions': interactions})
