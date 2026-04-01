# Publishing To GitHub

这套仓库更适合被发布成一个 **starter repo / template repo**，而不是“你团队内部 Base 的完整镜像”。

## 推荐定位

仓库名建议：

- `feishu-content-intel-starter`
- `feishu-topic-radar`
- `lark-content-intel-pipeline`

一句话描述建议：

> Collect public music signals into Feishu Base, generate weekly topic packets, and write topic ideas back into the same workflow.

## 发布前先确认不要提交什么

已经在 `.gitignore` 里的：

- `config/*.local.json`
- `data/*.json`
- `data/*.md`

发布前还要人工检查：

- 不要提交你自己的 `base_token`
- 不要提交你自己的 `table_id` / `view_id`
- 不要提交真实用户授权后的配置文件
- 不要提交带团队隐私内容的周报或样本数据

## 建议保留在公开仓库里的内容

- `README.md`
- `config/intel_v1.example.json`
- `scripts/*.py`
- `scripts/run_intel_pipeline.sh`
- `prompts/weekly_topic_prompt.md`
- `docs/BASE_SCHEMA.md`
- `docs/PUBLISHING.md`
- `Makefile`

## README 应该回答的 4 个问题

1. 这个仓库是干什么的
2. 别人需要先准备什么
3. 最短路径怎么跑起来
4. 数据会写到哪里

## 最适合别人使用的方式

### 方式 A：直接用你这个 starter repo

1. fork / use this template
2. 安装并授权 `lark-cli`
3. 在飞书里建一张符合 `docs/BASE_SCHEMA.md` 的表
4. 复制 `config/intel_v1.example.json` 为本地配置
5. 运行 `make dry-run` / `make pipeline`

### 方式 B：只复用思路

适合别人已经有自己的 Base，只想借你这套：

- 采集逻辑
- 周报生成逻辑
- 选题回写逻辑

这种情况下，让他们只改：

- 字段名
- Base token / table id / view id
- sources 和 keywords

## 你自己上传 GitHub 的最小步骤

```bash
cd /path/to/feishu-team
git init
git add .
git commit -m "Initial public starter repo"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

## 推荐再补的仓库元信息

- 许可证：MIT 或 Apache-2.0 二选一
- `SECURITY.md`：说明不要提交授权信息
- GitHub Topics：
  - `feishu`
  - `lark`
  - `content-strategy`
  - `rss`
  - `automation`
  - `python`

## 现实建议

如果你的目标是“让别人真的能用”，最重要的不是把代码发出去，而是把下面两件事讲清楚：

1. **Base 要长什么样**
2. **别人第一次跑什么命令**

所以这两个文件最关键：

- `README.md`
- `docs/BASE_SCHEMA.md`
