@echo off
chcp 65001 >nul

scrapy crawl nike_t -O nike.json

IF EXIST "./nike.json" (
    echo 获取商品列表成功 开始获取商品SKU信息

    scrapy crawl sku_products -O sku48.json

    IF EXIST "./sku48.json" (
        echo 获取SKU成功 请检查 sku48.json 文件
    ) ELSE (
        echo 获取SKU失败
    )
) ELSE (
    echo 获取商品列表失败
)
