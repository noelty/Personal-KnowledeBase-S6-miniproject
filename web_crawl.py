import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def get_scrape_content(url):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url= url,
        )
        print(result.markdown)
        # file = f"{url[8:].replace('/', '_')}.md"
        file = "sample.md"
        with open(file, "w") as md_file:
            md_file.write(result.markdown)
        return file
        
    

# asyncio.run(get_scrape_content(url))        

# if __name__ == "__main__":
#     asyncio.run(main())
