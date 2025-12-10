import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polysphere.settings')
django.setup()

from kanoodleApp.models import Piece

deleted = Piece.objects.all().delete()
print(f'Deleted: {deleted}')
