import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
client = TestClient(app)

def test_get_genres():
    res = client.get("/roulette/genres")
    assert res.status_code == 200
    assert "genres" in res.json()

def test_spin_no_genre():
    res = client.post("/roulette/spin", json={"genres": []})
    assert res.status_code == 200
    assert "title" in res.json()

def test_spin_multiple_genres():
    res = client.post("/roulette/spin", json={"genres": ["Action", "Drama"]})
    assert res.status_code == 200
    data = res.json()
    assert any(g in ["Action", "Drama"] for g in data["movieGenres"])
