# CamelCase version of the provided test file

import pytest
import sys
from pathlib import Path
import json
from backend.users.user import User
from backend.users.penaltyPoints import PenaltyPoints
from unittest.mock import mock_open, patch, MagicMock
from unittest import TestCase
from datetime import datetime, timedelta
import threading

# pylint: disable=function-naming-style, method-naming-style

@pytest.fixture(autouse=True)
def cleanupUsersDb():
    User.usersDb.clear()
    User.activeSessions.clear()
    # Also clear the persistent JSON file for tests
    path = Path("backend/data/Users/userList.json")
    if path.exists():
        path.write_text("{}")
    yield
    User.usersDb.clear()
    User.activeSessions.clear()
    if path.exists():
        path.write_text("{}")

@pytest.fixture
def testUser():
    name = "test"
    email = "email@email.com"
    pswd = "password"
    return User(name, email, pswd, save=False)


class TestCheckUsername:
    def testCheckUsernameTooShort(self, testUser):
        assert testUser.checkUsername("a") is False

    def testCheckUsernameTooLong(self, testUser):
        assert testUser.checkUsername("a" * 26) is False

    def testCheckUsernameNonAlphnum(self, testUser):
        assert testUser.checkUsername("abcde%") is False

    def testCheckUsernameValid(self, testUser):
        assert testUser.checkUsername("Username") is True

    def testCheckUsernameMinLength(self, testUser):
        assert testUser.checkUsername("abc") is True

    def testCheckUsernameMaxLength(self, testUser):
        assert testUser.checkUsername("a" * 20) is True

    def testCheckUsernameJustOverMax(self, testUser):
        assert testUser.checkUsername("a" * 21) is False

    def testCheckUsernameWithUnderscore(self, testUser):
        assert testUser.checkUsername("user_name") is False
        assert testUser.checkUsername("test_user_123") is False

    def testCheckUsernameEmpty(self, testUser):
        assert testUser.checkUsername("") is False


class TestCheckEmail:
    def testCheckEmailBadPattern(self, testUser):
        assert testUser.checkEmail("email.com") is False
        assert testUser.checkEmail("email.email.com") is False

    def testCheckEmailValidPattern(self, testUser):
        assert testUser.checkEmail("email@email.com") is True

    def testCheckEmailMultipleAt(self, testUser):
        assert testUser.checkEmail("email@@email.com") is False

    def testCheckEmailNoTopLevelDomain(self, testUser):
        assert testUser.checkEmail("email@email") is False

    def testCheckEmailSpecialCharsInvalid(self, testUser):
        assert testUser.checkEmail("em ail@email.com") is False

    def testCheckEmailEmpty(self, testUser):
        assert testUser.checkEmail("") is False

    def testCheckEmailValidWithPlus(self, testUser):
        assert testUser.checkEmail("user+tag@email.com") is True


class TestEncryptPassword:
    def testEncryptPasswordInvalid(self, testUser):
        with pytest.raises(Exception):
            testUser.encryptPassword("a")

    def testEncryptPasswordValid(self, testUser):
        assert isinstance(testUser.encryptPassword("password"), bytes)

    def testEncryptPasswordMinLength(self, testUser):
        result = testUser.encryptPassword("12345678")
        assert isinstance(result, bytes)

    def testEncryptPasswordVeryLong(self, testUser):
        longPassword = "a" * 100
        with pytest.raises(ValueError, match="cannot be longer than 72 bytes"):
            testUser.encryptPassword(longPassword)

    def testEncryptPasswordSpecialChars(self, testUser):
        result = testUser.encryptPassword("P@ssw0rd!")
        assert isinstance(result, bytes)

    def testEncryptPasswordUnicode(self, testUser):
        result = testUser.encryptPassword("pässwörd123")
        assert isinstance(result, bytes)


class TestVerifyPassword:
    def testVerifyPasswordInvalid(self, testUser):
        assert testUser.verifyPassword("notpass") is False

    def testVerifyPasswordValid(self, testUser):
        assert testUser.verifyPassword("password") is True

    def testVerifyPasswordEmpty(self, testUser):
        assert testUser.verifyPassword("") is False

    def testVerifyPasswordCaseSensitive(self, testUser):
        assert testUser.verifyPassword("Password") is False
        assert testUser.verifyPassword("PASSWORD") is False

    def testVerifyPasswordWithSpaces(self, testUser):
        assert testUser.verifyPassword(" password") is False
        assert testUser.verifyPassword("password ") is False


class TestVerifyEmail:
    def testVerifyEmail(self, testUser):
        assert testUser.verifyEmail(testUser.verificationToken) is True

    def testVerifyEmailFalse(self, testUser):
        assert testUser.verifyEmail(testUser.id) is False

    def testVerifyEmailEmpty(self, testUser):
        assert testUser.verifyEmail("") is False

    def testVerifyEmailAlreadyVerified(self, testUser):
        user = User("testverify", "verify@test.com", "password123", save=False)
        user.verifyEmail(user.verificationToken)
        assert user.isVerified is True
        assert user.verifyEmail(user.verificationToken) is True
        assert user.isVerified is True


# Module-level variables for functions that need them
name = "testuser"
email = "testuser@email.com"
pswd = "password123"


def testLoginAllowedWithFewerThan3Penalties(cleanupUsersDb):
    user = User(name, email, pswd, save=False)
    user.isVerified = True
    PenaltyPoints(1, user, "Reason 1")
    PenaltyPoints(1, user, "Reason 2")
    User.usersDb[user.username] = user
    token = User.login(user.username, pswd)
    assert token is not None


def testLoginBlockedWithMoreThan3Penalties(cleanupUsersDb):
    blockedUser = User("blockeduser", "blocked@email.com", pswd, save=False)
    blockedUser.isVerified = True
    for i in range(5):
        PenaltyPoints(1, blockedUser, f"Reason {i+1}")
    User.usersDb[blockedUser.username] = blockedUser
    with pytest.raises(ValueError, match="too many penalty points"):
        User.login(blockedUser.username, pswd)


def testLoginBlockedWithExactly3Penalties(cleanupUsersDb):
    user = User("boundaryuser", "boundary@test.com", pswd, save=False)
    user.isVerified = True
    PenaltyPoints(1, user, "Reason 1")
    PenaltyPoints(1, user, "Reason 2")
    PenaltyPoints(1, user, "Reason 3")
    User.usersDb[user.username] = user
    with pytest.raises(ValueError, match="too many penalty points"):
        User.login(user.username, pswd)


def testLoginAllowedWithExpiredPenalties(cleanupUsersDb):
    user = User("expireduser", "expired@test.com", pswd, save=False)
    user.isVerified = True
    pp1 = PenaltyPoints(2, user, "Old violation")
    pp2 = PenaltyPoints(2, user, "Another old violation")
    pastTime = datetime.now() - timedelta(days=1)
    pp1.expiresAt = pastTime
    pp2.expiresAt = pastTime
    User.usersDb[user.username] = user
    token = User.login(user.username, pswd)
    assert token is not None


def testTotalPenaltyPoints(cleanupUsersDb):
    user = User("penaltytest", "penalty@test.com", "password123", save=False)
    PenaltyPoints(1, user, "Minor violation")
    PenaltyPoints(2, user, "Major violation")
    assert user.totalPenaltyPoints() == 3


def testTotalPenaltyPointsZero(cleanupUsersDb):
    user = User("newpenalty", "newpenalty@test.com", "password123", save=False)
    assert user.totalPenaltyPoints() == 0


def testCreateAccountSuccess(cleanupUsersDb):
    username = "newuser1"
    emailNew = "newuser1@example.com"
    password = "StrongPass123!"
    user = User(username, emailNew, password, save=False)
    assert user.username == username
    assert user.email == emailNew
    assert isinstance(user.passwordHash, bytes)
    assert user.isVerified is False
    assert user.penaltyPointsList == []


def testCreateAccountDuplicateUsername(cleanupUsersDb):
    username = "duplicateUser"
    email1 = "duplicate1@example.com"
    email2 = "duplicate2@example.com"
    password = "password1234"
    user1 = User(username, email1, password, save=False)
    User.usersDb[user1.username] = user1
    with pytest.raises(ValueError, match="(?i)username already exists"):
        User.createAccount(username, email2, password)


def testCreateAccountDuplicateEmail(cleanupUsersDb):
    username1 = "user1"
    username2 = "user2"
    sharedEmail = "same@example.com"
    password = "password1234"
    user1 = User(username1, sharedEmail, password, save=False)
    User.usersDb[user1.username] = user1
    with pytest.raises(ValueError, match="(?i)email already registered"):
        User.createAccount(username2, sharedEmail, password)


def testCreateAccountInvalidUsername():
    with pytest.raises(ValueError, match="Invalid username"):
        User("ab", "test@test.com", "password123", save=False)
    with pytest.raises(ValueError, match="Invalid username"):
        User("user@name", "test@test.com", "password123", save=False)


def testCreateAccountInvalidEmail():
    with pytest.raises(ValueError, match="Invalid email"):
        User("validuser", "invalidemail", "password123", save=False)


def testCreateAccountWeakPassword():
    with pytest.raises(ValueError, match="at least 8 characters"):
        User("validuser", "valid@test.com", "short", save=False)


def testLoginFailsNotVerified(cleanupUsersDb):
    username = "unverified"
    emailUnverified = "unverified@example.com"
    password = "password123"
    user = User(username, emailUnverified, password, save=False)
    user.isVerified = False
    User.usersDb[user.username] = user
    with pytest.raises(ValueError, match="verify your email"):
        User.login(username, password)


def testLoginInvalidUsername():
    with pytest.raises(ValueError, match="Invalid username or password"):
        User.login("nonexistent", "password123")


def testLoginInvalidPassword(cleanupUsersDb):
    user = User("testlogin", "testlogin@test.com", "correct123", save=False)
    user.isVerified = True
    User.usersDb[user.username] = user
    with pytest.raises(ValueError, match="Invalid username or password"):
        User.login(user.username, "wrongpassword")


def testLoginSuccess(cleanupUsersDb):
    user = User("logintest", "login@test.com", "password123", save=False)
    user.isVerified = True
    User.usersDb[user.username] = user
    token = User.login(user.username, "password123")
    assert token is not None
    assert token in User.activeSessions
    assert user.lastLogin is not None


def testLogoutSuccess(cleanupUsersDb):
    user = User("logouttest", "logout@test.com", "password123", save=False)
    user.isVerified = True
    User.usersDb[user.username] = user
    token = User.login(user.username, "password123")
    assert token in User.activeSessions
    result = user.logout(token)
    assert result is True
    assert token not in User.activeSessions


def testLogoutInvalidToken(cleanupUsersDb):
    user = User("logouttest2", "logout2@test.com", "password123", save=False)
    result = user.logout("invalid-token-12345")
    assert result is False


def testGetCurrentUserValid(cleanupUsersDb):
    user = User("sessiontest", "session@test.com", "password123", save=False)
    user.isVerified = True
    User.usersDb[user.username] = user
    token = User.login(user.username, "password123")
    retrievedUser = user.getCurrentUser(token)
    assert retrievedUser is not None
    assert retrievedUser.username == user.username


def testGetCurrentUserInvalid(cleanupUsersDb):
    user = User("sessiontest2", "session2@test.com", "password123", save=False)
    retrievedUser = user.getCurrentUser("invalid-token")
    assert retrievedUser is None


def testGetCurrentUserExpired(cleanupUsersDb):
    user = User("expiredtest", "expired@test.com", "password123", save=False)
    user.isVerified = True
    User.usersDb[user.username] = user
    token = User.login(user.username, "password123")
    if token in User.activeSessions:
        oldUser, _ = User.activeSessions[token]
        expiredTime = datetime.now() - timedelta(hours=25)
        User.activeSessions[token] = (oldUser, expiredTime)
    retrievedUser = user.getCurrentUser(token)
    assert retrievedUser is None
    assert token not in User.activeSessions


def testCleanExpiredSessions(cleanupUsersDb):
    user1 = User("cleanup1", "cleanup1@test.com", "password123", save=False)
    user2 = User("cleanup2", "cleanup2@test.com", "password123", save=False)
    user1.isVerified = True
    user2.isVerified = True
    User.usersDb[user1.username] = user1
    User.usersDb[user2.username] = user2
    token1 = User.login(user1.username, "password123")
    token2 = User.login(user2.username, "password123")
    if token1 in User.activeSessions:
        oldUser, _ = User.activeSessions[token1]
        expiredTime = datetime.now() - timedelta(hours=25)
        User.activeSessions[token1] = (oldUser, expiredTime)
    User._cleanExpiredSessions()
    assert token1 not in User.activeSessions
    assert token2 in User.activeSessions


def testCompleteUserWorkflow(cleanupUsersDb):
    username = "workflow"
    emailWorkflow = "workflow@test.com"
    password = "password123"
    user = User(username, emailWorkflow, password, save=False)
    User.usersDb[user.username] = user
    assert user.username == username
    assert user.isVerified is False
    user.verifyEmail(user.verificationToken)
    assert user.isVerified is True
    token = User.login(username, password)
    assert token is not None
    assert token in User.activeSessions
    result = user.logout(token)
    assert result is True
    assert token not in User.activeSessions


def testThreadSafetyLockExists():
    assert hasattr(User, "_lock")

    lock_type = type(threading.Lock())

    assert isinstance(User._lock, lock_type)


def testUserInitializationAttributes():
    user = User("attrtest", "attr@test.com", "password123", save=False)
    assert hasattr(user, "id")
    assert hasattr(user, "username")
    assert hasattr(user, "email")
    assert hasattr(user, "passwordHash")
    assert hasattr(user, "isVerified")
    assert hasattr(user, "verificationToken")
    assert hasattr(user, "createdAt")
    assert hasattr(user, "lastLogin")
    assert hasattr(user, "penaltyPointsList")
    assert isinstance(user.id, str)
    assert user.lastLogin is None
    assert isinstance(user.createdAt, datetime)
    assert isinstance(user.penaltyPointsList, list)


def testVerificationTokenIsUnique():
    user1 = User("unique1", "unique1@test.com", "password123", save=False)
    user2 = User("unique2", "unique2@test.com", "password123", save=False)
    assert user1.verificationToken != user2.verificationToken
    assert user1.id != user2.id
