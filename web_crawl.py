import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def get_scrape_content(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url= url,
        )
        print(result.markdown)
        return result.markdown
        # with open("example.md", "w") as file:
        #     file.write(result.markdown)
    

# asyncio.run(get_scrape_content("https://qdrant.tech/documentation/quickstart/"))        

# if __name__ == "__main__":
#     asyncio.run(main())
