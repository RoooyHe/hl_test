#!/bin/bash

# 参数检查：必须包含文件名和搜索内容
if [ $# -ne 2 ]; then
    echo "用法：$0 <文件名> <搜索内容>"
    exit 1
fi

input_file="$1"
search_content="$2"
timestamp=$(date +%Y%m%d%H%M%S)
output_file="${input_file}_search_result_${timestamp}.txt"

# 文件存在性检查
if [ ! -f "$input_file" ]; then
    echo "错误：文件 $input_file 不存在。"
    exit 1
fi

# 文件可读性检查
if [ ! -r "$input_file" ]; then
    echo "错误：无法读取文件 $input_file。"
    exit 1
fi

# 执行搜索并捕获结果
results=$(grep -n -- "$search_content" "$input_file" 2>/dev/null)

# 结果处理
if [ -z "$results" ]; then
    echo "在文件 $input_file 中未找到内容：$search_content"
else
    echo "搜索结果："
    echo "$results" | tee "$output_file"
    echo -e "\n搜索结果已保存到：$output_file"
fi