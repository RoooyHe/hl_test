from datetime import datetime
from pathlib import Path
import json
import asyncio

import scrapy
from itemadapter import ItemAdapter


class NkprojectPipeline:
    """Nike项目数据处理管道 - 异步版本"""

    def __init__(self):
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)

        # 分别处理两个爬虫的数据
        self.nike_products_file = None
        self.sku_products_file = None

        # 数据存储
        self.nike_products_data = []
        self.sku_products_data = []
        
        # 文件锁，防止并发写入问题
        self.file_lock = asyncio.Lock()

    async def open_spider(self, spider):
        """爬虫开始时调用"""
        spider.logger.info(f"Pipeline opened for spider: {spider.name}")

        if spider.name == 'nike_products':
            # 为产品链接爬虫准备文件
            file_path = self.data_dir / 'nike_products.json'
            self.nike_products_file = open(file_path, 'w', encoding='utf-8')
            spider.logger.info(f"Nike products file opened: {file_path}")

        elif spider.name == 'sku_products':
            # 为SKU详情爬虫准备文件
            file_path = self.data_dir / 'sku_products.json'
            self.sku_products_file = open(file_path, 'w', encoding='utf-8')
            spider.logger.info(f"SKU products file opened: {file_path}")

    async def close_spider(self, spider):
        """爬虫结束时调用"""
        if spider.name == 'nike_products' and self.nike_products_file:
            # 保存Nike产品链接数据
            async with self.file_lock:
                json.dump(
                    self.nike_products_data,
                    self.nike_products_file,
                    ensure_ascii=False,
                    indent=2
                )
                self.nike_products_file.close()
            spider.logger.info(f"Nike products saved: {len(self.nike_products_data)} items")

        elif spider.name == 'sku_products' and self.sku_products_file:
            # 保存SKU详情数据
            async with self.file_lock:
                json.dump(
                    self.sku_products_data,
                    self.sku_products_file,
                    ensure_ascii=False,
                    indent=2
                )
                self.sku_products_file.close()
            spider.logger.info(f"SKU products saved: {len(self.sku_products_data)} items")

            # 同时保存为CSV格式
            await self._save_sku_to_csv()

    async def process_item(self, item, spider):
        """处理每个item"""
        adapter = ItemAdapter(item)

        if spider.name == 'nike_products':
            # 处理Nike产品链接数据
            processed_item = await self._process_nike_product_item(adapter, spider)
            async with self.file_lock:
                self.nike_products_data.append(processed_item)

        elif spider.name == 'sku_products':
            # 处理SKU详情数据
            processed_item = await self._process_sku_item(adapter, spider)
            async with self.file_lock:
                self.sku_products_data.append(processed_item)

        return item

    async def _process_nike_product_item(self, adapter, spider):
        """处理Nike产品链接数据"""
        item_dict = dict(adapter)

        # 数据验证和清洗
        if 'product_links' not in item_dict:
            item_dict['product_links'] = []

        if 'link_count' not in item_dict:
            item_dict['link_count'] = len(item_dict.get('product_links', []))

        # 添加处理时间戳
        item_dict['processed_at'] = datetime.now().isoformat()

        spider.logger.info(f"Processed Nike product item: {item_dict['link_count']} links")
        return item_dict

    async def _process_sku_item(self, adapter, spider):
        """处理SKU详情数据"""
        item_dict = dict(adapter)

        # 数据清洗
        if 'title' in item_dict and item_dict['title']:
            item_dict['title'] = item_dict['title'].strip()

        if 'price' in item_dict and item_dict['price']:
            item_dict['price'] = item_dict['price'].strip()

        if 'details' in item_dict and item_dict['details']:
            item_dict['details'] = item_dict['details'].strip()

        # 确保size是列表
        if 'size' in item_dict and not isinstance(item_dict['size'], list):
            item_dict['size'] = [item_dict['size']] if item_dict['size'] else []

        # 确保img_urls是列表
        if 'img_urls' in item_dict and not isinstance(item_dict['img_urls'], list):
            item_dict['img_urls'] = [item_dict['img_urls']] if item_dict['img_urls'] else []

        # 添加处理时间戳
        item_dict['processed_at'] = datetime.now().isoformat()

        spider.logger.info(f"Processed SKU item: {item_dict.get('title', 'Unknown')}")
        return item_dict

    async def _save_sku_to_csv(self):
        """将SKU数据保存为CSV格式"""
        try:
            import csv

            if not self.sku_products_data:
                return

            csv_file = self.data_dir / 'sku_products.csv'

            # 获取所有字段名
            fieldnames = set()
            for item in self.sku_products_data:
                fieldnames.update(item.keys())
            fieldnames = sorted(list(fieldnames))

            # 使用异步文件操作
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_csv, csv_file, fieldnames)

            print(f"SKU data saved to CSV: {csv_file}")

        except Exception as e:
            print(f"Error saving CSV: {e}")
            
    def _write_csv(self, csv_file, fieldnames):
        """在执行器中运行的同步CSV写入函数"""
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in self.sku_products_data:
                # 处理列表字段
                row = item.copy()
                for key, value in row.items():
                    if isinstance(value, list):
                        row[key] = ', '.join(str(v) for v in value)
                writer.writerow(row)


# 其他管道类也需要类似的异步改造
class DataValidationPipeline:
    """数据验证管道"""

    async def process_item(self, item, spider):
        """验证数据完整性"""
        adapter = ItemAdapter(item)

        if spider.name == 'nike_products':
            # 验证Nike产品数据
            if not adapter.get('product_links'):
                spider.logger.warning("Item missing product_links")

            if adapter.get('status') == 'error':
                spider.logger.error(f"Error item: {adapter.get('error')}")

        elif spider.name == 'sku_products':
            # 验证SKU数据
            required_fields = ['url', 'title']
            missing_fields = []

            for field in required_fields:
                if not adapter.get(field):
                    missing_fields.append(field)

            if missing_fields:
                spider.logger.warning(f"Item missing fields: {missing_fields}")

        return item


class DuplicatesPipeline:
    """去重管道"""

    def __init__(self):
        self.seen_urls = set()
        self.lock = asyncio.Lock()

    async def process_item(self, item, spider):
        """去除重复的URL"""
        adapter = ItemAdapter(item)

        if spider.name == 'sku_products':
            url = adapter.get('url')
            if url:
                async with self.lock:
                    if url in self.seen_urls:
                        spider.logger.debug(f"Duplicate item found: {url}")
                        raise scrapy.exceptions.DropItem(f"Duplicate item: {url}")
                    else:
                        self.seen_urls.add(url)

        return item


class StatsPipeline:
    """统计管道"""

    def __init__(self):
        self.stats = {
            'nike_products': {'processed': 0, 'errors': 0},
            'sku_products': {'processed': 0, 'errors': 0, 'duplicates': 0}
        }
        self.lock = asyncio.Lock()

    async def process_item(self, item, spider):
        """收集统计信息"""
        adapter = ItemAdapter(item)

        if spider.name in self.stats:
            async with self.lock:
                self.stats[spider.name]['processed'] += 1

                if adapter.get('error'):
                    self.stats[spider.name]['errors'] += 1

        return item

    async def close_spider(self, spider):
        """输出统计信息"""
        if spider.name in self.stats:
            stats = self.stats[spider.name]
            spider.logger.info(f"Pipeline Stats for {spider.name}:")
            spider.logger.info(f"  - Processed: {stats['processed']}")
            spider.logger.info(f"  - Errors: {stats['errors']}")
            if 'duplicates' in stats:
                spider.logger.info(f"  - Duplicates: {stats['duplicates']}")