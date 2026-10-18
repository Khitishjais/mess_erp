
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.common.mixins import OutletScopedMixin
from apps.common.permissions import IsPortalUser
from apps.common.request import body_str, get_id, resolve_outlet
from apps.common.scope import outlets_for

from . import llm, services
from .models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'outlet', 'text', 'rating', 'meal', 'date', 'sentiment', 'topics']
        read_only_fields = ['sentiment', 'topics', 'date']
        extra_kwargs = {'rating': {'min_value': 1, 'max_value': 5}}

    def validate_meal(self, meal):
        if meal not in ('', 'breakfast', 'lunch', 'dinner'):
            raise serializers.ValidationError('Use breakfast, lunch or dinner.')
        return meal

    def validate_outlet(self, o):
        if not outlets_for(self.context['request'].user).filter(pk=o.pk).exists():
            raise serializers.ValidationError('Outlet not accessible.')
        return o


class FeedbackViewSet(OutletScopedMixin, viewsets.ModelViewSet):
    queryset = Feedback.objects.order_by('-date', '-id')
    serializer_class = FeedbackSerializer
    permission_classes = [IsPortalUser]
    filterset_fields = ['outlet', 'sentiment', 'meal']

    def perform_create(self, ser):
        d = ser.validated_data
        s, t = services.sentiment(d['text'], d.get('rating'))
        ser.save(sentiment=s, topics=t)

    def perform_update(self, ser):
        text = ser.validated_data.get('text', ser.instance.text)
        rating = ser.validated_data.get('rating', ser.instance.rating)
        s, t = services.sentiment(text, rating)          # edited text is analysed again, never a stale label
        ser.save(sentiment=s, topics=t)


@api_view(['GET'])
@permission_classes([IsPortalUser])
def feedback_summary(request):
    from collections import Counter
    qs = Feedback.objects.filter(outlet__in=outlets_for(request.user))
    if get_id(request, 'outlet'):
        qs = qs.filter(outlet_id=get_id(request, 'outlet'))
    sent = Counter(qs.values_list('sentiment', flat=True))
    neg_topics = Counter(t for f in qs.filter(sentiment='negative') for t in f.topics)
    return Response({'total': qs.count(), 'sentiment': dict(sent), 'top_complaints': neg_topics.most_common(5)})


@api_view(['GET'])
@permission_classes([IsPortalUser])
def anomalies(request):
    return Response(services.anomalies(outlets_for(request.user)))


@api_view(['GET'])
@permission_classes([IsPortalUser])
def pricing(request):
    return Response(services.pricing_hints(outlets_for(request.user)))


@api_view(['GET'])
@permission_classes([IsPortalUser])
def kitchen_eta(request):
    cats = [c for c in request.query_params.get('categories', '').split(',') if c]
    return Response(services.kitchen_eta(resolve_outlet(request), cats))


@api_view(['POST'])
@permission_classes([IsPortalUser])
def chat(request):
    """Ask in English or Hinglish. Known questions are answered from our own numbers; others go to the LLM if configured."""
    q = body_str(request, 'question').strip()
    if not q:
        raise ValidationError('Ask something.')
    o, outlets = resolve_outlet(request), outlets_for(request.user)
    r = services.answer(q, o, outlets)
    if r:
        return Response({**r, 'source': 'rules'})
    if llm.allowed(request.user.tenant_owner):
        from apps.mess import services as m
        ctx = {'tomorrow_plan': m.day_plan(o, __import__('datetime').date.today()), 'wastage': m.wastage_insights(o)}
        try:
            return Response({'intent': 'llm', 'answer': llm.ask(q, ctx), 'source': 'llm'})
        except Exception as e:
            return Response({'intent': 'error', 'answer': f'AI service error: {e}', 'source': 'llm'}, status=502)
    return Response({'intent': 'unknown', 'source': 'rules', 'answer': 'I can answer: wastage, purchase plan, stock alerts, staffing, '
                     'how much <ingredient> tomorrow, forecast (kitne log), sales today, top items. '
                     '(Free-form questions need an AI key: set GEMINI_API_KEY or ANTHROPIC_API_KEY.)'})


@api_view(['POST'])
@permission_classes([IsPortalUser])
def agent(request):
    """RAG assistant: retrieves from the guides + this tenant's own records, uses read-only tools, cites its sources."""
    from .agent import run_agent
    q = body_str(request, 'question').strip()
    if not q:
        raise ValidationError('Ask something.')
    history = request.data.get('history') if isinstance(request.data, dict) else None
    return Response(run_agent(request.user, q, resolve_outlet(request), outlets_for(request.user), history))


@api_view(['POST'])
@permission_classes([IsPortalUser])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def invoice_scan(request):
    """Photo of a supplier bill -> structured lines. Needs an LLM key (not available otherwise)."""
    if llm.enabled() and not llm.allowed(request.user.tenant_owner):
        return Response({'detail': 'External AI is switched off in Settings.'}, status=403)
    if not llm.enabled():
        return Response({'detail': 'Invoice reading is switched off. Set GEMINI_API_KEY (or ANTHROPIC_API_KEY) on the server to enable it.'}, status=501)
    f = request.FILES.get('image')
    if not f:
        raise ValidationError('Upload an image as "image".')
    try:
        return Response(llm.read_invoice(f.read(), f.content_type or 'image/jpeg'))
    except Exception as e:
        return Response({'detail': f'Could not read invoice: {e}'}, status=502)


@api_view(['POST'])
@permission_classes([IsPortalUser])
def describe(request):
    name, ing = body_str(request, 'name'), body_str(request, 'ingredients')
    if llm.allowed(request.user.tenant_owner):
        try:
            return Response({'text': llm.write_copy(name, ing), 'source': 'llm'})
        except Exception:
            pass
    return Response({'text': f'{name}: freshly prepared with {ing or "quality ingredients"}, served hot.', 'source': 'template'})