import pytest
import base64
import json
from unittest.mock import patch, MagicMock

from services.postfinance_service import (
    _get_auth_header,
    create_postfinance_iframe_session,
    create_postfinance_transaction,
    confirm_postfinance_transaction,
    parse_postfinance_webhook,
    get_postfinance_checkout_status,
    get_postfinance_payment_methods,
    get_postfinance_javascript_url,
    is_postfinance_success_status,
)


@pytest.fixture
def pf_env():
    with patch("services.postfinance_service.POSTFINANCE_USER_ID", "test-user-id"), \
         patch("services.postfinance_service.POSTFINANCE_AUTH_KEY", "test-auth-key"), \
         patch("services.postfinance_service.POSTFINANCE_SPACE_ID", "test-space"):
        yield


def test_get_auth_header(pf_env):
    header = _get_auth_header("/api/v2.0/payment/transactions", "POST")
    assert "Authorization" in header
    assert header["Authorization"].startswith("Bearer ")

    token = header["Authorization"].split(" ")[1]
    parts = token.split(".")
    assert len(parts) == 3

    payload_b64 = parts[1]
    payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))

    assert payload["sub"] == "test-user-id"
    assert payload["requestPath"] == "/api/v2.0/payment/transactions"
    assert payload["requestMethod"] == "POST"


@patch("services.postfinance_service.httpx.Client")
def test_create_postfinance_transaction(mock_client_class, pf_env):
    mock_client = mock_client_class.return_value.__enter__.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 109472, "state": "PENDING", "version": 1}
    mock_response.raise_for_status.return_value = None
    mock_client.post.return_value = mock_response

    res = create_postfinance_transaction(
        line_items=[{
            "uniqueId": "line-1",
            "name": "Book",
            "quantity": "1",
            "amountIncludingTax": 20.0,
            "type": "PRODUCT",
        }],
        billing_address={
            "givenName": "Sam",
            "familyName": "Test",
            "emailAddress": "sam@example.com",
            "street": "Rue 1",
            "city": "Genève",
            "postcode": "1200",
            "country": "CH",
        },
        success_url="http://return.url/success",
        failed_url="http://return.url/failed",
        merchant_reference="42",
    )

    assert res["id"] == 109472
    assert res["state"] == "PENDING"
    mock_client.post.assert_called_once()


@patch("services.postfinance_service.httpx.Client")
def test_create_postfinance_iframe_session(mock_client_class, pf_env):
    mock_client = mock_client_class.return_value.__enter__.return_value

    create_resp = MagicMock()
    create_resp.json.return_value = {"id": 109472, "state": "PENDING", "version": 1}
    create_resp.raise_for_status.return_value = None

    methods_resp = MagicMock()
    methods_resp.json.return_value = {
        "data": [{"id": 510, "name": "Credit / Debit Card"}],
        "hasMore": False,
    }
    methods_resp.raise_for_status.return_value = None

    js_resp = MagicMock()
    js_resp.json.return_value = "https://checkout.postfinance.ch/s/396/resource/javascript/iframe.js"
    js_resp.raise_for_status.return_value = None

    mock_client.post.return_value = create_resp
    mock_client.get.side_effect = [methods_resp, js_resp]

    res = create_postfinance_iframe_session(
        line_items=[{
            "uniqueId": "line-1",
            "name": "Book",
            "quantity": "1",
            "amountIncludingTax": 20.0,
            "type": "PRODUCT",
        }],
        billing_address={
            "givenName": "Sam",
            "familyName": "Test",
            "emailAddress": "sam@example.com",
            "street": "Rue 1",
            "city": "Genève",
            "postcode": "1200",
            "country": "CH",
        },
        success_url="http://return.url/success",
        failed_url="http://return.url/failed",
        merchant_reference="42",
    )

    assert res["transaction_id"] == "109472"
    assert res["javascript_url"].startswith("https://checkout.postfinance.ch")
    assert len(res["payment_methods"]) == 1


@patch("services.postfinance_service.httpx.Client")
def test_confirm_postfinance_transaction(mock_client_class, pf_env):
    mock_client = mock_client_class.return_value.__enter__.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 109472, "state": "CONFIRMED", "version": 2}
    mock_response.raise_for_status.return_value = None
    mock_client.post.return_value = mock_response

    res = confirm_postfinance_transaction(
        transaction_id="109472",
        version=1,
        merchant_reference="42",
        line_items=[{
            "uniqueId": "line-1",
            "name": "Book",
            "quantity": "1",
            "amountIncludingTax": 20.0,
            "type": "PRODUCT",
        }],
        billing_address={
            "givenName": "Sam",
            "familyName": "Test",
            "emailAddress": "sam@example.com",
            "street": "Rue 1",
            "city": "Genève",
            "postcode": "1200",
            "country": "CH",
        },
    )

    assert res["state"] == "CONFIRMED"
    mock_client.post.assert_called_once()


def test_parse_postfinance_webhook():
    payload = {
        "id": "chk-123",
        "state": "AUTHORIZED",
        "merchantReference": "ORDER_123",
    }
    parsed = parse_postfinance_webhook(payload)
    assert parsed["id"] == "chk-123"
    assert parsed["status"] == "AUTHORIZED"
    assert parsed["reference"] == "ORDER_123"


@patch("services.postfinance_service.httpx.Client")
def test_get_postfinance_checkout_status(mock_client_class, pf_env):
    mock_client = mock_client_class.return_value.__enter__.return_value
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 109472, "state": "FULFILL"}
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response

    res = get_postfinance_checkout_status(link_id="109472")

    assert res["id"] == 109472
    assert res["state"] == "FULFILL"
    mock_client.get.assert_called_once()


def test_is_postfinance_success_status():
    assert is_postfinance_success_status("AUTHORIZED")
    assert is_postfinance_success_status("FULFILL")
    assert not is_postfinance_success_status("FAILED")


def test_local_mode_without_credentials():
    with patch("services.postfinance_service.POSTFINANCE_USER_ID", None):
        methods = get_postfinance_payment_methods("local-1")
        js = get_postfinance_javascript_url("local-1")
        assert methods.get("local") is True
        assert js.get("local") is True
