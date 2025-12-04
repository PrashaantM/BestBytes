# BestBytes Frontend

Simple frontend for the BestBytes movie review application.

## Features

-  User authentication (login/register)
-  Browse movies with pagination
-  Search movies by title
-  View movie details and reviews
-  Responsive design
- Movie posters from TMDB

## Quick Start with Docker (Recommended)

### Run the entire application:

```bash
docker-compose up
```

Then open:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

### Stop the application:

```bash
docker-compose down
```

## Alternative: Run Without Docker

### Option 1: Using Python HTTP Server

```bash
cd frontend
python -m http.server 8080
```

Then open http://localhost:8080 in your browser.

**Note:** Make sure the backend is running separately:
```bash
# From project root
python -m uvicorn backend.app:app --reload
```

### Option 2: Using Live Server (VS Code)

1. Install the "Live Server" extension in VS Code
2. Right-click on `index.html`
3. Select "Open with Live Server"

### Option 3: Double-click index.html

Simply open `index.html` in your web browser.

## Default Admin Account

- Username: `admin`
- Password: `Admin123!`

## Usage

1. **Register** a new account or **Login** with existing credentials
2. **Browse** movies on the main page
3. **Search** for specific movies
4. **Click** on a movie card to view details and reviews
5. Use **pagination** to browse more movies

## API Configuration

The frontend connects to `http://localhost:8000` by default. 

To change the API URL, edit `app.js`:

```javascript
const API_URL = 'http://localhost:8000';
```

## Technologies

- HTML5
- CSS3 (with gradients and animations)
- Vanilla JavaScript (no frameworks)
- Fetch API for HTTP requests
