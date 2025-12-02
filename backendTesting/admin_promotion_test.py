import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.adminRouter import router
from backend.users.user import User
from datetime import datetime


# Create test app
app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def mockUserDb(tmp_path):
    """Mock user database and isolate from persistent admin"""
    from unittest.mock import patch
    
    # Clear in-memory state
    originalDb = User.usersDb.copy() if hasattr(User, 'usersDb') else {}
    originalSessions = User.activeSessions.copy() if hasattr(User, 'activeSessions') else {}
    User.usersDb = {}
    User.activeSessions = {}
    
    # Mock the path to avoid conflicts with persistent admin
    mock_path = tmp_path / "test_userList.json"
    mock_path.write_text("{}")
    
    with patch('backend.users.user.Path') as mock_path_class:
        mock_path_class.return_value = mock_path
        yield User.usersDb
    
    User.usersDb = originalDb
    User.activeSessions = originalSessions


class TestAdminPromotion:
    """Tests for POST /admin/promote endpoint"""
    
    def testPromoteUserSuccess(self, mockUserDb):
        """Successfully promote a user to admin"""
        # Create admin user
        adminUser = User("testadmin", "admin@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["testadmin"] = adminUser
        User.activeSessions["admin-token-123"] = (adminUser, datetime.now())
        
        # Create regular user
        regularUser = User("testuser", "test@test.com", "Test123!", save=False, isAdmin=False)
        User.usersDb["testuser"] = regularUser
        
        response = client.post(
            "/promote",
            params={"username": "testuser"},
            headers={"session-token": "admin-token-123"}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "User 'testuser' promoted to admin"
        assert regularUser.isAdmin is True
    
    def testPromoteUserNotFound(self, mockUserDb):
        """Fail to promote non-existent user"""
        adminUser = User("admin", "admin@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["admin"] = adminUser
        User.activeSessions["admin-token-123"] = (adminUser, datetime.now())
        
        response = client.post(
            "/promote",
            params={"username": "nonexistent"},
            headers={"session-token": "admin-token-123"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def testPromoteAlreadyAdmin(self, mockUserDb):
        """Fail to promote user who is already admin"""
        adminUser = User("admin", "admin@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["admin"] = adminUser
        User.activeSessions["admin-token-123"] = (adminUser, datetime.now())
        
        otherAdmin = User("admin2", "admin2@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["admin2"] = otherAdmin
        
        response = client.post(
            "/promote",
            params={"username": "admin2"},
            headers={"session-token": "admin-token-123"}
        )
        
        assert response.status_code == 400
        assert "already an admin" in response.json()["detail"].lower()
    
    def testPromoteWithoutAdminPrivileges(self, mockUserDb):
        """Fail to promote user when caller is not admin"""
        regularUser = User("regular", "regular@test.com", "Test123!", save=False, isAdmin=False)
        User.usersDb["regular"] = regularUser
        User.activeSessions["regular-token-123"] = (regularUser, datetime.now())
        
        targetUser = User("target", "target@test.com", "Test123!", save=False, isAdmin=False)
        User.usersDb["target"] = targetUser
        
        response = client.post(
            "/promote",
            params={"username": "target"},
            headers={"session-token": "regular-token-123"}
        )
        
        assert response.status_code == 403
        assert "admin privileges required" in response.json()["detail"].lower()
    
    def testPromoteWithoutSessionToken(self, mockUserDb):
        """Fail to promote without session token"""
        response = client.post(
            "/promote",
            params={"username": "testuser"}
        )
        
        assert response.status_code == 401
        assert "session token required" in response.json()["detail"].lower()


class TestAdminDemotion:
    """Tests for POST /admin/demote endpoint"""
    
    def testDemoteUserSuccess(self, mockUserDb):
        """Successfully demote a user from admin"""
        # Create admin user
        adminUser = User("admin", "admin@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["admin"] = adminUser
        User.activeSessions["admin-token-123"] = (adminUser, datetime.now())
        
        # Create another admin user
        targetAdmin = User("admin2", "admin2@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["admin2"] = targetAdmin
        
        response = client.post(
            "/demote",
            params={"username": "admin2"},
            headers={"session-token": "admin-token-123"}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "User 'admin2' demoted from admin"
        assert targetAdmin.isAdmin is False
    
    def testDemoteSelf(self, mockUserDb):
        """Fail to demote yourself"""
        adminUser = User("admin", "admin@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["admin"] = adminUser
        User.activeSessions["admin-token-123"] = (adminUser, datetime.now())
        
        response = client.post(
            "/demote",
            params={"username": "admin"},
            headers={"session-token": "admin-token-123"}
        )
        
        assert response.status_code == 400
        assert "cannot demote yourself" in response.json()["detail"].lower()
    
    def testDemoteNonAdmin(self, mockUserDb):
        """Fail to demote user who is not admin"""
        adminUser = User("admin", "admin@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["admin"] = adminUser
        User.activeSessions["admin-token-123"] = (adminUser, datetime.now())
        
        regularUser = User("regular", "regular@test.com", "Test123!", save=False, isAdmin=False)
        User.usersDb["regular"] = regularUser
        
        response = client.post(
            "/demote",
            params={"username": "regular"},
            headers={"session-token": "admin-token-123"}
        )
        
        assert response.status_code == 400
        assert "not an admin" in response.json()["detail"].lower()
    
    def testDemoteUserNotFound(self, mockUserDb):
        """Fail to demote non-existent user"""
        adminUser = User("admin", "admin@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["admin"] = adminUser
        User.activeSessions["admin-token-123"] = (adminUser, datetime.now())
        
        response = client.post(
            "/demote",
            params={"username": "nonexistent"},
            headers={"session-token": "admin-token-123"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def testDemoteWithoutAdminPrivileges(self, mockUserDb):
        """Fail to demote when caller is not admin"""
        regularUser = User("regular", "regular@test.com", "Test123!", save=False, isAdmin=False)
        User.usersDb["regular"] = regularUser
        User.activeSessions["regular-token-123"] = (regularUser, datetime.now())
        
        adminUser = User("admin", "admin@test.com", "Admin123!", save=False, isAdmin=True)
        User.usersDb["admin"] = adminUser
        
        response = client.post(
            "/demote",
            params={"username": "admin"},
            headers={"session-token": "regular-token-123"}
        )
        
        assert response.status_code == 403
        assert "admin privileges required" in response.json()["detail"].lower()
