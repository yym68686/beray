import pytest
import responses
from beray.client import BeRayClient
from beray.exceptions import AuthenticationError, ConflictError

BASE_URL = "http://localhost:8000"
API_V1_BASE = f"{BASE_URL}/api/v1"

@pytest.fixture
def client():
    """Provides a BeRayClient instance for testing."""
    return BeRayClient(base_url=BASE_URL)

@pytest.fixture
def mocked_responses():
    """Provides a responses context manager."""
    with responses.RequestsMock() as rsps:
        yield rsps

def test_request_verification_code_success(client, mocked_responses):
    mocked_responses.add(
        responses.POST,
        f"{API_V1_BASE}/auth/request-verification-code",
        json={"message": "Verification code sent."},
        status=200,
    )
    response = client.request_verification_code("test@example.com")
    assert response["message"] == "Verification code sent."

def test_request_verification_code_conflict(client, mocked_responses):
    mocked_responses.add(
        responses.POST,
        f"{API_V1_BASE}/auth/request-verification-code",
        json={"detail": "Email already registered."},
        status=409,
    )
    with pytest.raises(ConflictError) as excinfo:
        client.request_verification_code("test@example.com")
    assert "Email already registered" in str(excinfo.value)

def test_register_success(client, mocked_responses):
    mocked_responses.add(
        responses.POST,
        f"{API_V1_BASE}/auth/register",
        json={"access_token": "fake_token", "token_type": "bearer", "user": {"email": "test@example.com"}},
        status=200,
    )
    response = client.register("test@example.com", "123456", "password")
    assert response["access_token"] == "fake_token"
    assert client._session.headers["Authorization"] == "Bearer fake_token"

def test_login_success(client, mocked_responses):
    mocked_responses.add(
        responses.POST,
        f"{API_V1_BASE}/auth/login",
        json={"access_token": "fake_token", "token_type": "bearer", "user": {}},
        status=200,
    )
    response = client.login("test@example.com", "password")
    assert response["access_token"] == "fake_token"
    assert client._session.headers["Authorization"] == "Bearer fake_token"

def test_login_failure(client, mocked_responses):
    mocked_responses.add(
        responses.POST,
        f"{API_V1_BASE}/auth/login",
        json={"detail": "Incorrect email or password"},
        status=401,
    )
    with pytest.raises(AuthenticationError):
        client.login("test@example.com", "wrong_password")

def test_login_with_form_success(client, mocked_responses):
    mocked_responses.add(
        responses.POST,
        f"{API_V1_BASE}/auth/token",
        json={"access_token": "fake_token_form", "token_type": "bearer", "user": {}},
        status=200,
    )
    response = client.login_with_form("test@example.com", "password")
    assert response["access_token"] == "fake_token_form"
    assert client._session.headers["Authorization"] == "Bearer fake_token_form"

def test_logout_success(client, mocked_responses):
    # First, simulate a login to set the token
    client.set_token("fake_token")
    assert "Authorization" in client._session.headers

    mocked_responses.add(
        responses.POST,
        f"{API_V1_BASE}/auth/logout",
        json={"message": "Successfully logged out"},
        status=200,
    )

    response = client.logout()
    assert response["message"] == "Successfully logged out"
    assert "Authorization" not in client._session.headers

def test_get_current_user_success(client, mocked_responses):
    client.set_token("fake_token")
    user_data = {"email": "test@example.com", "id": 1}
    mocked_responses.add(
        responses.GET,
        f"{API_V1_BASE}/users/me",
        json=user_data,
        status=200,
    )
    response = client.get_current_user()
    assert response == user_data

def test_get_current_user_unauthorized(client, mocked_responses):
    # No token is set
    mocked_responses.add(
        responses.GET,
        f"{API_V1_BASE}/users/me",
        json={"detail": "Not authenticated"},
        status=401,
    )
    with pytest.raises(AuthenticationError):
        client.get_current_user()

# #################################################
# Task Management Tests
# #################################################

def test_create_task_success(client, mocked_responses):
    client.set_token("fake_token")
    task_data = {"id": 1, "goal": "test goal", "status": "RUNNING"}
    mocked_responses.add(
        responses.POST,
        f"{API_V1_BASE}/tasks/",
        json=task_data,
        status=200,
    )
    response = client.create_task(goal="test goal")
    assert response == task_data

def test_list_tasks_success(client, mocked_responses):
    client.set_token("fake_token")
    tasks_data = [{"id": 1, "goal": "test goal", "status": "COMPLETED"}]
    mocked_responses.add(
        responses.GET,
        f"{API_V1_BASE}/tasks/",
        json=tasks_data,
        status=200,
    )
    response = client.list_tasks()
    assert response == tasks_data

def test_get_task_success(client, mocked_responses):
    client.set_token("fake_token")
    task_data = {"id": 1, "goal": "test goal", "status": "COMPLETED"}
    mocked_responses.add(
        responses.GET,
        f"{API_V1_BASE}/tasks/1",
        json=task_data,
        status=200,
    )
    response = client.get_task(task_id=1)
    assert response == task_data

def test_delete_task_success(client, mocked_responses):
    client.set_token("fake_token")
    mocked_responses.add(
        responses.DELETE,
        f"{API_V1_BASE}/tasks/1",
        json={"status": "success", "message": "Task deleted"},
        status=200,
    )
    response = client.delete_task(task_id=1)
    assert response["status"] == "success"

# #################################################
# Task File Management Tests
# #################################################

def test_list_files_tree_success(client, mocked_responses):
    client.set_token("fake_token")
    tree_data = [{"name": "file.txt", "type": "file"}]
    mocked_responses.add(
        responses.GET,
        f"{API_V1_BASE}/tasks/1/files/tree",
        json=tree_data,
        status=200,
    )
    response = client.list_files_tree(task_id=1, path=".")
    assert response == tree_data

def test_get_file_content_success(client, mocked_responses):
    client.set_token("fake_token")
    file_content = b"Hello, World!"
    mocked_responses.add(
        responses.GET,
        f"{API_V1_BASE}/tasks/1/files/content",
        body=file_content,
        status=200,
        content_type="text/plain",
    )
    response = client.get_file_content(task_id=1, path="file.txt")
    assert response.content == file_content
    assert response.status_code == 200

def test_upload_file_success(client, mocked_responses):
    client.set_token("fake_token")
    upload_response = {"message": "File saved", "path": "new_file.txt", "size": 13}
    mocked_responses.add(
        responses.PUT,
        f"{API_V1_BASE}/tasks/1/files/content?path=new_file.txt",
        json=upload_response,
        status=200,
    )
    response = client.upload_file(task_id=1, path="new_file.txt", content=b"Hello, Upload!")
    assert response == upload_response

def test_download_files_as_zip_success(client, mocked_responses):
    client.set_token("fake_token")
    zip_content = b"PK..."
    mocked_responses.add(
        responses.POST,
        f"{API_V1_BASE}/tasks/1/files/download",
        body=zip_content,
        status=200,
        content_type="application/zip",
    )
    response = client.download_files_as_zip(task_id=1, paths=["file.txt"])
    assert response.content == zip_content
    assert response.status_code == 200
