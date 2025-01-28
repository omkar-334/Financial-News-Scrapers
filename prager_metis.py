import re
from typing import Literal

import pandas as pd
from bs4 import BeautifulSoup

from scraper import AsyncScraper
from scraper_utils import check_months, clean


class PragerMetis:
    def __init__(self, headless=True):
        self.url = "https://pragermetis.com/insight_categories/featured-uk/"
        self.scraper = AsyncScraper(headless=headless)
        self.posts = []

    async def show_more_posts(self, page, fetch: Literal["first", "6m", "12m", "all"]):
        page_num = 1
        while True:
            await page.wait_for_selector("div#posts-container")
            content = await page.content()
            df = self.make_df(content)
            self.posts.append(df)

            if fetch == "first":
                break
            elif fetch == "all":
                pass
            elif re.match(r"\b\d{1,2}m\b", fetch):
                if check_months(df, fetch):
                    break
            else:
                break

            page_num += 1
            button_selector = f"ul.pagination a:has-text('{page_num}')"

            if not await page.is_visible(button_selector):
                return
            await page.click(button_selector)
            await page.wait_for_timeout(2000)

    def make_df(self, content):
        soup = BeautifulSoup(content, "html.parser")
        articles = soup.find("div", {"id": "posts-container"})
        articles = articles.find_all("article")
        data = []
        for i in articles:
            title = clean(i.find("h2", {"class": "entry-title fusion-post-title"}))
            link = title.find("a").get("href")
            date = i.find("div", {"class": "author-block"}).contents[0].strip()

            data.append({"link": link, "title": title, "date": date})

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
        posts = pd.concat(self.posts)
        posts = posts.sort_values(by="date", ascending=False)
        print(len(posts))
        return posts
