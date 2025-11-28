
# BestBytes

This is the repo for the 310 project

this is my modification 

Khushi's edit

Prashaant's edit


docker build -t bestbytes-backend .


uvicorn backend.app:app --reload

## Admin Account

The repository includes a persistent admin account committed to `backend/data/Users/userList.json`:

- **Username**: `admin`
- **Password**: `Admin123!`
- **Email**: `admin@bestbytes.com`
- **Status**: Verified and ready to use

This account persists across container restarts and can be used immediately after deployment.

### Admin-only Endpoints

- `POST /admin/promote` — Promote a user to admin
  - Header: `session-token` (must belong to an admin session)
  - Query param: `username`
- `POST /admin/demote` — Demote an admin to a regular user
  - Header: `session-token` (must belong to an admin session)
  - Query param: `username`
  - Note: Admins cannot demote themselves