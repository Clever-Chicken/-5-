from time import perf_counter

from app.name_match import group_donor_names, normalize_donor_name


def test_normalize_donor_name_removes_space_punctuation_and_suffix_words():
    assert normalize_donor_name(" 新加坡·李氏基金会 ") == "新加坡李氏"


def test_group_donor_names_merges_contained_foundation_names():
    names = ["李氏基金", "新加坡李氏基金", "陈嘉庚"]

    groups = group_donor_names(names)

    assert groups["李氏基金"] == "新加坡李氏基金"
    assert groups["新加坡李氏基金"] == "新加坡李氏基金"
    assert groups["陈嘉庚"] == "陈嘉庚"


def test_group_donor_names_keeps_unrelated_names_separate():
    names = ["李氏基金", "王氏基金", "李明"]

    groups = group_donor_names(names)

    assert groups["李氏基金"] == "李氏基金"
    assert groups["王氏基金"] == "王氏基金"
    assert groups["李明"] == "李明"


def test_group_donor_names_does_not_merge_person_into_project_name():
    names = ["张三", "厦门大学张三奖学金"]

    groups = group_donor_names(names)

    assert groups["张三"] == "张三"
    assert groups["厦门大学张三奖学金"] == "厦门大学张三奖学金"


def _reference_group_donor_names(names):
    unique_names = [name for name in dict.fromkeys(names) if name]
    normalized = {name: normalize_donor_name(name) for name in unique_names}
    groups = {}
    for name in unique_names:
        canonical = name
        for candidate in unique_names:
            if "基金" not in name or "基金" not in candidate:
                continue
            left = normalized[name]
            right = normalized[candidate]
            if left and right and (left in right or right in left):
                if len(candidate) > len(canonical) or (
                    len(candidate) == len(canonical) and candidate < canonical
                ):
                    canonical = candidate
        groups[name] = canonical
    return groups


def test_group_donor_names_matches_reference_for_constructed_foundation_names():
    names = [
        "李氏基金",
        "新加坡李氏基金",
        "厦门李氏基金会",
        "王氏基金",
        "香港王氏基金会",
        "张三",
        "厦门大学张三奖学金",
        "陈嘉庚基金会",
        "厦门陈嘉庚基金会",
    ]

    assert group_donor_names(names) == _reference_group_donor_names(names)


def test_group_donor_names_scales_to_many_unrelated_foundation_names():
    names = [f"测试{i:05d}基金" for i in range(6000)]

    start = perf_counter()
    groups = group_donor_names(names)
    elapsed = perf_counter() - start

    assert len(groups) == len(names)
    assert groups["测试00000基金"] == "测试00000基金"
    assert groups["测试05999基金"] == "测试05999基金"
    assert elapsed < 1.0
