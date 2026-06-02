import pytest
import base64
import json
from unittest.mock import patch, MagicMock

from services.postfinance_service import (
    _get_auth_header,
    create_postfinance_checkout,
    parse_postfinance_webhook,
    get_postfinance_checkout_status,
)

@pytest.fixture
def pf_env():
    with patch("services.postfinance_service.POSTFINANCE_USER_ID", "test-user-id"), \
         patch("services.postfinance_service.POSTFINANCE_AUTH_KEY", "test-auth-key"), \
         patch("services.postfinance_service.POSTFINANCE_SPACE_ID", "test-space"):
        yield

def test_get_auth_header(pf_env):
    header = _get_auth_header("/api/v2.0/payment/links", "POST")
    assert "Authorization" in header
    assert header["Authorization"].startswith("Bearer ")
    
    token = header["Authorization"].split(" ")[1]
    parts = token.split(".")
    assert len(parts) == 3
    
    # decode JWT payload
    # Pad base64 appropriately
    payload_b64 = parts[1]
    payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
    
    assert payload["sub"] == "test-user-id"
    assert payload["requestPath"] == "/api/v2.0/payment/links"
    assert payload["requestMethod"] == "POST"

@patch("services.postfinance_service.httpx.Client")
def test_create_postfinance_checkout(mock_client_class, pf_env):
    mock_client = mock_client_class.return_value.__enter__.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "pf-link-123", "linkUrl": "https://pay.example.com"}
    mock_response.raise_for_status.return_value = None
    mock_client.post.return_value = mock_response

    res = create_postfinance_checkout(
        amount_chf=100.0,
        reference="ORDER_123",
        return_url="http://return.url",
        cancel_url="http://cancel.url",
        description="Test Order"
    )
    
    assert res["id"] == "pf-link-123"
    assert res["redirect_url"] == "https://pay.example.com"
    assert res["status"] == "CREATED"
    
    mock_client.post.assert_called_once()

def test_parse_postfinance_webhook():
    payload = {
        "id": "chk-123",
        "status": "AUTHORIZED",
        "merchantOrderId": "ORDER_123"
    }
    parsed = parse_postfinance_webhook(payload)
    assert parsed["id"] == "chk-123"
    assert parsed["status"] == "AUTHORIZED"
    assert parsed["reference"] == "ORDER_123"

@patch("services.postfinance_service.httpx.Client")
def test_get_postfinance_checkout_status(mock_client_class, pf_env):
    mock_client = mock_client_class.return_value.__enter__.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "pf-link-123", "status": "COMPLETED"}
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response

    res = get_postfinance_checkout_status(link_id="pf-link-123")
    
    assert res["id"] == "pf-link-123"
    assert res["status"] == "COMPLETED"
    mock_client.get.assert_called_once()
