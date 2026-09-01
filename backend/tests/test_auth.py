from fastapi.testclient import TestClient
from app.main import app


def test_register_login_and_protected_route():
    with TestClient(app) as client:
        email='auth-check@example.com'; password='SecurePassword123!'
        register=client.post('/api/v1/auth/register',json={'full_name':'Auth Check','email':email,'password':password})
        assert register.status_code in (201,409)
        login=client.post('/api/v1/auth/login',json={'email':email,'password':password})
        assert login.status_code==200 and login.json()['access_token']
        assert client.get('/api/v1/manuals').status_code==401
        client.headers['Authorization']=f"Bearer {login.json()['access_token']}"
        assert client.get('/api/v1/manuals').status_code==200


def test_provider_configuration_is_backend_only(client):
    response=client.get('/api/v1/providers')
    assert response.status_code==200
    body=response.json()
    assert body['llm']['selected']=='local'
    assert set(body['llm']['available']) == {'local','groq','openai','anthropic'}
    assert client.get('/api/v1/user/providers').status_code==404
