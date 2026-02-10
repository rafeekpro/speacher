"""Tests for project management API endpoints"""

import uuid
from typing import Dict, Tuple

import pytest
from fastapi.testclient import TestClient


class TestProjectManagementAPI:
    """Test suite for project management endpoints"""

    @pytest.fixture
    def auth_client_with_user(self, client: TestClient) -> Tuple[TestClient, Dict[str, str], str]:
        """Create authenticated client with user ID"""
        # Generate unique email for each test
        unique_id = str(uuid.uuid4())[:8]
        email = f"project_user_{unique_id}@example.com"

        # Register user
        register_data = {"email": email, "password": "SecurePass123!", "full_name": "Project User"}
        reg_response = client.post("/api/auth/register", json=register_data)
        assert reg_response.status_code == 201, f"Registration failed: {reg_response.json()}"

        user_data = reg_response.json()
        assert "id" in user_data, f"No id in registration response: {user_data}"
        user_id = user_data["id"]

        # Login
        login_data = {"email": email, "password": "SecurePass123!"}
        login_response = client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200, f"Login failed: {login_response.json()}"

        tokens = login_response.json()
        assert "access_token" in tokens, f"No access_token in response: {tokens}"

        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        return client, headers, user_id

    def test_create_project(self, auth_client_with_user):
        """Test creating a new project"""
        client, headers, _ = auth_client_with_user

        project_data = {
            "name": "Test Project",
            "description": "A test project for speech processing",
            "tags": ["test", "development", "speech"],
        }

        response = client.post("/api/projects", json=project_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project for speech processing"
        assert set(data["tags"]) == {"test", "development", "speech"}
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["status"] == "active"

    def test_create_project_without_description(self, auth_client_with_user):
        """Test creating project without description"""
        client, headers, _ = auth_client_with_user

        project_data = {"name": "Minimal Project", "tags": []}

        response = client.post("/api/projects", json=project_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Project"
        assert data["description"] is None
        assert data["tags"] == []

    def test_create_project_invalid_name(self, auth_client_with_user):
        """Test creating project with invalid name"""
        client, headers, _ = auth_client_with_user

        project_data = {"name": "", "description": "Invalid project"}  # Empty name

        response = client.post("/api/projects", json=project_data, headers=headers)

        assert response.status_code == 422
        data = response.json()
        assert "name" in str(data).lower()

    def test_list_user_projects(self, auth_client_with_user):
        """Test listing user's projects"""
        client, headers, _ = auth_client_with_user

        # Create multiple projects
        for i in range(5):
            project_data = {"name": f"Project {i+1}", "description": f"Description {i+1}", "tags": [f"tag{i+1}"]}
            client.post("/api/projects", json=project_data, headers=headers)

        # List projects
        response = client.get("/api/projects", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert data["total"] >= 5
        assert len(data["projects"]) >= 5

        # Check pagination
        response = client.get("/api/projects?page=1&per_page=2", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) <= 2

    def test_get_project_details(self, auth_client_with_user):
        """Test getting project details"""
        client, headers, _ = auth_client_with_user

        # Create project
        project_data = {"name": "Detail Project", "description": "Project with details", "tags": ["detail", "test"]}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Get project details
        response = client.get(f"/api/projects/{project_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Detail Project"
        assert data["description"] == "Project with details"
        assert set(data["tags"]) == {"detail", "test"}
        assert "recording_count" in data

    def test_get_nonexistent_project(self, auth_client_with_user):
        """Test getting non-existent project"""
        client, headers, _ = auth_client_with_user

        response = client.get("/api/projects/nonexistent-id", headers=headers)

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_update_project(self, auth_client_with_user):
        """Test updating project"""
        client, headers, _ = auth_client_with_user

        # Create project
        project_data = {"name": "Original Name", "description": "Original description", "tags": ["original"]}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Update project
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "tags": ["updated", "modified"],
            "status": "active",
        }
        response = client.put(f"/api/projects/{project_id}", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert set(data["tags"]) == {"updated", "modified"}

    def test_partial_update_project(self, auth_client_with_user):
        """Test partial project update"""
        client, headers, _ = auth_client_with_user

        # Create project
        project_data = {"name": "Partial Update", "description": "Original description", "tags": ["tag1", "tag2"]}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Partial update (only name)
        update_data = {"name": "New Name Only"}
        response = client.put(f"/api/projects/{project_id}", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name Only"
        assert data["description"] == "Original description"  # Unchanged
        assert set(data["tags"]) == {"tag1", "tag2"}  # Unchanged

    def test_archive_project(self, auth_client_with_user):
        """Test archiving project"""
        client, headers, _ = auth_client_with_user

        # Create project
        project_data = {"name": "Project to Archive"}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Archive project
        update_data = {"status": "archived"}
        response = client.put(f"/api/projects/{project_id}", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"

    def test_delete_project(self, auth_client_with_user):
        """Test deleting project"""
        client, headers, _ = auth_client_with_user

        # Create project
        project_data = {"name": "Project to Delete"}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Delete project
        response = client.delete(f"/api/projects/{project_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

        # Verify deletion
        get_response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert get_response.status_code == 404

    def test_project_recordings(self, auth_client_with_user):
        """Test getting project recordings"""
        client, headers, _ = auth_client_with_user

        # Create project
        project_data = {"name": "Recording Project"}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Add recordings to project
        for i in range(3):
            recording_data = {"filename": f"recording_{i+1}.wav", "duration": 60.5 + i, "file_size": 1024 * (i + 1)}
            client.post(f"/api/projects/{project_id}/recordings", json=recording_data, headers=headers)

        # Get project recordings
        response = client.get(f"/api/projects/{project_id}/recordings", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "recordings" in data
        assert len(data["recordings"]) >= 3
        assert data["total"] >= 3

    def test_add_recording_to_project(self, auth_client_with_user):
        """Test adding recording to project"""
        client, headers, user_id = auth_client_with_user

        # Create project
        project_data = {"name": "Audio Project"}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Add recording
        recording_data = {"filename": "speech_sample.wav", "duration": 120.5, "file_size": 2048576}
        response = client.post(f"/api/projects/{project_id}/recordings", json=recording_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "speech_sample.wav"
        assert data["duration"] == 120.5
        assert data["file_size"] == 2048576
        assert data["project_id"] == project_id
        assert data["user_id"] == user_id
        assert data["status"] == "pending"

    def test_project_tags(self, auth_client_with_user):
        """Test managing project tags"""
        client, headers, _ = auth_client_with_user

        # Create project with tags
        project_data = {"name": "Tagged Project", "tags": ["tag1", "tag2", "tag3"]}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Get project tags
        response = client.get(f"/api/projects/{project_id}/tags", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert len(data["tags"]) == 3

        # Add new tags
        new_tags = {"tags": ["tag4", "tag5"]}
        response = client.post(f"/api/projects/{project_id}/tags", json=new_tags, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["tags"]) == 5

    def test_remove_project_tags(self, auth_client_with_user):
        """Test removing project tags"""
        client, headers, _ = auth_client_with_user

        # Create project with tags
        project_data = {"name": "Remove Tags Project", "tags": ["keep1", "remove1", "keep2", "remove2"]}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Remove specific tags
        remove_tags = {"tags": ["remove1", "remove2"]}
        response = client.request("DELETE", f"/api/projects/{project_id}/tags", json=remove_tags, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert set(data["tags"]) == {"keep1", "keep2"}

    def test_search_projects(self, auth_client_with_user):
        """Test searching projects"""
        client, headers, _ = auth_client_with_user

        # Create projects with different names and tags
        projects = [
            {"name": "Speech Recognition", "tags": ["ai", "speech"]},
            {"name": "Text Analysis", "tags": ["nlp", "text"]},
            {"name": "Speech Synthesis", "tags": ["ai", "speech", "tts"]},
        ]

        for project in projects:
            client.post("/api/projects", json=project, headers=headers)

        # Search by name
        response = client.get("/api/projects?search=speech", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

        # Search by tag
        response = client.get("/api/projects?tag=speech", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

        # Search by multiple tags
        response = client.get("/api/projects?tag=ai&tag=speech", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert all("ai" in p["tags"] and "speech" in p["tags"] for p in data["projects"])

    def test_project_statistics(self, auth_client_with_user):
        """Test getting project statistics"""
        client, headers, _ = auth_client_with_user

        # Create project
        project_data = {"name": "Stats Project"}
        create_response = client.post("/api/projects", json=project_data, headers=headers)
        project_id = create_response.json()["id"]

        # Add some recordings
        for i in range(5):
            recording_data = {"filename": f"rec_{i}.wav", "duration": 30 + i * 10, "file_size": 1024 * (i + 1)}
            client.post(f"/api/projects/{project_id}/recordings", json=recording_data, headers=headers)

        # Get statistics
        response = client.get(f"/api/projects/{project_id}/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_recordings" in data
        assert "total_duration" in data
        assert "total_size" in data
        assert "average_duration" in data
        assert data["total_recordings"] == 5

    def test_project_access_control(self, client: TestClient):
        """Test project access control between users"""
        # Create two users
        users = []
        for i in range(2):
            register_data = {
                "email": f"user{i+1}@example.com",
                "password": "SecurePass123!",
                "full_name": f"User {i+1}",
            }
            client.post("/api/auth/register", json=register_data)

            login_data = {"email": f"user{i+1}@example.com", "password": "SecurePass123!"}
            login_response = client.post("/api/auth/login", json=login_data)
            headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
            users.append(headers)

        # User 1 creates project
        project_data = {"name": "Private Project"}
        create_response = client.post("/api/projects", json=project_data, headers=users[0])
        project_id = create_response.json()["id"]

        # User 2 tries to access User 1's project
        response = client.get(f"/api/projects/{project_id}", headers=users[1])
        assert response.status_code == 403

        # User 2 tries to update User 1's project
        update_data = {"name": "Hacked Project"}
        response = client.put(f"/api/projects/{project_id}", json=update_data, headers=users[1])
        assert response.status_code == 403

        # User 2 tries to delete User 1's project
        response = client.delete(f"/api/projects/{project_id}", headers=users[1])
        assert response.status_code == 403
