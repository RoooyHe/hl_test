# Scrapy settings for nkproject project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "nkproject"

SPIDER_MODULES = ["nkproject.spiders"]
NEWSPIDER_MODULE = "nkproject.spiders"

# Addons
ADDONS = {}

# Obey robots.txt rules (建议设为 False，因为很多商业网站会阻止爬虫)
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 8

# Configure a delay for requests for the same website (default: 0)
# The randomize delay setting will randomize between 0.5 * to 1.5 * DOWNLOAD_DELAY
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

# Reduce concurrent requests per domain
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# AutoThrottle extension settings
# Enable and configure the AutoThrottle extension (disabled by default)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False  # Enable to see throttling stats

# Disable cookies (enabled by default)
COOKIES_ENABLED = True

# Override the default request headers
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Configure pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "nkproject.pipelines.NkprojectPipeline": 300,
}

# Enable and configure spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    "nkproject.middlewares.NkprojectSpiderMiddleware": 543,
}

# Enable and configure downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    # 禁用默认的重试中间件
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,

    # 启用自定义的 Playwright 重试中间件
    "nkproject.middlewares.PlaywrightRetryMiddleware": 200,

    # User-Agent 轮换
    "nkproject.middlewares.UserAgentRotateMiddleware": 300,

    # 页面配置中间件
    "nkproject.middlewares.PlaywrightPageConfigMiddleware": 400,

    # 请求延时中间件
    "nkproject.middlewares.RequestDelayMiddleware": 500,

    # 响应验证中间件
    "nkproject.middlewares.ResponseValidationMiddleware": 600,

    # 保持原有的下载器中间件
    "nkproject.middlewares.NkprojectDownloaderMiddleware": 800,
}

# Playwright 相关配置
# =====================================

# 设置下载处理器
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Twisted 反应器设置
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# Playwright 浏览器类型
PLAYWRIGHT_BROWSER_TYPE = "chromium"

# Playwright 启动选项
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,  # 无头模式，设为 False 可以看到浏览器窗口
    "args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-web-security",
        "--disable-features=VizDisplayCompositor",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-images",  # 禁用图片加载以提高速度
    ],
    "ignoreDefaultArgs": ["--enable-automation"],
    "ignoreHTTPSErrors": True,
}

# Playwright 上下文设置
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000  # 30秒
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "ignore_https_errors": True,
        "java_script_enabled": True,
        "accept_downloads": False,
    },
}

# 重试相关设置
# =====================================
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]
RETRY_PRIORITY_ADJUST = -1

# 下载超时设置
DOWNLOAD_TIMEOUT = 60

# DNS 超时设置
DNS_TIMEOUT = 60

# 缓存设置
# =====================================
# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600  # 1小时
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [503, 504, 505, 500, 403, 404, 408, 429]

# 数据导出设置
# =====================================
FEED_EXPORT_ENCODING = "utf-8"

# 支持的导出格式
FEEDS = {
    "data/nike_products.json": {
        "format": "json",
        "encoding": "utf8",
        "store_empty": False,
        "item_export_kwargs": {
            "ensure_ascii": False,
            "indent": 2,
        },
    },
    "data/nike_products.csv": {
        "format": "csv",
        "encoding": "utf8",
        "store_empty": False,
    },
}

# 日志设置
# =====================================
#LOG_LEVEL = "INFO"
#LOG_FILE = "logs/scrapy.log"

# Stats 设置
# =====================================
STATS_CLASS = "scrapy.statscollectors.MemoryStatsCollector"

# 内存使用限制
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048
MEMUSAGE_WARNING_MB = 1024

# Telnet Console 设置
TELNETCONSOLE_ENABLED = False

# Extensions 设置
# =====================================
EXTENSIONS = {
    "scrapy.extensions.telnet.TelnetConsole": None,
    "scrapy.extensions.corestats.CoreStats": 0,
    "scrapy.extensions.memusage.MemoryUsage": 0,
}

# Request fingerprinting
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"

# 其他设置
# =====================================
# 禁用重定向
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 3

# Media pipeline 设置（如果需要下载图片）
# ITEM_PIPELINES.update({
#     'scrapy.pipelines.images.ImagesPipeline': 1,
# })
# IMAGES_STORE = 'images'
# IMAGES_EXPIRES = 90

# 代理设置（如果需要使用代理）
# DOWNLOADER_MIDDLEWARES.update({
#     'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
# })

# 如果在调试模式下运行
import os

if os.getenv('SCRAPY_DEBUG'):
    LOG_LEVEL = "DEBUG"
    PLAYWRIGHT_LAUNCH_OPTIONS["headless"] = False
    AUTOTHROTTLE_DEBUG = True