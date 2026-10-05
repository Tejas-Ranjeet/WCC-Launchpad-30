import os
import re
from html.parser import HTMLParser
import pytest

INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "web_ui", "index.html")

class DOMCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.metas = []
        self.links = []
        self.buttons = []
        self.images = []
        self.i18n_elements = []
        self.onclicks = []
        self.ids = {}

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        self.tags.append((tag, attr_dict))
        if "id" in attr_dict:
            self.ids[attr_dict["id"]] = (tag, attr_dict)
        if tag == "meta":
            self.metas.append(attr_dict)
        elif tag == "a":
            self.links.append(attr_dict)
        elif tag == "button":
            self.buttons.append(attr_dict)
        elif tag == "img":
            self.images.append(attr_dict)
        if "data-i18n" in attr_dict:
            self.i18n_elements.append(attr_dict["data-i18n"])
        if "onclick" in attr_dict:
            self.onclicks.append(attr_dict["onclick"])

@pytest.fixture(scope="module")
def html_content():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return f.read()

@pytest.fixture(scope="module")
def dom(html_content):
    parser = DOMCollector()
    parser.feed(html_content)
    return parser

def test_viewport_meta_tag(dom):
    """Verify viewport is configured for responsive scaling at 375px and desktop."""
    viewport = next((m for m in dom.metas if m.get("name") == "viewport"), None)
    assert viewport is not None, "Missing viewport meta tag"
    content = viewport.get("content", "")
    assert "width=device-width" in content
    assert "initial-scale=1.0" in content

def test_emergency_sos_modal_and_dial_links(dom, html_content):
    """Verify emergency SOS modal contains dialable tel: links for 112 and 108."""
    assert "emergency-sos-modal" in dom.ids, "Emergency SOS modal missing from DOM"
    
    tel_links = [l.get("href") for l in dom.links if l.get("href", "").startswith("tel:")]
    assert "tel:112" in tel_links, "tel:112 dial link missing in emergency modal"
    assert "tel:108" in tel_links, "tel:108 dial link missing in emergency modal"

def test_medical_disclaimers_present(html_content):
    """Verify statutory clinical disclaimer is prominently displayed."""
    disclaimer_terms = [
        "not a cleared medical device",
        "not a medical device",
        "informational and lifestyle planning purposes only",
        "112 / 108"
    ]
    html_lower = html_content.lower()
    for term in disclaimer_terms:
        assert term in html_lower, f"Required disclaimer term '{term}' missing from index.html"

def test_i18n_translation_keys_coverage(html_content, dom):
    """Verify every element with data-i18n has valid English and Hindi dictionary entries."""
    en_dict_match = re.search(r"airguardTranslations\s*=\s*\{[\s\S]*?en:\s*\{([\s\S]*?)\},[\s\S]*?hi:\s*\{([\s\S]*?)\}", html_content)
    assert en_dict_match is not None, "Could not find airguardTranslations in script"

    en_keys = set(re.findall(r"([a-zA-Z0-9_]+)\s*:\s*[\"']", en_dict_match.group(1)))
    hi_keys = set(re.findall(r"([a-zA-Z0-9_]+)\s*:\s*[\"']", en_dict_match.group(2)))

    for key in dom.i18n_elements:
        assert key in en_keys, f"DOM data-i18n key '{key}' missing from English translation dictionary"
        assert key in hi_keys, f"DOM data-i18n key '{key}' missing from Hindi translation dictionary"

def test_interactive_onclick_handlers_defined(html_content, dom):
    """Verify all inline onclick handlers refer to defined functions."""
    for onclick_val in dom.onclicks:
        match = re.match(r"([a-zA-Z0-9_]+)\s*\(", onclick_val)
        if match:
            func_name = match.group(1)
            if func_name in ["alert", "confirm", "prompt"]:
                continue
            assert f"function {func_name}" in html_content or f"{func_name} =" in html_content or f"{func_name}=" in html_content, (
                f"Handler function '{func_name}' referenced in onclick is not defined in script"
            )

def test_responsive_media_queries_present(html_content):
    """Verify CSS includes mobile media queries down to 375px/768px."""
    assert "@media" in html_content, "Missing @media queries for responsive layout"
    assert "max-width" in html_content, "Missing max-width responsive rules"

def test_accessibility_basics(dom):
    """Verify accessibility essentials: images have alt tags, buttons have text or aria labels."""
    for img in dom.images:
        assert "alt" in img, f"Image {img.get('src', 'unknown')} missing alt attribute"

    for btn in dom.buttons:
        has_aria = "aria-label" in btn
        has_title = "title" in btn
        has_id = "id" in btn
        has_class = "class" in btn
        assert has_aria or has_title or has_id or has_class, f"Button has no identifying attributes: {btn}"
