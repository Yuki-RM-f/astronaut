"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Mic2 } from "lucide-react";
import {
  PageTitle,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import { PersonaBackLink } from "@/src/components/PersonaBackLink";
import { ensureDemoSession } from "@/src/lib/auth";
import { uploadMaterials } from "@/src/lib/materials";
import { getPersona, PersonaRead } from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";
import {
  buildDefaultTtsPayload,
  cloneVoice,
  createVoiceSample,
  DEFAULT_TTS_NOTICE,
  DEFAULT_TTS_VOICES,
  DEFAULT_MINIMAX_TTS_VOICE_ID,
  defaultTtsVoiceLabel,
  getVoiceConfig,
  isBlankVoiceText,
  latestCloneSourceModel,
  selectDefaultTts,
  synthesizeSpeech,
  VoiceConfigResponse,
  voiceIdFromModel,
  voiceModelSummary,
  voiceSourceLabel,
  voiceStatusLabel
} from "@/src/lib/voice";

type PageState = "loading" | "ready" | "error";
type RecordingState = "idle" | "recording" | "processing" | "recorded";

const MINIMAX_VOICE_CLONE_MIN_SECONDS = 10;

export default function PersonaVoicePage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("loading");
  const [persona, setPersona] = useState<PersonaRead | null>(null);
  const [config, setConfig] = useState<VoiceConfigResponse | null>(null);
  const [selectedVoiceFile, setSelectedVoiceFile] = useState<File | null>(null);
  const [recordedVoiceFile, setRecordedVoiceFile] = useState<File | null>(null);
  const [recordedVoiceDurationSeconds, setRecordedVoiceDurationSeconds] = useState<number | null>(
    null
  );
  const [recordingAudioUrl, setRecordingAudioUrl] = useState<string | null>(null);
  const [recordingState, setRecordingState] = useState<RecordingState>("idle");
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [uploadInputKey, setUploadInputKey] = useState(0);
  const [lastCreatedVoiceSampleId, setLastCreatedVoiceSampleId] = useState<string | null>(null);
  const [selectedDefaultVoiceId, setSelectedDefaultVoiceId] = useState(
    DEFAULT_MINIMAX_TTS_VOICE_ID
  );
  const [previewText, setPreviewText] = useState("小铭，慢慢来，我在这里陪你说一会儿。");
  const [previewAudioUrl, setPreviewAudioUrl] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recordingTimerRef = useRef<number | null>(null);
  const recordingAudioUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    let isCurrent = true;
    setState("loading");
    setError(null);

    ensureDemoSession()
      .then(() => loadVoicePage(personaId))
      .then((loaded) => {
        if (!isCurrent) {
          return;
        }
        setPersona(loaded.persona);
        setConfig(loaded.config);
        setSelectedDefaultVoiceId(
          voiceIdFromModel(loaded.config.selected_voice_model) ?? DEFAULT_MINIMAX_TTS_VOICE_ID
        );
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载声音设置。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [personaId]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.onstop = null;
        mediaRecorderRef.current.stop();
      }
      if (recordingTimerRef.current !== null) {
        window.clearInterval(recordingTimerRef.current);
      }
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      if (recordingAudioUrlRef.current) {
        URL.revokeObjectURL(recordingAudioUrlRef.current);
      }
    };
  }, []);

  async function refreshVoiceConfig() {
    if (!personaId) {
      return;
    }
    setConfig(await getVoiceConfig(personaId));
  }

  async function runAction(actionName: string, action: () => Promise<void>) {
    setBusyAction(actionName);
    setNotice(null);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "操作失败。");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleDefaultTts() {
    if (!personaId) {
      return;
    }
    await runAction("default-tts", async () => {
      const nextConfig = await selectDefaultTts(
        personaId,
        buildDefaultTtsPayload(selectedDefaultVoiceId)
      );
      setConfig(nextConfig);
      setNotice(`已使用 ${defaultTtsVoiceLabel(selectedDefaultVoiceId)} 默认 TTS。`);
    });
  }

  async function handleCreateSample() {
    const sampleFile = selectedVoiceFile ?? recordedVoiceFile;
    if (!personaId || !sampleFile) {
      setError("需要先上传或录制一段纯净无噪声的人声音频。");
      return;
    }
    await runAction("sample", async () => {
      const durationSeconds = recordedVoiceFile
        ? recordedVoiceDurationSeconds
        : await readAudioDurationSeconds(sampleFile);
      validateCloneSampleDuration(durationSeconds);
      const created = await uploadMaterials(personaId, {
        files: [sampleFile],
        user_description: recordedVoiceFile
          ? "声音页音色克隆样本：浏览器录制的 TA 纯净无噪声人声音频"
          : "声音页音色克隆样本：纯净无噪声的人声音频"
      });
      const audioMaterial = created.find((material) => material.file_type === "audio");
      if (!audioMaterial) {
        throw new Error("上传的文件不是可用音频资料。请上传 mp3/m4a/wav，或使用浏览器录音自动转 WAV。");
      }
      const sample = await createVoiceSample(personaId, audioMaterial.id);
      setLastCreatedVoiceSampleId(sample.voice_model.id);
      await refreshVoiceConfig();
      setSelectedVoiceFile(null);
      clearRecordedVoice();
      setUploadInputKey((current) => current + 1);
      setNotice("已上传音频并创建可用于克隆的音色样本。");
    });
  }

  function handleVoiceFileChange(event: ChangeEvent<HTMLInputElement>) {
    clearRecordedVoice();
    setSelectedVoiceFile(event.target.files?.[0] ?? null);
  }

  async function handleStartRecording() {
    setNotice(null);
    setError(null);
    if (
      typeof navigator === "undefined" ||
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setError("当前浏览器不支持直接录音，请改为上传音频文件。");
      return;
    }

    clearRecordedVoice();
    setSelectedVoiceFile(null);
    setUploadInputKey((current) => current + 1);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recordingMimeType = getSupportedRecordingMimeType();
      const recorder = new MediaRecorder(
        stream,
        recordingMimeType ? { mimeType: recordingMimeType } : undefined
      );
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;
      recordingChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordingChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        void handleRecordingStop(recorder, recordingMimeType);
      };

      recorder.start();
      setRecordingSeconds(0);
      setRecordingState("recording");
      recordingTimerRef.current = window.setInterval(() => {
        setRecordingSeconds((current) => current + 1);
      }, 1000);
    } catch {
      clearRecordingTimer();
      stopRecordingStream();
      mediaRecorderRef.current = null;
      setRecordingState("idle");
      setError("无法访问麦克风，请检查浏览器权限，或改为上传音频文件。");
    }
  }

  async function handleRecordingStop(
    recorder: MediaRecorder,
    recordingMimeType: string | undefined
  ) {
    clearRecordingTimer();
    stopRecordingStream();
    mediaRecorderRef.current = null;
    const blobType = recorder.mimeType || recordingMimeType || "audio/webm";
    const blob = new Blob(recordingChunksRef.current, { type: blobType });
    recordingChunksRef.current = [];
    if (blob.size === 0) {
      setRecordingState("idle");
      setRecordingSeconds(0);
      setError("没有录到可用音频，请重新录制。");
      return;
    }
    setRecordingState("processing");
    try {
      const recording = await convertRecordedBlobToWavFile(blob);
      const nextAudioUrl = URL.createObjectURL(blob);
      revokeRecordingAudioUrl();
      recordingAudioUrlRef.current = nextAudioUrl;
      setRecordingAudioUrl(nextAudioUrl);
      setRecordedVoiceFile(recording.file);
      setRecordedVoiceDurationSeconds(recording.durationSeconds);
      setRecordingState("recorded");
      if (recording.durationSeconds < MINIMAX_VOICE_CLONE_MIN_SECONDS) {
        setNotice(null);
        setError(minimaxCloneDurationError(recording.durationSeconds));
      } else {
        setNotice("录音已转为 WAV，可用于 MiniMax 音色克隆上传。");
      }
    } catch {
      setRecordingState("idle");
      setRecordingSeconds(0);
      setRecordedVoiceFile(null);
      setRecordedVoiceDurationSeconds(null);
      setError("录音转 WAV 失败，请重新录制或上传 mp3/m4a/wav 音频。");
    }
  }

  function handleStopRecording() {
    if (!mediaRecorderRef.current || mediaRecorderRef.current.state === "inactive") {
      return;
    }
    mediaRecorderRef.current.stop();
  }

  function clearRecordingTimer() {
    if (recordingTimerRef.current !== null) {
      window.clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
  }

  function stopRecordingStream() {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
  }

  function revokeRecordingAudioUrl() {
    if (recordingAudioUrlRef.current) {
      URL.revokeObjectURL(recordingAudioUrlRef.current);
      recordingAudioUrlRef.current = null;
    }
    setRecordingAudioUrl(null);
  }

  function clearRecordedVoice() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.onstop = null;
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;
    recordingChunksRef.current = [];
    clearRecordingTimer();
    stopRecordingStream();
    revokeRecordingAudioUrl();
    setRecordedVoiceFile(null);
    setRecordedVoiceDurationSeconds(null);
    setRecordingState("idle");
    setRecordingSeconds(0);
  }

  async function handleCloneVoice() {
    if (!personaId || !config) {
      return;
    }
    const sample = latestCloneSourceModel(config.voice_models, lastCreatedVoiceSampleId);
    if (!sample) {
      setError("需要先创建可克隆的音色样本。");
      return;
    }
    await runAction("clone", async () => {
      const result = await cloneVoice(personaId, sample.id);
      await refreshVoiceConfig();
      setNotice(
        result.voice_status === "cloned_ready"
          ? "已生成模拟音色。"
          : cloneFailureNotice(result.job.error_message)
      );
    });
  }

  async function handleSynthesize(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!personaId || isBlankVoiceText(previewText)) {
      return;
    }
    await runAction("synthesize", async () => {
      const result = await synthesizeSpeech(personaId, previewText);
      setPreviewAudioUrl(result.audio_url);
      await refreshVoiceConfig();
      setNotice("已生成一段 mock 语音预览。");
    });
  }

  const defaultTtsVoices =
    config?.default_tts_voices && config.default_tts_voices.length > 0
      ? config.default_tts_voices
      : DEFAULT_TTS_VOICES;
  const selectedDefaultVoice =
    defaultTtsVoices.find((voice) => voice.voice_id === selectedDefaultVoiceId) ??
    defaultTtsVoices.find((voice) => voice.voice_id === DEFAULT_MINIMAX_TTS_VOICE_ID);
  const hasSampleAudio = Boolean(selectedVoiceFile || recordedVoiceFile);
  const recordedVoiceTooShort =
    recordedVoiceFile !== null &&
    recordedVoiceDurationSeconds !== null &&
    recordedVoiceDurationSeconds < MINIMAX_VOICE_CLONE_MIN_SECONDS;
  const canCreateSample = hasSampleAudio && !recordedVoiceTooShort;

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-12 sm:px-8 lg:px-10">
        {!personaId ? (
          <Link href={ROUTES.dashboard} className="text-sm font-bold text-starGold">
            返回我的星空
          </Link>
        ) : null}
        {personaId ? <PersonaBackLink personaId={personaId} /> : null}

        <PageTitle
          className="mt-6"
          title={persona ? `${persona.name}的声音` : "TA 的声音"}
          subtitle="设置默认 TTS、整理音色样本并试听一段回复。当前不声明真实音色能力。"
        />

        {state === "loading" ? <Notice text="正在加载声音设置..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载声音设置。"} /> : null}

        {state === "ready" && config ? (
          <div className="mt-8 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <StarPanel className="p-6">
              <h2 className="font-serif text-2xl font-bold text-starGold">
                当前状态：{voiceStatusLabel(config.voice_status)}
              </h2>
              <VoiceOrb label={persona ? `${persona.name}的声音` : "TA 的声音"} />
              <p className="mt-5 rounded-2xl border border-white/8 bg-white/6 p-3 text-sm font-semibold leading-7 text-starMist/74">
                {config.default_tts_notice || DEFAULT_TTS_NOTICE}
              </p>

              <dl className="mt-5 grid gap-4 text-sm">
                <Detail
                  label="选中声音"
                  value={
                    config.selected_voice_model
                      ? voiceModelSummary(config.selected_voice_model)
                      : "未设置"
                  }
                />
                <Detail label="样本数量" value={`${config.voice_models.length}`} />
              </dl>

              {config.voice_models.length > 0 ? (
                <div className="mt-5 border-t border-white/8 pt-4">
                  <p className="text-sm font-bold text-starCream">声音记录</p>
                  <div className="mt-3 grid gap-2">
                    {config.voice_models.map((model) => (
                      <p
                        key={model.id}
                        className="rounded-2xl border border-white/8 bg-white/6 px-4 py-3 text-sm font-semibold leading-6 text-starMist/72"
                      >
                        {voiceModelSummary(model)}
                      </p>
                    ))}
                  </div>
                </div>
              ) : null}
            </StarPanel>

            <section className="grid gap-5">
              {error ? <Alert tone="error" text={error} /> : null}
              {notice ? <Alert tone="success" text={notice} /> : null}

              <Panel title="1. 默认 TTS">
                <p className="text-sm font-semibold leading-7 text-starMist/70">
                  无定制音色时，先从 MiniMax 中文普通话系统音色中选择一个默认 TTS。该声音必须明确标注不是 TA 的真实声音。
                </p>
                <label
                  className="mt-4 block text-sm font-bold text-starMist/78"
                  htmlFor="default-tts-voice"
                >
                  MiniMax 默认音色
                </label>
                <select
                  id="default-tts-voice"
                  value={selectedDefaultVoiceId}
                  onChange={(event) => setSelectedDefaultVoiceId(event.target.value)}
                  className={`${inputClass} mt-2`}
                >
                  {defaultTtsVoices.map((voice) => (
                    <option key={voice.voice_id} value={voice.voice_id}>
                      {voice.voice_name}：{voice.voice_id}
                    </option>
                  ))}
                </select>
                {selectedDefaultVoice ? (
                  <p className="mt-3 rounded-2xl border border-white/8 bg-white/6 p-3 text-sm font-semibold leading-6 text-starMist/70">
                    {selectedDefaultVoice.description}
                    <span className="mt-1 block break-all text-xs text-starMist/52">
                      voice_id：{selectedDefaultVoice.voice_id}
                    </span>
                  </p>
                ) : null}
                <button
                  type="button"
                  onClick={handleDefaultTts}
                  disabled={busyAction !== null}
                  className={primaryButtonClass}
                >
                  {busyAction === "default-tts" ? "正在设置..." : "使用所选默认 TTS"}
                </button>
              </Panel>

              <Panel title="2. 音色样本与克隆">
                <label className="text-sm font-bold text-starMist/78" htmlFor="voice-sample-upload">
                  上传人声音频
                </label>
                <p className="mt-2 text-sm font-semibold leading-7 text-starMist/70">
                  必须上传纯净无噪声的人声音频：只包含 TA 的清晰人声，避免背景音乐、多人同时说话和明显环境噪声。用于 MiniMax 克隆时推荐上传 mp3/m4a/wav；也可以用下方录音入口自动转 WAV。
                  MiniMax 音色克隆要求样本至少 10 秒。
                </p>
                <input
                  key={uploadInputKey}
                  id="voice-sample-upload"
                  type="file"
                  accept="audio/*"
                  onChange={handleVoiceFileChange}
                  disabled={
                    busyAction !== null ||
                    recordingState === "recording" ||
                    recordingState === "processing"
                  }
                  className={`${inputClass} mt-2`}
                />
                {selectedVoiceFile ? (
                  <p className="mt-3 rounded-2xl border border-white/8 bg-white/6 p-3 text-sm font-semibold leading-6 text-starMist/70">
                    已选择：<span className="break-all text-starCream">{selectedVoiceFile.name}</span>
                    <span className="mt-1 block text-xs text-starMist/52">
                      {formatFileSize(selectedVoiceFile.size)}
                    </span>
                  </p>
                ) : null}
                <div className="mt-5 border-t border-white/8 pt-4">
                  <p className="text-sm font-bold text-starMist/78">录制 TA 的人声音频</p>
                  <p className="mt-2 text-sm font-semibold leading-7 text-starMist/70">
                    可直接调取浏览器麦克风录制一段 TA 的清晰人声。录制后先试听确认，再上传并创建音色样本。
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    {recordingState === "recording" ? (
                      <button
                        type="button"
                        onClick={handleStopRecording}
                        disabled={busyAction !== null}
                        className={secondaryButtonClass}
                      >
                        停止录音
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={handleStartRecording}
                        disabled={busyAction !== null || recordingState === "processing"}
                        className={secondaryButtonClass}
                      >
                        开始录音
                      </button>
                    )}
                    {recordedVoiceFile ? (
                      <button
                        type="button"
                        onClick={clearRecordedVoice}
                        disabled={busyAction !== null || recordingState === "processing"}
                        className={secondaryButtonClass}
                      >
                        重新录制
                      </button>
                    ) : null}
                    <span className="text-sm font-semibold text-starMist/60">
                      {recordingState === "recording"
                        ? `录音中 ${formatDuration(recordingSeconds)}`
                        : recordingState === "processing"
                          ? "正在转为 WAV"
                          : recordedVoiceFile
                          ? `已录制 ${formatFileSize(recordedVoiceFile.size)}${
                              recordedVoiceDurationSeconds === null
                                ? ""
                                : ` · ${formatDurationLabel(recordedVoiceDurationSeconds)}`
                            }`
                          : "等待录音"}
                    </span>
                  </div>
                  {recordingAudioUrl ? (
                    <div className="mt-3">
                      <audio className="w-full" controls src={recordingAudioUrl}>
                        <track kind="captions" />
                      </audio>
                      <p className="mt-2 break-all text-xs font-semibold text-starMist/52">
                        {recordedVoiceFile?.name}
                      </p>
                      <p className="mt-1 text-xs font-semibold text-starMist/52">
                        已转为 WAV，可用于 MiniMax 音色克隆上传。
                      </p>
                      {recordedVoiceTooShort ? (
                        <p className="mt-1 text-xs font-bold text-rose-100">
                          录音少于 10 秒，请重新录制更长的 TA 清晰人声。
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
                <div className="mt-4 grid gap-2 text-xs font-semibold leading-5 text-starMist/58">
                  <p>上传或录音后会创建“音色样本”，还不会生成可用模拟音色。</p>
                  <p>生成模拟音色会调用 MiniMax 克隆接口，成功后得到 MiniMax voice_id 并设为当前模拟音色。</p>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={handleCreateSample}
                    disabled={busyAction !== null || !canCreateSample}
                    className={secondaryButtonClass}
                  >
                    {busyAction === "sample"
                      ? "正在上传..."
                      : recordedVoiceFile
                        ? "确认上传录音并创建音色样本"
                        : "上传并创建音色样本"}
                  </button>
                  <button
                    type="button"
                    onClick={handleCloneVoice}
                    disabled={busyAction !== null}
                    className={secondaryButtonClass}
                  >
                    {busyAction === "clone" ? "正在克隆..." : "生成模拟音色"}
                  </button>
                </div>
              </Panel>

              <Panel title="3. 语音预览">
                <div className="mb-4 rounded-2xl border border-white/8 bg-white/6 p-3 text-sm font-semibold leading-6 text-starMist/72">
                  <p className="font-bold text-starCream">当前语音来源</p>
                  <p className="mt-1 break-all">
                    {voiceSourceLabel(config.selected_voice_model, config.tts_model)}
                  </p>
                </div>
                <form onSubmit={handleSynthesize} className="grid gap-3">
                  <label className="text-sm font-bold text-starMist/78" htmlFor="voice-preview">
                    预览文本
                  </label>
                  <textarea
                    id="voice-preview"
                    value={previewText}
                    onChange={(event) => setPreviewText(event.target.value)}
                    rows={3}
                    className={`${inputClass} leading-7`}
                  />
                  <button
                    type="submit"
                    disabled={busyAction !== null || isBlankVoiceText(previewText)}
                    className={`${primaryButtonClass} md:w-fit`}
                  >
                    {busyAction === "synthesize" ? "正在生成..." : "生成语音预览"}
                  </button>
                </form>
                {previewAudioUrl ? (
                  <div className="mt-4 rounded-2xl border border-white/8 bg-white/6 p-3">
                    <p className="text-sm font-bold text-starCream">预览音频</p>
                    <audio className="mt-3 w-full" controls src={previewAudioUrl}>
                      <track kind="captions" />
                    </audio>
                    <p className="mt-2 break-all text-xs text-starMist/50">{previewAudioUrl}</p>
                  </div>
                ) : null}
              </Panel>
            </section>
          </div>
        ) : null}
      </main>
    </StarShell>
  );
}

async function loadVoicePage(personaId: string): Promise<{
  persona: PersonaRead;
  config: VoiceConfigResponse;
}> {
  const [persona, config] = await Promise.all([
    getPersona(personaId),
    getVoiceConfig(personaId)
  ]);
  return { persona, config };
}

function getSupportedRecordingMimeType(): string | undefined {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return candidates.find((mimeType) => MediaRecorder.isTypeSupported(mimeType));
}

async function convertRecordedBlobToWavFile(
  blob: Blob
): Promise<{ file: File; durationSeconds: number }> {
  const audioContextConstructor =
    window.AudioContext ??
    (window as Window & typeof globalThis & { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext;
  if (!audioContextConstructor) {
    throw new Error("AudioContext unavailable");
  }

  const audioContext = new audioContextConstructor();
  try {
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0));
    const wavBlob = encodeWavAudioBuffer(audioBuffer);
    return {
      file: new File([wavBlob], `voice-sample-recording-${Date.now()}.wav`, {
        type: "audio/wav"
      }),
      durationSeconds: audioBuffer.duration
    };
  } finally {
    await audioContext.close();
  }
}

function readAudioDurationSeconds(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const audio = document.createElement("audio");
    const audioUrl = URL.createObjectURL(file);
    const cleanup = () => {
      audio.removeAttribute("src");
      audio.load();
      URL.revokeObjectURL(audioUrl);
    };
    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      const durationSeconds = audio.duration;
      cleanup();
      if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) {
        reject(new Error("无法读取音频时长，请重新录制或上传 mp3/m4a/wav 音频。"));
        return;
      }
      resolve(durationSeconds);
    };
    audio.onerror = () => {
      cleanup();
      reject(new Error("无法读取音频时长，请重新录制或上传 mp3/m4a/wav 音频。"));
    };
    audio.src = audioUrl;
  });
}

function validateCloneSampleDuration(durationSeconds: number | null) {
  if (durationSeconds === null || !Number.isFinite(durationSeconds)) {
    throw new Error("无法读取音频时长，请重新录制或上传 mp3/m4a/wav 音频。");
  }
  if (durationSeconds < MINIMAX_VOICE_CLONE_MIN_SECONDS) {
    throw new Error(minimaxCloneDurationError(durationSeconds));
  }
}

function minimaxCloneDurationError(durationSeconds: number): string {
  return `当前音频约 ${formatDurationLabel(durationSeconds)}，MiniMax 音色克隆要求样本至少 10 秒。请重新录制或上传更长的 mp3/m4a/wav 人声音频。`;
}

function cloneFailureNotice(errorMessage?: string | null): string {
  const normalized = (errorMessage || "").toLowerCase();
  if (normalized.includes("voice duration too short") || errorMessage?.includes("至少 10 秒")) {
    return "音色克隆失败：音频时长不足，MiniMax 音色克隆要求样本至少 10 秒。请重新录制或上传更长的人声音频，已回退默认 TTS。";
  }
  return errorMessage
    ? `音色克隆失败：${errorMessage}，已回退默认 TTS。`
    : "音色克隆失败，已回退默认 TTS。";
}

function encodeWavAudioBuffer(audioBuffer: AudioBuffer): Blob {
  const numChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const samples = interleaveAudioBuffer(audioBuffer);
  const bytesPerSample = 2;
  const blockAlign = numChannels * bytesPerSample;
  const dataSize = samples.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bytesPerSample * 8, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (const sample of samples) {
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    offset += bytesPerSample;
  }

  return new Blob([buffer], { type: "audio/wav" });
}

function interleaveAudioBuffer(audioBuffer: AudioBuffer): Float32Array {
  const channelData = Array.from({ length: audioBuffer.numberOfChannels }, (_, index) =>
    audioBuffer.getChannelData(index)
  );
  const samples = new Float32Array(audioBuffer.length * audioBuffer.numberOfChannels);
  let writeIndex = 0;
  for (let frame = 0; frame < audioBuffer.length; frame += 1) {
    for (let channel = 0; channel < audioBuffer.numberOfChannels; channel += 1) {
      samples[writeIndex] = channelData[channel][frame] ?? 0;
      writeIndex += 1;
    }
  }
  return samples;
}

function writeAscii(view: DataView, offset: number, text: string) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index));
  }
}

function VoiceOrb({ label }: { label: string }) {
  return (
    <div className="mt-5 rounded-[1.5rem] border border-starGold/14 bg-indigo-950/32 p-5">
      <div className="flex items-center gap-4">
        <span className="grid h-16 w-16 place-items-center rounded-full bg-starGold/14 text-starGold shadow-[0_0_34px_rgba(255,190,109,0.28)]">
          <Mic2 className="h-8 w-8" aria-hidden="true" />
        </span>
        <div>
          <p className="text-sm font-bold text-starGold">{label}</p>
          <div className="mt-3 flex items-end gap-1">
            {[14, 28, 18, 36, 22, 30, 16].map((height, index) => (
              <span
                key={`${height}-${index}`}
                className="w-2 rounded-full bg-starGold/70"
                style={{ height }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <StarPanel className="p-5">
      <h2 className="font-serif text-2xl font-bold text-starGold">{title}</h2>
      <div className="mt-4">{children}</div>
    </StarPanel>
  );
}

function Detail({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="font-bold text-starMist/60">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap leading-6 text-starCream">{value || "未设置"}</dd>
    </div>
  );
}

function Notice({ text }: { text: string }) {
  return (
    <StarPanel className="mt-8 p-5 text-sm font-semibold leading-7 text-starMist/72">
      {text}
    </StarPanel>
  );
}

function Alert({ tone, text }: { tone: "error" | "success"; text: string }) {
  return (
    <div
      className={`rounded-2xl border p-4 text-sm font-bold ${
        tone === "error"
          ? "border-rose-300/20 bg-rose-500/15 text-rose-100"
          : "border-emerald-200/20 bg-emerald-400/12 text-emerald-100"
      }`}
    >
      {text}
    </div>
  );
}

function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function formatDurationLabel(totalSeconds: number): string {
  if (totalSeconds < 60) {
    return `${totalSeconds.toFixed(1)} 秒`;
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds - minutes * 60;
  return `${minutes} 分 ${seconds.toFixed(1)} 秒`;
}

const inputClass = "star-input text-sm";
const primaryButtonClass = "star-button mt-4 min-w-32 disabled:opacity-60";
const secondaryButtonClass =
  "rounded-full border border-starGold/22 bg-starGold/10 px-4 py-2.5 text-sm font-bold text-starCream transition hover:bg-starGold/16 disabled:cursor-not-allowed disabled:opacity-35";
