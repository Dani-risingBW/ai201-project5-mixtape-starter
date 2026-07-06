"""Debug script to print all users"""
from app import create_app, db
from models import User

app = create_app()
with app.app_context():
    users = db.session.query(User).all()
    if not users:
        print("No users found in database")
    else:
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"  ID: {user.id}")
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Streak: {user.listening_streak}")
            print()
