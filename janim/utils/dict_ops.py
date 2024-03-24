import itertools as it


def merge_dicts_recursively(*dicts: dict) -> dict:
    '''
    递归合并字典

    - 创建一个字典，其键集是所有输入字典的并集
    - 在列表中位置越靠后的字典具有更高的优先级
    - 当值为字典时，将递归应用
    '''
    result = {}
    all_items = it.chain(*[d.items() for d in dicts])
    for key, value in all_items:
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts_recursively(result[key], value)
        else:
            result[key] = value
    return result
