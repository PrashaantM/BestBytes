Admin Endpoints Summary

=== USER MANAGEMENT ===

GET    /admin/users                    - Get all users with details
GET    /admin/users/{username}         - Get detailed user info
DELETE /admin/users/{username}         - Delete user account
POST   /admin/promote                  - Promote user to admin
POST   /admin/demote                   - Demote admin to user

=== PENALTY MANAGEMENT ===

GET    /admin/users/{username}/penalties - Get all penalties for user
POST   /admin/penalty                     - Assign penalty to user
DELETE /admin/users/{username}/penalties/{index} - Remove specific penalty

=== MOVIE MANAGEMENT ===

GET    /admin/movies          - Get all movies with details
POST   /admin/add-movie       - Add new movie
PUT    /admin/movies/{title}  - Update movie metadata
DELETE /admin/delete-movie/{title} - Delete movie

=== STATISTICS ===

GET    /admin/stats           - Get system statistics

All endpoints require admin authentication via session-token header.
