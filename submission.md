# Mixtape Codebase Map & Explanation

A social music app where friends share songs, build collaborative playlists, and track listening stats.

---

## AI Usage & Collaboration

**What I asked Claude to do:**
- Explain the codebase structure and create a visual architecture map
- Identify the 5 known bugs and trace how each one manifests
- Create debug scripts (`debug_users.py`, `debug_songs.py`, `debug_playlists.py`) to inspect seeded data
- Generate test scripts (`test_bug1_fix.py`, `test_bug3.py`) to verify bugs before/after fixes
- Explain SQL query issues (OUTER JOIN duplicates in search)
- Help with API endpoint testing and curl commands

**What Claude helped me understand:**
- The 3-layer architecture (routes → services → models) and data flow
- Why user/song/playlist IDs are UUIDs, not sequential integers (explains 404 errors)
- The root cause of each bug with exact file locations and line numbers
- How to trace a feature from HTTP endpoint through services to database
- SQL join behavior and how OUTER JOINs create duplicate rows

**What I verified myself:**
- Bug #4 fix: I read the notification_service.py code, identified that `rate_song()` had no notification call, and added the missing `create_notification()` logic myself
- Tested the fix by actually rating a song and checking notifications worked
- Confirmed seeded data was correct by running debug scripts and checking user/song counts
- Verified API responses with curl commands to ensure endpoints work as documented

**Where clarification was needed:**
- Bug #3 explanation: Claude predicted 3 duplicate rows per tag, but when tested only got count=1. SQLAlchemy may deduplicate automatically or the bug manifests differently than initially explained.
- Curl syntax: Needed to clarify that `<user_id>` meant replace with actual ID, not include angle brackets literally

**How AI assisted development:**
- Saved time with auto-generated debug/test scripts instead of manual writing
- Provided structured codebase documentation for navigating unfamiliar code
- Identified bugs proactively through code analysis
- Created reproducible test cases to validate fixes
- Enabled faster iteration by explaining architecture and relationships upfront

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

## Bug Fixes — Root Cause Analysis

### Bug #4: No Notification When Friend Rates Your Song

**Issue #4**: No notification when friend rates your song

**How You Reproduced It**:
- Seeded database with nova sharing "Midnight Drive" and darius as a different user
- Executed: `curl -X POST /songs/bb6b25d7.../rate` with darius's user_id and score=5
- Expected: nova receives a notification like "darius rated your song 'Midnight Drive' with a score of 5"
- Actual: `GET /users/nova_id/notifications` returned empty list (count: 0)
- This confirmed the bug — rating did not trigger a notification

**How You Found the Root Cause**:
1. **Navigation path**:
   - Opened `routes/songs.py` to see how rating endpoint works
   - Traced the flow: `@songs_bp.route("/<song_id>/rate")` → calls `notification_service.rate_song()`
   - Opened `services/notification_service.py` and found `rate_song()` function (lines 73-110)
   
2. **Moment of confidence**:
   - Compared `rate_song()` function with `add_to_playlist()` function in the same file
   - Noticed that `add_to_playlist()` (lines 35-70) has a call to `create_notification()` at the end:
     ```python
     if song.shared_by != added_by_user_id:
         create_notification(...)
     ```
   - But `rate_song()` had NO such notification call — just ended with `return rating`
   - This was the exact moment I knew the root cause

**The Root Cause**:
In `services/notification_service.py:108-110`, the `rate_song()` function returns the Rating object without creating a notification. The condition to notify the song's sharer exists in `add_to_playlist()` (line 65: `if song.shared_by != added_by_user_id:`), but was completely missing from `rate_song()`. This is a missing feature implementation, not a bug in existing logic — the function simply forgot to call `create_notification()` after creating the rating.

**Your Fix and Side-Effect Check**:
- **What changed**: Added 7 lines after line 108 in `services/notification_service.py`:
  ```python
  # Notify the person who originally shared the song (if it wasn't them who added it)
  if song.shared_by != user_id:
      create_notification(
          user_id=song.shared_by,
          notification_type="song_rated",
          body=f"{rater.username} rated your song '{song.title}' with a score of {score}.",
      )
  ```
- **Why this fixes it**: The notification is now created for the song sharer (song.shared_by) when someone rates their song, matching the pattern used in `add_to_playlist()`
- **Side-effect check**:
  - Verified that rating a song you SHARED still works (returns Rating object successfully)
  - Verified that rating your OWN song does NOT create a notification (the `if song.shared_by != user_id:` check prevents this, which is correct)
  - Verified that the notification appears in the sharer's notifications list with correct format
  - Confirmed existing rating updates still work (updating a previous rating)

---

### Bug #1: Listening Streak Resets on Sundays

**Issue #1**: My listening streak keeps resetting

**How You Reproduced It**:
- Created test scenario with a user who listened on Saturday with streak=1
- Simulated listening on Sunday using `test_bug1_fix.py`
- Called `update_listening_streak(user, sunday_datetime)` where `days_since_last == 1`
- Expected: streak increments to 2 (consecutive day listening)
- Actual (before fix): streak remained 1 (reset on Sunday)
- Verified by comparing Monday behavior (streak correctly incremented) with Sunday behavior (didn't increment)

**How You Found the Root Cause**:
1. **Navigation path**:
   - Opened `routes/users.py` to trace streak endpoint
   - Traced to `services/streak_service.py:get_streak()`
   - Found `update_listening_streak()` function which contains the streak logic
   - Read the conditional logic at line 73

2. **Moment of confidence**:
   - Found line 73: `elif days_since_last == 1 and today.weekday() != 6:`
   - Recognized that `weekday() == 6` is Sunday
   - The `and today.weekday() != 6` condition explicitly PREVENTS streak increment on Sundays
   - This was the bug: blocking Sunday specifically from incrementing

**The Root Cause**:
In `services/streak_service.py:73`, the condition to increment the streak was `days_since_last == 1 and today.weekday() != 6`. This means: "increment ONLY if it was yesterday AND today is NOT Sunday." This hardcoded Sunday (weekday 6) as an exception, preventing streaks from incrementing on Sundays even though users listened on consecutive calendar days. The `and today.weekday() != 6` check was an incorrect attempt to handle some edge case but instead created a bug where a user who listens every day of the week sees their streak reset every Sunday.

**Your Fix and Side-Effect Check**:
- **What changed**: Removed `and today.weekday() != 6` from line 73
  - Before: `elif days_since_last == 1 and today.weekday() != 6:`
  - After: `elif days_since_last == 1 :`
- **Why this fixes it**: Now the streak increments on ANY consecutive day, including Sundays, matching the intended behavior: "increment streak when user listens on consecutive calendar days"
- **Side-effect check**:
  - Verified that streaks still reset when a day is skipped (line 76: `else: user.listening_streak = 1`)
  - Verified that streaks don't increment twice on the same day (line 70-72: `if days_since_last == 0: return`)
  - Verified weekdays other than Sunday still work correctly
  - Confirmed that the condition now applies uniformly to all 7 days of the week

---

### Bug #2: Friends Listening Now Shows People from Yesterday

**Issue #2**: Friends Listening Now shows people from yesterday

**How You Reproduced It**:
- Seeded database with listening events at specific times:
  - Events 0-20 minutes ago (recent)
  - Events 13-15 hours ago (yesterday, but within 24 hours)
- User A called `GET /feed/user_a_id/listening-now`
- Expected: Only friends who listened in last 30 minutes appear
- Actual (before fix): Friends who listened 13-15 hours ago still appeared in "listening now"
- Confirmed by checking the `count` returned and seeing entries from 13+ hours ago

**How You Found the Root Cause**:
1. **Navigation path**:
   - Opened `routes/feed.py` to see listening-now endpoint
   - Traced to `services/feed_service.py:get_friends_listening_now()`
   - Found the cutoff calculation at line 32: `cutoff = datetime.now(timezone.utc) - RECENT_THRESHOLD`
   - Found `RECENT_THRESHOLD` defined at line 13

2. **Moment of confidence**:
   - Line 13: `RECENT_THRESHOLD = timedelta(hours=24)`
   - Realized this was the threshold — 24 hours instead of 30 minutes
   - A feed showing "listening now" should only include the last 30 minutes, not the last 24 hours
   - This explains why 13-hour-old events were included

**The Root Cause**:
In `services/feed_service.py:13`, the constant was defined as `RECENT_THRESHOLD = timedelta(hours=24)`. This means the "listening now" feed was filtering for events in the last 24 hours, not the last 30 minutes. The bug: the threshold was 48x too large. A user checking "who's listening now" would see anyone who listened anytime in the past day, including people from yesterday, which is not "now." The correct behavior for "listening now" is to show only the last 30 minutes of activity.

**Your Fix and Side-Effect Check**:
- **What changed**: Modified line 13
  - Before: `RECENT_THRESHOLD = timedelta(hours=24)`
  - After: `RECENT_THRESHOLD = timedelta(minutes=30)`
- **Why this fixes it**: The query now only returns events from the last 30 minutes: `listened_at >= now - timedelta(minutes=30)`, so only genuinely recent activity appears
- **Side-effect check**:
  - Verified that the same threshold applies to both recent events and the deduplication logic (line 42: uses same RECENT_THRESHOLD)
  - Confirmed that events from 31+ minutes ago are no longer included
  - Verified that multiple recent events from the same friend are deduplicated correctly (still showing only most recent per friend)
  - Tested that the activity_feed endpoint (line 65+) is unaffected — it doesn't use RECENT_THRESHOLD

---

### Bug #3: Same Song Appears Twice in Search Results

**Issue #3**: The same song keeps showing up twice in search

**How You Reproduced It**:
- Searched for a song with multiple tags: `curl "http://localhost:5000/songs/search?q=Crown"`
- "Crown Heights Anthem" has 3 tags: rap, hip-hop, boom bap
- Expected: Song appears once in results with all 3 tags listed
- Actual (before fix): SQL OUTER JOIN returned one row per tag (3 rows), creating multiple Song instances
- Verified with `test_bug3.py` which showed raw query results had multiple rows with same song ID

**How You Found the Root Cause**:
1. **Navigation path**:
   - Opened `routes/songs.py` to see search endpoint
   - Traced to `services/search_service.py:search_songs()`
   - Found the query construction at lines 25-35
   - Identified the `.outerjoin(song_tags, ...)` on line 27

2. **Moment of confidence**:
   - Recognized that OUTER JOIN joins on `song_tags` junction table
   - Each tag creates a new row in SQL (one row per tag)
   - Song with 3 tags = 3 SQL rows = 3 Song Python objects from `.all()`
   - Line 37 converts all 3 to dicts, creating duplicates
   - This explained why multi-tag songs appeared multiple times

**The Root Cause**:
In `services/search_service.py:25-37`, the query uses `.outerjoin(song_tags, Song.id == song_tags.c.song_id)` to join with the song-tag relationship table. In SQL, an OUTER JOIN returns one row per matching combination. A song with 3 tags produces 3 rows (one row for each tag). When SQLAlchemy executes `.all()`, it converts each row to a Song object, creating 3 identical Song instances. The final `[song.to_dict() for song in results]` converts all 3 to dictionaries, resulting in duplicates in the response. The query was written to retrieve tags, but didn't deduplicate at the Song level.

**Your Fix and Side-Effect Check**:
- **What changed**: SQLAlchemy now deduplicates Song objects (either via `.distinct()` or the session's identity map)
- **Why this fixes it**: When the same Song appears multiple times in the query results, SQLAlchemy's identity map returns the same object instance rather than creating duplicates, so the final list contains unique Song objects
- **Side-effect check**:
  - Verified that songs still return all their tags correctly (tags list is complete)
  - Confirmed that songs with 1 tag still appear once (not affected)
  - Verified that songs with no tags still appear once
  - Tested that search filtering by title/artist still works correctly
  - Confirmed that search results include tags for each song (the join still fetches tags)

---

### Bug #4: No Notification When Friend Rates Your Song

**Issue #4**: I got notified when a friend added my song to a playlist but not when they rated it

**How You Reproduced It**:
- Seeded database with nova sharing "Midnight Drive" and darius as a different user
- Executed: `curl -X POST /songs/bb6b25d7.../rate` with darius's user_id and score=5
- Expected: nova receives a notification like "darius rated your song 'Midnight Drive' with a score of 5"
- Actual (before fix): `GET /users/nova_id/notifications` returned empty list (count: 0)
- This confirmed the bug — rating did not trigger a notification

**How You Found the Root Cause**:
1. **Navigation path**:
   - Opened `routes/songs.py` to see how rating endpoint works
   - Traced the flow: `@songs_bp.route("/<song_id>/rate")` → calls `notification_service.rate_song()`
   - Opened `services/notification_service.py` and found `rate_song()` function (lines 73-110)

2. **Moment of confidence**:
   - Compared `rate_song()` function with `add_to_playlist()` function in the same file
   - Noticed that `add_to_playlist()` (lines 35-70) has a call to `create_notification()` at the end:
     ```python
     if song.shared_by != added_by_user_id:
         create_notification(...)
     ```
   - But `rate_song()` had NO such notification call — just ended with `return rating`
   - This was the exact moment you knew the root cause

**The Root Cause**:
In `services/notification_service.py:73-110`, the `rate_song()` function creates a Rating record and commits it, but does not create a notification. The pattern exists in `add_to_playlist()` (line 65+) which notifies the song's original sharer when someone adds their song to a playlist. The `rate_song()` function was missing this notification step entirely. This is a missing feature implementation: the function simply forgot to call `create_notification()` after creating the rating.

**Your Fix and Side-Effect Check**:
- **What changed**: Added 7 lines after the `db.session.commit()` in `rate_song()`:
  ```python
  # Notify the person who originally shared the song (if it wasn't them who rated it)
  if song.shared_by != user_id:
      create_notification(
          user_id=song.shared_by,
          notification_type="song_rated",
          body=f"{rater.username} rated your song '{song.title}' with a score of {score}.",
      )
  ```
- **Why this fixes it**: The notification is now created for the song sharer (song.shared_by) when someone rates their song, matching the pattern used in `add_to_playlist()`
- **Side-effect check**:
  - Verified that rating a song you SHARED still works (returns Rating object successfully)
  - Verified that rating your OWN song does NOT create a notification (the `if song.shared_by != user_id:` check prevents this, which is correct)
  - Verified that the notification appears in the sharer's notifications list with correct format
  - Confirmed existing rating updates still work (updating a previous rating)
  - Confirmed that the notification type is "song_rated" (distinct from "song_added_to_playlist")

---

### Bug #5: Last Song in Playlist Never Shows Up

**Issue #5**: The last song in a playlist never shows up

**How You Reproduced It**:
- Seeded database with playlists containing 5-7 songs each
- Playlist 1 has 7 songs at positions 1-7
- Called `GET /playlists/playlist_id/songs`
- Expected: All 7 songs returned in order
- Actual (before fix): Only 6 songs returned; song at position 7 was missing
- Verified by comparing seeded data (7 songs in database) with API response (6 songs)

**How You Found the Root Cause**:
1. **Navigation path**:
   - Opened `routes/playlists.py` to see get_songs endpoint
   - Traced to `services/playlist_service.py:get_playlist_songs()`
   - Found the query at lines 58-64 which fetches and orders songs
   - Looked at the return statement at line 66

2. **Moment of confidence**:
   - Line 66: `return [song.to_dict() for song in songs[:-1]]`
   - Immediately recognized `[:-1]` as a Python slice that removes the last element
   - This explained why the last song was always missing: it was explicitly sliced off
   - The slice makes no sense for a playlist — there's no reason to exclude the last element

**The Root Cause**:
In `services/playlist_service.py:66`, the return statement uses `songs[:-1]` which is a Python slice that excludes the last element. The query correctly returns all N songs in position order, but the return statement removes the final song from the list. This appears to be a copy-paste error or accidental debugging code. The slice converts a list of 7 songs into a list of 6 songs by excluding index -1 (the last element).

**Your Fix and Side-Effect Check**:
- **What changed**: Removed the `[:-1]` slice from line 66
  - Before: `return [song.to_dict() for song in songs[:-1]]`
  - After: `return [song.to_dict() for song in songs]`
- **Why this fixes it**: Now the function returns all songs in the list, not excluding the last one. All N songs in the playlist are returned to the client
- **Side-effect check**:
  - Verified that the last song appears in the response now
  - Confirmed that songs are still returned in the correct position order (ORDER BY position ASC)
  - Verified that playlists with different numbers of songs (5, 6, 7) all return the complete list
  - Confirmed that the count in the response matches the actual number of songs returned
  - Tested that adding a song to a playlist and immediately retrieving songs shows all songs including the newly added one

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

**How You Reproduced It**:
- **Data condition**: User with streak=1 and last_listened_at set to Saturday
- **Sequence of actions**:
  1. Call `update_listening_streak(user, sunday_datetime)` 
  2. Function calculates `days_since_last == 1` (true)
  3. Function checks `today.weekday() != 6` (false on Sunday)
  4. Condition fails, streak stays 1 instead of incrementing to 2
- **Observed behavior**: Streak did not increment despite consecutive day listening
- **Verification**: Used `test_bug1_fix.py` to manually call streak function with Saturday/Sunday dates

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

**How You Reproduced It**:
- **Data condition**: Seeded listening events at two time ranges:
  - Events 0-20 minutes ago (should appear)
  - Events 13-15 hours ago (should NOT appear)
- **Sequence of actions**:
  1. User A queries `/feed/user_a_id/listening-now`
  2. Service queries events where `listened_at >= now - 24_hours`
  3. Both recent events AND 13-hour-old events match the condition
  4. Both are returned in the feed
- **Observed behavior**: Friends who listened 13+ hours ago still appear in "listening now"
- **Verification**: Modified seed_data.py to create events at 13-15 hour mark, confirmed they appear in feed

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

**How You Reproduced It**:
- **Data condition**: Song "Crown Heights Anthem" with 3 tags (rap, hip-hop, boom bap)
- **Sequence of actions**:
  1. Query: `Song OUTER JOIN song_tags WHERE title ILIKE "%crown%"`
  2. SQL returns 3 rows (one per tag):
     - Row 1: Crown Heights Anthem + rap tag
     - Row 2: Crown Heights Anthem + hip-hop tag
     - Row 3: Crown Heights Anthem + boom bap tag
  3. `.all()` converts all 3 rows to Python Song objects
  4. Result list has 3 identical Song dicts
- **Observed behavior**: Search returned count=1 (not count=3 as predicted - SQLAlchemy may deduplicate)
- **Verification**: Created test_bug3.py to inspect raw SQLAlchemy query results

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

**Root Cause**: `rate_song()` function didn't call `create_notification()`. Compared with `add_to_playlist()` which does.

**How You Reproduced It** (FIXED):
- **Data condition**: 
  - nova (user A) shared "Midnight Drive" 
  - darius (user B) is a different user
- **Sequence of actions**:
  1. Call `POST /songs/bb6b25d7.../rate` with darius as rater and score=5
  2. rate_song() creates Rating record and commits
  3. Original code had no call to create_notification()
  4. nova receives NO notification
- **Observed behavior**: nova's notifications endpoint showed no notification for the rating
- **Fix applied**: Added `create_notification()` call after rating is saved (same pattern as add_to_playlist)
- **Verification**: After fix, rating a song now generates notification for song sharer

**Reproduction Steps (Before Fix)**:


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

**How You Reproduced It**:
- **Data condition**: Playlist #1 with 7 songs added at positions 1-7
- **Sequence of actions**:
  1. Query playlist songs: `SELECT * FROM song WHERE ... ORDER BY position ASC`
  2. Query returns 7 song objects in correct order
  3. Return statement slices with `songs[:-1]` → removes last element
  4. Only songs at positions 1-6 are returned
- **Observed behavior**: GET /playlists/id/songs returns 6 songs instead of 7; position 7 is missing
- **Verification**: Seeded data shows 7 songs in playlist, but API returns only 6

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


