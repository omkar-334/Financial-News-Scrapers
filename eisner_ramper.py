import re
from typing import Literal

import pandas as pd
import requests

from scraper_utils import check_months


class EisnerRamper:
    def __init__(self):
        self.url = "https://www.eisneramper.com/InsightsListing/Load?pageId=35885&page={}&loadAll=true"
        self.search_url = "https://www.eisneramper.com/InsightsListing/Load?pageId=35885&page={}&loadAll=true&searchTerm=finance"

    def get_posts(self, fetch):
        page = 1
        posts = []

        while True:
            response = requests.get(self.url.format(page))
            if response.status_code != 200:
                break

            data = response.json()
            if not int(data["paging"]["recordsPerPage"]):
                break

            df = self.make_df(data["items"])
            posts.append(df)

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

    def make_df(self, posts):
        df = pd.DataFrame(posts)[["title", "link", "displayDate"]]
        df["link"] = "https://www.eisneramper.com" + df["link"]
        return df

    async def execute(self, fetch: Literal["first", "6m", "12m", "all"] = "first"):
        print(f"---{self.url}", end="---")
        posts = self.get_posts(fetch)
        posts = pd.concat(posts)
        posts = posts.sort_values(by="date", ascending=False)
        print(len(posts))
        return posts
