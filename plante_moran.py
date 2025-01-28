import asyncio
import re
from typing import Literal

import pandas as pd
from bs4 import BeautifulSoup

from scraper import AsyncScraper
from scraper_utils import check_months, clean


class PlanteMoran:
    def __init__(self, headless=True):
        self.url = "https://www.plantemoran.com/explore-our-thinking/search?skip=0&keyword="
        self.scraper = AsyncScraper(headless=headless)
        self.posts = None
        self.months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

    async def show_more_posts(self, page, fetch):
        while True:
            await page.wait_for_selector("div.section.thought-list.fade-ng-cloak")
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

            button_selector = "div.expand-icon.cta.cta--icon.cta--expand"

            if not await page.is_visible(button_selector):
                return
            await page.click(button_selector)
            await page.wait_for_timeout(2000)

            await asyncio.sleep(2)
            await page.wait_for_timeout(2000)

    def make_df(self, content):
        soup = BeautifulSoup(content, "html.parser")
        articles = soup.find("ul", {"class": "thought-items"})
        articles = articles.find_all("li", {"class": "thought-item ng-scope"})
        data = []
        for i in articles:
            i = i.find("div", {"class": "thought-item-details"})
            title = clean(i.find("a"))
            link = i.find("a").get("href")
            date = clean(i.find("span", {"class": "item date ng-binding"})).replace(".", "")
            for month in self.months:
                if month in date:
                    date = date.replace(month, month[:3])
                    break
            desc = clean(i.find("div", {"class": "brief ng-binding ng-scope"}))
            category = clean(i.find("span", {"class": "item type ng-binding ng-scope"}))

            data.append({"link": link, "title": title, "date": date, "desc": desc, "category": category})

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"], format="%b %d, %Y", errors="coerce")
        return df

    async def execute(self, fetch: Literal["first", "3m", "6m", "12m", "all"] = "first"):
        print(f"---{self.url}", end="---")
        await self.scraper.scrape(
            self.url,
            custom_function=self.show_more_posts,
            fetch=fetch,
        )
        self.posts.sort_values(by="date", ascending=False, inplace=True)
        print(len(self.posts))
        return self.posts
