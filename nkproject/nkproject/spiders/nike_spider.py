import asyncio
import json
from urllib.parse import urljoin
from datetime import datetime

import scrapy
from scrapy import Request


class NikeSpider(scrapy.Spider):
    name = "nike_products"
    start_urls = ['https://www.nike.com.cn/w/']

    # 自定义设置
    # 自定义设置
    custom_settings = {
        'DOWNLOAD_TIMEOUT': 90,
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 60000,
        # 确保使用所有管道
        'ITEM_PIPELINES': {
            'nkproject.pipelines.NkprojectPipeline': 300,
            'nkproject.pipelines.DataValidationPipeline': 400,
            'nkproject.pipelines.DuplicatesPipeline': 500,
            'nkproject.pipelines.StatsPipeline': 600,
        },
        # 其他设置保持不变
    }

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_context': 'default',
                    'playwright_page_goto_kwargs': {
                        'wait_until': 'domcontentloaded',
                        'timeout': 60000,
                    },
                },
                callback=self.parse,
                dont_filter=True,
            )

    def parse(self, response):
        """修改为同步方法，使用 playwright_page_coroutine"""
        page = response.meta.get('playwright_page')

        if not page:
            self.logger.error("未获取到 playwright_page")
            return self._create_error_result(response.url, "未获取到页面对象")

        try:
            self.logger.info(f"开始处理页面: {response.url}")

            # 创建异步处理的 Request，让 Playwright 处理异步逻辑
            return Request(
                response.url,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_context': 'default',
                    'playwright_page_coroutine': self._async_process_page,
                    'playwright_page_goto_kwargs': {
                        'wait_until': 'domcontentloaded',
                        'timeout': 60000,
                    },
                },
                callback=self.parse_result,
                dont_filter=True,
            )

        except Exception as e:
            self.logger.error(f"处理页面时出错: {e}")
            yield self._create_error_result(response.url, str(e))

    async def _async_process_page(self, page):
        """异步处理页面的协程"""
        try:
            self.logger.info("开始异步处理页面")

            # 1. 等待页面完全加载
            await self._wait_for_page_load(page)

            # 2. 执行滚动加载
            total_links = await self._scroll_and_load_content(page)

            # 3. 获取最终页面内容
            body = await page.content()

            self.logger.info(f"异步处理完成，总链接数: {total_links}")
            return body

        except asyncio.TimeoutError as e:
            self.logger.error(f"页面加载超时: {e}")
            raise
        except Exception as e:
            self.logger.error(f"异步处理出错: {e}")
            raise

    def parse_result(self, response):
        """解析最终结果"""
        try:
            # 获取页面内容（由异步协程处理后的结果）
            body = response.text

            # 解析产品链接
            result = self._parse_product_links(body, response.url)

            self.logger.info(f"成功解析 {result['link_count']} 个产品链接")

            # 返回结果 - 这里会被 pipeline 处理
            yield result

        except Exception as e:
            self.logger.error(f"解析结果时出错: {e}")
            yield self._create_error_result(response.url, f"解析错误: {e}")

    async def _wait_for_page_load(self, page):
        """等待页面加载完成"""
        self.logger.info("等待页面初始加载...")

        # 尝试多个可能的选择器
        selectors_to_try = [
            'div[id="skip-to-products"]',
            '[data-testid="product-grid"]',
            '.product-card',
            '.grid-item',
            'main',
        ]

        page_loaded = False
        for selector in selectors_to_try:
            try:
                await page.wait_for_selector(selector, timeout=15000)
                self.logger.info(f"页面加载完成，找到选择器: {selector}")
                page_loaded = True
                break
            except Exception as e:
                self.logger.debug(f"选择器 {selector} 未找到: {e}")
                continue

        if not page_loaded:
            self.logger.warning("未找到预期的页面元素，但继续处理")

        # 等待网络请求稳定
        await asyncio.sleep(3)

    async def _scroll_and_load_content(self, page):
        """执行滚动加载内容"""
        self.logger.info("开始滚动加载内容...")

        max_scrolls = 5
        no_change_count = 0
        max_no_change = 2

        for i in range(max_scrolls):
            try:
                # 获取滚动前的状态
                prev_height = await page.evaluate("document.body.scrollHeight")
                prev_links = await self._count_product_links(page)

                self.logger.info(f"第 {i + 1} 次滚动前: 页面高度={prev_height}, 链接数={prev_links}")

                # 滚动到页面底部
                await page.evaluate("""
                    window.scrollTo({ 
                        top: document.body.scrollHeight, 
                        behavior: 'smooth' 
                    });
                """)

                # 等待滚动完成和新内容加载
                await asyncio.sleep(3)

                # 检查页面变化
                current_height = await page.evaluate("document.body.scrollHeight")
                current_links = await self._count_product_links(page)

                if current_height == prev_height and current_links == prev_links:
                    no_change_count += 1
                    if no_change_count >= max_no_change:
                        self.logger.info("连续多次无新内容，停止滚动")
                        break
                else:
                    no_change_count = 0

                self.logger.info(f"第 {i + 1} 次滚动完成: 高度={current_height}, 链接数={current_links}")

            except Exception as e:
                self.logger.error(f"第 {i + 1} 次滚动出错: {e}")
                continue

        final_links = await self._count_product_links(page)
        self.logger.info(f"滚动完成，最终链接数: {final_links}")
        return final_links

    async def _count_product_links(self, page):
        """统计产品链接数量"""
        try:
            selectors = [
                'div[id="skip-to-products"] a[href]',
                '[data-testid="product-grid"] a[href]',
                '.product-card a[href]',
                'a[href*="/product/"]',
            ]

            for selector in selectors:
                try:
                    count = await page.evaluate(f'document.querySelectorAll("{selector}").length')
                    if count > 0:
                        return count
                except:
                    continue

            return await page.evaluate('document.querySelectorAll("a[href]").length')

        except Exception as e:
            self.logger.debug(f"统计链接数出错: {e}")
            return 0

    def _parse_product_links(self, body, base_url):
        """解析产品链接"""
        selector = scrapy.Selector(text=body)

        # 尝试多个选择器策略
        product_containers = [
            selector.xpath('//div[@id="skip-to-products"]'),
            selector.css('[data-testid="product-grid"]'),
            selector.css('.product-grid'),
            selector,
        ]

        all_links = []
        for container in product_containers:
            if container:
                links = container.css('a[href]::attr(href)').getall()
                if links:
                    all_links = links
                    break

        if not all_links:
            self.logger.warning("未找到任何链接")
            return self._create_error_result(base_url, "未找到产品链接")

        # 过滤和去重链接
        valid_links = []
        seen = set()

        product_patterns = [
            '/product/',
            '/shoes/',
            '/clothing/',
            '/accessories/',
            '/gear/',
            '/kids/',
            '/men/',
            '/women/',
        ]

        for link in all_links:
            if not link or link in seen:
                continue

            full_url = urljoin(base_url, link)

            if any(pattern in full_url.lower() for pattern in product_patterns):
                if not any(exclude in full_url.lower() for exclude in ['help', 'size-guide', 'reviews', 'wishlist']):
                    valid_links.append(full_url)
                    seen.add(link)

        self.logger.info(f"提取到 {len(valid_links)} 个有效产品链接")

        return {
            "page_url": base_url,
            "product_links": valid_links,
            "link_count": len(valid_links),
            "total_links_found": len(all_links),
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }

    def _create_error_result(self, url, error_msg):
        """创建错误结果"""
        return {
            "page_url": url,
            "product_links": [],
            "link_count": 0,
            "total_links_found": 0,
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }


class SkuSpider(scrapy.Spider):
    name = "sku_products"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = self._load_product_urls()

    def _load_product_urls(self):
        """从文件加载产品URL"""
        try:
            with open('data/nike_products.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
                # 处理不同的数据格式
                if isinstance(data, list):
                    urls = []
                    for item in data:
                        if isinstance(item, dict) and 'product_links' in item:
                            urls.extend(item['product_links'])
                    return urls
                return []
        except FileNotFoundError:
            self.logger.error("nike_products.json 文件不存在，请先运行 nike_products 爬虫")
            return []
        except Exception as e:
            self.logger.error(f"加载产品URL失败: {e}")
            return []

    def parse(self, response):
        """解析产品详情页"""
        try:
            title_container = response.xpath('//*[@id="title-container"]')
            title = title_container.xpath('//h1[@data-testid="product_title"]/text()').get()
            subtitle = title_container.xpath('//h2[@data-testid="product_subtitle"]/text()').get()

            price_container = response.xpath('//*[@id="price-container"]')
            price = price_container.xpath('//span[@data-testid="currentPrice-container"]/text()').get()

            description_container = response.xpath('//*[@id="product-description-container"]')
            detail = description_container.xpath('//p/text()').get()

            color = description_container.xpath(
                'normalize-space(//li[@data-testid="product-description-color-description"])'
            ).re_first(r'：(.+)$')

            sku = description_container.xpath(
                'normalize-space(//li[@data-testid="product-description-style-color"])'
            ).re_first(r'：(.+)$')

            size = response.xpath('//input[@name="grid-selector-input"]/@value').getall()
            img_urls = response.xpath('//img[@data-testid="HeroImg"]/@src').getall()

            yield {
                'url': response.url,
                'title': f"{title or ''} | {subtitle or ''}".strip(' |'),
                'price': price.strip() if price else '',
                'color': color,
                'size': size,
                'sku': sku,
                'details': detail.strip() if detail else '',
                'img_urls': img_urls,
                'timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"解析产品页面失败 {response.url}: {e}")
            yield {
                'url': response.url,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }