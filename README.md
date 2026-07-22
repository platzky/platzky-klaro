# platzky-klaro

Injects a [Klaro](https://klaro.org/) consent banner and wires visitor choices into
[Google Consent Mode v2](https://developers.google.com/tag-platform/security/guides/consent).

Each configured `SERVICES` entry becomes a togglable switch in the banner. On accept/decline,
Klaro pushes a `consent update` event directly onto `window.dataLayer` for the listed
`consent_types` — this doesn't depend on `gtag`/GTM having loaded yet, so it works regardless
of plugin load order.

## Installation

```sh
pip install platzky_klaro
```

## Activation

Add the plugin to the `plugins` list in your Platzky database configuration.
The `name` must match the entry-point key declared in `pyproject.toml`:

```json
{
    "plugins": [
        {
            "name": "platzky_klaro",
            "config": {
                "SERVICES": [
                    {
                        "name": "google-consent",
                        "title": "Analytics",
                        "purposes": ["analytics"],
                        "consent_types": ["analytics_storage", "ad_storage"]
                    }
                ],
                "TRANSLATIONS": {
                    "en": {
                        "consentModal": { "title": "Cookie settings" },
                        "consentNotice": { "description": "We use cookies for analytics." },
                        "purposes": { "analytics": "Analytics" }
                    },
                    "pl": {
                        "consentModal": { "title": "Ustawienia cookies" },
                        "consentNotice": { "description": "Używamy cookies do analityki." },
                        "purposes": { "analytics": "Analityka" }
                    }
                },
                "allowed_page_sections": ["head"]
            }
        }
    ]
}
```

`allowed_page_sections` is required by Platzky's `HtmlInjectorPluginBase` capability gate —
without it the plugin loads but silently injects nothing. This plugin only targets `head`.

### Config fields

| Field                       | Required | Default                    | Notes                                                        |
|------------------------------|----------|-----------------------------|---------------------------------------------------------------|
| `SERVICES`                  | yes      | —                           | List of services; each needs `name`, `title`, `consent_types` |
| `SERVICES[].purposes`       | no       | `["analytics"]`             | Klaro purpose grouping                                        |
| `SERVICES[].default`        | no       | `false`                     | Pre-checked in the banner                                     |
| `SERVICES[].required`       | no       | `false`                     | User can't opt out                                             |
| `TRANSLATIONS`              | no       | `{}`                        | Klaro translation objects, keyed by language code             |
| `PURPOSES`                  | no       | `[]`                        | Klaro purpose descriptions shown in the modal                 |
| `KLARO_VERSION`             | no       | `"0.7"`                     | Pins the Klaro CDN script version                              |
| `COOKIE_NAME`                | no       | `"klaro"`                   |                                                                 |
| `COOKIE_EXPIRES_AFTER_DAYS` | no       | `365`                       |                                                                 |
| `DEFAULT`                   | no       | `false`                     | Whether services are opted-in by default globally             |
| `MUST_CONSENT`               | no       | `false`                     | Blocks the page behind the banner until a choice is made       |
| `HIDE_DECLINE_ALL`           | no       | `false`                     |                                                                 |
| `STYLING_THEME`              | no       | `["light", "top", "wide"]`  | Klaro CSS theme classes                                        |

## Development

This plugin extends [`HtmlInjectorPluginBase`](https://platzky.readthedocs.io/en/latest/plugins.html),
the same capability the `google-tag-manager` plugin uses. Two plugins can both inject into
`head` independently — Klaro doesn't need to load before or after the GTM plugin's
consent-default script, since it talks to `dataLayer` directly rather than the `gtag` helper.
