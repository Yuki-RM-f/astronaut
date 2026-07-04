# GPT-SoVITS 实时录音克隆封装

这个封装是在当前 GPT-SoVITS 项目上新增的一层轻量应用，用于完成：

- 在浏览器页面调用麦克风录制参考音频
- 自动把参考音频整理为模型可读取的 WAV
- 使用 v2ProPlus 底模进行无参考文本音色克隆
- 合成页面输入的目标文本并返回音频

原始 GPT-SoVITS 代码仍保留在 `GPT_SoVITS/`、`webui.py`、`api.py` 等文件中；本封装主要集中在 `voice_clone_app/`，便于单独维护。

## 目录结构

```text
voice_clone_app/
  __main__.py      应用启动入口，负责 launch Gradio
  settings.py      端口、模型路径、默认文本、录音时长等配置
  languages.py     页面语言选项和语言值归一化
  audio.py         麦克风录音/上传文件的转码、归一化、时长校验
  service.py       GPT-SoVITS 模型加载和合成服务
  ui.py            Gradio 页面定义

mic_tts.py         兼容入口，内部调用 voice_clone_app
run_realtime_voice_clone.ps1  Windows PowerShell 启动脚本
run_realtime_voice_clone.bat  Windows 双击启动脚本
```

## 快速启动

在项目根目录运行：

```powershell
.\venv\Scripts\python.exe -m voice_clone_app
```

也可以直接使用脚本：

```powershell
.\run_realtime_voice_clone.ps1
```

或双击：

```text
run_realtime_voice_clone.bat
```

默认访问地址：

```text
http://127.0.0.1:7860/
```

## 页面使用

1. 打开 `http://127.0.0.1:7860/`
2. 浏览器提示麦克风权限时选择允许
3. 在“参考录音”中录制 3-10 秒声音
4. 在“合成文本”中填写要生成的文字，默认是“你好黑客松”
5. 点击“开始合成”
6. 在“合成结果”中播放或下载生成音频

## 默认模型

当前封装使用无参考文本模式，因此不需要填写参考音频对应文字。

默认配置在 `voice_clone_app/settings.py`：

```python
MODEL_VERSION = "v2ProPlus"
GPT_PATH = "GPT_SoVITS/pretrained_models/s1v3.ckpt"
SOVITS_PATH = "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2ProPlus.pth"
```

这些权重文件需要存在，否则启动或合成会失败。

## 可配置项

可以通过环境变量覆盖默认配置：

```powershell
$env:VOICE_CLONE_PORT = "7861"
$env:VOICE_CLONE_DEFAULT_TEXT = "你好黑客松"
$env:VOICE_CLONE_MIN_SECONDS = "3"
$env:VOICE_CLONE_MAX_SECONDS = "10"
$env:VOICE_CLONE_TOP_K = "20"
$env:VOICE_CLONE_TOP_P = "0.6"
$env:VOICE_CLONE_TEMPERATURE = "0.6"
$env:VOICE_CLONE_SPEED = "1.0"
.\venv\Scripts\python.exe -m voice_clone_app
```

可覆盖模型路径：

```powershell
$env:VOICE_CLONE_GPT_PATH = "GPT_SoVITS/pretrained_models/s1v3.ckpt"
$env:VOICE_CLONE_SOVITS_PATH = "GPT_SoVITS/pretrained_models/v2Pro/s2Gv2ProPlus.pth"
```

## 临时文件

浏览器录音会先转为标准 WAV，默认保存到：

```text
TEMP/ref_audio_wav/
```

这个目录只用于缓存参考音频，文件可以定期清理。清理时请先停止正在运行的服务。

## 常见问题

### 页面打不开

确认服务是否启动，并检查 7860 端口是否被占用。可以改端口启动：

```powershell
$env:VOICE_CLONE_PORT = "7861"
.\venv\Scripts\python.exe -m voice_clone_app
```

### 浏览器没有麦克风

确认浏览器地址栏的麦克风权限已经允许。如果权限被拒绝，需要在浏览器站点设置中重新开启。

### 提示参考音频时长不合适

当前默认限制是 3-10 秒。录音太短音色不稳定，太长会增加推理风险。可以通过 `VOICE_CLONE_MIN_SECONDS` 和 `VOICE_CLONE_MAX_SECONDS` 调整。

### 合成时看到 CUDA 或 onnxruntime 警告

如果最后显示“合成完成”并能播放音频，这类警告通常不影响当前流程。它来自某些依赖尝试加载 CUDA 后端失败后回退执行。

### 中文路径或中文文本异常

页面内输入中文文本是正常的。如果从命令行调用，建议使用 UTF-8 终端或避免在命令行里直接传中文路径。

## 开发说明

- `audio.py` 只负责输入音频整理，不直接调用模型
- `service.py` 是推理边界，集中处理模型加载、锁和错误返回
- `ui.py` 只定义页面组件和按钮绑定
- `mic_tts.py` 仅保留为兼容入口，后续业务逻辑优先放到 `voice_clone_app/`

这种拆分便于后续继续扩展，例如加入录音历史、批量合成、保存输出文件、模型切换或 API 接口。
