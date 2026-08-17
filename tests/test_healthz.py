import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_healthz_returns_200(client):
    response = client.get(reverse("healthz"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
