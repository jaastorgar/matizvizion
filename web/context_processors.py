def mv_context(request):
    user = getattr(request, 'user', None)
    logged = bool(user and getattr(user, 'is_authenticated', False))
    role = getattr(user, 'role', None) if logged else None
    email = getattr(user, 'email', '') if logged else ''
    return {'mv_logged': logged, 'mv_role': role, 'mv_email': email}