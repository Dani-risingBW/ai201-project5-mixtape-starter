"""Test script to verify Bug #1 is fixed (streak resets on Sunday)"""
from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import User
from services.streak_service import update_listening_streak

app = create_app()

def test_streak_on_sunday():
    """Test that streak increments on Sunday (currently fails due to bug)"""
    with app.app_context():
        # Create a test user
        user = User(username="test_user", email="test@mixtape.app")
        db.session.add(user)
        db.session.commit()

        # Simulate listening on Saturday
        saturday = datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc)  # Saturday
        user.last_listened_at = saturday - timedelta(days=1)  # Friday
        user.listening_streak = 1
        update_listening_streak(user, saturday)

        print(f"After listening on Saturday (days_since_last=1):")
        print(f"  Streak: {user.listening_streak} (should be 2)")
        print()

        # Simulate listening on Sunday (THE BUG HAPPENS HERE)
        sunday = datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc)  # Sunday
        update_listening_streak(user, sunday)

        print(f"After listening on Sunday (days_since_last=1):")
        print(f"  Streak: {user.listening_streak}")
        print(f"  Expected: 3 (should increment)")
        print(f"  Actual: {user.listening_streak}")

        if user.listening_streak == 3:
            print("\n✅ BUG #1 IS FIXED!")
        else:
            print("\n❌ BUG #1 STILL EXISTS (streak reset on Sunday)")

        # Cleanup
        db.session.delete(user)
        db.session.commit()

def test_streak_on_weekday():
    """Test that streak increments on weekdays (should work)"""
    with app.app_context():
        user = User(username="test_user2", email="test2@mixtape.app")
        db.session.add(user)
        db.session.commit()

        # Listen on Monday
        monday = datetime(2026, 7, 6, 12, 0, 0, tzinfo=timezone.utc)
        user.last_listened_at = monday - timedelta(days=1)
        user.listening_streak = 1
        update_listening_streak(user, monday)

        print(f"\nWeekday test - Monday:")
        print(f"  Streak: {user.listening_streak} (should be 2)")

        if user.listening_streak == 2:
            print("  ✅ Weekday increment works")
        else:
            print("  ❌ Weekday increment broken")

        db.session.delete(user)
        db.session.commit()

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Bug #1: Streak resets on Sunday")
    print("=" * 60)
    print()
    test_streak_on_sunday()
    test_streak_on_weekday()
