import os 
import google.generativeai as genai
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from .models import FlashcardDeck, Flashcard, Review
from .forms import FlashcardDeckForm, FlashcardForm, ReviewForm, RegisterForm
from .models import StudyGroup
from .models import AiInteraction
from .forms import StudyGroupForm
from .forms import GroupMessageForm
from .forms import QuestionnaireForm
from django.http import JsonResponse

# --- Gemini API Configuration ---
# Ensure genai.configure(api_key=settings.GEMINI_API_KEY) was called in settings.py or manage.py
# Initialize the model (handle potential errors)
try:
    # Use a known stable model like 1.5 flash, or the specific one if available and confirmed
    model_name = "gemini-2.0-flash" # Using a generally available model
    model = genai.GenerativeModel(model_name)
    print(f"Successfully initialized Gemini model in views.py: {model_name}")
except Exception as e:
    # Log the error appropriately in a real application
    print(f"ERROR: Failed to initialize Gemini model in views.py: {e}")
    model = None # Set model to None if initialization fails

# --- Helper Function for Gemini Prompt ---
def create_gemini_prompt(question, answer, desired_response_type):
    """
    Formats the prompt according to the specified structure.
    """
    # Basic prompt structure
    prompt = f"""Context: A user is interacting with an educational web application.

Question asked to the user:
{question}

User's Answer:
{answer}

Task: Based *only* on the user's answer provided above in response to the question, provide {desired_response_type}. Keep the response concise and directly related to the answer."""
    # You might add safety settings or generation config here if needed
    return prompt


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
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
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'base/login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect('home')

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
            return redirect('flashcards')
    else:
        form = FlashcardDeckForm()
    return render(request, 'base/create_deck.html', {'form': form})

@login_required
def deck_detail_view(request, deck_id):
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    cards = deck.flashcards.all()

    if request.method == 'POST':
        form = FlashcardForm(request.POST)
        if form.is_valid():
            flashcard = form.save(commit=False)
            flashcard.deck = deck
            flashcard.save()
            return redirect('deck_detail', deck_id=deck.id)
    else:
        form = FlashcardForm()

    return render(request, 'base/deck_detail.html', {'deck': deck, 'cards': cards, 'form': form})

@login_required
def study_flashcards_view(request, deck_id):
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    cards = deck.flashcards.all()
    current_card_index = int(request.GET.get('card', 0))

    if not cards.exists():
        messages.warning(request, "This deck is empty. Add flashcards to study.")
        return redirect('deck_detail', deck_id=deck.id)

    if current_card_index >= len(cards):
        current_card_index = 0
        current_card = cards[0]
    else:
        current_card = cards[current_card_index]

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
        return redirect('deck_detail', deck_id=deck.id)
    
    return redirect('deck_detail', deck_id=deck.id)

def timer_page(request):
    return render(request, 'base/timer.html')

@login_required
def delete_deck_view(request, deck_id):
    deck = get_object_or_404(FlashcardDeck, id=deck_id)
    
    if request.method == 'POST':
        deck.delete()
        messages.success(request, 'Deck deleted successfully!')
        return redirect('flashcards')
    
    return redirect('flashcards')

@login_required
def review_page(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.save()
            return redirect('review_page')
    
    sort_by = request.GET.get('sort', 'date')
    
    if sort_by == 'rating':
        reviews = Review.objects.all().order_by('-stars', '-created_at')
    else:
        reviews = Review.objects.all().order_by('-created_at')
    
    form = ReviewForm()
    return render(request, 'base/reviews.html', {
        'form': form,
        'reviews': reviews
    })

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if review.user != request.user and not request.user.is_staff:
        messages.error(request, "You are not authorized to edit this review.")
        return redirect('review_page')

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Review updated successfully!")
            return redirect('review_page')
    else:
        form = ReviewForm(instance=review)

    return render(request, 'base/edit_review.html', {'form': form, 'review': review})

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    if review.user != request.user and not request.user.is_staff:
        messages.error(request, "You are not authorized to delete this review.")
        return redirect('review_page')

    if request.method == 'POST':
        review.delete()
        messages.success(request, "Review deleted successfully!")
        return redirect('review_page')

    return render(request, 'base/confirm_delete_review.html', {'review': review})



@login_required
def study_groups_view(request):
    user_groups = request.user.study_groups.all()
    all_groups = StudyGroup.objects.all()
    
    return render(request, 'base/study_groups.html', {
        'user_groups': user_groups,
        'all_groups': all_groups
    })

@login_required
def create_study_group(request):
    if request.method == 'POST':
        form = StudyGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            group.members.add(request.user)
            messages.success(request, f"Study group '{group.name}' created successfully!")
            return redirect('study_group_detail', group_id=group.id)
    else:
        form = StudyGroupForm()
    
    return render(request, 'base/create_study_group.html', {'form': form})

@login_required
def study_group_detail(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    messages_list = group.messages.all().order_by('created_at')
    
    if request.method == 'POST':
        message_form = GroupMessageForm(request.POST)
        if message_form.is_valid():
            message = message_form.save(commit=False)
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
            return redirect('study_group_detail', group_id=group.id)
    
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
    
    return redirect('study_group_detail', group_id=group.id)

@login_required
def leave_study_group(request, group_id):
    group = get_object_or_404(StudyGroup, id=group_id)
    
    if request.user in group.members.all():
        group.members.remove(request.user)
        messages.info(request, f"You've left '{group.name}'")
    
    return redirect('study_groups')

# --- Added AI Interaction Views ---

@login_required # Ensure user is logged in
def questionnaire_view(request, section_slug):
    """
    Handles displaying the AI questionnaire form (GET) and processing
    the submission (POST) for a specific section.
    Calls the Gemini API and saves the interaction.
    """
    # Define questions and desired response types per section slug
    section_details = {
        'online-tutorials': {
            'title': "Online Tutorials Feedback",
            'question': "What specific topic or concept from the online tutorials are you finding most challenging right now?",
            'response_type': "provide targeted feedback and suggest one specific online resource (like a documentation page, video, or article) to help clarify the challenging topic mentioned."
        },
        'study-guides': {
            'title': "Study Guide Clarification",
            'question': "Which concept or section from the study guides do you need further explanation on?",
            'response_type': "provide a concise and clear explanation of the concept or section mentioned, focusing on simplifying complex points."
        },
        'recommended-books': {
            'title': "Book Recommendations",
            'question': "Describe the type of book (genre, topic, author style) you're interested in reading next for your studies or personal growth.",
            'response_type': "suggest one relevant book title and author, along with a brief (1-2 sentence) explanation of why it matches the user's interest."
        },
        'mood-assessment': {
            'title': "Mood Assessment Reflection",
            'question': "Briefly describe how you are feeling today regarding your studies or workload.",
            'response_type': "offer a short, supportive, and encouraging comment acknowledging the feeling described, perhaps suggesting a brief positive action (like taking a short break or acknowledging progress)."
        },
        # Add other sections here if needed, matching the slugs used in urls.py
    }

    if section_slug not in section_details:
        messages.error(request, "Invalid AI interaction section requested.")
        return redirect('home') # Redirect to a safe default page

    current_section_config = section_details[section_slug]
    question_text = current_section_config['question']
    desired_response_type = current_section_config['response_type']
    section_title = current_section_config['title']

    if request.method == 'POST':
        form = QuestionnaireForm(request.POST)
        if form.is_valid():
            user_answer = form.cleaned_data['user_answer']
            # Security/Consistency Check: Ensure hidden fields match the current context
            submitted_question = form.cleaned_data['question_text']
            submitted_section = form.cleaned_data['section']

            if submitted_question != question_text or submitted_section != section_slug:
                 messages.error(request, "There was a mismatch in the form submission. Please try again.")
                 # Log this potential tampering attempt
                 print(f"WARN: Form mismatch for user {request.user.username}. Expected: {section_slug}/{question_text}. Got: {submitted_section}/{submitted_question}")
                 # Re-render form with error
                 initial_data = {'question_text': question_text, 'section': section_slug}
                 form = QuestionnaireForm(initial=initial_data) # Reset form with correct initial data
                 context = {
                     'form': form,
                     'question': question_text,
                     'section_slug': section_slug,
                     'section_title': section_title
                 }
                 return render(request, 'base/questionnaire_page.html', context) # Assuming template path

            # --- Call Gemini API ---
            ai_response_text = None # Initialize
            if not model:
                messages.error(request, "The AI model is currently unavailable. Please try again later.")
                # Optionally save interaction attempt with error status
                ai_response_text = "Error: AI model not initialized."
            else:
                try:
                    prompt = create_gemini_prompt(question_text, user_answer, desired_response_type)
                    # Make the API call (consider adding safety settings)
                    safety_settings = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    ]
                    response = model.generate_content(prompt, safety_settings=safety_settings)
                    response = model.generate_content(prompt) # Simpler call

                    # Safely access the generated text
                    try:
                        ai_response_text = response.text
                    except ValueError:
                        # Handle cases where the response might be blocked due to safety settings
                        ai_response_text = "Response could not be generated due to safety constraints."
                        print(f"WARN: Gemini response blocked for user {request.user.username}, section {section_slug}. Feedback: {response.prompt_feedback}")
                    except AttributeError:
                         # Handle cases where response structure might differ or be empty
                         ai_response_text = "An unexpected issue occurred while retrieving the AI response."
                         print(f"WARN: Unexpected Gemini response structure for user {request.user.username}, section {section_slug}. Response: {response}")


                except Exception as e:
                    # Log the detailed error
                    print(f"ERROR: Gemini API call failed for user {request.user.username}, section {section_slug}. Error: {e}")
                    # Provide a user-friendly message
                    messages.error(request, f"Sorry, there was an error communicating with the AI. Please try again later.")
                    # Store error indicator
                    ai_response_text = f"Error generating response: Communication failure ({type(e).__name__})."

            # --- Save Interaction to Database ---
            try:
                AiInteraction.objects.create(
                    user=request.user,
                    section=section_slug,
                    question_text=question_text,
                    user_answer=user_answer,
                    ai_response=ai_response_text # Save the generated text or error indicator
                )
                # Provide success message only if AI response was likely successful
                if ai_response_text and "Error:" not in ai_response_text and "Response could not be generated" not in ai_response_text:
                     messages.success(request, "AI response received and saved!")
                # Error messages related to AI generation are handled above

            except Exception as e:
                 # Log database saving error
                 print(f"ERROR: Failed to save AiInteraction for user {request.user.username}. Error: {e}")
                 messages.error(request, "There was an issue saving your interaction after getting the AI response.")

            # --- Redirect to Results Feed ---
            # Redirect after POST to prevent double submission on refresh
            # Assuming the results feed URL name is 'results_feed' in the 'ai_features' namespace
            return redirect('ai_features:results_feed')

        else:
            # Form is invalid (e.g., empty answer), re-render the page with errors
            messages.error(request, "Please provide an answer to the question.")
            # Fall through to render the GET request part with the invalid form

    # --- Handle GET Request ---
    else:
        # Prepare initial data for the hidden fields in the form
        initial_data = {'question_text': question_text, 'section': section_slug}
        form = QuestionnaireForm(initial=initial_data)

    context = {
        'form': form,
        'question': question_text,
        'section_slug': section_slug,
        'section_title': section_title
    }
    # Ensure you have a template at this path or adjust as needed
    return render(request, 'base/questionnaire_page.html', context)


@login_required # Ensure user is logged in
def results_feed_view(request):
    """
    Displays a feed of the logged-in user's past AI interactions,
    ordered by the most recent first.
    """
    # Retrieve interactions specifically for the logged-in user
    interactions = AiInteraction.objects.filter(user=request.user).order_by('-timestamp')
    context = {
        'interactions': interactions,
    }
    # Ensure you have a template at this path or adjust as needed
    return render(request, 'base/results_feed.html', context)

