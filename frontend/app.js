// API Base URL
const API_URL = 'http://localhost:8000';

// State
let currentUser = null;
let sessionToken = null;
let currentPage = 1;
let currentSearchQuery = '';
let isLastPage = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkSession();
});

// Auth Functions
function showLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('verifyForm').style.display = 'none';
    document.querySelectorAll('.tab-btn')[0].classList.add('active');
    document.querySelectorAll('.tab-btn')[1].classList.remove('active');
    document.querySelectorAll('.tab-btn')[2].classList.remove('active');
}

function showRegister() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
    document.getElementById('verifyForm').style.display = 'none';
    document.querySelectorAll('.tab-btn')[0].classList.remove('active');
    document.querySelectorAll('.tab-btn')[1].classList.add('active');
    document.querySelectorAll('.tab-btn')[2].classList.remove('active');
}

function showVerify() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('verifyForm').style.display = 'block';
    document.querySelectorAll('.tab-btn')[0].classList.remove('active');
    document.querySelectorAll('.tab-btn')[1].classList.remove('active');
    document.querySelectorAll('.tab-btn')[2].classList.add('active');
}

async function register() {
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    
    const errorEl = document.getElementById('registerError');
    const successEl = document.getElementById('registerSuccess');
    errorEl.textContent = '';
    successEl.textContent = '';

    try {
        console.log('Registering:', { username, email });
        const response = await fetch(`${API_URL}/users/register?username=${encodeURIComponent(username)}&email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, {
            method: 'POST'
        });

        const data = await response.json();
        console.log('Register response:', data);

        if (response.ok) {
            successEl.innerHTML = `
                <strong>Registration successful!</strong><br>
                <strong>⚠️ IMPORTANT: Save your verification token!</strong><br>
                <div style="background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; font-family: monospace; word-break: break-all;">
                    ${data.verificationToken}
                </div>
                <strong>Instructions:</strong> Copy this token and use the "Verify Account" tab to verify your account before logging in.
            `;
            document.getElementById('registerUsername').value = '';
            document.getElementById('registerEmail').value = '';
            document.getElementById('registerPassword').value = '';
        } else {
            // Handle error - could be a string or object
            if (typeof data.detail === 'string') {
                errorEl.textContent = data.detail;
            } else if (data.detail && data.detail.length) {
                // Pydantic validation errors
                errorEl.textContent = data.detail.map(err => err.msg).join(', ');
            } else if (data.message) {
                errorEl.textContent = data.message;
            } else {
                errorEl.textContent = 'Registration failed: ' + JSON.stringify(data);
            }
        }
    } catch (error) {
        console.error('Registration error:', error);
        errorEl.textContent = 'Error connecting to server: ' + error.message;
    }
}

async function verifyAccount() {
    const username = document.getElementById('verifyUsername').value;
    const token = document.getElementById('verifyToken').value;
    
    const errorEl = document.getElementById('verifyError');
    const successEl = document.getElementById('verifySuccess');
    errorEl.textContent = '';
    successEl.textContent = '';

    try {
        const response = await fetch(`${API_URL}/users/verify?username=${encodeURIComponent(username)}&token=${encodeURIComponent(token)}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            successEl.textContent = 'Account verified successfully! You can now login.';
            document.getElementById('verifyUsername').value = '';
            document.getElementById('verifyToken').value = '';
            // Automatically switch to login tab after 2 seconds
            setTimeout(() => {
                showLogin();
            }, 2000);
        } else {
            errorEl.textContent = data.detail || 'Verification failed';
        }
    } catch (error) {
        console.error('Verify error:', error);
        errorEl.textContent = 'Network error. Please try again.';
    }
}

async function login() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    const errorEl = document.getElementById('loginError');
    errorEl.textContent = '';

    try {
        console.log('Logging in:', { username });
        const response = await fetch(`${API_URL}/users/login?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`, {
            method: 'POST'
        });

        const data = await response.json();
        console.log('Login response:', data);

        if (response.ok) {
            sessionToken = data.sessionToken;
            currentUser = username;
            localStorage.setItem('sessionToken', sessionToken);
            localStorage.setItem('username', username);
            showApp();
        } else {
            // Handle error - could be a string or object
            if (typeof data.detail === 'string') {
                errorEl.textContent = data.detail;
            } else if (data.detail && data.detail.length) {
                // Pydantic validation errors
                errorEl.textContent = data.detail.map(err => err.msg).join(', ');
            } else if (data.message) {
                errorEl.textContent = data.message;
            } else {
                errorEl.textContent = 'Login failed: ' + JSON.stringify(data);
            }
        }
    } catch (error) {
        console.error('Login error:', error);
        errorEl.textContent = 'Error connecting to server: ' + error.message;
    }
}

async function logout() {
    if (sessionToken) {
        try {
            await fetch(`${API_URL}/users/logout?sessionToken=${sessionToken}`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
    }
    
    sessionToken = null;
    currentUser = null;
    localStorage.removeItem('sessionToken');
    localStorage.removeItem('username');
    showAuth();
}

function checkSession() {
    const savedToken = localStorage.getItem('sessionToken');
    const savedUsername = localStorage.getItem('username');
    
    if (savedToken && savedUsername) {
        sessionToken = savedToken;
        currentUser = savedUsername;
        showApp();
    }
}

function showAuth() {
    document.getElementById('authSection').style.display = 'block';
    document.getElementById('appSection').style.display = 'none';
}

function showApp() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('appSection').style.display = 'block';
    document.getElementById('welcomeMessage').textContent = `Welcome, ${currentUser}!`;
    
    // Check if user is admin
    checkAdminStatus();
    
    loadMovies();
    loadLeaderboard('homeLeaderboard'); // Load leaderboard on home page
}

async function checkAdminStatus() {
    try {
        const response = await fetch(`${API_URL}/users/me?sessionToken=${sessionToken}`);
        if (response.ok) {
            const userData = await response.json();
            console.log('User data:', userData); // Debug log
            // Show admin tab if user is admin
            if (userData.isAdmin) {
                console.log('User is admin, showing admin elements'); // Debug log
                document.querySelectorAll('.admin-only').forEach(el => {
                    el.style.display = 'block';
                });
            }
        }
    } catch (error) {
        console.error('Error checking admin status:', error);
    }
}

// Movie Functions
async function loadMovies(page = 1) {
    try {
        const response = await fetch(`${API_URL}/movies/?page=${page}&limit=12&include_tmdb=true`);
        
        // Check for HTTP error status (like 404 for out of range)
        if (!response.ok) {
            console.error('Error loading movies - page out of range');
            // Mark that we've reached the last page
            isLastPage = true;
            document.getElementById('nextPage').disabled = true;
            return;
        }
        
        const movies = await response.json();
        
        // Check if response is an error object (shouldn't happen if response.ok works)
        if (movies.detail) {
            console.error('API Error:', movies.detail);
            isLastPage = true;
            document.getElementById('nextPage').disabled = true;
            return;
        }
        
        displayMovies(movies);
        currentPage = page;
        // Reset last page flag on successful load
        isLastPage = false;
        updatePagination(movies.length);
    } catch (error) {
        console.error('Error loading movies:', error);
        isLastPage = true;
        document.getElementById('nextPage').disabled = true;
    }
}

async function searchMovies() {
    const query = document.getElementById('searchInput').value.trim();
    const searchField = document.getElementById('searchField').value;
    currentSearchQuery = query;
    
    if (!query) {
        loadMovies();
        return;
    }

    try {
        const searchBody = { 
            title: query,
            searchField: searchField
        };
        
        const response = await fetch(`${API_URL}/movies/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(searchBody)
        });
        const movies = await response.json();
        displayMovies(movies);
        document.getElementById('prevPage').disabled = true;
        document.getElementById('nextPage').disabled = true;
    } catch (error) {
        console.error('Error searching movies:', error);
        alert('Error searching movies. Please try again.');
    }
}

function displayMovies(movies) {
    const grid = document.getElementById('moviesGrid');
    grid.innerHTML = '';

    if (movies.length === 0) {
        grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #666;">No movies found</p>';
        return;
    }

    movies.forEach(movie => {
        const card = document.createElement('div');
        card.className = 'movie-card';
        // Pass the full movie object instead of just the title
        card.onclick = () => showMovieDetails(movie);

        const posterUrl = movie.posterUrl || 'https://via.placeholder.com/250x350?text=No+Poster';
        
        card.innerHTML = `
            <img src="${posterUrl}" alt="${movie.title}" class="movie-poster" onerror="this.src='https://via.placeholder.com/250x350?text=No+Poster'">
            <div class="movie-info">
                <div class="movie-title">${movie.title}</div>
                <div class="movie-rating">⭐ ${movie.movieIMDbRating || 'N/A'}/10</div>
                <div class="movie-year">${movie.datePublished || 'Unknown'}</div>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

async function showMovieDetails(movie) {
    try {
        // Movie object is already passed, just fetch reviews
        const reviewsResponse = await fetch(`${API_URL}/reviews/${encodeURIComponent(movie.title)}/reviews`);
        let reviews = [];
        
        // Reviews might not exist for TMDB movies, so handle 404
        if (reviewsResponse.ok) {
            reviews = await reviewsResponse.json();
        } else {
            console.log('No reviews found for this movie');
        }
        
        displayMovieModal(movie, reviews);
    } catch (error) {
        console.error('Error loading movie details:', error);
        // Still display the modal even if reviews fail
        displayMovieModal(movie, []);
    }
}

function displayMovieModal(movie, reviews) {
    const modal = document.getElementById('movieModal');
    const detailsDiv = document.getElementById('movieDetails');
    
    // Store movie globally for review modal
    currentMovieForReview = movie;
    
    const posterUrl = movie.posterUrl || 'https://via.placeholder.com/300x450?text=No+Poster';
    const genres = Array.isArray(movie.movieGenres) ? movie.movieGenres.join(', ') : movie.movieGenres || 'N/A';
    const directors = Array.isArray(movie.directors) ? movie.directors.join(', ') : movie.directors || 'N/A';
    const stars = Array.isArray(movie.mainStars) ? movie.mainStars.join(', ') : movie.mainStars || 'N/A';
    
    let reviewsHtml = '';
    if (reviews && reviews.length > 0) {
        reviewsHtml = reviews.map(review => `
            <div class="review-card">
                <div class="review-header">
                    <span class="review-user">${review.user}</span>
                    <span class="review-rating">⭐ ${review.userRatingOutOf10}/10</span>
                </div>
                <div><strong>${review.reviewTitle}</strong></div>
                <div class="review-text">${review.review}</div>
                <div style="margin-top: 10px; font-size: 0.9rem; color: #888;">
                    ${review.dateOfReview} • 👍 ${review.usefulnessVote}/${review.totalVotes}
                </div>
            </div>
        `).join('');
    } else {
        reviewsHtml = '<p style="color: #666;">No reviews yet. Be the first to review!</p>';
    }
    
    detailsDiv.innerHTML = `
        <button onclick='openReviewModalForCurrentMovie()'  
                class="btn-primary" style="float: right;">✍️ Write Review</button>
        <div class="movie-detail-header">
            <img src="${posterUrl}" alt="${movie.title}" class="movie-detail-poster" onerror="this.src='https://via.placeholder.com/300x450?text=No+Poster'">
            <div class="movie-detail-info">
                <h1>${movie.title}</h1>
                <p><strong>Rating:</strong> ⭐ ${movie.movieIMDbRating || 'N/A'}/10 (${movie.totalRatingCount || 0} ratings)</p>
                <p><strong>Year:</strong> ${movie.datePublished || 'Unknown'}</p>
                <p><strong>Runtime:</strong> ${movie.movieRuntime || 'N/A'}</p>
                <p><strong>Genres:</strong> ${genres}</p>
                <p><strong>Directors:</strong> ${directors}</p>
                <p><strong>Stars:</strong> ${stars}</p>
                <p><strong>Metascore:</strong> ${movie.metaScore || 'N/A'}</p>
                ${movie.trailerUrl ? `<p><a href="${movie.trailerUrl}" target="_blank" style="color: #667eea;">Watch Trailer 🎬</a></p>` : ''}
            </div>
        </div>
        <p><strong>Description:</strong></p>
        <p>${movie.description || 'No description available'}</p>
        
        ${sessionToken ? `<button onclick="showAddToListModal('${movie.title.replace(/'/g, "\\'")}')">📋 Add to List</button>` : ''}
        
        <div class="reviews-section">
            <h3>Reviews (${reviews ? reviews.length : 0})</h3>
            ${reviewsHtml}
        </div>
    `;
    
    modal.style.display = 'block';
}

function closeModal() {
    document.getElementById('movieModal').style.display = 'none';
}

function updatePagination(moviesCount = 12) {
    document.getElementById('pageInfo').textContent = `Page ${currentPage}`;
    document.getElementById('prevPage').disabled = currentPage === 1;
    
    // Disable next button if:
    // 1. We've already tried and hit the last page, OR
    // 2. We got fewer than 12 movies (definitely last page)
    document.getElementById('nextPage').disabled = isLastPage || moviesCount < 12;
}

function previousPage() {
    if (currentPage > 1) {
        loadMovies(currentPage - 1);
    }
}

function nextPage() {
    loadMovies(currentPage + 1);
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('movieModal');
    if (event.target === modal) {
        closeModal();
    }
}
// Extended features for BestBytes

// Global state for current movie being reviewed
let currentMovieForReview = null;

// Tab Navigation
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });
    
    // Remove active class from all nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab and activate button
    document.getElementById(`${tabName}Tab`).style.display = 'block';
    event.target.classList.add('active');
    
    // Load data for specific tabs
    if (tabName === 'mylists') {
        loadUserLists();
    } else if (tabName === 'roulette') {
        loadGenres();
    } else if (tabName === 'profile') {
        loadProfile();
        loadLeaderboard();
    } else if (tabName === 'series') {
        loadSeries();
    } else if (tabName === 'recommendations') {
        // Don't auto-load, let user click button
    } else if (tabName === 'admin') {
        // Auto-load admin stats when admin tab opens
        loadAdminStats();
    }
}

// ==================== REVIEW FEATURES ====================

function openReviewModalForCurrentMovie() {
    if (!currentMovieForReview) {
        alert('No movie selected');
        return;
    }
    document.getElementById('reviewModal').style.display = 'block';
    document.getElementById('reviewTitle').value = '';
    document.getElementById('reviewRating').value = '';
    document.getElementById('reviewText').value = '';
}

function openReviewModal(movie) {
    currentMovieForReview = movie;
    document.getElementById('reviewModal').style.display = 'block';
    document.getElementById('reviewTitle').value = '';
    document.getElementById('reviewRating').value = '';
    document.getElementById('reviewText').value = '';
}

function closeReviewModal() {
    document.getElementById('reviewModal').style.display = 'none';
    currentMovieForReview = null;
}

async function submitReview() {
    if (!currentMovieForReview) return;
    
    const title = document.getElementById('reviewTitle').value.trim();
    const rating = parseFloat(document.getElementById('reviewRating').value);
    const reviewText = document.getElementById('reviewText').value.trim();
    
    if (!title || !rating || !reviewText) {
        alert('Please fill in all fields');
        return;
    }
    
    if (rating < 1 || rating > 10) {
        alert('Rating must be between 1 and 10');
        return;
    }
    
    try {
        const today = new Date();
        const dateOfReview = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
        
        const reviewData = {
            user: currentUser,
            reviewTitle: title,
            userRatingOutOf10: rating,
            review: reviewText,
            dateOfReview: dateOfReview,
            usefulnessVote: 0,
            totalVotes: 0
        };
        
        console.log('Submitting review:', reviewData);
        
        const response = await fetch(
            `${API_URL}/reviews/${encodeURIComponent(currentMovieForReview.title)}?sessionToken=${sessionToken}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reviewData)
            }
        );
        
        if (response.ok) {
            alert('Review submitted successfully!');
            closeReviewModal();
            // Reload movie details to show new review
            showMovieDetails(currentMovieForReview);
        } else {
            const error = await response.json();
            console.error('Review error:', error);
            alert(`Error: ${error.detail || 'Failed to submit review'}`);
        }
    } catch (error) {
        console.error('Error submitting review:', error);
        alert('Failed to submit review');
    }
}

// ==================== MOVIE LISTS FEATURES ====================

async function loadUserLists() {
    try {
        const response = await fetch(`${API_URL}/lists/${currentUser}?sessionToken=${sessionToken}`);
        
        if (!response.ok) {
            document.getElementById('userLists').innerHTML = '<p>No lists yet. Create your first list!</p>';
            return;
        }
        
        const listsObj = await response.json();
        
        const container = document.getElementById('userLists');
        container.innerHTML = '';
        
        const listNames = Object.keys(listsObj);
        
        if (listNames.length > 0) {
            listNames.forEach(listName => {
                const movies = listsObj[listName];
                const listDiv = document.createElement('div');
                listDiv.className = 'list-card';
                listDiv.innerHTML = `
                    <h3>${listName}</h3>
                    <p>${movies.length} movies</p>
                    <div class="list-movies">
                        ${movies.length > 0 
                            ? movies.map(m => `
                                <div class="movie-tag">
                                    <span>${m}</span>
                                    <button class="remove-movie-btn" onclick="removeMovieFromList('${listName.replace(/'/g, "\\'")  }', '${m.replace(/'/g, "\\'")}')" title="Remove">&times;</button>
                                </div>
                            `).join('') 
                            : '<p>No movies in this list yet</p>'}
                    </div>
                    <button onclick="deleteList('${listName.replace(/'/g, "\\'")}')" class="btn-danger">Delete List</button>
                `;
                container.appendChild(listDiv);
            });
        } else {
            container.innerHTML = '<p>No lists yet. Create your first list!</p>';
        }
    } catch (error) {
        console.error('Error loading lists:', error);
        document.getElementById('userLists').innerHTML = '<p>No lists yet. Create your first list!</p>';
    }
}

async function createList() {
    const listName = document.getElementById('newListName').value.trim();
    
    if (!listName) {
        alert('Please enter a list name');
        return;
    }
    
    console.log('Creating list:', { currentUser, sessionToken, listName });
    
    if (!sessionToken || !currentUser) {
        alert('You must be logged in to create lists');
        return;
    }
    
    try {
        const url = `${API_URL}/lists/create?username=${currentUser}&listName=${encodeURIComponent(listName)}&sessionToken=${sessionToken}`;
        console.log('Creating list at:', url);
        
        const response = await fetch(url, { method: 'POST' });
        
        if (response.ok) {
            document.getElementById('newListName').value = '';
            loadUserLists();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to create list'}`);
        }
    } catch (error) {
        console.error('Error creating list:', error);
        alert('Failed to create list');
    }
}

async function removeMovieFromList(listName, movieTitle) {
    if (!confirm(`Remove "${movieTitle}" from "${listName}"?`)) return;
    
    try {
        const response = await fetch(
            `${API_URL}/lists/remove?username=${currentUser}&listName=${encodeURIComponent(listName)}&movieTitle=${encodeURIComponent(movieTitle)}&sessionToken=${sessionToken}`,
            { method: 'DELETE' }
        );
        
        if (response.ok) {
            loadUserLists();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to remove movie'}`);
        }
    } catch (error) {
        console.error('Error removing movie:', error);
        alert('Failed to remove movie from list');
    }
}

async function deleteList(listName) {
    if (!confirm(`Delete list "${listName}"?`)) return;
    
    try {
        const response = await fetch(
            `${API_URL}/lists/delete?username=${currentUser}&listName=${encodeURIComponent(listName)}&sessionToken=${sessionToken}`,
            { method: 'DELETE' }
        );
        
        if (response.ok) {
            loadUserLists();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to delete list'}`);
        }
    } catch (error) {
        console.error('Error deleting list:', error);
        alert('Failed to delete list');
    }
}

let selectedMovieForList = null;

async function showAddToListModal(movieTitle) {
    if (!sessionToken || !currentUser) {
        alert('Please log in to add movies to lists');
        return;
    }
    
    selectedMovieForList = movieTitle;
    
    try {
        // Fetch user's lists
        const response = await fetch(`${API_URL}/lists/${currentUser}?sessionToken=${sessionToken}`);
        
        let listsObj = {};
        if (response.ok) {
            listsObj = await response.json();
        }
        
        const listNames = Object.keys(listsObj);
        
        if (listNames.length === 0) {
            alert('You have no lists yet. Create a list first from the "My Lists" tab.');
            return;
        }
        
        // Populate the dropdown
        const selector = document.getElementById('listSelector');
        selector.innerHTML = '<option value="">Select a list...</option>';
        listNames.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            selector.appendChild(option);
        });
        
        // Show the modal
        document.getElementById('addToListMovieTitle').textContent = `Movie: ${movieTitle}`;
        document.getElementById('addToListModal').style.display = 'block';
        
    } catch (error) {
        console.error('Error showing lists:', error);
        alert('Error loading lists');
    }
}

function closeAddToListModal() {
    document.getElementById('addToListModal').style.display = 'none';
    selectedMovieForList = null;
}

async function confirmAddToList() {
    const listName = document.getElementById('listSelector').value;
    
    if (!listName) {
        alert('Please select a list');
        return;
    }
    
    await addMovieToList(selectedMovieForList, listName);
    closeAddToListModal();
}

async function addMovieToList(movieTitle, listName) {
    try {
        const response = await fetch(
            `${API_URL}/lists/add?username=${currentUser}&listName=${encodeURIComponent(listName)}&movieTitle=${encodeURIComponent(movieTitle)}&sessionToken=${sessionToken}`,
            { method: 'POST' }
        );
        
        if (response.ok) {
            alert(`✓ Added "${movieTitle}" to "${listName}"`);
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to add movie'}`);
        }
    } catch (error) {
        console.error('Error adding to list:', error);
        alert('Failed to add movie to list');
    }
}

// ==================== ROULETTE FEATURES ====================

async function loadGenres() {
    try {
        // Fetch all movies and extract unique genres
        const response = await fetch(`${API_URL}/movies/?page=1&limit=100&include_tmdb=true`);
        const movies = await response.json();
        
        const genresSet = new Set();
        movies.forEach(movie => {
            if (movie.movieGenres && Array.isArray(movie.movieGenres)) {
                movie.movieGenres.forEach(genre => genresSet.add(genre));
            }
        });
        
        const genres = Array.from(genresSet).sort();
        
        const select = document.getElementById('rouletteGenre');
        select.innerHTML = '<option value="">Any Genre</option>';
        
        genres.forEach(genre => {
            const option = document.createElement('option');
            option.value = genre;
            option.textContent = genre;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading genres:', error);
    }
}

async function spinRoulette() {
    const genre = document.getElementById('rouletteGenre').value;
    const resultDiv = document.getElementById('rouletteResult');
    
    resultDiv.innerHTML = '<p>🎲 Spinning...</p>';
    
    try {
        // Fetch all movies and pick random one
        const response = await fetch(`${API_URL}/movies/?page=1&limit=100&include_tmdb=true`);
        const allMovies = await response.json();
        
        // Filter by genre if selected
        let filteredMovies = allMovies;
        if (genre) {
            filteredMovies = allMovies.filter(m => 
                m.movieGenres && m.movieGenres.some(g => g.toLowerCase() === genre.toLowerCase())
            );
        }
        
        if (filteredMovies.length > 0) {
            const randomIndex = Math.floor(Math.random() * filteredMovies.length);
            const movie = filteredMovies[randomIndex];
            const posterUrl = movie.posterUrl || 'https://via.placeholder.com/200x300?text=No+Poster';
            
            resultDiv.innerHTML = `
                <div class="roulette-movie-card">
                    <img src="${posterUrl}" alt="${movie.title}" 
                         onerror="this.src='https://via.placeholder.com/200x300?text=No+Poster'">
                    <div class="roulette-movie-info">
                        <h3>${movie.title}</h3>
                        <p><strong>Rating:</strong> ⭐ ${movie.movieIMDbRating || 'N/A'}/10</p>
                        <p><strong>Genres:</strong> ${Array.isArray(movie.movieGenres) ? movie.movieGenres.join(', ') : 'N/A'}</p>
                        <p>${movie.description || 'No description available'}</p>
                    </div>
                </div>
            `;
        } else {
            resultDiv.innerHTML = '<p>No movies found with that genre!</p>';
        }
    } catch (error) {
        console.error('Error spinning roulette:', error);
        resultDiv.innerHTML = '<p>Error loading movie. Try again!</p>';
    }
}

// ==================== PROFILE & LEADERBOARD ====================

async function loadProfile() {
    try {
        const response = await fetch(`${API_URL}/reviews/stats/${currentUser}`);
        
        if (response.ok) {
            const stats = await response.json();
            const statsDiv = document.getElementById('profileStats');
            
            statsDiv.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>${stats.totalReviews || 0}</h3>
                        <p>Total Reviews</p>
                    </div>
                    <div class="stat-card">
                        <h3>${stats.averageRating ? stats.averageRating.toFixed(1) : 'N/A'}</h3>
                        <p>Average Rating</p>
                    </div>
                    <div class="stat-card">
                        <h3>${stats.totalUsefulnessVotes || 0}</h3>
                        <p>Helpful Votes</p>
                    </div>
                    <div class="stat-card">
                        <h3>${stats.averageUsefulnessRatio ? (stats.averageUsefulnessRatio * 100).toFixed(1) : '0'}%</h3>
                        <p>Usefulness Ratio</p>
                    </div>
                </div>
            `;
        } else {
            document.getElementById('profileStats').innerHTML = '<p>No stats available yet. Start reviewing!</p>';
        }
    } catch (error) {
        console.error('Error loading profile:', error);
        document.getElementById('profileStats').innerHTML = '<p>Error loading stats</p>';
    }
}

async function loadLeaderboard(containerId = 'leaderboard') {
    try {
        const response = await fetch(`${API_URL}/reviews/leaderboard`);
        const leaderboard = await response.json();
        
        const leaderboardDiv = document.getElementById(containerId);
        
        if (leaderboard && leaderboard.length > 0) {
            leaderboardDiv.innerHTML = `
                <table class="leaderboard-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>User</th>
                            <th>Reviews</th>
                            <th>Avg Rating</th>
                            <th>Helpful Votes</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${leaderboard.map((entry) => `
                            <tr ${entry.username === currentUser ? 'class="current-user"' : ''}>
                                <td>${entry.rank}</td>
                                <td>${entry.username}</td>
                                <td>${entry.totalReviews}</td>
                                <td>⭐ ${entry.averageRating.toFixed(1)}</td>
                                <td>👍 ${entry.totalUsefulnessVotes}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } else {
            leaderboardDiv.innerHTML = '<p>No leaderboard data available</p>';
        }
    } catch (error) {
        console.error('Error loading leaderboard:', error);
        leaderboardDiv.innerHTML = '<p>Error loading leaderboard</p>';
    }
}

// Update the displayMovieModal function to add review button
function enhanceMovieModal(movie) {
    const existingModal = document.getElementById('movieDetails');
    const writeReviewBtn = document.createElement('button');
    writeReviewBtn.textContent = '✍️ Write a Review';
    writeReviewBtn.className = 'btn-primary';
    writeReviewBtn.onclick = () => openReviewModal(movie);
    
    // Insert at top of modal content
    if (existingModal && existingModal.firstChild) {
        existingModal.insertBefore(writeReviewBtn, existingModal.firstChild.nextSibling);
    }
}

// ==================== RECOMMENDATIONS ====================

async function loadRecommendations() {
    const container = document.getElementById('recommendationsContainer');
    container.innerHTML = '<p>Loading recommendations...</p>';
    
    try {
        const response = await fetch(`${API_URL}/users/recommendations?sessionToken=${sessionToken}`);
        
        if (response.ok) {
            const recommendations = await response.json();
            
            if (recommendations && recommendations.length > 0) {
                container.innerHTML = '';
                recommendations.forEach(rec => {
                    // Extract movie data from Metadata field
                    const movie = rec.Metadata || rec;
                    const matchScore = rec['Match Score'] ? (rec['Match Score'] * 100).toFixed(0) : null;
                    
                    const card = document.createElement('div');
                    card.className = 'movie-card';
                    card.onclick = () => showMovieDetails(movie);

                    const posterUrl = movie.posterUrl || 'https://via.placeholder.com/250x350?text=No+Poster';
                    
                    card.innerHTML = `
                        <img src="${posterUrl}" alt="${movie.title}" class="movie-poster" 
                             onerror="this.src='https://via.placeholder.com/250x350?text=No+Poster'">
                        <div class="movie-info">
                            <div class="movie-title">${movie.title}</div>
                            <div class="movie-rating">⭐ ${movie.movieIMDbRating || 'N/A'}/10</div>
                            <div class="movie-year">${movie.datePublished || 'Unknown'}</div>
                            ${matchScore ? `<div class="match-score">🎯 ${matchScore}% Match</div>` : ''}
                        </div>
                    `;
                    
                    container.appendChild(card);
                });
            } else {
                container.innerHTML = '<p>No recommendations available yet. Watch and rate more movies!</p>';
            }
        } else {
            container.innerHTML = '<p>Unable to load recommendations</p>';
        }
    } catch (error) {
        console.error('Error loading recommendations:', error);
        container.innerHTML = '<p>Error loading recommendations</p>';
    }
}

// ==================== SERIES ====================

async function loadSeries() {
    const container = document.getElementById('seriesContainer');
    container.innerHTML = '<p>Loading series...</p>';
    
    try {
        const response = await fetch(`${API_URL}/series/`);
        
        if (response.ok) {
            const seriesData = await response.json();
            container.innerHTML = '';
            
            for (const [seriesName, movies] of Object.entries(seriesData)) {
                const seriesDiv = document.createElement('div');
                seriesDiv.className = 'series-card';
                seriesDiv.innerHTML = `
                    <h3>${seriesName}</h3>
                    <div class="series-movies">
                        ${movies.map(m => `<div class="series-movie-item">
                            <span class="series-order">${m.order}</span>
                            <span>${m.title}</span>
                        </div>`).join('')}
                    </div>
                `;
                container.appendChild(seriesDiv);
            }
            
            if (Object.keys(seriesData).length === 0) {
                container.innerHTML = '<p>No series available yet</p>';
            }
        } else {
            container.innerHTML = '<p>No series available</p>';
        }
    } catch (error) {
        console.error('Error loading series:', error);
        container.innerHTML = '<p>Error loading series</p>';
    }
}

// ==================== DOWNLOADS ====================

async function downloadMyReviews(format) {
    try {
        const response = await fetch(`${API_URL}/downloads/my-reviews?sessionToken=${sessionToken}&format=${format}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentUser}_reviews.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Error downloading reviews');
        }
    } catch (error) {
        console.error('Error downloading reviews:', error);
        alert('Error downloading reviews');
    }
}

async function downloadMyLists(format) {
    try {
        const response = await fetch(`${API_URL}/downloads/my-lists?sessionToken=${sessionToken}&format=${format}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentUser}_lists.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Error downloading lists');
        }
    } catch (error) {
        console.error('Error downloading lists:', error);
        alert('Error downloading lists');
    }
}

// ==================== ADMIN FUNCTIONS ====================

async function adminDeleteMovie() {
    const title = document.getElementById('adminDeleteTitle').value.trim();
    if (!title) {
        alert('Please enter a movie title');
        return;
    }
    
    if (!confirm(`Delete "${title}"?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/admin/delete-movie/${encodeURIComponent(title)}`, {
            method: 'DELETE',
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            alert('Movie deleted successfully');
            document.getElementById('adminDeleteTitle').value = '';
            loadAdminMovies(); // Refresh the movie list
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to delete movie'}`);
        }
    } catch (error) {
        console.error('Error deleting movie:', error);
        alert('Error deleting movie');
    }
}

async function promoteUser() {
    const username = document.getElementById('adminPromoteUser').value.trim();
    if (!username) {
        alert('Please enter a username');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/admin/promote?username=${username}`, {
            method: 'POST',
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            alert(`${username} promoted to admin`);
            document.getElementById('adminPromoteUser').value = '';
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to promote user'}`);
        }
    } catch (error) {
        console.error('Error promoting user:', error);
        alert('Error promoting user');
    }
}

async function demoteUser() {
    const username = document.getElementById('adminPromoteUser').value.trim();
    if (!username) {
        alert('Please enter a username');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/admin/demote?username=${username}`, {
            method: 'POST',
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            alert(`${username} demoted from admin`);
            document.getElementById('adminPromoteUser').value = '';
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to demote user'}`);
        }
    } catch (error) {
        console.error('Error demoting user:', error);
        alert('Error demoting user');
    }
}

async function assignPenalty() {
    const username = document.getElementById('penaltyUsername').value.trim();
    const points = document.getElementById('penaltyPoints').value;
    const reason = document.getElementById('penaltyReason').value.trim();
    
    if (!username || !points || !reason) {
        alert('Please fill all penalty fields');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/admin/penalty?username=${username}&points=${points}&reason=${encodeURIComponent(reason)}`, {
            method: 'POST',
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            alert('Penalty assigned successfully');
            document.getElementById('penaltyUsername').value = '';
            document.getElementById('penaltyPoints').value = '';
            document.getElementById('penaltyReason').value = '';
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to assign penalty'}`);
        }
    } catch (error) {
        console.error('Error assigning penalty:', error);
        alert('Error assigning penalty');
    }
}

// Admin Panel Functions

function showAdminSection(section, event) {
    // Hide all admin sections
    document.querySelectorAll('.admin-content-section').forEach(el => {
        el.style.display = 'none';
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.admin-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected section and activate tab
    const sections = {
        'stats': 'adminStatsSection',
        'users': 'adminUsersSection',
        'movies': 'adminMoviesSection',
        'series': 'adminSeriesSection',
        'penalties': 'adminPenaltiesSection'
    };
    
    document.getElementById(sections[section]).style.display = 'block';
    if (event && event.target) {
        event.target.classList.add('active');
    } else {
        // If called without event, activate first matching button
        document.querySelector(`.admin-tab-btn[onclick*="${section}"]`)?.classList.add('active');
    }
}

async function loadAdminStats() {
    console.log('Loading admin stats...');
    console.log('Session token:', sessionToken);
    console.log('API URL:', API_URL);
    
    try {
        const response = await fetch(`${API_URL}/admin/stats`, {
            headers: { 'session-token': sessionToken }
        });
        
        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);
        
        if (response.ok) {
            const stats = await response.json();
            console.log('Stats data:', stats);
            const container = document.getElementById('adminStatsContainer');
            container.innerHTML = `
                <div class="stat-card">
                    <h4>Users</h4>
                    <p class="stat-number">${stats.users.total}</p>
                    <p class="stat-detail">Admins: ${stats.users.admins}</p>
                    <p class="stat-detail">Verified: ${stats.users.verified}</p>
                    <p class="stat-detail">With Penalties: ${stats.users.withPenalties}</p>
                </div>
                <div class="stat-card">
                    <h4>Movies</h4>
                    <p class="stat-number">${stats.movies.total}</p>
                </div>
                <div class="stat-card">
                    <h4>Reviews</h4>
                    <p class="stat-number">${stats.reviews.total}</p>
                    <p class="stat-detail">Avg Rating: ${stats.reviews.averageRating.toFixed(1)}/10</p>
                </div>
            `;
        } else {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            let errorMsg = 'Failed to load statistics';
            try {
                const error = JSON.parse(errorText);
                errorMsg = error.detail || errorMsg;
            } catch (e) {
                errorMsg = errorText || errorMsg;
            }
            const container = document.getElementById('adminStatsContainer');
            container.innerHTML = `<p style="color: #e53e3e;">Error: ${errorMsg}</p>`;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        const container = document.getElementById('adminStatsContainer');
        container.innerHTML = `<p style="color: #e53e3e;">Error: ${error.message}. Check console for details.</p>`;
    }
}

async function loadAllUsers() {
    try {
        const response = await fetch(`${API_URL}/admin/users`, {
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            const data = await response.json();
            const container = document.getElementById('usersTableContainer');
            
            if (data.users.length === 0) {
                container.innerHTML = '<p>No users found</p>';
                return;
            }
            
            let html = `
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Admin</th>
                            <th>Verified</th>
                            <th>Penalty Points</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            data.users.forEach(user => {
                html += `
                    <tr>
                        <td>${user.username}</td>
                        <td>${user.email}</td>
                        <td>${user.isAdmin ? '✅' : '❌'}</td>
                        <td>${user.isVerified ? '✅' : '❌'}</td>
                        <td>${user.totalPenaltyPoints} (${user.totalPenalties})</td>
                        <td>
                            <button onclick="viewUserDetails('${user.username}')" class="btn-small">View</button>
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        } else {
            alert('Failed to load users');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        alert('Error loading users');
    }
}

async function viewUserDetails(username) {
    try {
        const response = await fetch(`${API_URL}/admin/users/${username}`, {
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            const user = await response.json();
            let details = `
                Username: ${user.username}
                Email: ${user.email}
                Admin: ${user.isAdmin ? 'Yes' : 'No'}
                Verified: ${user.isVerified ? 'Yes' : 'No'}
                Total Penalty Points: ${user.totalPenaltyPoints}
                Number of Reviews: ${user.reviewCount}
                
                Penalties:
            `;
            
            if (user.penalties.length > 0) {
                user.penalties.forEach((penalty, idx) => {
                    details += `\n${idx + 1}. ${penalty.points} points - ${penalty.reason}`;
                });
            } else {
                details += '\nNo penalties';
            }
            
            alert(details);
        } else {
            alert('Failed to load user details');
        }
    } catch (error) {
        console.error('Error loading user details:', error);
        alert('Error loading user details');
    }
}

async function deleteUser() {
    const username = document.getElementById('adminDeleteUser').value.trim();
    if (!username) {
        alert('Please enter a username');
        return;
    }
    
    if (!confirm(`Are you sure you want to delete user "${username}"? This cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/admin/users/${username}`, {
            method: 'DELETE',
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            alert(`User "${username}" deleted successfully`);
            document.getElementById('adminDeleteUser').value = '';
            loadAllUsers(); // Refresh the list
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to delete user'}`);
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('Error deleting user');
    }
}

async function loadAdminMovies() {
    try {
        const response = await fetch(`${API_URL}/admin/movies`, {
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            const data = await response.json();
            const container = document.getElementById('moviesTableContainer');
            
            if (data.movies.length === 0) {
                container.innerHTML = '<p>No movies found</p>';
                return;
            }
            
            let html = `
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Title</th>
                            <th>Rating</th>
                            <th>Genres</th>
                            <th>Reviews</th>
                            <th>Published</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            data.movies.forEach(movie => {
                const genres = movie.movieGenres ? movie.movieGenres.slice(0, 2).join(', ') : 'N/A';
                html += `
                    <tr>
                        <td>${movie.title}</td>
                        <td>${movie.movieIMDbRating || 'N/A'}</td>
                        <td>${genres}</td>
                        <td>${movie.reviewCount || 0}</td>
                        <td>${movie.datePublished || 'N/A'}</td>
                        <td>
                            <button onclick="adminDeleteMovieByTitle('${movie.title.replace(/'/g, "\\'")}')" class="btn-small btn-danger">Delete</button>
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        } else {
            alert('Failed to load movies');
        }
    } catch (error) {
        console.error('Error loading movies:', error);
        alert('Error loading movies');
    }
}

async function adminDeleteMovieByTitle(title) {
    if (!confirm(`Are you sure you want to delete "${title}"? This cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/admin/delete-movie/${encodeURIComponent(title)}`, {
            method: 'DELETE',
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            alert(`Movie "${title}" deleted successfully`);
            loadAdminMovies(); // Refresh the list
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to delete movie'}`);
        }
    } catch (error) {
        console.error('Error deleting movie:', error);
        alert('Error deleting movie');
    }
}

async function loadUserPenalties() {
    const username = document.getElementById('viewPenaltiesUsername').value.trim();
    if (!username) {
        alert('Please enter a username');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/admin/users/${username}/penalties`, {
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            const data = await response.json();
            const container = document.getElementById('penaltiesContainer');
            
            if (data.penalties.length === 0) {
                container.innerHTML = `<p>No penalties found for user "${username}"</p>`;
                return;
            }
            
            let html = `
                <h4>Penalties for ${username} (Total: ${data.totalPenaltyPoints} points)</h4>
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Points</th>
                            <th>Reason</th>
                            <th>Date</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            data.penalties.forEach(penalty => {
                html += `
                    <tr>
                        <td>${penalty.points}</td>
                        <td>${penalty.reason}</td>
                        <td>${penalty.dateAssigned ? new Date(penalty.dateAssigned).toLocaleDateString() : 'N/A'}</td>
                        <td>${penalty.isExpired ? 'Expired' : 'Active'}</td>
                        <td>
                            <button onclick="removePenalty('${username}', ${penalty.index})" class="btn-small btn-danger">Remove</button>
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to load penalties'}`);
        }
    } catch (error) {
        console.error('Error loading penalties:', error);
        alert('Error loading penalties');
    }
}

async function removePenalty(username, penaltyIndex) {
    if (!confirm('Are you sure you want to remove this penalty?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/admin/users/${username}/penalties/${penaltyIndex}`, {
            method: 'DELETE',
            headers: { 'session-token': sessionToken }
        });
        
        if (response.ok) {
            alert('Penalty removed successfully');
            loadUserPenalties(); // Refresh the list
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to remove penalty'}`);
        }
    } catch (error) {
        console.error('Error removing penalty:', error);
        alert('Error removing penalty');
    }
}

async function adminAddMovie() {
    const title = document.getElementById('addMovieTitle').value.trim();
    const genres = document.getElementById('addMovieGenres').value.trim();
    const directors = document.getElementById('addMovieDirectors').value.trim();
    const stars = document.getElementById('addMovieStars').value.trim();
    const creators = document.getElementById('addMovieCreators').value.trim();
    const rating = document.getElementById('addMovieRating').value;
    const datePublished = document.getElementById('addMovieDatePublished').value.trim();
    const description = document.getElementById('addMovieDescription').value.trim();
    const ratingCount = document.getElementById('addMovieRatingCount').value || '0';
    const userReviews = document.getElementById('addMovieUserReviews').value.trim() || '0';
    const criticReviews = document.getElementById('addMovieCriticReviews').value.trim() || '0';
    const metaScore = document.getElementById('addMovieMetaScore').value.trim() || 'N/A';
    const posterUrl = document.getElementById('addMoviePosterUrl').value.trim();
    
    if (!title || !genres || !directors || !stars || !creators || !rating || !datePublished || !description) {
        alert('Please fill all required fields');
        return;
    }
    
    // Parse comma-separated values
    const genreList = genres.split(',').map(g => g.trim()).filter(g => g);
    const directorList = directors.split(',').map(d => d.trim()).filter(d => d);
    const starList = stars.split(',').map(s => s.trim()).filter(s => s);
    const creatorList = creators.split(',').map(c => c.trim()).filter(c => c);
    
    const movieData = {
        title: title,
        movieIMDbRating: parseFloat(rating),
        totalRatingCount: parseInt(ratingCount),
        totalUserReviews: userReviews,
        totalCriticReviews: criticReviews,
        metaScore: metaScore,
        movieGenres: genreList,
        directors: directorList,
        datePublished: datePublished,
        creators: creatorList,
        mainStars: starList,
        description: description,
        posterUrl: posterUrl || null
    };
    
    try {
        const response = await fetch(`${API_URL}/admin/add-movie`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'session-token': sessionToken 
            },
            body: JSON.stringify(movieData)
        });
        
        if (response.ok) {
            alert(`Movie "${title}" added successfully!`);
            // Clear form
            document.getElementById('addMovieTitle').value = '';
            document.getElementById('addMovieGenres').value = '';
            document.getElementById('addMovieDirectors').value = '';
            document.getElementById('addMovieStars').value = '';
            document.getElementById('addMovieCreators').value = '';
            document.getElementById('addMovieRating').value = '';
            document.getElementById('addMovieDatePublished').value = '';
            document.getElementById('addMovieDescription').value = '';
            document.getElementById('addMoviePosterUrl').value = '';
            // Refresh movie list
            loadAdminMovies();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to add movie'}`);
        }
    } catch (error) {
        console.error('Error adding movie:', error);
        alert('Error adding movie');
    }
}

// ==================== SERIES ADMIN FUNCTIONS ====================

function addSeriesMovieRow() {
    const container = document.getElementById('seriesMoviesInputs');
    const newRow = document.createElement('div');
    newRow.style.cssText = 'display: grid; grid-template-columns: 2fr 1fr auto; gap: 10px; margin-bottom: 10px;';
    newRow.innerHTML = `
        <input type="text" placeholder="Movie Title" class="series-movie-title">
        <input type="number" placeholder="Order #" class="series-movie-order" min="1">
        <button onclick="this.parentElement.remove()" type="button">-</button>
    `;
    container.appendChild(newRow);
}

async function createSeries() {
    const seriesName = document.getElementById('createSeriesName').value.trim();
    if (!seriesName) {
        alert('Please enter a series name');
        return;
    }

    // Collect all movie entries
    const titleInputs = document.querySelectorAll('.series-movie-title');
    const orderInputs = document.querySelectorAll('.series-movie-order');
    
    const movies = [];
    for (let i = 0; i < titleInputs.length; i++) {
        const title = titleInputs[i].value.trim();
        const order = parseInt(orderInputs[i].value);
        
        if (title && order) {
            movies.push([title, order]);
        }
    }

    if (movies.length === 0) {
        alert('Please add at least one movie to the series');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/series/create?seriesName=${encodeURIComponent(seriesName)}&sessionToken=${sessionToken}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(movies)
        });

        if (response.ok) {
            alert('Series created successfully!');
            document.getElementById('createSeriesName').value = '';
            // Reset movie inputs to just one row
            document.getElementById('seriesMoviesInputs').innerHTML = `
                <div style="display: grid; grid-template-columns: 2fr 1fr auto; gap: 10px; margin-bottom: 10px;">
                    <input type="text" placeholder="Movie Title" class="series-movie-title">
                    <input type="number" placeholder="Order #" class="series-movie-order" min="1">
                    <button onclick="addSeriesMovieRow()" type="button">+</button>
                </div>
            `;
            loadAdminSeries();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to create series'}`);
        }
    } catch (error) {
        console.error('Error creating series:', error);
        alert('Error creating series');
    }
}

async function deleteSeries() {
    const seriesName = document.getElementById('deleteSeriesName').value.trim();
    if (!seriesName) {
        alert('Please enter a series name');
        return;
    }

    if (!confirm(`Delete series "${seriesName}"? This will remove series information from all movies.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/series/${encodeURIComponent(seriesName)}?sessionToken=${sessionToken}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            alert('Series deleted successfully!');
            document.getElementById('deleteSeriesName').value = '';
            loadAdminSeries();
        } else {
            const error = await response.json();
            alert(`Error: ${error.detail || 'Failed to delete series'}`);
        }
    } catch (error) {
        console.error('Error deleting series:', error);
        alert('Error deleting series');
    }
}

async function loadAdminSeries() {
    const container = document.getElementById('seriesTableContainer');
    container.innerHTML = '<p>Loading series...</p>';

    try {
        const response = await fetch(`${API_URL}/series/`);
        
        if (response.ok) {
            const seriesData = await response.json();
            
            if (Object.keys(seriesData).length === 0) {
                container.innerHTML = '<p>No series found</p>';
                return;
            }

            let html = '<table class="admin-table"><thead><tr><th>Series Name</th><th>Movies</th><th>Count</th></tr></thead><tbody>';
            
            for (const [seriesName, movies] of Object.entries(seriesData)) {
                const movieList = movies
                    .sort((a, b) => (a.order || 999) - (b.order || 999))
                    .map(m => `${m.order}. ${m.title}`)
                    .join('<br>');
                
                html += `
                    <tr>
                        <td><strong>${seriesName}</strong></td>
                        <td style="text-align: left;">${movieList}</td>
                        <td>${movies.length}</td>
                    </tr>
                `;
            }
            
            html += '</tbody></table>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<p>Error loading series</p>';
        }
    } catch (error) {
        console.error('Error loading series:', error);
        container.innerHTML = '<p>Error loading series</p>';
    }
}
