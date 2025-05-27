import asyncio
import json
from urllib.parse import urljoin

import scrapy

import scrapy
import asyncio
from urllib.parse import urljoin


class NikeSpider(scrapy.Spider):
    name = "nike_products"
    start_urls = ['https://www.nike.com.cn/w/']

    # 自定义设置，覆盖 settings.py 中的部分配置
    custom_settings = {
        'DOWNLOAD_TIMEOUT': 90,
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 60000,
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_context': 'default',
                    'playwright_page_goto_kwargs': {
                        'wait_until': 'domcontentloaded',  # 等待 DOM 加载完成
                        'timeout': 60000,
                    },
                },
                callback=self.parse,
                dont_filter=True,  # 允许重复请求（如果需要重试）
            )

    async def parse(self, response):
        page = response.meta['playwright_page']

        try:
            self.logger.info(f"开始处理页面: {response.url}")

            # 1. 等待页面完全加载
            await self._wait_for_page_load(page)

            # 2. 执行滚动加载
            total_links = await self._scroll_and_load_content(page)

            # 3. 获取最终页面内容
            body = await page.content()

            self.logger.info(f"页面处理完成，准备解析数据")

        except asyncio.TimeoutError as e:
            self.logger.error(f"页面加载超时: {e}")
            yield self._create_error_result(response.url, "页面加载超时")
            return
        except Exception as e:
            self.logger.error(f"页面处理出错: {e}")
            yield self._create_error_result(response.url, str(e))
            return
        finally:
            # 确保页面被关闭
            try:
                await page.close()
                self.logger.debug("页面已关闭")
            except Exception as e:
                self.logger.warning(f"关闭页面时出错: {e}")

        # 解析数据
        try:
            result = self._parse_product_links(body, response.url)
            yield result
        except Exception as e:
            self.logger.error(f"数据解析出错: {e}")
            yield self._create_error_result(response.url, f"数据解析错误: {e}")

    async def _wait_for_page_load(self, page):
        """等待页面加载完成"""
        self.logger.info("等待页面初始加载...")

        # 尝试多个可能的选择器
        selectors_to_try = [
            'div[id="skip-to-products"]',
            '[data-testid="product-grid"]',
            '.product-card',
            '.grid-item',
            'main',  # 备用选择器
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

        max_scrolls = 5  # 增加滚动次数
        no_change_count = 0  # 连续无变化次数
        max_no_change = 2  # 最大连续无变化次数

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

                # 等待滚动完成
                await asyncio.sleep(2)

                # 等待新内容加载
                max_wait_time = 10  # 最大等待时间（秒）
                waited_time = 0

                while waited_time < max_wait_time:
                    await asyncio.sleep(1)
                    waited_time += 1

                    # 检查页面是否有变化
                    current_height = await page.evaluate("document.body.scrollHeight")
                    current_links = await self._count_product_links(page)

                    if current_height > prev_height or current_links > prev_links:
                        self.logger.info(
                            f"检测到新内容: 高度 {prev_height}→{current_height}, 链接 {prev_links}→{current_links}")
                        no_change_count = 0
                        break

                    # 检查是否已经到达页面底部
                    at_bottom = await page.evaluate("""
                        window.innerHeight + window.scrollY >= document.body.scrollHeight - 100
                    """)

                    if at_bottom and waited_time > 3:
                        self.logger.info("已滚动到页面底部")
                        break

                # 如果没有新内容加载
                current_height = await page.evaluate("document.body.scrollHeight")
                current_links = await self._count_product_links(page)

                if current_height == prev_height and current_links == prev_links:
                    no_change_count += 1
                    self.logger.info(f"第 {i + 1} 次滚动无新内容 (连续 {no_change_count} 次)")

                    if no_change_count >= max_no_change:
                        self.logger.info("连续多次无新内容，停止滚动")
                        break
                else:
                    no_change_count = 0

                self.logger.info(f"第 {i + 1} 次滚动完成")

            except Exception as e:
                self.logger.error(f"第 {i + 1} 次滚动出错: {e}")
                continue

        # 获取最终链接数
        final_links = await self._count_product_links(page)
        self.logger.info(f"滚动完成，最终链接数: {final_links}")
        return final_links

    async def _count_product_links(self, page):
        """统计产品链接数量"""
        try:
            # 尝试多种选择器
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

            # 如果都没找到，返回所有链接数
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
            selector,  # 整个页面作为备用
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

        # 产品页面的URL模式
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

            # 构建完整URL
            full_url = urljoin(base_url, link)

            # 过滤有效的产品链接
            if any(pattern in full_url.lower() for pattern in product_patterns):
                # 进一步过滤，排除一些非产品页面
                if not any(exclude in full_url.lower() for exclude in ['help', 'size-guide', 'reviews', 'wishlist']):
                    valid_links.append(full_url)
                    seen.add(link)

        self.logger.info(f"提取到 {len(valid_links)} 个有效产品链接")

        return {
            "page_url": base_url,
            "product_links": valid_links,
            "link_count": len(valid_links),
            "total_links_found": len(all_links),
            "timestamp": scrapy.utils.misc.load_object("datetime").datetime.now().isoformat(),
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
            "timestamp": scrapy.utils.misc.load_object("datetime").datetime.now().isoformat(),
            "status": "error"
        }


def init():
    with open('nike_links.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        return [
            url
            for item in data
            for url in item["product_links"]
        ]


class SkuSpider(scrapy.Spider):
    name = "sku_products"
    start_urls = init()
    print(start_urls)



    def parse(self, response):
        title_container = response.xpath('//*[@id="title-container"]')

        title = title_container.xpath('//h1[@data-testid="product_title"]/text()').get().strip()
        subtitle = title_container.xpath('//h2[@data-testid="product_subtitle"]/text()').get().strip()

        price_container = response.xpath('//*[@id="price-container"]')
        price = price_container.xpath('//span[@data-testid="currentPrice-container"]/text()').get().strip()

        description_container = response.xpath('//*[@id="product-description-container"]')
        detail = description_container.xpath('//*[@id="product-description-container"]/p/text()').get().strip()

        color = description_container.xpath(
            'normalize-space(//li[@data-testid="product-description-color-description"])').re_first(r'：(.+)$'),
        sku = description_container.xpath(
            'normalize-space(//li[@data-testid="product-description-style-color"])').re_first(r'：(.+)$')

        size = response.xpath('//input[@name="grid-selector-input"]/@value').getall()
        img_urls = response.xpath(
            '//img[@data-testid="HeroImg"]/@src'
        ).getall()

        yield {
            'title': f"{title} | {subtitle}",
            'price': price,
            'color': color,
            'size': size,
            'sku': sku,
            'details': detail,
            'img_urls': img_urls
        }
