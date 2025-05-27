from typing import List


def two_sum_hash(nums: List[int], target: int) -> List[int]:
    hashtable = dict()
    for i, num in enumerate(nums):
        if target - num in hashtable:
            return [hashtable[target - num], i]
        hashtable[nums[i]] = i
    return []


def two_sum_list(nums: List[int], target: int) -> List[int]:
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []


if __name__ == '__main__':
    print(two_sum_hash(nums=[2, 7, 11, 15], target=9))
    print(two_sum_hash(nums=[3, 2, 4], target=6))
    print(two_sum_hash(nums=[3, 3], target=6))
