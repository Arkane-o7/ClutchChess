# Profile Pictures: Upload, Display, and PlayerBadge Component

## Summary

Add profile picture upload to the profile page, display pictures on profiles, and create a reusable `PlayerBadge` component (avatar + username + link) used everywhere usernames appear.

## Legacy Compatibility

- S3 bucket: `com-kfchess-public`, key format: `profile-pics/{uuid}`
- URL format: `https://s3-{region}.amazonaws.com/com-kfchess-public/profile-pics/{uuid}`
- Old picture URLs already stored in `users.picture_url` column — continue working as-is
- Size limit: 64 KB, ACL: `public-read`, no image processing

## Implementation

### Phase 1: Backend — S3 Upload Service & Endpoint

**1a. S3 service** — New file: `server/src/clutchchess/services/s3.py`
- `upload_profile_picture(file_bytes: bytes, content_type: str) -> str`
- Generates UUID key, uploads to `com-kfchess-public` with `public-read` ACL
- Returns full S3 URL
- Validates size ≤ 64KB, content_type in `{image/jpeg, image/png, image/gif, image/webp}`
- Uses `boto3` (already a dependency in pyproject.toml)
- Settings from `get_settings()` (aws_access_key_id, aws_secret_access_key, aws_bucket, aws_region)

**1b. Upload endpoint** — Modify: `server/src/clutchchess/api/users.py`
```python
@router.post("/me/picture", response_model=UserRead)
async def upload_profile_picture(
    file: UploadFile,
    user: User = Depends(get_required_user_with_dev_bypass),
    user_manager: UserManager = Depends(get_user_manager_dep),
) -> User:
```
- Read file bytes, validate size and content type
- Call S3 service, get URL
- Update `user.picture_url` via user_manager
- Return updated user

### Phase 2: Backend — Extend Player Info Resolution ✅

**2a. Extend display_name.py** — `server/src/clutchchess/utils/display_name.py`
- `PlayerDisplay` is a Pydantic `BaseModel` (serves both internal use and API serialization)
- `resolve_player_info(session, players)` — single dict resolution
- `resolve_player_info_batch(session, players_list)` — batch resolution with single DB query (avoids N+1)
- `resolve_player_names()` and `fetch_usernames()` removed (fully replaced)

**2b. Update ReplaySummary** — `server/src/clutchchess/api/replays.py`
- `PlayerDisplay` imported from `display_name.py` (no separate `PlayerDisplayModel`)
- `ReplaySummary.players` changed from `dict[str, str]` to `dict[str, PlayerDisplay]`
- `list_replays` uses `resolve_player_info_batch()` for single DB query

**2c. Update LeaderboardEntry** — `server/src/clutchchess/api/leaderboard.py`
- Added `picture_url: str | None` to `LeaderboardEntry`
- Added `picture_url` to SQL query

**2d. Update LobbyPlayer** — `server/src/clutchchess/lobby/models.py`
- Added `picture_url: str | None = None` to `LobbyPlayer` dataclass
- Added `"pictureUrl": p.picture_url` to `Lobby.to_dict()`

**2e. Update LobbyListItem** — `server/src/clutchchess/api/lobbies.py`
- Added `host_picture_url: str | None` to `LobbyListItem`
- Populated from `host.picture_url`

**2f. Update lobby manager** — `server/src/clutchchess/lobby/manager.py`
- `create_lobby()` and `join_lobby()` accept `picture_url` parameter
- API endpoints pass `user.picture_url` through

**2g. Update replay WebSocket** — `server/src/clutchchess/ws/replay_handler.py`
- Migrated from `resolve_player_names()` to `resolve_player_info()`
- `ReplaySession` serializes `PlayerDisplay` objects via `model_dump()`

### Phase 3: Frontend — PlayerBadge Component

**3a. Create component** — New file: `client/src/components/PlayerBadge.tsx`
```tsx
interface PlayerBadgeProps {
  userId?: number | null;
  username: string;
  pictureUrl?: string | null;
  size?: 'sm' | 'md' | 'lg';  // 24px, 32px, 100px
  linkToProfile?: boolean;
}
```
- Renders circular avatar + username text
- Falls back to `default-profile.jpg` for null pictureUrl
- If `linkToProfile && userId`, wraps in `<Link to={/profile/${userId}}>`
- For AI/Guest (no userId), no link

**3b. CSS** — Add to `client/src/styles/index.css`
- `.player-badge` base styles (inline-flex, align-center, gap)
- `.player-badge-avatar` (circular, border)
- Size variants: `.player-badge-sm` (24px), `.player-badge-md` (32px), `.player-badge-lg` (100px)

### Phase 4: Frontend — Update All Username Displays

**4a. Header** — `client/src/components/layout/Header.tsx`
- Use user's actual `pictureUrl` from auth store instead of `default-profile.jpg`

**4b. Leaderboard** — `client/src/components/Leaderboard.tsx`
- Add `picture_url` to `LeaderboardEntry` interface
- Replace `{entry.username}` with `<PlayerBadge>` in player column

**4c. Lobby Player Slots** — `client/src/pages/Lobby.tsx`
- Add `pictureUrl` to `LobbyPlayer` type
- Replace `formatDisplayName(player)` with `<PlayerBadge>`

**4d. Replays List** — `client/src/pages/Replays.tsx`
- Update `ApiReplaySummary.players` type from `Record<string, string>` to `Record<string, PlayerDisplay>`
- Use `<PlayerBadge>` for each player name

**4e. Watch/Live Games** — `client/src/pages/Watch.tsx`
- Add `hostPictureUrl` to `LobbyListItem` type
- Use `<PlayerBadge>` for host display

**4f. Profile Match History** — `client/src/pages/Profile.tsx`
- Use `<PlayerBadge>` for player names in match history items

**4g. Profile Header** — `client/src/pages/Profile.tsx`
- Show large avatar with upload button (own profile only)
- Click avatar or upload button to open file picker
- Show loading state during upload
- Update auth store with new pictureUrl on success

### Phase 5: Frontend Type Updates

Modify: `client/src/api/types.ts`
- Add `PlayerDisplay` interface: `{name: string, picture_url: string | null, user_id: number | null}`
- Change `ApiReplaySummary.players` from `Record<string, string>` to `Record<string, PlayerDisplay>`
- Add `picture_url: string | null` to `LeaderboardEntry` (if not already a type)
- Add `pictureUrl: string | null` to `LobbyPlayer`
- Add `hostPictureUrl: string | null` to `LobbyListItem`

Add to `client/src/api/client.ts`:
- `uploadProfilePicture(file: File): Promise<ApiUser>` — POSTs multipart form data

## Files to Modify

| File | Changes |
|------|---------|
| `server/src/clutchchess/services/s3.py` | **New** — S3 upload service |
| `server/src/clutchchess/api/users.py` | Add `POST /me/picture` upload endpoint |
| `server/src/clutchchess/utils/display_name.py` | `PlayerDisplay` (Pydantic), `resolve_player_info`, `resolve_player_info_batch` |
| `server/src/clutchchess/api/replays.py` | `ReplaySummary.players` uses `PlayerDisplay`, batch resolution |
| `server/src/clutchchess/ws/replay_handler.py` | Migrated to `resolve_player_info` |
| `server/src/clutchchess/replay/session.py` | Serializes `PlayerDisplay` via `model_dump()` |
| `server/src/clutchchess/api/leaderboard.py` | Add `picture_url` to `LeaderboardEntry` + SQL query |
| `server/src/clutchchess/lobby/models.py` | Add `picture_url` to `LobbyPlayer` + `to_dict()` |
| `server/src/clutchchess/api/lobbies.py` | Add `host_picture_url` to `LobbyListItem` |
| `server/src/clutchchess/lobby/manager.py` | Pass `picture_url` when creating `LobbyPlayer` |
| `client/src/components/PlayerBadge.tsx` | **New** — Reusable avatar + name + link component |
| `client/src/api/types.ts` | Add `PlayerDisplay`, update types with picture_url |
| `client/src/api/client.ts` | Add `uploadProfilePicture()` |
| `client/src/components/layout/Header.tsx` | Use actual pictureUrl |
| `client/src/components/Leaderboard.tsx` | Use `<PlayerBadge>` |
| `client/src/pages/Lobby.tsx` | Use `<PlayerBadge>` |
| `client/src/pages/Replays.tsx` | Use `<PlayerBadge>` |
| `client/src/pages/Watch.tsx` | Use `<PlayerBadge>` |
| `client/src/pages/Profile.tsx` | Upload UI + large avatar + `<PlayerBadge>` in match history |
| `client/src/styles/index.css` | PlayerBadge styles + profile upload styles |

## Verification

1. **Backend tests**: `cd server && uv run pytest tests/ -v`
2. **Frontend**: `cd client && npm run typecheck && npm run lint && npm test`
3. **Manual testing**:
   - Upload a profile picture on `/profile` — appears immediately
   - View public profile `/profile/:id` — shows picture
   - Leaderboard — shows avatar + clickable username
   - Lobby player slots — shows avatar + clickable username
   - Replays list — shows avatars + clickable names
   - Watch page — shows host avatar
   - Match history on profile — shows player avatars
