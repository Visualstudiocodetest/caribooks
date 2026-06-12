import pytest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from services.postfinance_service import (
    build_postfinance_address,
    build_postfinance_line_items,
    create_postfinance_iframe_session,
    create_postfinance_transaction,
    confirm_postfinance_transaction,
    parse_postfinance_webhook,
    get_postfinance_checkout_status,
    get_postfinance_payment_methods,
    get_postfinance_javascript_url,
    is_postfinance_success_status,
)

LINE_ITEMS = [{
    "uniqueId": "line-1",
    "name": "Book",
    "quantity": 1,
    "amountIncludingTax": 20.0,
    "type": "PRODUCT",
}]

BILLING = {
    "givenName": "Sam",
    "familyName": "Test",
    "emailAddress": "sam@example.com",
    "street": "Rue 1",
    "city": "Genève",
    "postcode": "1200",
    "country": "CH",
}


def _mock_tx(id=109472, state="PENDING", version=1, merchant_reference="42"):
    tx = MagicMock()
    tx.id = id
    tx.state = SimpleNamespace(value=state)
    tx.version = version
    tx.merchant_reference = merchant_reference
    return tx


@pytest.fixture
def pf_env():
    with patch("services.postfinance_service.POSTFINANCE_USER_ID", "171353"), \
         patch("services.postfinance_service.POSTFINANCE_AUTH_KEY", "test-auth-key"), \
         patch("services.postfinance_service.POSTFINANCE_SPACE_ID", "12345"):
        yield


@pytest.fixture
def mock_svc(pf_env):
    with patch("services.postfinance_service._transactions_service") as factory:
        svc = MagicMock()
        factory.return_value = svc
        yield svc


def test_create_postfinance_transaction(mock_svc):
    mock_svc.post_payment_transactions.return_value = _mock_tx()

    res = create_postfinance_transaction(
        line_items=LINE_ITEMS,
        billing_address=BILLING,
        success_url="http://return.url/success",
        failed_url="http://return.url/failed",
        merchant_reference="42",
    )

    assert res["id"] == 109472
    assert res["state"] == "PENDING"
    mock_svc.post_payment_transactions.assert_called_once()
    kwargs = mock_svc.post_payment_transactions.call_args.kwargs
    assert kwargs["space"] == 12345
    tx_create = kwargs["transaction_create"]
    assert tx_create.currency == "CHF"
    assert tx_create.success_url == "http://return.url/success"
    assert len(tx_create.line_items) == 1


def test_create_postfinance_iframe_session(mock_svc):
    mock_svc.post_payment_transactions.return_value = _mock_tx()

    method = MagicMock()
    method.to_dict.return_value = {"id": 510, "name": "Credit / Debit Card"}
    mock_svc.get_payment_transactions_id_payment_method_configurations.return_value = MagicMock(data=[method])

    mock_svc.get_payment_transactions_id_iframe_javascript_url.return_value = (
        "https://checkout.postfinance.ch/assets/payment/iframe-checkout-handler.js?x=1"
    )

    res = create_postfinance_iframe_session(
        line_items=LINE_ITEMS,
        billing_address=BILLING,
        success_url="http://return.url/success",
        failed_url="http://return.url/failed",
        merchant_reference="42",
    )

    assert res["transaction_id"] == "109472"
    assert res["javascript_url"].startswith("https://checkout.postfinance.ch")
    assert res["payment_methods"] == [{"id": 510, "name": "Credit / Debit Card"}]
    assert res["error"] is None
    mock_svc.get_payment_transactions_id_payment_method_configurations.assert_called_once_with(
        id=109472, space=12345, integration_mode="IFRAME"
    )
    mock_svc.get_payment_transactions_id_iframe_javascript_url.assert_called_once_with(
        id=109472, space=12345
    )


def test_create_postfinance_transaction_error(mock_svc):
    mock_svc.post_payment_transactions.side_effect = RuntimeError("boom")

    res = create_postfinance_transaction(
        line_items=LINE_ITEMS,
        billing_address=BILLING,
        success_url="http://return.url/success",
        failed_url="http://return.url/failed",
    )

    assert res["id"] is None
    assert res["state"] == "ERROR"
    assert "boom" in res["error"]


def test_confirm_postfinance_transaction(mock_svc):
    mock_svc.post_payment_transactions_id_confirm.return_value = _mock_tx(state="CONFIRMED", version=2)

    res = confirm_postfinance_transaction(
        transaction_id="109472",
        version=1,
        merchant_reference="42",
        line_items=LINE_ITEMS,
        billing_address=BILLING,
    )

    assert res["state"] == "CONFIRMED"
    assert res["version"] == 2
    mock_svc.post_payment_transactions_id_confirm.assert_called_once()
    kwargs = mock_svc.post_payment_transactions_id_confirm.call_args.kwargs
    assert kwargs["id"] == 109472
    assert kwargs["space"] == 12345
    assert kwargs["transaction_pending"].version == 1
    assert kwargs["transaction_pending"].merchant_reference == "42"


def test_get_postfinance_checkout_status(mock_svc):
    mock_svc.get_payment_transactions_id.return_value = _mock_tx(state="FULFILL")

    res = get_postfinance_checkout_status(link_id="109472")

    assert res["id"] == 109472
    assert res["state"] == "FULFILL"
    mock_svc.get_payment_transactions_id.assert_called_once_with(id=109472, space=12345)


def test_build_postfinance_line_items():
    ligne = SimpleNamespace(
        article=SimpleNamespace(sku="sku-1", titre="Mon Livre"),
        quantite=2,
        prix_unitaire_chf=10.5,
        id_ligne_commande=7,
        id_article=3,
    )
    items = build_postfinance_line_items([ligne], frais_port_chf=9.0, shipping_label="Poste", commande_id=42)

    assert len(items) == 2
    product, shipping = items
    assert product["uniqueId"] == "ligne-7"
    assert product["quantity"] == 2
    assert product["amountIncludingTax"] == 21.0
    assert product["type"] == "PRODUCT"
    assert product["shippingRequired"] is True
    assert shipping["uniqueId"] == "shipping-42"
    assert shipping["amountIncludingTax"] == 9.0
    assert shipping["type"] == "SHIPPING"
    assert shipping["shippingRequired"] is False


def test_build_postfinance_line_items_no_shipping_fee():
    ligne = SimpleNamespace(
        article=None, quantite=1, prix_unitaire_chf=5.0, id_ligne_commande=1, id_article=9,
    )
    items = build_postfinance_line_items([ligne], frais_port_chf=0, shipping_label="Retrait", commande_id=1)
    assert len(items) == 1
    assert items[0]["name"] == "Article 9"


def test_build_postfinance_address():
    user = SimpleNamespace(
        prenom="Jean", nom="Dupont", email="jean@example.com",
        billing_address_line1="Rue A 1", billing_city="Genève",
        billing_postal_code="1200", billing_country="Switzerland", billing_phone=None,
    )
    addr = build_postfinance_address(user)
    assert addr["givenName"] == "Jean"
    assert addr["country"] == "CH"  # >2 chars falls back to CH
    assert addr["phoneNumber"] == ""


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


def test_parse_postfinance_webhook_nested_entity():
    payload = {
        "entity": {"id": 99, "state": "COMPLETED", "merchantReference": "ORDER_9"},
    }
    parsed = parse_postfinance_webhook(payload)
    assert parsed["id"] == 99
    assert parsed["status"] == "COMPLETED"
    assert parsed["reference"] == "ORDER_9"


def test_is_postfinance_success_status():
    assert is_postfinance_success_status("AUTHORIZED")
    assert is_postfinance_success_status("FULFILL")
    assert not is_postfinance_success_status("FAILED")
    assert not is_postfinance_success_status(None)


def test_local_mode_without_credentials():
    with patch("services.postfinance_service.POSTFINANCE_USER_ID", None):
        methods = get_postfinance_payment_methods("local-1")
        js = get_postfinance_javascript_url("local-1")
        tx = create_postfinance_transaction(
            line_items=LINE_ITEMS,
            billing_address=BILLING,
            success_url="http://x/s",
            failed_url="http://x/f",
            merchant_reference="42",
        )
        assert methods.get("local") is True
        assert js.get("local") is True
        assert tx.get("local") is True
        assert str(tx["id"]).startswith("local-")
