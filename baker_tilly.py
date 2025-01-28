import asyncio
import re
from typing import Literal

import pandas as pd
from bs4 import BeautifulSoup

from scraper import AsyncScraper, Scroller
from scraper_utils import check_months, clean


class BakerTilly:
    def __init__(self, headless=True):
        self.url = "https://www.bakertilly.com/insights"
        self.scraper = AsyncScraper(headless=headless)
        self.scroller = Scroller()
        self.posts = None

    async def show_more_posts(self, page, fetch):
        while True:
            await page.wait_for_selector("div.container-fluid")
            await page.wait_for_selector("div.position-relative.py-6.border-bottom.border-dark", timeout=5000)
            content = await page.content()
            self.posts = self.make_df(content)

            if fetch == "first":
                break
            elif fetch == "all":
                pass
            elif re.match(r"\b\d{1,2}m\b", fetch):
                if check_months(self.posts, fetch):
                    break
            else:
                break

            divs = await page.query_selector_all("div.position-relative.py-6.border-bottom.border-dark")
            last_div = divs[-1]
            await last_div.scroll_into_view_if_needed()

            await asyncio.sleep(2)
            await page.wait_for_timeout(2000)

    def make_df(self, content):
        soup = BeautifulSoup(content, "html.parser")
        articles = soup.find_all("div", {"class": "position-relative py-6 border-bottom border-dark"})
        data = []
        for i in articles:
            title = clean(i.find("a"))
            link = i.find("a").get("href")
            date = clean(i.find("div", {"class": "row"}).find("div", {"class": "col-md-7"}).find_all("p", class_=None, recursive=False)[0])
            desc = clean(i.find("p", {"class": "line-clamp-3"}))
            category = clean(i.find("p", {"class": "kicker"}))

            data.append({"link": link, "title": title, "date": date, "desc": desc, "category": category})

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"], format="%b %d, %Y")
        return df

    async def execute(self, fetch: Literal["first", "6m", "12m", "all"] = "first"):
        print(f"---{self.url}", end="---")
        await self.scraper.scrape(
            self.url,
            custom_function=self.show_more_posts,
            fetch=fetch,
        )
        self.posts.sort_values(by="date", ascending=False, inplace=True)
        print(len(self.posts))
        return self.posts
