from rest_framework import serializers
from django.contrib.auth import get_user_model
from support_tickets.models import SupportCategory, SupportTicket, TicketComment, TicketAttachment

User = get_user_model()


class SupportCategorySerializer(serializers.ModelSerializer):
    ticket_count = serializers.IntegerField(source='tickets.count', read_only=True)

    class Meta:
        model = SupportCategory
        fields = ('id', 'name', 'slug', 'description', 'ticket_count', 'created_at')
        read_only_fields = ('id', 'ticket_count', 'created_at')


class TicketAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TicketAttachment
        fields = ('id', 'file', 'file_url', 'uploaded_by', 'uploaded_by_name', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_by', 'uploaded_at')

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = TicketComment
        fields = ('id', 'ticket', 'author', 'author_name', 'author_role', 'body', 'is_internal', 'attachments', 'created_at', 'updated_at')
        read_only_fields = ('id', 'author', 'created_at', 'updated_at')


class SupportTicketListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    reporter_name = serializers.CharField(source='reporter.get_full_name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.get_full_name', read_only=True, allow_null=True)
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)

    class Meta:
        model = SupportTicket
        fields = ('id', 'ticket_number', 'title', 'status', 'priority', 'category_name', 'reporter_name', 'assignee_name', 'comment_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'ticket_number', 'created_at', 'updated_at')


class SupportTicketSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    reporter_name = serializers.CharField(source='reporter.get_full_name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.get_full_name', read_only=True, allow_null=True)
    comments = TicketCommentSerializer(many=True, read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=SupportCategory.objects.all())

    class Meta:
        model = SupportTicket
        fields = ('id', 'ticket_number', 'title', 'description', 'status', 'priority', 'category', 'category_name', 'reporter', 'reporter_name', 'assignee', 'assignee_name', 'due_date', 'resolved_at', 'comments', 'attachments', 'created_at', 'updated_at')
        read_only_fields = ('id', 'ticket_number', 'reporter', 'resolved_at', 'created_at', 'updated_at')


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ('title', 'description', 'priority', 'category', 'due_date')

    def create(self, validated_data):
        validated_data['reporter'] = self.context['request'].user
        from common.utils import generate_ticket_number
        validated_data['ticket_number'] = generate_ticket_number()
        return super().create(validated_data)


class TicketStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SupportTicket.Status.choices)
    comment = serializers.CharField(required=False, allow_blank=True)
