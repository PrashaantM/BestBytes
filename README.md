
# BestBytes

This is the repo for the 310 project

this is my modification 

Khushi's edit

Prashaant's edit


docker build -t bestbytes-backend .


uvicorn backend.app:app --reload

## Admin Login

- Username: `admin`
- Password: `Admin123!`

Login endpoint:

```
POST /users/login?username=admin&password=Admin123!
```

The response includes `sessionToken`, which you use for authenticated requests.