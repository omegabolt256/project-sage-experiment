import asyncio

from browser_use import Agent, Browser
from browser_use.llm import ChatOllama


async def main():
    llm = ChatOllama(
        model="sage-browser-vl",
        host="http://127.0.0.1:11434",
    )

    browser = Browser()

    agent = Agent(
        task="Open https://example.com and report the page title.",
        llm=llm,
        browser=browser,
    )

    result = await agent.run()

    print("RESULT:")
    print(result)


asyncio.run(main())

