import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    "url_name,anchors",
    [
        ("accounts:login_admin", ["feature-2fa", "feature-biometric", "feature-hardware-key"]),
        ("accounts:login_empleado", ["feature-verification", "feature-employee-biometric"]),
    ],
)
def test_login_page_has_tour_buttons_and_anchors(client, url_name, anchors):
    response = client.get(reverse(url_name))
    content = response.content.decode()
    assert "Ver Premium" in content
    assert "Ver Gold" in content
    assert "feature-tour.js" in content
    for anchor_id in anchors:
        assert f'id="{anchor_id}"' in content
