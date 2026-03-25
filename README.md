# p115offlinebridge

MoviePilot 独立插件仓库：`P115OfflineBridge`（115离线桥接）。

## 目录结构

```text
repo_p115offlinebridge/
├─ package.v2.json
└─ plugins.v2/
   └─ p115offlinebridge/
      ├─ __init__.py
      ├─ adapters.py
      ├─ schemas.py
      ├─ version.py
      ├─ requirements.txt
      ├─ clouddrive_pb2.py
      └─ clouddrive_pb2_grpc.py
```

## 功能

- 默认通过 `P115StrmHelper` 现有 API 提交离线下载任务
- 可切换到 `CloudDrive2 gRPC` 直连提交
- 支持 MoviePilot 系统通知
- 提供插件 API：`/status`、`/submit`
- 提供命令：`/p115_offline <链接>`

## 开发与发布

1. 本地开发目录就是当前仓库根目录。
2. 修改插件代码后，记得同步更新：
   - `plugins.v2/p115offlinebridge/version.py`
   - `package.v2.json` 对应版本号与 history
3. 推送到 GitHub 后，在 MoviePilot 里添加你的仓库地址作为插件仓库。

## 快速初始化 Git

```bash
git init
git add .
git commit -m "feat: init p115offlinebridge"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```
