"""Test script to verify Bug #3 (duplicate search results)"""
from app import create_app, db
from models import Song, song_tags

app = create_app()
with app.app_context():
    query = (
        db.session.query(Song)
        .outerjoin(song_tags, Song.id == song_tags.c.song_id)
        .filter(Song.title.ilike("%crown%"))
    )

    results = query.all()
    print(f"Total rows returned by SQLAlchemy: {len(results)}")
    print(f"Unique song IDs: {len(set(r.id for r in results))}")
    print()

    for i, r in enumerate(results):
        print(f"  Row {i+1}: {r.title} (ID: {r.id})")

    print()
    print("If Total rows > Unique song IDs, then BUG #3 EXISTS")
    print(f"  Total: {len(results)}, Unique: {len(set(r.id for r in results))}")

    if len(results) > len(set(r.id for r in results)):
        print("  ❌ BUG #3 CONFIRMED - Duplicates found!")
    else:
        print("  ✅ No duplicates found (bug may be fixed or non-existent)")
