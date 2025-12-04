import pytest
import sys
from pathlib import Path
import json
from backend.services.userServices import saveUserToDB,findUserInDB,changeUserStatus
from backend.users import user
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock, mock_open


@pytest.fixture
def mockBaseDir(tmp_path):
    """Create a temporary base directory for tests"""
    return tmp_path / "data"



#pylint: disable = function-naming-style, method-naming-style
@pytest.fixture
def testUser():
    user.User.usersDb.clear()
    name = "testservice"
    email = "testservice@email.com"
    pswd = "password123"
    return user.User(name, email, pswd, save = False)

def test_saveUserToDB(mockBaseDir, testUser):
    #If we call this function, we should be able to find the specific user created
    mockBaseDir.mkdir(parents=True, exist_ok=True)
    path = mockBaseDir/"userList.json"
    saveUserToDB(testUser.username,testUser.email,testUser.passwordHash,False,path)
    with open(path,'r') as jsonFile:
        try:
            data = json.load(jsonFile) 
        except json.JSONDecodeError:
            data = {}
        
    assert testUser.username in data
    assert testUser.email == data[testUser.username]["email"]
    assert testUser.passwordHash.decode('utf-8') == data[testUser.username]["password"]

    #clean up
    with open(path,'w') as jsonFile:
        jsonFile.truncate(0)

def test_ChangeUser(mockBaseDir, testUser):
    #If we call this function, we should be able to find the specific user created
    mockBaseDir.mkdir(parents=True, exist_ok=True)
    path = mockBaseDir/"userList.json"
    saveUserToDB(testUser.username,testUser.email,testUser.passwordHash,False,path)
    changeUserStatus(testUser.username,True, path)
    with open(path,'r') as jsonFile:
        try:
            data = json.load(jsonFile) 
        except json.JSONDecodeError:
            data = {}
        
    assert data[testUser.username]["isVerified"] 

    #clean up
    with open(path,'w') as jsonFile:
        jsonFile.truncate(0)

        


def testFindUserInDB(mockBaseDir, testUser):
    mockBaseDir.mkdir(parents=True, exist_ok=True)
    path = mockBaseDir/"userList.json"
    saveUserToDB(testUser.username,testUser.email,testUser.passwordHash,False,path)
    saveUserToDB("testUser.username",testUser.email,testUser.passwordHash,False,path)
    saveUserToDB("tester",testUser.email,testUser.passwordHash,False,path)

    assert findUserInDB(testUser.username,path) == {"email":testUser.email,"password":testUser.passwordHash.decode('utf-8'),"isVerified": False, "verificationToken": None, "isAdmin": False}
    with pytest.raises(ValueError):
        findUserInDB("notTester",path)
