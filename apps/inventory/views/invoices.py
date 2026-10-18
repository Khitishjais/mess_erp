"""Supplier bill -> stock. scan (photo -> review table), review (typed lines -> review table), apply (reviewed lines -> stock)."""
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.ai import gemini, llm
from apps.common.permissions import IsPortalUser
from apps.common.request import resolve_outlet

from ..invoice import apply_invoice, build_review, clean

MAX_IMAGE = 4 * 1024 * 1024        # hosted platforms cap request bodies at about 4.5 MB; the portal shrinks photos before upload
TYPES = ('image/jpeg', 'image/png', 'image/webp', 'image/gif')


@api_view(['POST'])
@permission_classes([IsPortalUser])
@parser_classes([MultiPartParser, FormParser])
def invoice_scan(request):
    """A photo of the bill -> a review table. NOTHING is saved here; a person checks the table and then calls apply."""
    if llm.enabled() and not llm.allowed(request.user.tenant_owner):
        return Response({'detail': 'External AI is switched off in Settings (AI and privacy), so bill photos are not sent anywhere. You can type the lines by hand.', 'code': 'ai_blocked'}, status=403)
    if not llm.enabled():
        return Response({'detail': 'Reading bills from a photo needs an AI key (GEMINI_API_KEY or ANTHROPIC_API_KEY) on the server. You can still type the lines by hand.',
                         'code': 'ai_off'}, status=501)
    f = request.FILES.get('image')
    if not f:
        raise ValidationError('Upload the bill photo as "image".')
    if f.content_type not in TYPES:
        raise ValidationError('Use a JPG, PNG or WebP photo.')
    if f.size > MAX_IMAGE:
        raise ValidationError('The photo is larger than 4 MB. Take it again at a lower quality.')
    try:
        cleaned = clean(llm.read_invoice(f.read(), f.content_type))
    except Exception as e:                      # model/network/parse problems: tell the user, let them type instead
        return Response({'detail': f'Could not read this bill: {gemini.friendly(e)}. Retry, retake the photo in better light, or type the lines.', 'code': 'read_failed'}, status=502)
    return Response(build_review(request.user.tenant_owner, cleaned))


@api_view(['POST'])
@permission_classes([IsPortalUser])
@parser_classes([JSONParser])
def invoice_review(request):
    """Typed bill lines (name, qty, unit, rate) -> the same review table, so manual entry gets matching and unit conversion too."""
    try:
        cleaned = clean(request.data if isinstance(request.data, dict) else None)
    except ValueError as e:
        raise ValidationError(str(e))
    return Response(build_review(request.user.tenant_owner, cleaned))


@api_view(['POST'])
@permission_classes([IsPortalUser])
@parser_classes([JSONParser])
def invoice_apply(request):
    """Enter the reviewed lines as purchases for one outlet. Refuses a bill number that was already entered (409)."""
    if not isinstance(request.data, dict):
        raise ValidationError('Send a JSON object.')
    return Response(apply_invoice(request.user, resolve_outlet(request), request.data), status=201)
