import re

import pandas as pd
from bs4 import Comment, Declaration, NavigableString, Tag


def check_months(df, fetch):
    months = int(fetch[:-1])
    min_date = min(df["date"].dropna())
    current_date = pd.Timestamp.now()
    days_diff = (current_date - min_date).days
    months_diff = days_diff // 30
    if months_diff > months:
        return True
    return False


def clean(tag):
    if isinstance(tag, Tag):
        tag = tag.text
    if tag is not None:
        tag = tag.strip()
    return tag


def is_relevant_text(element):
    """
    Determines if an element contains relevant article text while filtering out menus,
    headers, footers, and other non-content elements.
    """
    # Skip hidden elements and special tags
    if element.parent.name in {"style", "script", "head", "title", "meta", "[document]", "header", "footer", "nav", "sidebar", "aside"}:
        return False

    # Skip comments and declarations
    if isinstance(element, (Comment, Declaration)):
        return False

    # Check if element is in a common navigation/footer class/id
    parent_classes = []
    parent_ids = []
    parent = element.parent

    while parent and parent.name != "[document]":
        if parent.get("class"):
            parent_classes.extend(parent["class"])
        if parent.get("id"):
            parent_ids.append(parent["id"])
        parent = parent.parent

    # Common class/id patterns for non-article content
    skip_patterns = ["nav", "menu", "header", "footer", "sidebar", "comment", "widget", "banner", "ad-", "-ad", "social", "share", "related", "recommended", "popular", "trending"]

    for pattern in skip_patterns:
        if any(pattern in str(class_).lower() for class_ in parent_classes):
            return False
        if any(pattern in str(id_).lower() for id_ in parent_ids):
            return False

    # Process text content
    if isinstance(element, NavigableString):
        text = str(element).strip()

        # Skip empty or very short texts
        if not text or len(text) < 50:
            return False

        # Skip whitespace-only text
        if re.match(r"^\s*$", text):
            return False

        # Skip common menu/footer text patterns
        menu_patterns = [r"^about\s+us$", r"^contact(\s+us)?$", r"^privacy\s+policy$", r"^terms(\s+of\s+service)?$", r"^copyright\s+\d{4}$", r"^all\s+rights\s+reserved$"]

        if any(re.match(pattern, text.lower()) for pattern in menu_patterns):
            return False

    return True


def extract_article_text(soup):
    """
    Extracts the main article text content from a BeautifulSoup object while
    filtering out navigation, menus, headers, footers, and other non-content elements.

    Args:
        soup: BeautifulSoup object of the webpage

    Returns:
        str: Extracted article text with extraneous content removed
    """
    main_content = None
    for tag in ["article", "main", '[role="main"]']:
        main_content = soup.find(tag)
        if main_content:
            break

    # If no main content found, use whole body
    if not main_content:
        main_content = soup

    # Extract visible text from main content
    texts = main_content.findAll(string=True)
    relevant_texts = filter(is_relevant_text, texts)

    return " ".join(text.strip() for text in relevant_texts)
