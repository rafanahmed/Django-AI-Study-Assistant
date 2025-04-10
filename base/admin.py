from django.contrib import admin
from .models import Profile
from .models import Profile, AiInteraction

admin.site.register(Profile)

# --- Added Admin Configuration for AI Interaction Feature ---
@admin.register(AiInteraction)
class AiInteractionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the AiInteraction model.
    Allows viewing and managing interactions in the Django admin site.
    """
    # Fields to display in the list view
    list_display = ('user', 'section', 'timestamp', 'question_text', 'ai_response_preview')
    # Fields to filter by in the sidebar
    list_filter = ('section', 'timestamp', 'user')
    # Fields to search within
    search_fields = ('user__username', 'question_text', 'user_answer', 'ai_response')
    # Make fields read-only in the admin detail view, as they are populated by the app logic
    readonly_fields = ('user', 'section', 'question_text', 'user_answer', 'ai_response', 'timestamp')

    def ai_response_preview(self, obj):
        """Shows a truncated preview of the AI response in the list display."""
        if obj.ai_response:
            return (obj.ai_response[:75] + '...') if len(obj.ai_response) > 75 else obj.ai_response
        return None # Or return an empty string ''
    ai_response_preview.short_description = 'AI Response Preview' # Column header

    # Disable the ability to add AiInteraction records directly via the admin interface,
    # as they should be created through the user-facing questionnaire.
    def has_add_permission(self, request):
        return False