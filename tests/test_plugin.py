import pytest
from platzky.plugin.plugin import ConfigPluginError

from platzky_klaro.plugin import PlatzkyKlaroPlugin

ANALYTICS_SERVICE = {
    "name": "google-consent",
    "title": "Analytics",
    "consent_types": ["analytics_storage", "ad_storage"],
}


def test_get_head_html_includes_klaro_library_script():
    """Test that the Klaro CDN script tag is emitted with the configured version."""
    plugin = PlatzkyKlaroPlugin({"SERVICES": [ANALYTICS_SERVICE], "KLARO_VERSION": "0.7"})

    head = plugin.get_head_html()

    assert "cdn.kiprotect.com/klaro/v0.7/klaro.js" in head
    assert 'data-config="klaroConfig"' in head


def test_get_head_html_wires_service_to_consent_update():
    """Test that a configured service's consent types appear in onAccept/onDecline."""
    plugin = PlatzkyKlaroPlugin({"SERVICES": [ANALYTICS_SERVICE]})

    head = plugin.get_head_html()

    assert "onAccept" in head
    assert "onDecline" in head
    assert "'consent', 'update'" in head
    assert '"analytics_storage":"granted"' in head or '"analytics_storage": "granted"' in head
    assert '"analytics_storage":"denied"' in head or '"analytics_storage": "denied"' in head


def test_get_head_html_does_not_call_gtag_directly():
    """Test that consent updates push to dataLayer directly, with no gtag() dependency."""
    plugin = PlatzkyKlaroPlugin({"SERVICES": [ANALYTICS_SERVICE]})

    head = plugin.get_head_html()

    assert "gtag(" not in head
    assert "dataLayer.push" in head


def test_get_head_html_includes_translations():
    """Test that configured translations are embedded in the Klaro config object."""
    plugin = PlatzkyKlaroPlugin(
        {
            "SERVICES": [ANALYTICS_SERVICE],
            "TRANSLATIONS": {"en": {"consentModal": {"title": "Cookie settings"}}},
        }
    )

    head = plugin.get_head_html()

    assert "Cookie settings" in head


def test_get_head_html_escapes_script_close_in_translations():
    """Test that a literal </script> in CMS-supplied text can't break out of the script tag."""
    plugin = PlatzkyKlaroPlugin(
        {
            "SERVICES": [ANALYTICS_SERVICE],
            "TRANSLATIONS": {"en": {"consentModal": {"title": "</script><script>evil()"}}},
        }
    )

    head = plugin.get_head_html()

    assert "</script><script>evil()" not in head


def test_accepted_page_sections():
    """Test that the plugin only declares head as an accepted section."""
    plugin = PlatzkyKlaroPlugin({"SERVICES": [ANALYTICS_SERVICE]})

    assert plugin.accepted_page_sections == frozenset({"head"})


def test_rejects_empty_services():
    """Test that plugin raises a config error when SERVICES is missing or empty."""
    with pytest.raises(ConfigPluginError):
        PlatzkyKlaroPlugin({"SERVICES": []})


def test_rejects_service_without_consent_types():
    """Test that a service with no consent_types fails validation."""
    with pytest.raises(ConfigPluginError):
        PlatzkyKlaroPlugin({"SERVICES": [{"name": "x", "title": "X", "consent_types": []}]})


def test_service_default_and_required_flags_rendered():
    """Test that per-service default/required flags are reflected in the rendered config."""
    plugin = PlatzkyKlaroPlugin(
        {
            "SERVICES": [
                {**ANALYTICS_SERVICE, "default": True, "required": True},
            ]
        }
    )

    head = plugin.get_head_html()

    assert "default:true" in head or "default: true" in head
    assert "required:true" in head or "required: true" in head
