import re


async def get_follower_count(page):
    elements = await page.get_by_text("Followers").all()
    followers_list = []
    for follower in elements:
        element_handle = await follower.element_handle()
        if element_handle:
            text = await page.evaluate("(element) => element.innerText", element_handle)
            followers_list.append(text)

    if len(followers_list) == 2:
        if followers_list[0] == followers_list[1]:
            return followers_list[0]


async def get_post_links(page, links={}):
    date_pattern = r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4}\b"
    elements = await page.locator("//div[@role='link']").all()
    links = {}
    for element in elements:
        link = await element.get_attribute("data-href")
        match = None
        element = await element.element_handle()
        if element:
            text = await page.evaluate("(element) => element.innerText", element)
            match = re.search(date_pattern, text)

        links[link] = match.group() if match else None
    print(links)
    print(len(links))
    return links
