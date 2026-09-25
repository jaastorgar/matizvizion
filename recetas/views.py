import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.base import ContentFile
from django.db.models import Q
from django.views.generic import TemplateView
from rest_framework import viewsets, serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Receta
from .serializers import RecetaSerializer, EXT_OK, MAX_MB


def es_staff(user):
    return bool(user and user.is_authenticated and
                (getattr(user, 'role', '') in ('VENDEDOR', 'ADMIN') or user.is_staff or user.is_superuser))


class MisRecetasPage(TemplateView):
    template_name = 'modules/recetas/mis_recetas.html'


class RecetasStaffPage(TemplateView):
    template_name = 'modules/recetas/staff_recetas.html'



class RecetaViewSet(viewsets.ModelViewSet):
    serializer_class = RecetaSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        qs = Receta.objects.select_related('cliente', 'subido_por')
        if es_staff(user):
            q = (self.request.query_params.get('q') or '').strip()
            cid = self.request.query_params.get('cliente')
            if cid:
                qs = qs.filter(cliente_id=cid)
            if q:
                qs = qs.filter(Q(cliente__email__icontains=q) |
                               Q(cliente__first_name__icontains=q) |
                               Q(cliente__last_name__icontains=q) |
                               Q(cliente__perfil_cliente__rut__icontains=q) |
                               Q(nombre__icontains=q))
            return qs
        return qs.filter(cliente=user)

    def perform_create(self, serializer):
        user = self.request.user
        data = self.request.data
        cliente = serializer.validated_data.get('cliente') or user
        if not es_staff(user):
            cliente = user
            from accounts.consent import requiere_salud, ERROR_CONSENTIMIENTO_SALUD
            if not requiere_salud(user):
                raise drf_serializers.ValidationError({
                    'code': ERROR_CONSENTIMIENTO_SALUD,
                    'detail': 'Debes autorizar el tratamiento de tus datos de salud visual para subir una receta.'
                })
        extra = {}
        if not serializer.validated_data.get('archivo') and data.get('archivo_base64'):
            raw = data['archivo_base64']
            if ',' in raw:
                raw = raw.split(',', 1)[1]
            try:
                content = base64.b64decode(raw)
            except Exception:
                raise drf_serializers.ValidationError({'archivo': 'Archivo base64 invalido.'})
            name = data.get('archivo_nombre') or 'receta.pdf'
            ext = ('.' + name.rsplit('.', 1)[-1].lower()) if '.' in name else ''
            if ext not in EXT_OK:
                raise drf_serializers.ValidationError({'archivo': 'Formato no permitido.'})
            if len(content) > MAX_MB * 1024 * 1024:
                raise drf_serializers.ValidationError({'archivo': 'El archivo supera %d MB.' % MAX_MB})
            extra['archivo'] = ContentFile(content, name=name)
        serializer.save(cliente=cliente, subido_por=user, **extra)

    @action(detail=False, methods=['get'], url_path='buscar-cliente')
    def buscar_cliente(self, request):
        if not es_staff(request.user):
            return Response({'error': 'Sin permisos.'}, status=403)
        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response({'error': 'Indica un correo.'}, status=400)
        User = get_user_model()
        u = User.objects.filter(email__iexact=q).first()
        if not u:
            return Response({'error': 'No existe un usuario con ese correo.'}, status=404)
        dn = ((u.first_name or '') + ' ' + (u.last_name or '')).strip()
        return Response({'id': u.id, 'email': u.email, 'nombre': dn or u.email})
