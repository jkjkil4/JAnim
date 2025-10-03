import subprocess as sp

# 得到所有 tag 的 hash，按照时间顺序排列，越新的在越前面
result = sp.run(['git', 'rev-list', '--abbrev-commit', '--tags', '--no-walk'], stdout=sp.PIPE, text=True)
hashes = result.stdout.splitlines()

# 得到 v2.1.0 的 hash
result = sp.run(['git', 'rev-list', '-n', '1', 'v2.1.0'], stdout=sp.PIPE, text=True)
hash_210 = result.stdout.strip()

# 得到 v2.1.0 之后的所有 hash，写入 .asv/tag_hashes.txt
with open('.asv/tag_hashes.txt', 'wt') as f:
    for h in hashes:
        if hash_210.startswith(h):
            break
        f.write(h + '\n')
