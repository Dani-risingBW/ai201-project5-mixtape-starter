"""Debug script to print all songs"""
from app import create_app, db
from models import Song

app = create_app()
with app.app_context():
    songs = db.session.query(Song).all()
    if not songs:
        print("No songs found in database")
    else:
        print(f"Found {len(songs)} songs:\n")
        for i, song in enumerate(songs, 1):
            print(f"{i}. {song.title}")
            print(f"   ID: {song.id}")
            print(f"   Artist: {song.artist}")
            print(f"   Genre: {song.genre}")
            print(f"   Tags: {[tag.name for tag in song.tags]}")
            print()
