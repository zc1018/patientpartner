---
name: audio-quote-extractor
description: 从会议录音中提取指定发言人的金句片段，自动剪辑并合并成音频文件，同时生成金句清单文档。
---

# 音频金句提取器

## Overview

从会议录音中提取指定发言人的精彩发言片段，自动剪辑并合并成音频文件，同时生成带时间戳和原文的金句清单文档。

**核心功能：**
- 根据转录文件的时间戳自动剪辑音频
- 多片段合并，片段间可插入静音间隔
- 自动生成结构化的金句清单文档
- 支持多种音频格式（wav, mp3, m4a等）

## When to Use

**使用场景：**
- 领导/嘉宾重要讲话摘录
- 会议精华内容归档
- 培训材料制作
- 播客/节目内容剪辑

**NOT用于：**
- 完整会议录音转录
- 实时录音剪辑
- 复杂音频后期处理（降噪、混音等）

## Prerequisites

**系统依赖：**
```bash
# macOS
brew install ffmpeg

# Linux
apt-get install ffmpeg

# 验证安装
ffmpeg -version
```

## Workflow

### 1. 准备输入文件

**必需文件：**
- **原始音频文件**（.wav/.mp3/.m4a等）
- **转录文档**（包含时间戳和发言人标识）

**转录文档格式要求：**
```markdown
发言人 00:04:43
> "缺结构，看了不知道动作优先级在哪"

发言人 00:05:16
> "就是你要把整个逻辑你试一遍"
```

或标准SRT格式：
```
1
00:04:43,000 --> 00:05:14,000
袁荣: 其实你这块我觉得就是你那个报告...
```

### 2. 确定剪辑片段

**分析转录文档，标记要提取的片段：**

| 片段编号 | 发言人 | 开始时间 | 结束时间 | 核心观点 |
|---------|--------|---------|---------|---------|
| 1 | 袁荣 | 00:04:43 | 00:05:14 | 缺结构 |
| 2 | 袁荣 | 00:05:16 | 00:05:41 | 整个逻辑试一遍 |

**时间戳转换规则：**
- 转录时间 `00:04:43` → ffmpeg参数 `00:04:43`
- 需要稍微前后留白（建议+/- 1-2秒）

### 3. 执行音频剪辑

**步骤一：创建临时目录**
```bash
mkdir -p /tmp/audio_clips_$(date +%s)
cd /tmp/audio_clips_$(date +%s)
```

**步骤二：剪辑单个片段**
```bash
# 基础剪辑命令
ffmpeg -i "input.wav" -ss 00:04:43 -to 00:05:14 -c copy clip1.wav

# 带前后留白的剪辑（推荐）
ffmpeg -i "input.wav" -ss 00:04:41 -to 00:05:16 -c copy clip1.wav
```

**参数说明：**
- `-ss`：开始时间（支持 HH:MM:SS 或秒数）
- `-to`：结束时间
- `-c copy`：直接复制，不重新编码（保持音质，速度快）

**步骤三：创建静音间隔（可选）**
```bash
# 生成0.5秒静音
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 0.5 -c pcm_s16le silence.wav
```

**常用采样率：**
- 16000 Hz（语音，文件小）
- 44100 Hz（CD音质）
- 48000 Hz（专业音频）

### 4. 合并片段

**步骤一：创建合并列表**
```bash
# 创建 concat 列表文件
cat > list.txt << 'EOF'
file 'clip1.wav'
file 'silence.wav'
file 'clip2.wav'
file 'silence.wav'
file 'clip3.wav'
EOF
```

**步骤二：执行合并**
```bash
ffmpeg -f concat -i list.txt -c copy "output.wav"
```

### 5. 生成金句清单文档

**文档结构：**
```markdown
# 袁荣金句清单 - 2026年3月2日

**来源**: 03-02 内部会议
**音频文件**: `袁荣金句_0302.wav`
**总时长**: 约2分54秒

---

## 金句列表

### 1. 缺结构（00:00:00 - 00:00:31）
**时间戳**: 00:04:43 - 00:05:14
**原文**:
> "其实你这块我觉得就是你那个报告刚看了一下，就是缺结构..."

**核心观点**: 报告缺乏结构，数据与结论脱节

---

### 2. 整个逻辑试一遍（00:00:31 - 00:00:56）
...

## 核心主题总结

### 关键词
框架、结构、逻辑、结论

### 核心方法论
1. 先有框架，再有动作
2. 数据服务于框架
```

## Common Scenarios

### 场景1：提取领导讲话金句

**输入：**
- 音频：`2026-03-02 10_00_51.wav`
- 转录：`03-02 内部会议.md`
- 目标发言人：袁荣

**处理流程：**
1. 从转录中筛选袁荣的发言段落
2. 标记精彩语句的时间戳（约8段）
3. 使用 ffmpeg 批量剪辑
4. 合并并插入0.5秒静音
5. 生成金句清单文档

**输出：**
- `袁荣金句_0302.wav`（约3分钟）
- `袁荣金句清单_0302.md`

### 场景2：提取多个发言人

**处理方式：**
- 为每个发言人分别生成独立音频文件
- 或使用文件名区分：`金句_袁荣_0302.wav`, `金句_刘红娇_0302.wav`

### 场景3：调整片段间隔

**静音时长调整：**
```bash
# 1秒间隔
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 1.0 -c pcm_s16le silence.wav

# 2秒间隔
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 2.0 -c pcm_s16le silence.wav
```

## Technical Reference

### ffmpeg 常用命令

**查看音频信息：**
```bash
ffprobe -i "input.wav" -show_format -show_streams
```

**剪辑精度说明：**
- `-c copy` 模式：快速但可能有1-2秒误差（关键帧限制）
- 重新编码：精准但慢
```bash
# 精准剪辑（重新编码）
ffmpeg -i "input.wav" -ss 00:04:43.500 -to 00:05:14.250 -c:a pcm_s16le clip1.wav
```

**格式转换：**
```bash
# 输出为mp3
ffmpeg -f concat -i list.txt -c:a libmp3lame -b:a 128k "output.mp3"
```

### 文件命名规范

**输出文件名：**
```
{发言人}金句_{日期}.{格式}
示例：袁荣金句_0302.wav

{发言人}金句清单_{日期}.md
示例：袁荣金句清单_0302.md
```

**临时文件：**
```
/tmp/audio_clips_{timestamp}/
  ├── clip1.wav
  ├── clip2.wav
  ├── silence.wav
  └── list.txt
```

## Common Mistakes

**❌ 错误做法：**
- 时间戳精确到毫秒但使用 `-c copy`（会有偏差）
- 忘记插入静音间隔，导致片段粘连
- 不保留原始音频备份
- 时间戳前后没有留白，截断发言

**✅ 正确做法：**
- 时间戳前后留1-2秒缓冲
- 使用 `-c copy` 保持音质和速度
- 保留完整转录原文
- 生成结构化的金句清单

## Implementation Example

**完整执行流程（Bash）：**

```bash
#!/bin/bash

# 配置
AUDIO_FILE="/Users/xdf/Downloads/2026-03-02 10_00_51.wav"
OUTPUT_DIR="/Users/xdf/Documents/XDF/OPE"
SPEAKER="袁荣"
DATE="0302"

# 创建临时目录
TMP_DIR="/tmp/audio_clips_$(date +%s)"
mkdir -p "$TMP_DIR"
cd "$TMP_DIR"

# 定义片段（开始时间 结束时间）
declare -a CLIPS=(
  "00:04:43 00:05:14"
  "00:05:16 00:05:41"
  "00:05:54 00:06:12"
  "00:06:12 00:06:40"
)

# 剪辑片段
for i in "${!CLIPS[@]}"; do
  read -r start end <<< "${CLIPS[$i]}"
  ffmpeg -i "$AUDIO_FILE" -ss "$start" -to "$end" -c copy "clip$((i+1)).wav" 2>/dev/null
done

# 生成静音
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 0.5 -c pcm_s16le silence.wav 2>/dev/null

# 创建合并列表
> list.txt
for i in "${!CLIPS[@]}"; do
  echo "file 'clip$((i+1)).wav'" >> list.txt
  if [ $i -lt $((${#CLIPS[@]}-1)) ]; then
    echo "file 'silence.wav'" >> list.txt
  fi
done

# 合并
ffmpeg -f concat -i list.txt -c copy "$OUTPUT_DIR/${SPEAKER}金句_${DATE}.wav" 2>/dev/null

# 清理
rm -rf "$TMP_DIR"

echo "完成：$OUTPUT_DIR/${SPEAKER}金句_${DATE}.wav"
```

## Output Checklist

**交付物：**
- [ ] 剪辑后的音频文件（.wav/.mp3）
- [ ] 金句清单文档（.md）
  - [ ] 包含每段的音频内时间戳
  - [ ] 包含原文转录
  - [ ] 包含核心观点摘要
  - [ ] 包含主题总结
- [ ] 原始音频未修改（备份保留）

**质量检查：**
- [ ] 音频片段之间有明显间隔
- [ ] 没有截断的发言
- [ ] 音量一致，无爆音
- [ ] 总时长符合预期
