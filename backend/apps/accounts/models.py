from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"

    ROLE_CHOICES = (
        (ROLE_STUDENT, "Student"),
        (ROLE_TEACHER, "Teacher"),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        help_text="Role determining user permissions in Quest Study",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_teacher(self):
        return self.role == self.ROLE_TEACHER

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT

    def __str__(self):
        return f"{self.username} ({self.role})"
