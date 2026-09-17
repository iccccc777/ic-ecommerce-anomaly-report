# PostgreSQL 方言

本目录提供与 SQLite/MySQL 等价的 PostgreSQL 建表和查询脚本。

日期统一使用：

```sql
TO_TIMESTAMP(timestamps::DOUBLE PRECISION)
    AT TIME ZONE 'Asia/Shanghai'
```

当前机器未运行 PostgreSQL，因此本目录完成静态可移植性测试，未执行真实 PostgreSQL 实例验证。
