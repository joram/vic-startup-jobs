#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import os.path
import re
import time
from typing import Iterator, Union
from fake_useragent import UserAgent
ua = UserAgent()

from bs4 import BeautifulSoup
from pyppeteer import launch
from pyppeteer_stealth import stealth

JOBS_DIR = os.path.join(os.path.dirname(__file__), "..", "job_postings")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".cache")


async def _get_uncached_content(url:str) -> str:
    browser = await launch()
    page = await browser.newPage()
    await stealth(page)

    await page.goto(url)
    # move mouse to trigger lazy loading
    time.sleep(1)
    await page.mouse.move(123,123)
    time.sleep(1)
    await page.mouse.move(125,125)
    time.sleep(1)
    content = await page.content()
    await browser.close()
    return content


async def get_content(url:str) -> str:
    if not os.path.exists(CACHE_DIR):
        os.mkdir(CACHE_DIR)

    key = url.replace("https://", "").replace("http://", "")
    if key.endswith("/"):
        key = f"{key}index.html"
    if not key.endswith(".html"):
        key = f"{key}.html"
    cache_file = os.path.join(CACHE_DIR, key)
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            content = f.read()
            return content

    content = await _get_uncached_content(url)

    file_dir = os.path.dirname(cache_file)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(cache_file, "w") as f:
        f.write(content)

    return content


def _get_absolute_urls(content: str, base_url: str) -> Iterator[Union[str, str]]:
    soup = BeautifulSoup(content, parser='html.parser', features="lxml")
    found = []
    anchors = soup.find_all("a")
    for a in anchors:
        href = a.attrs.get("href")
        if href is None:
            continue
        if not href.startswith("http"):
            href = os.path.join(base_url, href.lstrip("/"))
        if href in found:
            continue
        found.append(href)
        yield a.text, href


class Job:
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url


class Company:

    def __init__(self, name: str, homepage: str, careers_url: str, careers_regex: str):
        self.name = name
        self.homepage_url = homepage
        self.careers_url = careers_url
        self.careers_regex = careers_regex

    @property
    def safe_name(self):
        if "/" not in self.name:
            return self.name

        parts = self.name.split("/")
        if len(parts) != 2:
            raise Exception("more than one slash in name")

        return f"{parts[0]} ({parts[1]})"

    async def get_jobs(self):
        if not self.careers_url:
            return
        if self.careers_url == "":
            return
        if self.careers_regex == "":
            return

        content = await get_content(self.careers_url)
        for name, url in _get_absolute_urls(content, self.careers_url):
            if re.match(self.careers_regex, url):
                yield Job(name, url)
            # else:
            #     print(f"Skipping {url} because it does not match {self.careers_regex}")

    def save(self):
        print("Saving", self.name)
        if self.careers_url:
            with open(os.path.join(JOBS_DIR, f"{self.safe_name}.md"), "w") as f:
                s = f"""
# {self.name}
- [Careers]({self.careers_url})
## Job Postings"""
                for job in self.get_jobs():
                    s += f"\n- [{job.title}]({job.url})"
                f.write(s)

    def __unicode__(self):
        s = f"{self.name} ({self.careers_url} - {self.careers_regex})"
        return s

    def __str__(self):
        return self.__unicode__()


def get_companies() -> Iterator[Company]:
    with open("companies.csv") as f:
        for line in f:
            if line.startswith("####"):
                return
            parts = line.split(",")
            if len(parts) != 4:
                raise Exception(f"Invalid line: {line}")
            [name, url, careers_url, careers_regex] = parts
            url = url.strip()
            careers_url = careers_url.strip()
            careers_regex = careers_regex.strip()
            yield Company(name, url, careers_url, careers_regex)


async def main():
    if os.path.exists(JOBS_DIR):
        import shutil
        shutil.rmtree(JOBS_DIR)
    os.mkdir(JOBS_DIR)
    for c in get_companies():
        print(c)
        jobs = c.get_jobs()
        async for j in jobs:
            print("\t", j.title, j.url)
        # c.save()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
