from typing import List


def two_sum(nums: List[int], target: int) -> List[int]:
    hashtable = dict()
    for i, num in enumerate(nums):
        if target - num in hashtable:
            return [hashtable[target - num], i]
        hashtable[nums[i]] = i
    return []


if __name__ == '__main__':
    print(two_sum(nums=[2, 7, 11, 15], target=9))
    print(two_sum(nums=[3,2,4], target=6))
    print(two_sum(nums=[3,3], target=6))
