from django.contrib import admin
from .models import Consultation, ConsultationMessage, ConsultationStatusMaster, Question

class ConsultationMessageInline(admin.StackedInline):
    model = ConsultationMessage
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('title', 'requester', 'respondent', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'requester__username', 'respondent__username')
    inlines = [ConsultationMessageInline]

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'source_consultation', 'created_by', 'created_at')
    search_fields = ('title', 'problem_summary', 'solution_summary')

# If it's already registered, unregister it first to avoid errors
try:
    admin.site.unregister(ConsultationStatusMaster)
except admin.sites.NotRegistered:
    pass

@admin.register(ConsultationStatusMaster)
class ConsultationStatusMasterAdmin(admin.ModelAdmin):
    pass
