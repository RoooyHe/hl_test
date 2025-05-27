# hl_test

#### Q1 : Scrapy爬取测试

    1. 通过 scrapy 实现网页信息爬取和采集。
    2. 通过提供的列表页网址采集到详情页的信息。
    3. 爬取结果存成一份 JSON文档。
    4. JSON文档要求： 主要信息（标题（title） 价格(price) 颜色(color) 尺码(size) 网站货号(sku) 详情(details) 大图的URL (img_urls)，其它字段随意
    5. 抓取前48个
    6. 要爬取的地址
        网站 https://www.nike.com.cn/
        列表页网址 https://www.nike.com.cn/w/

#### A : 
  将爬取过程拆分为 获取商品网址 和 获取商品详情
在[spider.py](https://github.com/RoooyHe/hl_test/blob/main/hl/hl/spiders/spider.py) 中 两个类 NikeSpider 和 SkuSpider 分别完成两个部分
抓取 JS 渲染数据，如单页加载24个商品需要爬取48个的问题和商品尺码和图片URL通过接口返回JS加载的问题，通过Selenuim + Scrapy的方式实现 
可以使用 [.bat](https://github.com/RoooyHe/hl_test/blob/main/hl/hl/spiders/.bat) 测试

#### Q2 : 算法

     Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.You may assume that each input would have exactly one solution, and you may not use the same element twice.You can return the answer in any order.
        Example1:
        Input: nums = [2,7,11,15], target = 9
        Output: [0,1]
        Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].
        Constraints:
            2 <= nums.length <= 104
            -109 <= nums[i] <= 109
            -109 <= target <= 109
            Only one valid answer exists.

#### A :
非常经典Leetcode算法题 一般做法是Hash表和暴力求解两种 [two_sum.py](https://github.com/RoooyHe/hl_test/blob/main/two_sum.py)
暴力求解 时间复杂度 O(N²) 空间复杂度 O(1)
哈希表 时间复杂度 O(N) 空间复杂度 O(N)

#### Q3 : Linux
    编写一个shell脚本(linux)，功能如下:
    在给定文件中搜索指定内容，并将搜索结果(含内容出现的行号)保存到新的文件中，同时结果输出到控制台

#### A :

用法：$0 <文件名> <搜索内容>
[search.sh](https://github.com/RoooyHe/hl_test/blob/main/search.sh)

![image](https://github.com/user-attachments/assets/5d768906-a353-4acf-8f3c-177fe1c6dd38)


