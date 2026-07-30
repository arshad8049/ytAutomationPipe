"""Resolve a persona name to a public-domain headshot URL via the Wikipedia REST API.

Wikipedia's /page/summary endpoint returns a thumbnail field for most notable historical
figures. The thumbnail URL points to Wikimedia Commons and is publicly accessible, which
means D-ID can fetch it directly as the source_url for a /talks job.
"""
import requests


_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{name}"
_HEADERS = {"User-Agent": "ZenoShorts/1.0 (automation; contact via GitHub)"}


def get_headshot_url(person_name: str) -> str | None:
    """Return a Wikimedia thumbnail URL for person_name, or None if not found."""
    if not person_name:
        return None
    encoded = requests.utils.quote(person_name.replace(" ", "_"), safe="")
    try:
        resp = requests.get(
            _SUMMARY_API.format(name=encoded),
            headers=_HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("thumbnail", {}).get("source")
    except requests.RequestException:
        pass
    return None
