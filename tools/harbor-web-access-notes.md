# Harbor Job 的 Web 访问笔记

> 整理日期：2026-10-04 ｜ 环境：远程 Linux 服务器（SSH 使用，中国网络环境）、Harbor 0.23.0（uv tool 安装）、Docker
>
> "job 的 web 访问"在本笔记中指两件事，两方向都已实际验证：
> 1. **用浏览器查看 job** —— `harbor view` 查看器（主要需求）
> 2. **job 容器访问外网** —— v2ray 代理链方案（供容器内 agent 下载/联网）

---

## 一、harbor view：用浏览器查看 job

### 1. 是什么

Harbor 自带的 Web 查看器，用于浏览 `jobs` 目录下的所有 job / trial：轨迹（trajectory）、reward、日志，也能浏览任务定义。

- 实现：FastAPI（uvicorn）+ **随安装包一起分发的已构建前端**（`harbor/viewer/static`），开箱即用，**不需要 bun/node**（`--dev` 开发模式才需要 bun）。
- 注意它**不只是只读**：页面上可以直接发起 run、上传结果、删除 job。

### 2. 启动

```bash
cd ~/harbor-test
harbor view                                    # 默认目录 ./jobs，端口从 8080-8089 自动挑空闲
harbor view jobs --port 8080                   # 固定端口
harbor view /path/to/official-tasks --tasks    # 浏览任务定义（而非 job）
```

- 目录参数必须是**包含子目录的文件夹**：子目录含 `config.json` → jobs 模式；含 `task.toml` → tasks 模式。自动探测，可用 `--tasks` / `--jobs` 强制。
- 默认只监听 `127.0.0.1`，启动后输出 `Server: http://127.0.0.1:8080`。

### 3. 从笔记本远程访问（服务器是 SSH 远程机器）

**方式 A：SSH 隧道（推荐）**

```bash
ssh -N -L 8080:127.0.0.1:8080 tyu@<服务器IP>
# 本地浏览器打开 http://localhost:8080
```

或固化到 `~/.ssh/config`，以后连服务器自动带上：

```
Host myserver
    HostName <服务器IP>
    LocalForward 8080 127.0.0.1:8080
```

**方式 B：直接绑局域网**

```bash
harbor view --host 0.0.0.0 --port 8080     # 浏览器开 http://<服务器IP>:8080
```

### 4. ⚠️ 安全注意（重要）

- 查看器**没有登录认证**。
- API 含写操作：`POST /api/run`（从网页直接跑 job）、`POST /api/jobs/{name}/upload`、`DELETE /api/jobs/{name}` 等。已有的跨源保护只拦带 Origin 的浏览器跨站请求，挡不住局域网内直接 curl 的人。
- trajectory 里可能含敏感内容（指令、命令输出、日志）。
- **结论：优先 SSH 隧道；若必须 `--host 0.0.0.0`，用防火墙限制来源 IP，不要长期裸绑。**

### 5. 常驻运行

简单法：

```bash
tmux new -d -s viewer 'harbor view --port 8080'
```

systemd user service（`~/.config/systemd/user/harbor-view.service`）：

```ini
[Unit]
Description=Harbor job viewer
After=network.target

[Service]
WorkingDirectory=%h/harbor-test
ExecStart=%h/.local/bin/harbor view jobs --port 8080
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now harbor-view
loginctl enable-linger tyu    # 需要"不登录也常跑"时
```

### 6. 实测记录（2026-10-04）

- `harbor view jobs --port 8099` 启动正常：`/` 返回 200（静态前端），`/api/jobs` 列出全部 job（含 humanevalfix-python-0），`/api/health` ok。
- 默认端口段 8080-8089 会自动避让占用；结束后 Ctrl+C 或按端口找进程 kill。

---

## 二、附：job 容器访问外网（v2ray 代理链方案）

### 1. 背景

- 容器直连时国际站点（GitHub、downloads.claude.ai、Harbor Hub 等）不可达。
- 宿主机已有 v2ray 服务（`127.0.0.1:10808` socks / `10809` http，带分流，走 SS 节点；详见 `proxy-setup-notes.md`），但**只监听回环，容器够不着**。
- 方案：另起一个 v2ray 实例，专门监听 docker 网桥网关，供容器使用。

### 2. 链路

```
容器内程序（读 HTTP(S)_PROXY）
   └─► http://172.17.0.1:10810          # chain 实例（HTTP 入站，监听 docker0 网关）
          └─► socks-out ► 127.0.0.1:10808   # 主 v2ray（systemd: v2ray.service）
                 └─► SS 节点 ► 境外出口
```

- **为什么 172.17.0.1 容器可达**：它是宿主机 docker0 的地址。容器发往宿主机自身 IP 的包走 INPUT 路径，不受 DOCKER-ISOLATION（只影响跨网桥 FORWARD）限制 —— 自定义 docker 网络（harbor 的 compose 网络）里同样可用。
- 当前状态：chain 配置在 `/tmp/v2ray-chain-test.json`，是**临时用户态进程，重启即失**。

### 3. Harbor 侧的注入方式（三级 env）

| 目标 | 方法 |
|---|---|
| agent 进程 | `--ae/--agent-env HTTP_PROXY=... --ae HTTPS_PROXY=... --ae NO_PROXY=api.deepseek.com,...` |
| verifier | `--ve/--verifier-env ...` |
| 主容器进程 | job 配置里的 `environment.env` |
| 备注 | `--env-file` 是加载进 harbor **本地进程**环境（适合放 API key），不是容器 env |

- **`no_proxy` 必须包含 `api.deepseek.com`**：模型 API（`ANTHROPIC_BASE_URL` 指向其 Anthropic 兼容端点）必须直连，走代理会绕路甚至失败；`localhost,127.0.0.1,::1` 同理。
- 大小写两套变量（`HTTP_PROXY`/`http_proxy`）都注入更稳（不同程序认的不一样）。

### 4. 实测

- 新建独立 docker 网络起 `python:3.12-bookworm` 容器，经 `http://172.17.0.1:10810` 出网：出口 IP `97.64.23.x`（美国节点），`hub.harborframework.com` HTTP 200。
- humanevalfix job 容器内 Claude Code bootstrap（downloads.claude.ai）经代理下载成功。

### 5. 生产化待办

1. `/tmp/v2ray-chain-test.json` 挪到 `/etc/v2ray/` 并做成 systemd unit（`After=docker.service`，否则开机时 docker0 未就绪、绑定 172.17.0.1 会失败）。
2. **只监听 `172.17.0.1`，绝不 `0.0.0.0`**（否则整个局域网都能白嫖代理）。
3. docker0 网段若有变动，需同步更新 job 的代理 env。
4. 若之后启用 Harbor 的 egress 白名单（`--allow-environment-host` / `--allow-agent-host`），记得放行代理地址与目标域名。
5. 验证命令：

```bash
docker run --rm -e HTTPS_PROXY=http://172.17.0.1:10810 python:3.12-bookworm \
  python -c "import urllib.request;print(urllib.request.urlopen('https://api.ipify.org',timeout=20).read().decode())"
```

---

## 三、速查表

| 事项 | 命令 / 值 |
|---|---|
| 起查看器 | `harbor view [folder] [-p 8080] [--host 127.0.0.1]` |
| 远程访问（推荐） | `ssh -L 8080:127.0.0.1:8080 tyu@<服务器IP>` |
| 查看器默认 | 目录 `./jobs`；端口 8080-8089 自动选；监听 127.0.0.1 |
| 查看任务定义 | `harbor view <tasks目录> --tasks` |
| 容器代理入口 | `http://172.17.0.1:10810`（chain 实例，当前 /tmp 临时） |
| 代理注入 | `--ae` / `--ve` / job 配置 `environment.env` |
| 必须直连 | `api.deepseek.com`（no_proxy 内） |
