from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import User


class AccountsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_student(self):
        url = reverse("auth-register")
        data = {
            "username": "student1",
            "email": "student1@example.com",
            "password": "password123",
            "role": "student",
            "first_name": "Test",
            "last_name": "Student",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["role"], "student")

        user = User.objects.get(username="student1")
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_teacher)
        # Streak automatically initialized
        self.assertTrue(hasattr(user, "streak"))

    def test_register_teacher(self):
        url = reverse("auth-register")
        data = {
            "username": "teacher1",
            "email": "teacher1@example.com",
            "password": "password123",
            "role": "teacher",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], "teacher")

    def test_login_and_me(self):
        user = User.objects.create_user(
            username="user1", email="u1@example.com", password="password123", role="student"
        )
        login_url = reverse("auth-login")
        response = self.client.post(
            login_url, {"username": "user1", "password": "password123"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data["token"]

        # Call /api/auth/me/ with token
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        me_url = reverse("auth-me")
        me_response = self.client.get(me_url)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["username"], "user1")
