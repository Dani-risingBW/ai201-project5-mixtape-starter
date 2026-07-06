"""Debug script to print all playlists"""
from app import create_app, db
from models import Playlist

app = create_app()
with app.app_context():
    playlists = db.session.query(Playlist).all()
    if not playlists:
        print("No playlists found in database")
    else:
        print(f"Found {len(playlists)} playlists:\n")
        for playlist in playlists:
            print(f"Playlist: {playlist.name}")
            print(f"  ID: {playlist.id}")
            print(f"  Created by: {playlist.created_by}")
            print(f"  Collaborative: {playlist.is_collaborative}")
            print(f"  Songs: {len(playlist.songs)}")
            print()
