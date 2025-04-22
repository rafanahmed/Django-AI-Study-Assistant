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
from .models import TimerSession
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from .models import TimerSession
from django.views.decorators.http import require_POST
from django.utils.timezone import now
from .models import LoginActivity
from .models import Exam, ExamQuestion  
from .forms import ExamForm, ExamQuestionForm
from .forms import ExamAnswerForm
from .models import ExamAnswer
from datetime import datetime, timedelta
from django.db.models import Sum


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

# --- Gemini API Configuration & Check ---
gemini_configured_successfully = False
try:
    model_name = "gemini-1.5-flash-latest"
    model = genai.GenerativeModel(model_name)
    print(f"DEBUG: Successfully initialized Gemini model: {model_name}")
    gemini_configured_successfully = True
except Exception as e:
    print(f"ERROR: Failed to initialize Gemini model in views.py (check API key configuration and value). Error: {e}")
    model = None

# --- Helper Function for Gemini Prompt ---
def create_gemini_prompt(question, answer, desired_response_type):
    """Formats the prompt for the Gemini API."""
    return f"""Context: A user is interacting with an educational web application.

Question asked to the user:
{question}

User's Answer:
{answer}

Task: Based *only* on the user's answer provided above in response to the question, provide {desired_response_type}. 
Please provide a helpful and reasonably detailed response suitable for the context. 
Format the entire response as plain text only, without using any Markdown formatting (no asterisks, underscores, backticks, lists, etc.)."""


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Log today's login
            LoginActivity.objects.get_or_create(user=user, login_date=now().date())

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
    return render(request, 'base/register.html', {'form': form})


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
            deck = form.save(commit=False)
            deck.user = request.user  # 🔥 THIS LINE IS NEEDED
            deck.save()
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
        flashcard.deck = deck  # 🔥 this line is essential!
        flashcard.save()
        return redirect('ai_features:deck_detail', deck_id=deck.id)

    return render(request, 'base/deck_detail.html', {
        'deck': deck,
        'cards': cards,
        'form': form
    })



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


from .models import LoginActivity

@login_required
def study_sessions_view(request):
    total_seconds = sum(session.duration_seconds for session in request.user.timer_sessions.all())
    hours_spent = total_seconds // 3600
    timer_uses = request.user.timer_sessions.count()
    flashcard_count = Flashcard.objects.filter(deck__user=request.user).count()

    study_hours_per_week = []
    trend = 'the same as'
    percent_change = 0

    today = datetime.today()

    for i in range(7):
        week_start = today - timedelta(weeks=i)
        week_end = week_start + timedelta(weeks=1)

        weekly_hours = TimerSession.objects.filter(
            user=request.user,
            started_at__gte=week_start,
            started_at__lt=week_end
        ).aggregate(total_hours=Sum('duration_seconds'))['total_hours'] or 0

        study_hours_per_week.append(weekly_hours // 3600)

    if len(study_hours_per_week) > 1:
        last_week = study_hours_per_week[0]
        previous_week = study_hours_per_week[1]
        if previous_week != 0:
            if last_week > previous_week:
                trend = 'up'
            elif last_week < previous_week:
                trend = 'down'
            percent_change = round(((last_week - previous_week) / previous_week) * 100, 2)
        else:
            trend = 'the same as'
            percent_change = 0

    return render(request, 'base/study_sessions.html', {
        'hours_spent': hours_spent,
        'timer_uses': timer_uses,
        'flashcard_count': flashcard_count,
        'study_hours_per_week': study_hours_per_week,
        'trend': trend,
        'percent_change': percent_change,
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


@login_required
def study_groups_view(request):
    return render(request, 'base/study_groups.html', {
        'user_groups': request.user.study_groups.all(),
        'all_groups': StudyGroup.objects.all()
    })


@csrf_exempt
@require_POST
@login_required
def log_timer_session(request):
    try:
        seconds = int(request.POST.get("duration_seconds", 0))
        if seconds > 0:
            TimerSession.objects.create(user=request.user, duration_seconds=seconds)
            return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "invalid"})


@login_required
def exam_list(request):
    exams = Exam.objects.all()
    return render(request, 'base/exam_list.html', {'exams': exams})

@login_required
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    return render(request, 'base/exam_detail.html', {'exam': exam})

@login_required
def create_exam(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            return redirect('ai_features:exam_list')  # Updated to use ai_features
    else:
        form = ExamForm()
    return render(request, 'base/create_exam.html', {'form': form})

@login_required
def edit_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Check if the current user is the exam creator
    if request.user != exam.created_by:
        messages.error(request, "You don't have permission to edit this exam.")
        return redirect('ai_features:exam_detail', exam_id=exam.id)
    
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, "Exam updated successfully!")
            return redirect('ai_features:exam_detail', exam_id=exam.id)
    else:
        form = ExamForm(instance=exam)
    
    return render(request, 'base/edit_exam.html', {
        'form': form,
        'exam': exam
    })

    # Add to views.py
@login_required
def add_question(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.user != exam.created_by:
        messages.error(request, "You don't have permission to add questions to this exam.")
        return redirect('ai_features:exam_detail', exam_id=exam.id)
    
    if request.method == 'POST':
        form = ExamQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam  # Connect question to exam
            question.save()
            messages.success(request, "Question added successfully!")
            return redirect('ai_features:add_question', exam_id=exam.id)  # Stay on same page to add more
    else:
        form = ExamQuestionForm()
    
    # Get all existing questions for this exam
    existing_questions = exam.questions.all().order_by('order')
    
    return render(request, 'base/add_question.html', {
        'form': form,
        'exam': exam,
        'questions': existing_questions
    })

@login_required
def add_answer(request, question_id):
    question = get_object_or_404(ExamQuestion, id=question_id)
    exam = question.exam
    
    if request.user != exam.created_by:
        messages.error(request, "You don't have permission to add answers to this question.")
        return redirect('ai_features:exam_detail', exam_id=exam.id)
    
    if request.method == 'POST':
        form = ExamAnswerForm(request.POST)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.question = question
            answer.save()
            messages.success(request, "Answer added successfully!")
            return redirect('ai_features:add_answer', question_id=question.id)
    else:
        form = ExamAnswerForm()
    
    existing_answers = question.answers.all()
    
    return render(request, 'base/add_answer.html', {
        'form': form,
        'question': question,
        'exam': exam,
        'answers': existing_answers
    })

@login_required
def delete_question(request, question_id):
    question = get_object_or_404(ExamQuestion, id=question_id)
    exam_id = question.exam.id
    
    if request.user != question.exam.created_by:
        messages.error(request, "You don't have permission to delete this question.")
    else:
        question.delete()
        messages.success(request, "Question deleted successfully!")
    
    return redirect('ai_features:exam_detail', exam_id=exam_id)

@login_required
def delete_answer(request, answer_id):
    answer = get_object_or_404(ExamAnswer, id=answer_id)
    question = answer.question
    exam = question.exam
    
    if request.user != exam.created_by:
        messages.error(request, "You don't have permission to delete this answer.")
    else:
        answer.delete()
        messages.success(request, "Answer deleted successfully!")
    
    return redirect('ai_features:add_answer', question_id=question.id)


@login_required
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Check if the current user is the exam creator
    if request.user != exam.created_by:
        messages.error(request, "You don't have permission to delete this exam.")
        return redirect('ai_features:exam_list')
    
    if request.method == 'POST':
        exam.delete()
        messages.success(request, "Exam deleted successfully!")
        return redirect('ai_features:exam_list')
    
    # If GET request, show confirmation page
    return render(request, 'base/delete_exam.html', {'exam': exam})


@login_required
def take_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = exam.questions.all().order_by('order')
    
    # Convert minutes to milliseconds for JavaScript timer
    duration_ms = exam.duration_minutes * 60 * 1000
    
    if request.method == 'POST':
        # Process submitted answers here
        return redirect('ai_features:exam_result', exam_id=exam.id)
    
    return render(request, 'base/take_exam.html', {
        'exam': exam,
        'questions': questions,
        'duration_ms': duration_ms,
    })


@login_required
def submit_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    questions = exam.questions.all()
    score = 0
    total_questions = questions.count()
    results = []
    
    if request.method == 'POST':
        for question in questions:
            selected_answer_id = request.POST.get(f'question_{question.id}')
            correct_answer = question.answers.filter(is_correct=True).first()
            
            is_correct = False
            if selected_answer_id and correct_answer:
                is_correct = (int(selected_answer_id) == correct_answer.id)
            
            results.append({
                'question': question,
                'selected_answer': question.answers.filter(id=selected_answer_id).first() if selected_answer_id else None,
                'correct_answer': correct_answer,
                'is_correct': is_correct
            })
            
            if is_correct:
                score += 1
        
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        
        return render(request, 'base/exam_results.html', {
            'exam': exam,
            'results': results,
            'score': score,
            'total_questions': total_questions,
            'percentage': percentage
        })
    
    return redirect('ai_features:take_exam', exam_id=exam.id)


@login_required
def exam_result(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Retrieve results from session
    results_data = request.session.get('exam_results', {})
    
    # Verify we have results for this exam
    if not results_data or results_data.get('exam_id') != exam.id:
        messages.error(request, "No exam results found. Please take the exam first.")
        return redirect('ai_features:take_exam', exam_id=exam.id)
    
    # Reconstruct the full results with question and answer objects
    results = []
    for r in results_data['results']:
        question = get_object_or_404(ExamQuestion, id=r['question_id'])
        selected_answer = question.answers.filter(id=r['selected_answer_id']).first() if r['selected_answer_id'] else None
        correct_answer = question.answers.filter(is_correct=True).first()
        
        results.append({
            'question': question,
            'selected_answer': selected_answer,
            'correct_answer': correct_answer,
            'is_correct': r['is_correct']
        })
    
    return render(request, 'base/exam_results.html', {
        'exam': exam,
        'results': results,
        'score': results_data['score'],
        'total_questions': results_data['total_questions'],
        'percentage': results_data['percentage']
    })