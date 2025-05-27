import json
from datetime import datetime

import scrapy
from scrapy.linkextractors import LinkExtractor


class NikeSpider(scrapy.Spider):
    name = "nike_t"
    start_urls = ['https://www.nike.com.cn/w/']

    def parse(self, response):
        # 限定在#skip-to-products区域内提取链接[1,4](@ref)
        le = LinkExtractor(
            restrict_xpaths='//*[@id="skip-to-products"]'
        )
        links = le.extract_links(response)

        # 去重处理
        seen = set()
        for link in links:
            if link.url not in seen:
                seen.add(link.url)
                yield {'url': link.url}


def _load_product_urls():
    """从文件加载产品URL"""
    with open('nike.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        return [item["url"] for item in data]


class SkuSpider(scrapy.Spider):
    name = "sku_products"

    start_urls = _load_product_urls()

    def parse(self, response):
        """解析产品详情页"""

        title_container = response.xpath('//*[@id="title-container"]')
        title = title_container.xpath('//h1[@data-testid="product_title"]/text()').get()
        subtitle = title_container.xpath('//h2[@data-testid="product_subtitle"]/text()').get()

        price_container = response.xpath('//*[@id="price-container"]')
        price = price_container.xpath('//span[@data-testid="currentPrice-container"]/text()').get()

        description_container = response.xpath('//*[@id="product-description-container"]')
        detail = description_container.xpath('//p[@data-testid="product-description"]/text()').get()

        color = description_container.xpath(
            'normalize-space(//li[@data-testid="product-description-color-description"])'
        ).re_first(r'：(.+)$')

        sku = description_container.xpath(
            'normalize-space(//li[@data-testid="product-description-style-color"])'
        ).re_first(r'：(.+)$')

        size = response.css('input[name=grid-selector-input]::attr(value)').getall()
        src_list = response.xpath('//div[@data-testid="HeroImgContainer"]//img/@src').getall()

        yield {
            'url': response.url,
            'title': f"{title or ''} | {subtitle or ''}".strip(' |'),
            'price': price.strip() if price else '',
            'color': color,
            'size': size,
            'sku': sku,
            'details': detail.strip() if detail else '',
            'img_urls': src_list,
            'timestamp': datetime.now().isoformat(),
        }
