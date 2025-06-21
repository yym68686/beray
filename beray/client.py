import requests
import json
from typing import Optional, Dict, Any, List, Iterator, Union
import mimetypes

from .exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
)

class BeRayClient:
    """
    A client for interacting with the BeRay API.
    """

    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        """
        Initializes the BeRa yClient.

        Args:
            base_url: The base URL of the BeRay API.
            token: An optional initial access token.
        """
        self.base_url = base_url.rstrip('/')
        self.api_base_url = f"{self.base_url}/api/v1"
        self._session = requests.Session()
        if token:
            self.set_token(token)

    def set_token(self, token: str):
        """
        Sets the access token for authentication.

        Args:
            token: The access token.
        """
        self._session.headers.update({"Authorization": f"Bearer {token}"})

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handles API responses, checking for errors and returning JSON data.
        """
        if 200 <= response.status_code < 300:
            if response.status_code == 204:  # No Content
                return {}
            return response.json()

        error_detail = response.text
        try:
            error_json = response.json()
            error_detail = error_json.get("detail", error_detail)
        except requests.exceptions.JSONDecodeError:
            pass

        if response.status_code == 401:
            raise AuthenticationError(f"Authentication failed: {error_detail}")
        elif response.status_code == 403:
            raise AuthenticationError(f"Forbidden: {error_detail}")
        elif response.status_code == 404:
            raise NotFoundError(response.status_code, error_detail)
        elif response.status_code == 409:
            raise ConflictError(response.status_code, error_detail)
        elif response.status_code == 422:
            raise UnprocessableEntityError(response.status_code, error_detail)
        else:
            raise APIError(response.status_code, error_detail)

    def request_verification_code(self, email: str) -> Dict[str, Any]:
        """
        Requests a verification code for a given email address.
        """
        url = f"{self.api_base_url}/auth/request-verification-code"
        response = self._session.post(url, json={"email": email})
        return self._handle_response(response)

    def register(self, email: str, verification_code: str, password: str) -> Dict[str, Any]:
        """
        Registers a new user with an email, verification code, and password.
        """
        url = f"{self.api_base_url}/auth/register"
        payload = {
            "email": email,
            "verification_code": verification_code,
            "password": password,
        }
        response = self._session.post(url, json=payload)
        data = self._handle_response(response)
        if "access_token" in data:
            self.set_token(data["access_token"])
        return data

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Logs in a user with an email and password.
        """
        url = f"{self.api_base_url}/auth/login"
        payload = {"email": email, "password": password}
        response = self._session.post(url, json=payload)
        data = self._handle_response(response)
        if "access_token" in data:
            self.set_token(data["access_token"])
        return data

    def login_with_form(self, email: str, password: str) -> Dict[str, Any]:
        """
        Logs in a user via OAuth2 form data.
        """
        url = f"{self.api_base_url}/auth/token"
        payload = {"username": email, "password": password}
        response = self._session.post(url, data=payload)
        data = self._handle_response(response)
        if "access_token" in data:
            self.set_token(data["access_token"])
        return data

    def logout(self) -> Dict[str, Any]:
        """
        Logs out the current user.
        """
        url = f"{self.api_base_url}/auth/logout"
        response = self._session.post(url)
        # Clear the token on logout
        self._session.headers.pop("Authorization", None)
        return self._handle_response(response)

    def get_current_user(self) -> Dict[str, Any]:
        """
        Retrieves the details of the currently authenticated user.
        """
        url = f"{self.api_base_url}/users/me"
        response = self._session.get(url)
        return self._handle_response(response)

    # #################################################
    # Task Management
    # #################################################

    def create_task(self, goal: str, tools: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Creates a new AI assistant task.

        Args:
            goal: The goal or input for the task.

        Returns:
            A dictionary representing the created task.
        """
        url = f"{self.api_base_url}/tasks/"
        response = self._session.post(url, json={"goal": goal, "tools": tools})
        return self._handle_response(response)

    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        Retrieves a list of all tasks for the current user.

        Returns:
            A list of task dictionaries.
        """
        url = f"{self.api_base_url}/tasks/"
        response = self._session.get(url)
        return self._handle_response(response)

    def get_task(self, task_id: int) -> Dict[str, Any]:
        """
        Retrieves details for a specific task.

        Args:
            task_id: The ID of the task.

        Returns:
            A dictionary representing the task.
        """
        url = f"{self.api_base_url}/tasks/{task_id}"
        response = self._session.get(url)
        return self._handle_response(response)

    def stream_task_updates(self, task_id: int) -> Iterator[Dict[str, Any]]:
        """
        Streams task status updates and events via Server-Sent Events (SSE).
        This implementation manually parses the SSE stream for robustness.

        Args:
            task_id: The ID of the task to stream.

        Yields:
            Dictionaries representing task events or status updates.
        """
        url = f"{self.api_base_url}/tasks/{task_id}/stream"
        headers = self._session.headers.copy()
        headers["Accept"] = "text/event-stream"

        # Using a fresh request for streaming connection
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()  # Raise for non-2xx codes before streaming

        for line in response.iter_lines():
            if not line:
                # Empty lines are message separators in SSE.
                continue

            # SSE lines are expected to be utf-8 encoded.
            decoded_line = line.decode('utf-8')

            # We are only interested in lines that start with "data:".
            if decoded_line.startswith('data:'):
                # Remove the "data:" prefix and any leading whitespace.
                data_str = decoded_line[5:].strip()
                if data_str:
                    try:
                        # Parse the JSON string into a dictionary.
                        data = json.loads(data_str)
                        yield data
                    except json.JSONDecodeError:
                        # If parsing fails, we can log it and continue.
                        print(f"Warning: Could not decode JSON from SSE data: {data_str}")
                        continue

    def stop_task(self, task_id: int) -> Dict[str, Any]:
        """
        Requests to stop a running task.

        Args:
            task_id: The ID of the task to stop.

        Returns:
            A confirmation message.
        """
        url = f"{self.api_base_url}/tasks/{task_id}/stop"
        response = self._session.post(url)
        return self._handle_response(response)

    def delete_task(self, task_id: int) -> Dict[str, Any]:
        """
        Deletes a specific task and its associated data.

        Args:
            task_id: The ID of the task to delete.

        Returns:
            A confirmation message.
        """
        url = f"{self.api_base_url}/tasks/{task_id}"
        response = self._session.delete(url)
        return self._handle_response(response)

    # #################################################
    # Task File Management
    # #################################################

    def list_files_tree(self, task_id: int, path: str = ".") -> List[Dict[str, Any]]:
        """
        Lists files and folders in a task's working directory.

        Args:
            task_id: The ID of the task.
            path: The subdirectory path within the work_dir. Defaults to ".".

        Returns:
            A list of file system item dictionaries.
        """
        url = f"{self.api_base_url}/tasks/{task_id}/files/tree"
        response = self._session.get(url, params={"path": path})
        return self._handle_response(response)

    def get_file_content(self, task_id: int, path: str) -> requests.Response:
        """
        Retrieves the content of a file from a task's working directory.

        Args:
            task_id: The ID of the task.
            path: The relative path of the file within the work_dir.

        Returns:
            A `requests.Response` object with the raw file content.
        """
        url = f"{self.api_base_url}/tasks/{task_id}/files/content"
        response = self._session.get(url, params={"path": path}, stream=True)

        if not response.ok:
            self._handle_response(response) # Will raise an exception

        return response

    def upload_file(self, task_id: int, path: str, content: Union[bytes, str], content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Updates or creates a file in a task's working directory.

        Args:
            task_id: The ID of the task.
            path: The relative path of the file to create/update.
            content: The file content, either as bytes or a string.
            content_type: The MIME type of the content. If None, it's guessed.

        Returns:
            A confirmation message with file path and size.
        """
        url = f"{self.api_base_url}/tasks/{task_id}/files/content"

        if content_type is None:
            content_type, _ = mimetypes.guess_type(path)
            if content_type is None:
                content_type = 'application/octet-stream'

        headers = {'Content-Type': content_type}

        data = content.encode() if isinstance(content, str) else content
        response = self._session.put(url, params={"path": path}, data=data, headers=headers)
        return self._handle_response(response)

    def download_files_as_zip(self, task_id: int, paths: Optional[List[str]] = None) -> requests.Response:
        """
        Downloads files/folders from a task's workspace as a ZIP archive.

        Args:
            task_id: The ID of the task.
            paths: A list of relative paths to include in the zip.
                   If None or empty, the entire workspace is downloaded.

        Returns:
            A `requests.Response` object with the raw ZIP content.
        """
        url = f"{self.api_base_url}/tasks/{task_id}/files/download"
        json_payload = {"paths": paths if paths is not None else []}

        response = self._session.post(url, json=json_payload, stream=True)

        if not response.ok:
            self._handle_response(response) # Will raise an exception

        return response
