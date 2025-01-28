import asyncio
import json
import os
import random
from asyncio import Semaphore

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


def create_args(headless=True, text_only=True):
    args = [
        "--disable-gpu",
        "--disable-gpu-compositing",
        "--disable-software-rasterizer",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-infobars",
        "--window-position=0,0",
        "--ignore-certificate-errors",
        "--ignore-certificate-errors-spki-list",
        "--disable-blink-features=AutomationControlled",
        "--window-position=400,0",
        "--disable-renderer-backgrounding",
        "--disable-ipc-flooding-protection",
        "--force-color-profile=srgb",
        "--mute-audio",
        "--disable-background-timer-throttling",
        "--disable-site-isolation-trials",  # Reduces resource usage
        "--disable-extensions",  # Prevents loading extensions
        "--disable-background-networking",  # Reduces network overhead
        "--disable-client-side-phishing-detection",  # Speeds up page loads
        "--disable-default-apps",  # Prevents loading of default Chrome apps
        "--disable-sync",  # Disables background synchronization
        "--enable-automation",  # Ensures automation optimizations
        "--metrics-recording-only",  # Reduces resource consumption
        "--no-proxy-server",  # Avoids proxy overhead if not needed
        "--js-flags=--noexpose_wasm,--max_old_space_size=256",  # Limit JS memory usage
        "--log-level=3",  # Suppress browser logs
    ]

    if text_only:
        args.extend(
            [
                "--blink-settings=imagesEnabled=false",
                "--disable-remote-fonts",
                "--disable-images",
                "--disable-javascript",
                "--disable-software-rasterizer",
                "--disable-dev-shm-usage",
            ]
        )
    args = {"headless": headless, "args": args, "downloads_path": os.path.join(os.getcwd(), "downloads")}
    return args


class Scroller:
    def __init__(self, scroll_config=None):
        if not scroll_config:
            self.scroll_config = {"scroll_steps": 2, "scroll_pause": 0.5}
        else:
            self.scroll_config = scroll_config

    async def scroll(self, page):
        total_height = await page.evaluate("document.body.scrollHeight")
        for step in range(self.scroll_config.get("scroll_steps", 3)):
            await page.evaluate(f"window.scrollTo(0, {step * total_height // self.scroll_config.get('scroll_steps', 3)})")
            await asyncio.sleep(self.scroll_config.get("scroll_pause", 1.5))

        # Scroll to bottom to ensure all content is loaded
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(self.scroll_config.get("scroll_pause", 1.5))

    async def content_scroll(self, page):
        previous_content = ""
        scroll_pause = self.scroll_config.get("scroll_pause", 1.5)

        while True:
            current_content = await page.content()
            if current_content == previous_content:
                break
            else:
                previous_content = current_content

            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(scroll_pause)

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(scroll_pause)


class AsyncScraper:
    def __init__(
        self,
        headless=True,
        scroll_config=None,
        max_concurrent=3,
    ):
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        self.scroller = Scroller(scroll_config)
        self.headless = headless

    def load_cookies(self):
        with open("cookies.json", "r") as file:
            raw_cookies = json.load(file)

        samesitemap = {"strict": "Strict", "no_restriction": "None", "None": "None"}
        cookies = [
            {
                "name": cookie["name"],
                "value": cookie["value"],
                "domain": cookie["domain"],
                "path": cookie.get("path", "/"),
                "httpOnly": cookie.get("httpOnly", False),
                "secure": cookie.get("secure", False),
                "sameSite": samesitemap[cookie.get("sameSite", "None")],
                "expires": int(cookie["expirationDate"]) if "expirationDate" in cookie else None,
            }
            for cookie in raw_cookies
        ]

        cookies = [cookie for cookie in cookies if cookie["expires"] is not None]
        return cookies

    async def scrape_with_cookies(self, url):
        cookies = self.load_cookies()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()

            await context.add_cookies(cookies)

            page = await context.new_page()
            await page.goto(url)
            await self.scroller.content_scroll(page)
            content = await page.content()
            await browser.close()

        return content

    async def scrape(
        self,
        url: str,
        text_only=False,
        cookies=False,
        custom_function=None,
        **custom_function_args,
    ):
        args = create_args(self.headless, text_only)

        async with self.semaphore:
            await asyncio.sleep(random.uniform(1, 2))
            async with async_playwright() as p:
                browser = await p.chromium.launch(**args)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/122.0.2365.92",
                    java_script_enabled=False if text_only else True,
                )

                if cookies:
                    cookies = self.load_cookies()
                    await context.add_cookies(cookies)

                page = await context.new_page()

                await page.goto(url)
                await page.wait_for_selector("body")

                if custom_function:
                    if asyncio.iscoroutinefunction(custom_function):
                        await custom_function(page, **custom_function_args)
                    else:
                        custom_function(page, **custom_function_args)
                else:
                    await self.scroller.content_scroll(page)

                content = await page.content()
                await browser.close()
                return content

    async def scrape_with_retry(self, url, insights=True, retries=2, delay=2):
        for attempt in range(retries):
            try:
                return await self.scrape(url, insights)
            except Exception:
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                else:
                    return None


async def format_src(src, url, title=None):
    soup = BeautifulSoup(src, "html.parser")

    if not title:
        title = soup.title.string if soup.title else "No title found"
    description = soup.find("meta", attrs={"name": "description"})
    description = description["content"] if description else ""

    body = soup.find("body")
    if body.name not in ["script", "style", "head", "title", "meta", "[document]"]:
        all_text = body.get_text(strip=True, separator=" ")
    else:
        all_text = ""

    base_url = "/".join(url.split("/")[:3])

    images = extract_image_data(soup, base_url)
    images = filter_image_urls(images)

    content = deduplicate_text(all_text)
    data = {
        "url": url,
        "title": title,
        "content": content,
        "images": images,
    }

    return data


def extract_image_data(soup, base_url):
    images_data = []

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src:
            if src.startswith("//"):
                src = f"https:{src}"
            elif src.startswith("/"):
                src = f"{base_url.rstrip('/')}{src}"
            elif not src.startswith(("http://", "https://")):
                src = f"{base_url.rstrip('/')}/{src.lstrip('/')}"

        images_data.append({"src": src, "alt": img.get("alt", "")})

    return images_data


def filter_image_urls(image_data):
    exclude_keywords = {
        "thumbnail",
        "icon",
        "logo",
        "search",
        "linkedin",
        "undefined",
        "gift",
        "author-image",
        "thecaptable",
        "twitter",
        "facebook",
        "instagram",
        "newsletter_loggedin",
    }
    filtered_image_urls = []
    for image in image_data:
        alt_text = image.get("alt", "").lower()
        src = image.get("src", "")

        # Include only images that have meaningful alt text and are not SVGs
        if alt_text and not any(keyword in alt_text for keyword in exclude_keywords) and not src.lower().endswith(".svg"):
            filtered_image_urls.append(src)
    return filtered_image_urls


def deduplicate_text(text):
    sentences = list(set(text.split(". ")))
    return ". ".join(sentences)
