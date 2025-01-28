import asyncio
import re
from typing import Literal

import pandas as pd
from bs4 import BeautifulSoup

from scraper import AsyncScraper
from scraper_utils import check_months, clean


class BDO:
    def __init__(self, headless=True):
        self.urls = [
            "https://www.bdo.com/insights?insightType=article&insightService=assurance&",
            "https://www.bdo.com/insights?insightType=article&insightService=advisory_1&",
            "https://www.bdo.com/insights?insightType=article&insightService=digital&",
            "https://www.bdo.com/insights?insightType=article&insightService=tax_1&",
        ]
        self.scraper = AsyncScraper(headless=headless)
        self.posts = None

    async def show_more_posts(self, page, fetch):
        while True:
            await page.wait_for_selector("div.card-grid")
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

            button_selector = "div.show-more-container > button"

            if not await page.is_visible(button_selector):
                return
            await page.click(button_selector)
            await page.wait_for_timeout(2000)

            await asyncio.sleep(2)
            await page.wait_for_timeout(2000)

    def make_df(self, content):
        soup = BeautifulSoup(content, "html.parser")
        articles = soup.find_all("div", {"class": "InsightCardWrapperStyled-sc-1w8ojf6-0 gLShon insight-card-wrapper"})
        data = []
        for i in articles:
            div = i.find("div", {"class": "animated-content hide"})
            title = clean(div.find("h3"))
            link = i.find("a").get("href")
            date = clean(div.find("span", {"class": "publish-date"}))
            desc = clean(div.find("p", {"class": "description"}))
            category = clean(div.find("span", {"class": "tag"}))

            data.append({"link": link, "title": title, "date": date, "desc": desc, "category": category})

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"], format="%B %d, %Y", errors="coerce")
        return df

    async def execute(self, url=None, fetch: Literal["first", "3m", "6m", "12m", "all"] = "first"):
        urls = self.urls if not url else [url]
        posts = []
        for url in urls:
            print(f"---{url}", end="---")
            self.posts = None
            await self.scraper.scrape(
                url,
                custom_function=self.show_more_posts,
                fetch=fetch,
            )
            posts.append(self.posts.sort_values(by="date", ascending=False))
        posts = pd.concat(posts)
        posts = posts.sort_values(by="date", ascending=False)
        print(len(self.posts))
        return posts
