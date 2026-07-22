"""Platzky Klaro plugin — injects a Klaro consent banner wired to Google Consent Mode."""

import json
from collections.abc import Sequence
from typing import Any, Literal

from platzky.plugin.html_injector import HtmlInjectorPluginBase
from platzky.plugin.plugin import ConfigPluginError
from pydantic import BaseModel, Field, ValidationError

ConsentType = Literal[
    "ad_storage",
    "analytics_storage",
    "ad_user_data",
    "ad_personalization",
    "functionality_storage",
    "personalization_storage",
    "security_storage",
]
ConsentStatus = Literal["granted", "denied"]


class KlaroService(BaseModel):
    """A single Klaro service: a togglable consent switch mapped to Consent Mode types."""

    name: str
    title: str
    purposes: list[str] = Field(default_factory=lambda: ["analytics"])
    consent_types: list[ConsentType] = Field(min_length=1)
    default: bool = False
    required: bool = False


class _Config(BaseModel):
    """Internal config model for the Klaro plugin."""

    SERVICES: list[KlaroService] = Field(min_length=1)
    TRANSLATIONS: dict[str, dict[str, Any]] = Field(default_factory=dict)
    PURPOSES: list[dict[str, Any]] = Field(default_factory=lambda: [])
    KLARO_VERSION: str = "0.7"
    COOKIE_NAME: str = "klaro"
    COOKIE_EXPIRES_AFTER_DAYS: int = 365
    DEFAULT: bool = False
    MUST_CONSENT: bool = False
    HIDE_DECLINE_ALL: bool = False
    STYLING_THEME: list[str] = Field(default_factory=lambda: ["light", "top", "wide"])


def _safe_json(value: Any) -> str:
    """Serialize a value for embedding in an inline ``<script>`` tag.

    Escapes ``</`` so CMS-supplied text (translations, titles) can never contain a
    literal ``</script>`` sequence that would break out of the script context.
    """
    return json.dumps(value).replace("</", "<\\/")


def _consent_update_js(consent_types: Sequence[str], status: ConsentStatus) -> str:
    """Build a JS function that pushes a Consent Mode update for the given types.

    Pushes directly onto ``dataLayer`` (rather than calling ``gtag(...)``) so this
    works whether or not another script has already defined the ``gtag`` helper —
    there's no load-order dependency on the GTM plugin's consent-default script.
    """
    payload = _safe_json({consent_type: status for consent_type in consent_types})
    return (
        "function(){"
        "window.dataLayer = window.dataLayer || [];"
        f"window.dataLayer.push(['consent', 'update', {payload}]);"
        "}"
    )


def _service_js(service: KlaroService) -> str:
    """Render a single Klaro service as a JavaScript object literal."""
    return (
        "{"
        f"name: {_safe_json(service.name)},"
        f"title: {_safe_json(service.title)},"
        f"purposes: {_safe_json(service.purposes)},"
        f"default: {_safe_json(service.default)},"
        f"required: {_safe_json(service.required)},"
        f"onAccept: {_consent_update_js(service.consent_types, 'granted')},"
        f"onDecline: {_consent_update_js(service.consent_types, 'denied')}"
        "}"
    )


class PlatzkyKlaroPlugin(HtmlInjectorPluginBase):
    """Platzky plugin that injects a Klaro consent banner wired to Google Consent Mode."""

    accepted_page_sections = frozenset({"head"})

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        try:
            self._config = _Config.model_validate(config)
        except ValidationError as e:
            raise ConfigPluginError(str(e)) from e

    def get_head_html(self) -> str:
        """Return the Klaro config script and library tag for injection into ``<head>``."""
        cfg = self._config
        services_js = ",".join(_service_js(service) for service in cfg.SERVICES)
        config_object = (
            "{"
            "version: 1,"
            f"cookieName: {_safe_json(cfg.COOKIE_NAME)},"
            f"cookieExpiresAfterDays: {_safe_json(cfg.COOKIE_EXPIRES_AFTER_DAYS)},"
            f"default: {_safe_json(cfg.DEFAULT)},"
            f"mustConsent: {_safe_json(cfg.MUST_CONSENT)},"
            f"hideDeclineAll: {_safe_json(cfg.HIDE_DECLINE_ALL)},"
            f"styling: {{theme: {_safe_json(cfg.STYLING_THEME)}}},"
            f"translations: {_safe_json(cfg.TRANSLATIONS)},"
            f"purposes: {_safe_json(cfg.PURPOSES)},"
            f"services: [{services_js}]"
            "}"
        )
        klaro_src = f"https://cdn.kiprotect.com/klaro/v{cfg.KLARO_VERSION}/klaro.js"
        return (
            "<!-- Klaro consent manager -->\n"
            f"<script>window.klaroConfig = {config_object};</script>\n"
            f'<script defer type="application/javascript" src="{klaro_src}" '
            'data-config="klaroConfig"></script>\n'
            "<!-- End Klaro consent manager -->\n"
        )
