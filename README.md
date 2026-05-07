# BestBytes — Movie Database & Review System

A full-stack movie database and review platform built to demonstrate structured software engineering practices for **COSC 310 at the University of British Columbia**. BestBytes supports user authentication, movie browsing, reviews, and admin moderation.

---

## 🚀 Features

*   **Authentication:** Role-based access control (User/Admin) via session-based tokens.
*   **Movie Catalog:** Structured metadata browsing with advanced filtering capabilities.
*   **Engagement:** User review and rating system linked to specific movie profiles.
*   **Personalization:** Dedicated user dashboards for tracking activity and history.
*   **Moderation:** Admin-specific tools for managing content and community reviews.

---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React |
| **Backend** | FastAPI (Python) |
| **Database** | *[Add Database, e.g., PostgreSQL / MongoDB]* |
| **Auth** | Session-based authentication with token handling |
| **DevOps** | Docker |
| **Testing** | *[Add Testing Framework, e.g., Pytest / Jest]* |

---

## 🏗 Architecture

The system utilizes a modular **Client-Server Architecture**:

*   **Frontend (React):** Manages the UI, client-side routing, and user interactions.
*   **Backend (FastAPI):** Exposes RESTful APIs for authentication, movie data, and reviews.
*   **Authentication Layer:** Enforces access control via session tokens for protected routes.
*   **Data Layer:** Provides structured storage for users, movies, and reviews.

Communication between the frontend and backend is handled via REST API calls, with security enforced through session tokens.

---

## 🚦 Getting Started

### Backend Setup

1.  **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd <project-folder>
    ```

2.  **Containerize with Docker:**
    ```bash
    docker build -t bestbytes-backend .
    ```

3.  **Run the application:**
    ```bash
    uvicorn backend.app:app --reload
    ```

### Admin Credentials & Authentication

To access moderation features, use the following default credentials:

*   **Username:** `admin`
*   **Password:** `Admin123!`

**Login Endpoint:**  
`POST /users/login?username=admin&password=Admin123!`  
*The response will include a `sessionToken` required for all subsequent authenticated requests.*

---

## 🧠 Engineering Decisions

*   **FastAPI:** Selected over Express for superior performance and native Python type-hinting/safety.
*   **Session-Based Auth:** Implemented for simplicity and secure request handling within a course project scope.
*   **Modular Services:** Separation of concerns between Auth, Movie, and Review services to ensure high maintainability.
*   **RESTful Standards:** Adopted to ensure predictable client-server communication and future scalability.
*   **Traceability:** Implementation was mapped directly to requirements following COSC 310 software engineering principles.

---

## 👥 Project Status & Team

*   **Context:** Developed for UBC COSC 310 (Software Engineering).
*   **Team Size:** 4 Members.
*   **Methodology:** **Agile Scrum** with iterative sprint delivery and GitHub-based version control.
