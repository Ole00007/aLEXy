"""Create admin user for aLEXy Railway deployment."""
import sys
sys.path.insert(0, '/Users/olesiarasing/aLEXy')

from wsgi import app
from crm.models.user import User
from werkzeug.security import generate_password_hash
from crm.extensions import db

with app.app_context():
    user = User.query.filter_by(email='admin@alexy.test').first()
    if not user:
        user = User()
        user.email = 'admin@alexy.test'
        user.role = 'admin'
        user.set_password('Admin123!')
        db.session.add(user)
        db.session.commit()
        print(f'Created user: {user.email} (id={user.id})')
    else:
        print(f'User exists: {user.email} (id={user.id})')
