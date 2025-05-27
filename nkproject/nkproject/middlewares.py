# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import logging
import random
import time

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

logger = logging.getLogger(__name__)


class NkprojectSpiderMiddleware:
    """Spider middleware for Nike project"""

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        spider.logger.error(f"Spider exception: {exception}")
        pass

    async def process_start(self, start):
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class PlaywrightRetryMiddleware(RetryMiddleware):
    """自定义重试中间件，针对 Playwright 请求优化"""

    def __init__(self, settings):
        super().__init__(settings)
        self.max_retry_times = settings.getint('RETRY_TIMES', 3)
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST', -1)

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response

        # 检查是否为 Playwright 请求
        if request.meta.get('playwright'):
            # 针对动态加载页面的特殊处理
            if response.status in self.retry_http_codes:
                reason = response_status_message(response.status)
                spider.logger.warning(f"Playwright request failed with status {response.status}: {reason}")
                return self._retry(request, reason, spider) or response

        return super().process_response(request, response, spider)

    def process_exception(self, request, exception, spider):
        if request.meta.get('playwright'):
            spider.logger.warning(f"Playwright request exception: {exception}")
            return self._retry(request, f"Playwright exception: {exception}", spider)

        return super().process_exception(request, exception, spider)


class UserAgentRotateMiddleware:
    """User-Agent 轮换中间件"""

    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

    def process_request(self, request, spider):
        # 为 Playwright 请求设置随机 User-Agent
        if request.meta.get('playwright'):
            ua = random.choice(self.user_agents)
            if 'playwright_page_init_callback' not in request.meta:
                request.meta['playwright_page_init_callback'] = []

            # 添加设置 User-Agent 的回调
            async def set_user_agent(page):
                await page.set_extra_http_headers({'User-Agent': ua})

            if isinstance(request.meta['playwright_page_init_callback'], list):
                request.meta['playwright_page_init_callback'].append(set_user_agent)
            else:
                request.meta['playwright_page_init_callback'] = [set_user_agent]

        return None


class RequestDelayMiddleware:
    """请求延时中间件，防止被反爬"""

    def __init__(self, delay=1, randomize_delay=True):
        self.delay = delay
        self.randomize_delay = randomize_delay

    @classmethod
    def from_crawler(cls, crawler):
        delay = crawler.settings.getfloat('DOWNLOAD_DELAY', 1)
        randomize = crawler.settings.getbool('RANDOMIZE_DOWNLOAD_DELAY', True)
        return cls(delay, randomize)

    def process_request(self, request, spider):
        # 只对 Playwright 请求添加延时
        if request.meta.get('playwright'):
            if self.randomize_delay:
                delay = random.uniform(self.delay * 0.5, self.delay * 1.5)
            else:
                delay = self.delay

            spider.logger.debug(f"Delaying request for {delay:.2f} seconds")
            time.sleep(delay)

        return None


class PlaywrightPageConfigMiddleware:
    """Playwright 页面配置中间件"""

    def process_request(self, request, spider):
        if request.meta.get('playwright'):
            # 确保有页面初始化回调列表
            if 'playwright_page_init_callback' not in request.meta:
                request.meta['playwright_page_init_callback'] = []

            # 添加页面配置回调
            async def configure_page(page):
                # 设置视窗大小
                await page.set_viewport_size({"width": 1920, "height": 1080})

                # 禁用图片加载以提高速度（可选）
                # await page.route("**/*.{png,jpg,jpeg,gif,svg,webp}", lambda route: route.abort())

                # 设置额外的请求头
                await page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                })

                # 模拟真实用户行为
                await page.evaluate("""
                    // 重写 webdriver 属性
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });

                    // 重写 plugins 属性
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });

                    // 重写 languages 属性
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['zh-CN', 'zh', 'en'],
                    });
                """)

            if isinstance(request.meta['playwright_page_init_callback'], list):
                request.meta['playwright_page_init_callback'].append(configure_page)
            else:
                request.meta['playwright_page_init_callback'] = [configure_page]

        return None


class ResponseValidationMiddleware:
    """响应验证中间件"""

    def process_response(self, request, response, spider):
        # 检查 Playwright 响应是否有效
        if request.meta.get('playwright'):
            # 检查响应状态
            if response.status != 200:
                spider.logger.warning(f"Unexpected status code: {response.status}")
                return response

            # 检查页面内容
            if len(response.body) < 1000:  # 页面内容太少可能有问题
                spider.logger.warning("Response body seems too short, might be blocked")

            # 检查是否包含预期的内容
            if b'nike' not in response.body.lower():
                spider.logger.warning("Response doesn't contain expected Nike content")

        return response


class NkprojectDownloaderMiddleware:
    """下载器中间件基类，保持向后兼容"""

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        spider.logger.error(f"Download exception: {exception}")
        pass

    def spider_opened(self, spider):
        spider.logger.info("Downloader middleware opened for spider: %s" % spider.name)