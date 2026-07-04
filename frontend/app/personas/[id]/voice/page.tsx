"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  AiReminder,
  GlassPanel,
  MemoryContainer,
  MemoryShell,
  MemoryTitle,
  VoiceWave
} from "@/src/components/MemorySpace";
import { getAuthToken } from "@/src/lib/auth";
import { listMaterials, SourceMaterialRead } from "@/src/lib/materials";
import { getPersona, PersonaRead } from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";
import {
  buildDefaultTtsPayload,
  cloneVoice,
  createVoiceSample,
  DEFAULT_TTS_NOTICE,
  getVoiceConfig,
  isBlankVoiceText,
  selectDefaultTts,
  synthesizeSpeech,
  VoiceConfigResponse,
  voiceModelSummary,
  voiceStatusLabel
} from "@/src/lib/voice";

type PageState = "checking" | "signedOut" | "loading" | "ready" | "error";

export default function PersonaVoicePage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("checking");
  const [persona, setPersona] = useState<PersonaRead | null>(null);
  const [config, setConfig] = useState<VoiceConfigResponse | null>(null);
  const [audioMaterials, setAudioMaterials] = useState<SourceMaterialRead[]>([]);
  const [selectedMaterialId, setSelectedMaterialId] = useState("");
  const [previewText, setPreviewText] = useState("小铭，慢慢来，我在这里陪你说一会儿。");
  const [previewAudioUrl, setPreviewAudioUrl] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  useEffect(() => {
    if (!getAuthToken()) {
      setState("signedOut");
      return;
    }
    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    let isCurrent = true;
    setState("loading");
    setError(null);
    loadVoicePage(personaId)
      .then((loaded) => {
        if (!isCurrent) {
          return;
        }
        setPersona(loaded.persona);
        setConfig(loaded.config);
        setAudioMaterials(loaded.audioMaterials);
        setSelectedMaterialId(loaded.audioMaterials[0]?.id ?? "");
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
      const nextConfig = await selectDefaultTts(personaId, buildDefaultTtsPayload());
      setConfig(nextConfig);
      setNotice("已选择系统默认 TTS。");
    });
  }

  async function handleCreateSample() {
    if (!personaId || !selectedMaterialId) {
      setError("需要先选择一条音频资料。");
      return;
    }
    await runAction("sample", async () => {
      await createVoiceSample(personaId, selectedMaterialId);
      await refreshVoiceConfig();
      setNotice("已创建可用于克隆的音色样本。");
    });
  }

  async function handleCloneVoice() {
    if (!personaId || !config) {
      return;
    }
    const sample = config.voice_models.find((model) => model.status === "sample_ready");
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
          : "音色克隆失败，已回退默认 TTS。"
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

  return (
    <MemoryShell background="memoryStringLights">
      <MemoryContainer>
      <div className="flex flex-wrap items-center gap-3 text-sm font-semibold text-memoryAccent">
        <Link href={personaId ? ROUTES.personaDetail(personaId) : ROUTES.dashboard}>
          返回记忆空间
        </Link>
        {personaId ? <Link href={ROUTES.personaChat(personaId)}>进入对话</Link> : null}
        {personaId ? <Link href={ROUTES.personaUploads(personaId)}>上传音频</Link> : null}
      </div>

      <div className="mt-6 grid gap-4">
        <MemoryTitle
          title={persona ? `${persona.name}的声音` : "TA 的声音"}
          subtitle="选择默认 TTS、整理音色样本并试听一段回复。当前仍是 mock 能力，不代表真实音色或真实语音质量。"
        />
        <AiReminder text="AI 身份提醒：语音预览不是 TA 的真实声音，当前仅用于本地 mock 演示。" />
      </div>

      {state === "signedOut" ? <SignedOutState /> : null}
      {state === "loading" || state === "checking" ? <Notice text="正在加载声音设置..." /> : null}
      {state === "error" ? <Notice text={error ?? "无法加载声音设置。"} /> : null}

      {state === "ready" && config ? (
        <div className="mt-8 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <GlassPanel>
            <h2 className="font-serif text-2xl font-semibold text-memoryText">
              当前状态：{voiceStatusLabel(config.voice_status)}
            </h2>
            <div className="mt-4">
              <VoiceWave label={persona ? `${persona.name}的声音` : "TA 的声音"} />
            </div>
            <p className="mt-5 rounded-2xl bg-memoryWarm/70 p-3 text-sm leading-7 text-memoryText/74">
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
              <div className="mt-5 border-t border-memoryLine/60 pt-4">
                <p className="text-sm font-semibold text-memoryText">声音记录</p>
                <div className="mt-3 grid gap-2">
                  {config.voice_models.map((model) => (
                    <p
                      key={model.id}
                      className="rounded-2xl bg-memoryPaper/75 px-4 py-3 text-sm leading-6 text-memoryText/72"
                    >
                      {voiceModelSummary(model)}
                    </p>
                  ))}
                </div>
              </div>
            ) : null}
          </GlassPanel>

          <section className="grid gap-5">
            {error ? <Alert tone="error" text={error} /> : null}
            {notice ? <Alert tone="success" text={notice} /> : null}

            <Panel title="1. 默认 TTS">
              <p className="text-sm leading-7 text-memoryText/70">
                无定制音色时，先选择系统默认 TTS。该声音必须明确标注不是 TA 的真实声音。
              </p>
              <button
                type="button"
                onClick={handleDefaultTts}
                disabled={busyAction !== null}
                className="memory-button mt-4 rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm disabled:bg-memoryText/30"
              >
                {busyAction === "default-tts" ? "正在设置..." : "选择默认 TTS"}
              </button>
            </Panel>

            <Panel title="2. 音色样本与克隆">
              <label className="text-sm font-semibold text-memoryText" htmlFor="audio-material">
                选择音频资料
              </label>
              <select
                id="audio-material"
                value={selectedMaterialId}
                onChange={(event) => setSelectedMaterialId(event.target.value)}
                className="mt-2 w-full rounded-2xl border border-memoryLine/80 bg-white/74 px-4 py-3 text-sm text-memoryText outline-none focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20"
              >
                <option value="">暂无可用音频资料</option>
                {audioMaterials.map((material) => (
                  <option key={material.id} value={material.id}>
                    {material.file_name || material.user_description || material.id}
                  </option>
                ))}
              </select>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleCreateSample}
                  disabled={busyAction !== null || !selectedMaterialId}
                  className="rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-2.5 text-sm font-semibold text-memoryText disabled:cursor-not-allowed disabled:text-memoryText/40"
                >
                  {busyAction === "sample" ? "正在创建..." : "创建音色样本"}
                </button>
                <button
                  type="button"
                  onClick={handleCloneVoice}
                  disabled={busyAction !== null}
                  className="rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-2.5 text-sm font-semibold text-memoryText disabled:cursor-not-allowed disabled:text-memoryText/40"
                >
                  {busyAction === "clone" ? "正在克隆..." : "生成模拟音色"}
                </button>
              </div>
            </Panel>

            <Panel title="3. 语音预览">
              <form onSubmit={handleSynthesize} className="grid gap-3">
                <label className="text-sm font-semibold text-memoryText" htmlFor="voice-preview">
                  预览文本
                </label>
                <textarea
                  id="voice-preview"
                  value={previewText}
                  onChange={(event) => setPreviewText(event.target.value)}
                  rows={3}
                  className="w-full rounded-2xl border border-memoryLine/80 bg-white/74 px-4 py-3 text-sm leading-7 text-memoryText outline-none focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20"
                />
                <button
                  type="submit"
                  disabled={busyAction !== null || isBlankVoiceText(previewText)}
                  className="memory-button rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm disabled:bg-memoryText/30 md:w-fit"
                >
                  {busyAction === "synthesize" ? "正在生成..." : "生成语音预览"}
                </button>
              </form>
              {previewAudioUrl ? (
                <div className="mt-4 rounded-2xl bg-memoryPaper/75 p-3">
                  <p className="text-sm font-semibold text-memoryText">预览音频</p>
                  <audio className="mt-3 w-full" controls src={previewAudioUrl}>
                    <track kind="captions" />
                  </audio>
                  <p className="mt-2 break-all text-xs text-memoryText/50">{previewAudioUrl}</p>
                </div>
              ) : null}
            </Panel>
          </section>
        </div>
      ) : null}
      </MemoryContainer>
    </MemoryShell>
  );
}

async function loadVoicePage(personaId: string): Promise<{
  persona: PersonaRead;
  config: VoiceConfigResponse;
  audioMaterials: SourceMaterialRead[];
}> {
  const [persona, config, materials] = await Promise.all([
    getPersona(personaId),
    getVoiceConfig(personaId),
    listMaterials(personaId)
  ]);
  return {
    persona,
    config,
    audioMaterials: materials.filter((material) => material.file_type === "audio")
  };
}

function SignedOutState() {
  return (
    <GlassPanel className="mt-8 max-w-3xl">
      <h2 className="font-serif text-2xl font-semibold text-memoryText">需要先进入记忆空间</h2>
      <p className="mt-2 max-w-2xl text-sm leading-7 text-memoryText/70">
        当前会以本地访客身份整理声音，也可以先体验外婆示例。
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        <DemoEntry label="立即体验示例" />
      </div>
    </GlassPanel>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <GlassPanel>
      <h2 className="font-serif text-2xl font-semibold text-memoryText">{title}</h2>
      <div className="mt-4">{children}</div>
    </GlassPanel>
  );
}

function Detail({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="font-semibold text-memoryText/60">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap leading-6 text-memoryText">{value || "未设置"}</dd>
    </div>
  );
}

function Notice({ text }: { text: string }) {
  return (
    <GlassPanel className="mt-8 text-sm leading-7 text-memoryText/72">
      {text}
    </GlassPanel>
  );
}

function Alert({ tone, text }: { tone: "error" | "success"; text: string }) {
  const color =
    tone === "error"
      ? "text-red-700 bg-red-50"
      : "text-memoryAccentDark bg-memoryWarm/70";
  return <div className={`rounded-2xl p-3 text-sm ${color}`}>{text}</div>;
}
