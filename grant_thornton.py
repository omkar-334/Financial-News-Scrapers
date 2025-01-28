import asyncio
import re
from datetime import datetime
from typing import Literal

import pandas as pd
from bs4 import BeautifulSoup

from scraper import AsyncScraper
from scraper_utils import clean


class GrantThornton:
    def __init__(self, headless=True):
        self.urls = [
            "https://grantthornton.com/insights/audit-committee",
            "https://grantthornton.com/insights/dc-dispatch",
            "https://grantthornton.com/insights/digital-transformation",
            "https://grantthornton.com/insights/growth-insights",
            "https://grantthornton.com/insights/work-place-evolution",
        ]
        self.scraper = AsyncScraper(headless=headless)

    async def show_more_posts(self, page, fetch: Literal["first", "6m", "12m", "all"]):
        cookie_button_selector = "#onetrust-accept-btn-handler"
        if await page.is_visible(cookie_button_selector):
            await page.click(cookie_button_selector)

        button_selector = "button.cmp-button:has-text('Show More')"

        clicks = 0
        while True:
            if fetch == "first":
                break
            elif fetch == "all":
                pass
            elif re.match(r"\b\d{1,2}m\b", fetch):
                content = await page.content()
                if await self.check_months(content, fetch):
                    break
            else:
                break

            if not await page.is_visible(button_selector):
                return
            await page.click(button_selector)
            clicks += 1
            await page.wait_for_timeout(2000)

            if not await page.is_visible(button_selector):
                return
            await page.click(button_selector)
            clicks += 1
            await page.wait_for_timeout(2000)

    async def check_months(self, content, fetch):
        months = int(fetch[:-1])
        for i in range(-1, -4, -1):
            articles = await self.extract_articles(content)
            last_url = articles[i]["link"]
            date, text = await self.scrape_article(last_url)
            if date:
                break

        date = datetime.strptime(date, "%B %d, %Y")

        current_date = datetime.now()
        days_diff = (current_date - date).days
        months_diff = days_diff // 30

        if months_diff > months:
            return True
        return False

    async def extract_articles(self, content, text=False):
        soup = BeautifulSoup(content, "html.parser")
        articles = soup.find_all("div", {"class": "coveo-card-layout CoveoResult"})
        data = []
        for i in articles:
            link = i.find("a").get("href")
            title = clean(i.find("h5", {"class": "cmp-search__result-title"}))
            category = clean(i.find("p", {"class": "cmp-search__result-category"}))
            if category == "SURVEY REPORT":
                continue
            if text:
                date, text = await self.scrape_article(link)
                data.append({"link": link, "title": title, "category": category, "date": date, "text": text})
            else:
                data.append({"link": link, "title": title, "category": category})
        return data

    async def scrape_article(self, url):
        content = await self.scraper.scrape(url)
        soup = BeautifulSoup(content, "html.parser")
        date = clean(soup.find("time", {"class": "cmp-hero-banner__article-date"}))
        divs = soup.find_all("div", {"class": "section aem-GridColumn aem-GridColumn--default--12"})
        text = "\n".join([clean(i) for i in divs])
        return date, text

    async def execute(self, url=None, fetch: Literal["first", "6m", "12m", "all"] = "first"):
        urls = [url] if url else self.urls
        posts = []
        for url in urls:
            print(f"---{url}", end="---")
            content = await self.scraper.scrape(
                url,
                custom_function=self.show_more_posts,
                fetch=fetch,
            )
            posts.extend(await self.extract_articles(content))
        posts = pd.DataFrame(posts)
        posts = posts.sort_values(by="date", ascending=False)
        print(len(posts))
        return posts
