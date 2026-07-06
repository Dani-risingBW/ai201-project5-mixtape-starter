# Mixtape Codebase Map & Explanation

A social music app where friends share songs, build collaborative playlists, and track listening stats.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flask Routes Layer                        │
│  (Handles HTTP requests and responses)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  /songs/          /playlists/        /users/          /feed/    │
│  • search         • create           • get_user       • listening-now
│  • get_detail     • get_detail       • get_streak     • activity
│  • rate           • get_songs        • notifications  │
│  • listen         • add_song         • read_notification
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                      Services Layer                              │
│    (Business logic - pure functions, no HTTP)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  search_service       playlist_service   feed_service   │
│  • search_songs       • create_playlist  • get_friends_listening_now
│  • get_song           • get_playlist     • get_activity_feed
│                       • get_playlist_songs
│                       • get_user_playlists    notification_service
│                                              • create_notification
│  streak_service                            • add_to_playlist
│  • record_listening_event                  • rate_song
│  • update_listening_streak                 • get_notifications
│  • get_streak                              • mark_as_read
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                      Models Layer                                │
│     (SQLAlchemy ORM - database entities)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User              Song                 ListeningEvent          │
│  • id (UUID)       • id (UUID)          • id (UUID)             │
│  • username        • title              • user_id               │
│  • email           • artist             • song_id               │
│  • listening_streak • album             • listened_at           │
│  • last_listened_at • genre                                      │
│  • created_at      • shared_by          Rating                  │
│  • friends (M2M)   • shared_at          • id (UUID)             │
│                    • share_note         • user_id               │
│  Tag               • tags (M2M)         • song_id               │
│  • id (UUID)                           • score                  │
│  • name            Playlist            • rated_at              │
│                    • id (UUID)          
│                    • name              Notification            │
│                    • created_by         • id (UUID)             │
│                    • created_at         • user_id               │
│                    • is_collaborative   • notification_type     │
│                    • songs (M2M)        • body                  │
│                                         • created_at            │
│                                         • read                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                      Database (SQLite)                           │
│           mixtape.db with 8 tables + 3 junction tables          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model Relationships

```
User
├── many shared_songs → Song
├── many ratings → Rating
├── many listening_events → ListeningEvent
├── many notifications → Notification
├── many playlists → Playlist
└── many friends → User (bidirectional through friendships table)

Song
├── one shared_by_user ← User
├── many ratings ← Rating
├── many listening_events ← ListeningEvent
├── many tags → Tag (M2M through song_tags)
└── many playlists → Playlist (M2M through playlist_entries)

Playlist
├── one creator ← User
└── many songs → Song (M2M through playlist_entries with position)

Tag
└── many songs ← Song (M2M through song_tags)

ListeningEvent
├── one listener ← User
└── one song ← Song

Rating
├── one rater ← User
└── one song ← Song

Notification
└── one recipient ← User
```

---

## Complete API Endpoint Map

### Songs Routes (`/songs`)
```
GET  /songs/search?q=<query>              Search songs by title or artist
GET  /songs/<song_id>                     Get song details
POST /songs/<song_id>/rate                Rate a song (user_id, score 1-5)
POST /songs/<song_id>/listen              Record a listening event (user_id)
```

### Playlists Routes (`/playlists`)
```
POST /playlists/                          Create a new playlist
GET  /playlists/<playlist_id>             Get playlist metadata
GET  /playlists/<playlist_id>/songs       Get all songs in playlist (ordered)
POST /playlists/<playlist_id>/songs       Add a song to playlist (song_id, added_by)
```

### Users Routes (`/users`)
```
GET  /users/<user_id>                     Get user profile
GET  /users/<user_id>/streak              Get listening streak
GET  /users/<user_id>/notifications       Get notifications (optional: unread_only=true)
POST /users/notifications/<notif_id>/read Mark notification as read
```

### Feed Routes (`/feed`)
```
GET  /feed/<user_id>/listening-now        Friends listening in last 24 hours (1 per friend)
GET  /feed/<user_id>/activity             Last 20 listening events from all friends
```

---

## Feature Call Chains (Request → Response)

### Sharing & Rating a Song
```
User rates a song
  → POST /songs/<song_id>/rate {user_id, score}
  → routes/songs.py:rate()
  → services/notification_service.rate_song()
  → create Rating record
  → ✗ BUG #4: No notification created for song_rater
```

### Listening Streak Updates
```
User listens to a song
  → POST /songs/<song_id>/listen {user_id}
  → routes/songs.py:listen()
  → services/streak_service.record_listening_event()
  → create ListeningEvent
  → update_listening_streak():
    - Compare last_listened_at.date() to today
    - If yesterday: increment streak (+1) ✗ BUG #1: condition on weekday
    - If today or skip day: reset/no-op
  → ✗ BUG #1: Streak resets on Sundays incorrectly
```

### Search Songs
```
User searches for a song
  → GET /songs/search?q=night
  → routes/songs.py:search()
  → services/search_service.search_songs(query)
  → SQL OUTER JOIN Song + song_tags
  → to_dict() on each song
  → ✗ BUG #3: Duplicate results when song has multiple tags
```

### Friends Listening Activity
```
User views "listening now"
  → GET /feed/<user_id>/listening-now
  → routes/feed.py:listening_now()
  → services/feed_service.get_friends_listening_now()
  → Query ListeningEvent where:
    - user_id in friends
    - listened_at >= now - 24 hours
  → Deduplicate by friend (show most recent per friend)
  → ✗ BUG #2: RECENT_THRESHOLD uses 24 hours, should be 30 minutes
```

### Playlist Song Ordering
```
User views playlist songs
  → GET /playlists/<playlist_id>/songs
  → routes/playlists.py:get_songs()
  → services/playlist_service.get_playlist_songs()
  → Query songs ORDERED BY position ASC
  → Return songs[:-1]  ✗ BUG #5: Slicing removes last song!
```

### Adding Song to Playlist
```
User adds a song to playlist
  → POST /playlists/<playlist_id>/songs {song_id, added_by}
  → routes/playlists.py:add_song()
  → services/notification_service.add_to_playlist()
  → Append song to playlist.songs
  → Create notification for song.shared_by (if different from adder)
  → ✓ Working correctly
```

---

## File Structure

```
ai201-project5-mixtape-starter/
├── app.py                          Flask app factory, DB initialization
├── models.py                       SQLAlchemy models (7 tables, 3 M2M tables)
├── seed_data.py                    Populate DB with test data (5 users, 13 songs, 3 playlists)
├── debug_users.py                  Debug script to print all users
│
├── routes/
│   ├── __init__.py                 (empty)
│   ├── songs.py                    Song endpoints (search, detail, rate, listen)
│   ├── playlists.py                Playlist endpoints (create, detail, songs, add_song)
│   ├── users.py                    User endpoints (profile, streak, notifications)
│   └── feed.py                     Feed endpoints (listening-now, activity)
│
├── services/
│   ├── __init__.py                 (empty)
│   ├── search_service.py           Song search logic
│   ├── playlist_service.py         Playlist retrieval & creation
│   ├── feed_service.py             Friends activity feed logic
│   ├── streak_service.py           Listening streak calculation
│   └── notification_service.py     Notifications & song ratings
│
├── tests/
│   ├── __init__.py                 (empty)
│   ├── test_search.py              Test song search
│   ├── test_streaks.py             Test streak logic
│   └── test_playlists.py           Test playlist operations
│
├── requirements.txt                Python dependencies
├── .gitignore                      Git ignore patterns
└── README.md                       Project overview
```

---

## The Five Known Issues

| # | Issue | Service | Root Cause |
|---|-------|---------|-----------|
| **1** | Listening streak keeps resetting | `streak_service.py:73` | Condition `today.weekday() != 6` prevents streak increment on Sundays |
| **2** | Friends Listening Now shows people from yesterday | `feed_service.py:13` | `RECENT_THRESHOLD = timedelta(hours=24)` should be 30 minutes |
| **3** | Same song appears twice in search results | `search_service.py:27` | OUTER JOIN on song_tags returns duplicate rows per tag; needs DISTINCT |
| **4** | No notification when friend rates your song | `notification_service.py:73-110` | `rate_song()` doesn't call `create_notification()` |
| **5** | Last song in playlist never shows up | `playlist_service.py:66` | `return [song.to_dict() for song in songs[:-1]]` slices off last song |

---

## Key Data Flow Patterns

### Listening Event Recording
```
1. User POSTs to /songs/<song_id>/listen with user_id
2. streak_service.record_listening_event() creates ListeningEvent
3. streak_service.update_listening_streak() checks dates and updates User.listening_streak
4. Database commits both changes
5. ListeningEvent returned to client
```

### Notification Creation
```
1. When song is added to playlist: notification_service.add_to_playlist()
   → Creates notification for song.shared_by (not adder)
2. When song is rated: notification_service.rate_song()
   → ✗ Currently does NOT create notification (BUG #4)
```

### Feed Deduplication
```
1. Query all recent listening events from friends
2. Iterate through results in recency order
3. Track seen_friends set
4. Only include first (most recent) occurrence per friend
5. Result: one entry per friend showing what they're currently listening to
```

---

## Component Explanations

### `app.py` — Flask Application Factory
- Creates and configures the Flask app
- Sets up SQLAlchemy database connection
- Registers all four blueprint routes (songs, playlists, users, feed)
- Initializes database tables on startup

### `models.py` — Data Models
- 7 core entities: User, Song, Tag, Playlist, ListeningEvent, Rating, Notification
- 3 junction tables for relationships: friendships (User-User M2M), song_tags (Song-Tag M2M), playlist_entries (Playlist-Song M2M with ordering)
- Each model has a `to_dict()` method for JSON serialization
- All IDs are UUIDs (36-character strings)

### `routes/` — HTTP Endpoints
- **songs.py**: Search, detail, rate, and listen endpoints
- **playlists.py**: Create, detail, get songs, add songs endpoints
- **users.py**: Profile, streak, notifications endpoints
- **feed.py**: Friends activity feed endpoints
- All routes call corresponding service functions and return JSON

### `services/` — Business Logic
- **search_service.py**: Full-text search on song title/artist (case-insensitive)
- **playlist_service.py**: Playlist CRUD and song retrieval (maintains position order)
- **feed_service.py**: Friends activity and "listening now" feed (with 24-hour recency cutoff)
- **streak_service.py**: Listening streak calculation (increments on consecutive days, resets if day skipped)
- **notification_service.py**: Creates notifications, retrieves them, marks as read

### `seed_data.py` — Test Data Population
- Creates 5 users (nova, darius, simone, kenji, aaliya) with friendships
- Creates 13 songs across multiple genres with tags
- Creates 3 playlists populated with 5-7 songs each
- Creates listening events and streak data for testing
- Drops and recreates entire database each run

---

## How to Trace a Feature

**Example: "A user rates a song"**

1. Client makes `POST /songs/1/rate {"user_id": "abc", "score": 5}`
2. Flask routes to `routes/songs.py:rate()` → extracts user_id and score from JSON
3. Calls `services/notification_service.rate_song(user_id, song_id, score)`
4. Service validates score (1-5), fetches User and Song from database
5. Checks if rating already exists, creates or updates Rating record
6. Commits to database and returns Rating object
7. Route converts to dict and returns HTTP 201 Created response

**BUG #4**: The `rate_song()` function doesn't create a notification, so the song sharer never gets notified that someone rated their song.

---

## Testing the Codebase

To verify the application works and explore the data:

1. **Seed the database**:
   ```bash
   python seed_data.py
   ```

2. **Start the server**:
   ```bash
   FLASK_APP=app:create_app flask run
   ```

3. **Debug users and their UUIDs**:
   ```bash
   python debug_users.py
   ```

4. **Test endpoints** with curl or Postman:
   ```bash
   # Search for songs
   curl "http://localhost:5000/songs/search?q=night"
   
   # Get a user (use UUID from debug_users.py)
   curl "http://localhost:5000/users/<uuid>"
   
   # Get user's streak
   curl "http://localhost:5000/users/<uuid>/streak"
   ```

5. **Run unit tests**:
   ```bash
   pytest tests/
   ```

---

## How to Reproduce Each Bug


### Bug #1: Listening Streak Resets on Sundays
**Location**: `services/streak_service.py:73`


**Root Cause**: Line 73 has `and today.weekday() != 6` which blocks streak increment on Sundays.


**Reproduction Steps**:


1. Find a user UUID:
   ```bash
   python debug_users.py  # Get a user ID, e.g., abc123...
   ```


2. Record a listen on Saturday, then Sunday:
   ```bash
   # Saturday listen
   curl -X POST http://localhost:5000/songs/1/listen \
     -H "Content-Type: application/json" \
     -d '{"user_id": "<user_id>"}'
   
   # Check streak (should be 1)
   curl "http://localhost:5000/users/<user_id>/streak"
   
   # Next day (Sunday) - listen again
   curl -X POST http://localhost:5000/songs/1/listen \
     -H "Content-Type: application/json" \
     -d '{"user_id": "<user_id>"}'
   
   # Check streak (SHOULD be 2, but resets to 1 on Sunday!)
   curl "http://localhost:5000/users/<user_id>/streak"
   ```


**Expected**: Streak increments to 2 on Sunday
**Actual**: Streak resets to 1 on Sunday


---


### Bug #2: Friends Listening Now Shows People from Yesterday
**Location**: `services/feed_service.py:13`


**Root Cause**: `RECENT_THRESHOLD = timedelta(hours=24)` should be `timedelta(minutes=30)`


**Reproduction Steps**:


1. Get two users (must be friends):
   ```bash
   python debug_users.py  # Get user A and user B IDs
   ```


2. User B records a listen 13 hours ago (seed data has this):
   ```bash
   # Already exists in seed data from 13 hours ago
   ```


3. User A checks "listening now":
   ```bash
   curl "http://localhost:5000/feed/<user_a_id>/listening-now"
   ```


**Expected**: Only shows friends who listened in last 30 minutes
**Actual**: Shows friends who listened in last 24 hours (so User B appears even though they listened 13 hours ago)


---


### Bug #3: Same Song Appears Twice in Search Results
**Location**: `services/search_service.py:27` (OUTER JOIN issue)


**Root Cause**: OUTER JOIN on `song_tags` returns duplicate rows for songs with multiple tags. SQL returns one row per tag, not one row per song.


**Reproduction Steps**:


1. Search for a song with multiple tags (from seed data: "Crown Heights Anthem" has 3 tags):
   ```bash
   curl "http://localhost:5000/songs/search?q=Crown"
   ```


2. Or search by tag: "rap", "hip-hop", "boom bap" all tagged with songs:
   ```bash
   curl "http://localhost:5000/songs/search?q=boom"
   ```


3. Check the "count" field and look for duplicates:
   ```json
   {
     "results": [
       {"id": "abc", "title": "Crown Heights Anthem", "tags": ["rap", "hip-hop", "boom bap"]},
       {"id": "abc", "title": "Crown Heights Anthem", "tags": ["rap", "hip-hop", "boom bap"]},  // DUPLICATE!
       {"id": "abc", "title": "Crown Heights Anthem", "tags": ["rap", "hip-hop", "boom bap"]}   // DUPLICATE!
     ],
     "count": 3
   }
   ```


**Expected**: Song appears once
**Actual**: Song appears once per tag it has (3 tags = 3 duplicates)


---


### Bug #4: No Notification When Friend Rates Your Song
**Location**: `services/notification_service.py:73-110`


**Root Cause**: `rate_song()` function doesn't call `create_notification()`. Compare with `add_to_playlist()` which does create notifications.


**Reproduction Steps**:


1. Get the song sharer and rater (from seed data: User nova shared "Midnight Drive", User darius can rate it):
   ```bash
   python debug_users.py  # Get nova_id and darius_id
   ```


2. Darius rates nova's song:
   ```bash
   curl -X POST http://localhost:5000/songs/1/rate \
     -H "Content-Type: application/json" \
     -d '{"user_id": "<darius_id>", "score": 5}'
   ```


3. Check nova's notifications:
   ```bash
   curl "http://localhost:5000/users/<nova_id>/notifications"
   ```


**Expected**: Nova sees a notification "darius rated your song 'Midnight Drive'"
**Actual**: No notification appears


**Comparison**: If darius adds nova's song to a playlist instead:
   ```bash
   curl -X POST http://localhost:5000/playlists/1/songs \
     -H "Content-Type: application/json" \
     -d '{"song_id": "1", "added_by": "<darius_id>"}'
   ```
   Nova DOES get a notification (because `add_to_playlist()` calls `create_notification()`)


---


### Bug #5: Last Song in Playlist Never Shows Up
**Location**: `services/playlist_service.py:66`


**Root Cause**: `return [song.to_dict() for song in songs[:-1]]` uses `[:-1]` slice which removes the last element


**Reproduction Steps**:


1. Get a playlist ID from seed data (or create one):
   ```bash
   # Seed data has 3 playlists with 5-7 songs each
   # Playlist 1 has 7 songs, so should show songs at positions 1-7
   ```


2. Get all songs in the playlist:
   ```bash
   curl "http://localhost:5000/playlists/1/songs"
   ```


3. Check the count:
   ```json
   {
     "songs": [
       {"title": "Midnight Drive"},    // position 1
       {"title": "Still Waters"},      // position 2
       {"title": "First Light"},       // position 3
       {"title": "Block Party"},       // position 4
       {"title": "Late Night Session"},// position 5
       {"title": "Golden Hour"}        // position 6
       // MISSING: position 7 song!
     ],
     "count": 6
   }
   ```


4. Verify by checking the database seed:
   ```bash
   python -c "from app import create_app, db; from models import Playlist; app = create_app(); db.app_context().push(); p = db.session.get(Playlist, '1'); print(f'Playlist has {len(p.songs)} songs')"
   ```


**Expected**: Shows all 7 songs
**Actual**: Shows only 6 songs (missing the last one)


---


## Testing All Bugs Systematically


Create a test script `test_bugs.py`:


```python
from app import create_app, db
from models import User, Song, Playlist


app = create_app()
with app.app_context():
    # Bug #5: Check playlist song count
    p = db.session.query(Playlist).first()
    print(f"BUG #5: Playlist '{p.name}' has {len(p.songs)} songs in DB")
   
    # Call the buggy service
    from services.playlist_service import get_playlist_songs
    songs = get_playlist_songs(p.id)
    print(f"  But get_playlist_songs() returns {len(songs)} songs")
    print(f"  Missing the last song: {p.songs[-1].title if p.songs else 'N/A'}")
   
    # Bug #3: Check search duplicates
    from services.search_service import search_songs
    results = search_songs("Crown")
    print(f"\nBUG #3: Search for 'Crown' returns {len(results)} results (should be 1)")
   
    # Bug #2: Check feed threshold
    from services.feed_service import RECENT_THRESHOLD
    print(f"\nBUG #2: RECENT_THRESHOLD = {RECENT_THRESHOLD} (should be 30 minutes, not 24 hours)")
```


Run it:
```bash
python test_bugs.py
```


