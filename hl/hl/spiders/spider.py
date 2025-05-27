import json
import time
from datetime import datetime
from urllib.parse import urlparse

import scrapy
from scrapy.linkextractors import LinkExtractor
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class NikeSpider(scrapy.Spider):
    name = "nike_t"
    start_urls = ['https://www.nike.com.cn/w/']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_window_size(1920, 1080)
        self.driver.implicitly_wait(5)

    def parse(self, response):
        try:
            self.driver.get(response.url)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            dynamic_html = self.driver.page_source
            dynamic_response = response.replace(body=dynamic_html)
        except TimeoutException as e:
            self.logger.error(f"加载超时: {response.url}")
        finally:
            self.driver.delete_all_cookies()

        le = LinkExtractor(
            restrict_xpaths='//*[@id="skip-to-products"]'
        )
        links = le.extract_links(dynamic_response)

        seen = set()
        count = 0
        for link in links:
            clean_url = urlparse(link.url)._replace(query='').geturl()
            if clean_url not in seen and count < 48:
                seen.add(clean_url)
                count += 1
                yield {'url': clean_url}
            if count >= 48:
                break

    def closed(self, reason):
        self.driver.quit()


def _load_product_urls():
    with open('nike.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        return [item["url"] for item in data]


class SkuSpider(scrapy.Spider):
    name = "sku_products"
    start_urls = _load_product_urls()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_window_size(1920, 1080)
        self.driver.implicitly_wait(5)
    def parse(self, response):
        try:
            self.driver.get(response.url)
            dynamic_html = self.driver.page_source
            dynamic_response = response.replace(body=dynamic_html)
            return self._parse_dynamic_content(dynamic_response)
        except TimeoutException as e:
            self.logger.error(f"加载超时: {response.url}")
        finally:
            self.driver.delete_all_cookies()

    def _parse_dynamic_content(self, response):
        try:
            size = response.css('input[name=grid-selector-input]::attr(value)').getall() or \
                   [el.get_attribute("value") for el in self.driver.find_elements(
                       By.CSS_SELECTOR, 'input[name=grid-selector-input]')]
        except Exception as e:
            size = ['售罄']
        img_elements = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '//div[@data-testid="HeroImgContainer"]//img')
            )
        )
        src_list = [img.get_attribute("src") for img in img_elements]

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

        return {
            'url': response.url,
            'title': f"{title or ''} | {subtitle or ''}".strip(' |'),
            'price': price.strip() if price else '',
            'color': color,
            'size': size,
            'sku': sku,
            'details': detail.strip() if detail else '',
            'img_urls': list(set(src_list)),
            'timestamp': datetime.now().isoformat(),
        }

    def closed(self, reason):
        self.driver.quit()
