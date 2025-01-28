import asyncio
import re
from typing import Literal

import pandas as pd
from bs4 import BeautifulSoup

from scraper import AsyncScraper
from scraper_utils import check_months, clean


class CBH:
    def __init__(self, headless=True):
        self.url = "https://www.cbh.com/insights/?p={}#SearchResults"
        self.scraper = AsyncScraper(headless=headless)

    async def scrape_website(self, fetch: Literal["first", "6m", "12m", "all"]):
        page = 1
        posts = []
        while True:
            content = await self.scraper.scrape(self.url.format(page))

            df = self.make_df(content)
            if df is not None:
                posts.append(df)
            else:
                break

            if fetch == "first":
                break
            elif fetch == "all":
                pass
            elif re.match(r"\b\d{1,2}m\b", fetch):
                if check_months(df, fetch):
                    break
            else:
                break

            page += 1
        return posts

    def make_df(self, content):
        soup = BeautifulSoup(content, "html.parser")
        if "no results" in soup.text.lower():
            return None
        articles = soup.find("div", {"id": "SearchResults"}).find_all("div", {"class": "insights-listing-block__card"})
        data = []
        for i in articles:
            title = i.find("div", {"class": "insights-listing-block__title"})
            link = title.find("a").get("href")
            category = clean(i.find("div", {"class": "insights-listing-block__category"}))
            date = clean(i.find("div", {"class": "insights-listing-block__date"}))
            desc = clean(i.find("div", {"class": "insights-listing-block__description"}))
            try:
                tags = [j.get("href").strip() for j in i.find("div", {"class": "insights-listing-block__badges"}).find_all("a")]
            except AttributeError:
                tags = []
            data.append({"link": link, "title": clean(title), "category": category, "date": date, "desc": desc, "tags": tags})

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"], format="%B %d, %Y")
        return df

    async def execute(self, fetch: Literal["first", "6m", "12m", "all"] = "first"):
        print(f"---{self.url}", end="---")
        posts = await self.scrape_website(fetch)
        posts = pd.concat(posts)
        posts = posts.sort_values(by="date", ascending=False)
        print(len(posts))
        return posts
