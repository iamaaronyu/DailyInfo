# V2Ray 代理配置记录（2026-10-04）

> 本机（Linux，SSH 远程使用，中国网络环境）代理服务的完整配置过程、当前状态与后续维护要点。
> 供后续分析/排障/更换节点时参考。

---

## 一、背景与症状

- 本机通过 v2ray 提供本地代理：`127.0.0.1:10809`（HTTP）、`127.0.0.1:10808`（SOCKS5），仅监听回环地址。
- 代理服务（systemd 的 `v2ray.service`）一直在运行、端口也正常监听，但 **上游节点已失效**：
  - 现象：连接代理端口成功，但转发全部失败（连 example.com 都超时）。
  - 影响：GitHub、Google、Harbor Hub（hub.harborframework.com）等国际站点全部不可达。
- 旧配置为 2024-10-13 写入，其上游 SS 节点已不可用。

## 二、配置过程（时间线）

### 1. 获取新节点
用户提供新的 Shadowsocks 订阅链接（SIP002 格式）。

> ⚠️ 该链接为 base64 编码，**解码后即含节点密码** —— 本文档不收录其内容；需要时请见 `/etc/v2ray/config.json`。

解码后参数（敏感项已隐去）：
| 项 | 值 |
|---|---|
| 加密方式 | `aes-256-gcm` |
| 服务器 | `<订阅节点主机（名称已隐去）>` |
| 端口 | `20728` |
| 密码 | （存于 `/etc/v2ray/config.json`，为安全起见不在本文重复） |

### 2. 生成新配置（保留原有分流规则）
生成 `/tmp/v2ray-config-new.json`，与旧配置结构一致：

- **入站（inbounds）**：不变 —— 10808 socks / 10809 http，仅 `127.0.0.1`。
- **出站（outbounds）**：
  - `proxy` → shadowsocks（新节点参数）
  - `direct` → freedom（直连）
  - `block` → blackhole
- **路由（routing）**：保留原分流规则（关键！）：
  - `geosite:cn` 域名 → 直连
  - `geoip:cn` + `geoip:private` → 直连
  - 其余流量 → 走代理
- 依赖的 geo 数据：`/usr/local/bin/geosite.dat`、`/usr/local/bin/geoip.dat`。

### 3. 部署前验证（免 sudo 技巧）
**不碰系统服务、不需要 sudo**：用同一份配置在非特权端口起临时实例验证节点可用性：

```bash
# 把测试配置的入站端口改为 10818(socks)/10819(http)，其余不变
nohup /usr/local/bin/v2ray -config /tmp/v2ray-config-test.json > /tmp/v2ray-test.log 2>&1 &
# 通过 10819 测试
curl -x http://127.0.0.1:10819 https://example.com
```

验证结果（全部通过后才动系统服务）：
| 目标 | 结果 |
|---|---|
| example.com | HTTP 200 |
| github.com | HTTP 200 |
| hub.harborframework.com | HTTP 200 |
| baidu.com（应走直连） | HTTP 200 |
| 代理出口 IP | `97.64.23.x`（美国洛杉矶，末段已隐去），对比直连出口 `125.120.28.x`（浙江杭州电信，末段已隐去） |

### 4. 部署到系统服务（需 sudo）
用脚本 `/tmp/deploy-v2ray.sh` 完成（在用户终端里以 `sudo bash /tmp/deploy-v2ray.sh` 执行）：

```bash
# 1) 备份旧配置（cp -a 保留原时间戳；脚本带"已存在则不覆盖"保护）
cp -a /etc/v2ray/config.json /etc/v2ray/config.json.bak-20261004
# 2) 安装新配置
cp /tmp/v2ray-config-new.json /etc/v2ray/config.json && chmod 644 /etc/v2ray/config.json
# 3) 重启并验证
systemctl restart v2ray && systemctl is-active v2ray   # 期望输出 active
ss -tln | grep -E '10808|10809'                        # 期望两个端口在听
```

### 5. 部署后验证（系统端口 10809）
| 目标 | 结果 |
|---|---|
| example.com / github.com / hub.harborframework.com | HTTP 200 |
| raw.githubusercontent.com（Harbor 官方 registry） | HTTP 200 |
| baidu.com | HTTP 200（0.37s，直连不减速） |
| api.deepseek.com | 网络通（401 = 无 key，属正常） |
| SOCKS 端口 10808 测试 | 通过 |
| 代理出口 IP | 美国洛杉矶 `97.64.23.x`（末段已隐去） |
| 流量确实经过代理 | `curl -v` 显示 `Connected to 127.0.0.1 ... port 10809` |

### 6. 收尾
- 临时实例（10818/10819）已停止，临时文件已清理。
- `v2ray.service` 为 `enabled`（开机自启），重启机器后自动恢复。

---

## 三、当前架构与文件清单

```
┌──────────────┐   SSH 终端/程序
│ 127.0.0.1:10809 (http)  ← ~/.bashrc 自动 export
│ 127.0.0.1:10808 (socks)    代理环境变量指向这里
└──────┬───────┘
       │ v2ray 4.28.2（systemd, root）
       │ 配置: /etc/v2ray/config.json
       │ 分流: geosite:cn / geoip:cn → 直连；其余 → SS 节点
       ▼
  <订阅节点主机>:20728 (aes-256-gcm) → 美国洛杉矶出口
```

| 项目 | 路径/值 |
|---|---|
| v2ray 程序 | `/usr/local/bin/v2ray`（V2Ray 4.28.2） |
| 服务 | `/etc/systemd/system/v2ray.service`（root 运行，enabled 自启） |
| 现用配置 | `/etc/v2ray/config.json`（644，可直接 cat 查看） |
| 旧配置备份 | `/etc/v2ray/config.json.bak-20261004`（本次换节点前的） |
| 更早备份 | `/etc/v2ray/config.json.bak`（2024 年） |
| geo 数据 | `/usr/local/bin/geosite.dat`、`geoip.dat` |
| 代理环境变量 | `~/.bashrc` 第 136-141 行（源自 2026-10-03） |
| 服务日志 | `journalctl -u v2ray` |

`~/.bashrc` 中的代理设置（**交互式 shell 自动生效**）：

```bash
export http_proxy="http://127.0.0.1:10809"
export https_proxy="http://127.0.0.1:10809"
export ftp_proxy="http://127.0.0.1:10809"
export ALL_PROXY="socks5://127.0.0.1:10808"
export no_proxy="localhost,127.0.0.1,::1,api.deepseek.com,deepseek.com"
```

> `no_proxy` 特意排除了 deepseek.com —— 本机跑 Harbor/Claude Code 任务要用 DeepSeek API，让它完全绕过代理直连。

---

## 四、日常验证方法（3 条命令）

```bash
# 1. 出口 IP（最快判定）；新 SSH 里环境变量已自动生效，无需 -x
curl -s -m 12 https://api.ipify.org; echo
#   期望：境外 IP（如 97.64.23.x）；若返回国内 IP 或超时 = 有问题

# 2. 目标站点连通
curl -I -m 12 https://github.com              # 期望 HTTP/2 200
curl -I -m 12 https://hub.harborframework.com # 期望 HTTP/2 200

# 3. 确认走了代理端口
curl -v -m 12 -o /dev/null https://github.com 2>&1 | grep -i "connected to"
#   期望：Connected to 127.0.0.1 (127.0.0.1) port 10809
```

---

## 五、关键注意点（后续维护必读）

### 1. 节点有效性 = 一切的前提
现用节点来自商业订阅服务（服务商名称已隐去）。**过期、换线路、被封都会导致代理再次全断**。
- 症状识别：端口在听但所有国际站点超时（可能连国内直连站点也不受影响）。
- 更换方法：拿到新订阅链接后，只改 `/etc/v2ray/config.json` 中 `outbounds` 里 `proxy` 段的 `address/port/method/password`，其余（入站 + 分流规则）不要动，然后 `sudo systemctl restart v2ray`。
- 更换前建议沿用本次的"临时实例预验证"技巧（第二节第 3 步），先在 10818/10819 端口验证新节点，再动系统服务。

### 2. 环境变量加载行为（容易踩的坑）
- ✅ **交互式 SSH 会话**（正常登录打字的那种）：自动从 `~/.bashrc` 加载代理变量 —— 无需任何手动设置。
  - 注：`~/.bashrc` 顶部有"非交互则 return"守卫，但用户用 SSH 登录得到的是交互式 shell，正常生效（已实测）。
- ❌ **非交互式场景不会自动加载**：
  - `ssh 本机 '某命令'`（从其他机器执行单条远程命令）→ 无代理变量，直连 Google 会超时；
  - `cron` 任务、`systemd` 单元、`env -i` 干净环境 → 同样没有。
  - 这些场景需要显式加：`https_proxy=http://127.0.0.1:10809 命令`。
- 判断某程序是否走了代理：`curl -v` 看 "Connected to ... port 10809"，或比对出口 IP。

### 3. 哪些程序"不吃"环境变量
会走代理：curl、wget、git（https 协议）、pip、python requests、node/npm 等绝大多数 CLI。
不走代理（需单独配置）：
- `docker` 守护进程拉镜像（有自己的 proxy 配置文件 `/etc/systemd/system/docker.service.d/`）；
- `ssh` 协议连接（22 端口）等非 HTTP(S) 流量；
- 少数不读 env 的程序。

### 4. 容器与代理是"绝缘"的（重要）
代理监听在 `127.0.0.1`（回环），**Docker 容器内无法访问**（harbor 也不会注入 host-gateway）。
- 因此 Harbor 任务容器不能借助主机代理翻墙；
- 容器的外网策略一直是：走国内镜像源 + 直连 api.deepseek.com（可用的容器网络清单见 Harbor 部署记录）；
- 若将来需要容器访问国际网络，需要额外方案（如容器内直连节点、给 v2ray 加 host-gateway 监听地址等），**不要指望现有回环代理**。

### 5. 回滚方法（换配置出问题时）
```bash
sudo cp -a /etc/v2ray/config.json.bak-20261004 /etc/v2ray/config.json
sudo systemctl restart v2ray
```

### 6. 其他
- `/tmp` 下的部署脚本与临时配置（`/tmp/deploy-v2ray.sh`、`/tmp/v2ray-config-new.json`）**重启后会消失**，属一次性产物；现用配置的真身在 `/etc/v2ray/`，不受影响。
- 本文档中的密码信息刻意未收录，需要时查看 `/etc/v2ray/config.json`（该文件为 644，所有用户可读，如需收紧可 `chmod 600` 并确认服务可读）。

---

## 附：本次事件一句话总结

旧 SS 节点失效导致代理"端口通、网络断" → 用户提供新节点 → 先生成配置并**用免 sudo 的临时实例验证通过** → 备份旧配置后替换 `/etc/v2ray/config.json` 并重启服务 → 全量验证通过（出口 IP 美国洛杉矶，国内外分流正常）。当前 `~/.bashrc` 自动加载代理，新 SSH 开箱即用；**唯一长期依赖是订阅节点保持有效**，失效时按第五.1 节更换。
