"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { AvatarPreview } from "@/src/components/AvatarPreview";
import { DemoEntry } from "@/src/components/DemoEntry";
import {
  AiReminder,
  GlassPanel,
  MemoryContainer,
  MemoryShell,
  MemoryTitle
} from "@/src/components/MemorySpace";
import {
  avatarModelSummary,
  avatarStatusLabel,
  avatarStyleLabel,
  AvatarConfigResponse,
  AvatarModelRead,
  AvatarStyle,
  buildDefaultAvatarPayload,
  buildGenerateAvatarPayload,
  generateAvatar,
  getAvatarConfig,
  hasRenderableAvatarModel,
  selectDefaultAvatar
} from "@/src/lib/avatar";
import { getAuthToken } from "@/src/lib/auth";
import { listMaterials, SourceMaterialRead } from "@/src/lib/materials";
import { getPersona, PersonaRead } from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";

type PageState = "checking" | "signedOut" | "loading" | "ready" | "error";

export default function PersonaAvatarPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("checking");
  const [persona, setPersona] = useState<PersonaRead | null>(null);
  const [config, setConfig] = useState<AvatarConfigResponse | null>(null);
  const [imageMaterials, setImageMaterials] = useState<SourceMaterialRead[]>([]);
  const [selectedMaterialId, setSelectedMaterialId] = useState("");
  const [style, setStyle] = useState<AvatarStyle>("memorial");
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [mouthTest, setMouthTest] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    loadAvatarPage(personaId)
      .then((loaded) => {
        if (!isCurrent) {
          return;
        }
        setPersona(loaded.persona);
        setConfig(loaded.config);
        setImageMaterials(loaded.imageMaterials);
        setSelectedMaterialId(loaded.imageMaterials[0]?.id ?? "");
        const selectedStyle = loaded.config.selected_avatar_model?.style;
        setStyle(
          selectedStyle === "semi_realistic" ||
            selectedStyle === "cartoon" ||
            selectedStyle === "memorial"
            ? selectedStyle
            : "memorial"
        );
        setState("ready");
      })
      .catch((caught) => {
        if (!isCurrent) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "无法加载形象设置。");
        setState("error");
      });

    return () => {
      isCurrent = false;
    };
  }, [personaId]);

  async function refreshAvatarConfig() {
    if (!personaId) {
      return;
    }
    setConfig(await getAvatarConfig(personaId));
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

  async function handleDefaultAvatar() {
    if (!personaId) {
      return;
    }
    await runAction("default", async () => {
      const nextConfig = await selectDefaultAvatar(
        personaId,
        buildDefaultAvatarPayload(style)
      );
      setConfig(nextConfig);
      setNotice("已选择默认纪念形象。");
    });
  }

  async function handleGenerateAvatar() {
    if (!personaId || !selectedMaterialId) {
      setError("需要先选择一张图片资料。");
      return;
    }
    await runAction("generate", async () => {
      const result = await generateAvatar(
        personaId,
        buildGenerateAvatarPayload(selectedMaterialId, style)
      );
      await refreshAvatarConfig();
      setNotice(
        result.avatar_status === "generated_ready"
          ? "已生成 mock 3D 形象。"
          : result.failure_notice
      );
    });
  }

  function handleMouthTest() {
    setMouthTest(true);
    window.setTimeout(() => setMouthTest(false), 2600);
  }

  const selectedModel = config?.selected_avatar_model ?? null;

  return (
    <MemoryShell background="memoryStringLights">
      <MemoryContainer>
      <div className="flex flex-wrap items-center gap-3 text-sm font-semibold text-memoryAccent">
        <Link href={personaId ? ROUTES.personaDetail(personaId) : ROUTES.dashboard}>
          返回记忆空间
        </Link>
        {personaId ? <Link href={ROUTES.personaChat(personaId)}>进入对话</Link> : null}
        {personaId ? <Link href={ROUTES.personaUploads(personaId)}>上传图片</Link> : null}
      </div>

      <div className="mt-6 grid gap-4">
        <MemoryTitle
          title={persona ? `${persona.name}的纪念形象预览` : "TA 的纪念形象预览"}
          subtitle="这里仅展示默认纪念形象、图片生成任务和简化动作测试。真实 3D 数字人、影视级拟真和口型同步不在当前范围。"
        />
        <AiReminder text="AI 身份提醒：当前是 mock 预览，不代表真实数字人生成质量。" />
      </div>

      {state === "signedOut" ? <SignedOutState /> : null}
      {state === "loading" || state === "checking" ? <Notice text="正在加载形象设置..." /> : null}
      {state === "error" ? <Notice text={error ?? "无法加载形象设置。"} /> : null}

      {state === "ready" && config ? (
        <div className="mt-8 grid gap-6">
          <AvatarPreview model={selectedModel} mouthActive={mouthTest} />

          <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
            <GlassPanel>
              <h2 className="font-serif text-2xl font-semibold text-memoryText">
                当前状态：{avatarStatusLabel(config.avatar_status)}
              </h2>
              <p className="mt-3 rounded-2xl bg-memoryWarm/70 p-3 text-sm leading-7 text-memoryText/74">
                {config.failure_notice}
              </p>
              <dl className="mt-5 grid gap-4 text-sm">
                <Detail
                  label="选中形象"
                  value={
                    selectedModel && hasRenderableAvatarModel(selectedModel)
                      ? avatarModelSummary(selectedModel)
                      : "未设置"
                  }
                />
                <Detail label="形象记录" value={`${config.avatar_models.length}`} />
                <Detail
                  label="模型地址"
                  value={selectedModel?.model_url ?? "未生成"}
                />
              </dl>
            </GlassPanel>

            <section className="grid gap-5">
              {error ? <Alert tone="error" text={error} /> : null}
              {notice ? <Alert tone="success" text={notice} /> : null}

              <Panel title="1. 选择风格">
                <select
                  value={style}
                  onChange={(event) => setStyle(event.target.value as AvatarStyle)}
                  className="w-full rounded-2xl border border-memoryLine/80 bg-white/74 px-4 py-3 text-sm text-memoryText outline-none focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20"
                >
                  {config.style_options.map((option) => (
                    <option key={option} value={option}>
                      {avatarStyleLabel(option)}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleDefaultAvatar}
                  disabled={busyAction !== null}
                  className="memory-button mt-4 rounded-2xl bg-memoryAccent px-5 py-3 text-sm font-semibold text-white shadow-warm disabled:bg-memoryText/30"
                >
                  {busyAction === "default" ? "正在设置..." : "选择默认纪念形象"}
                </button>
              </Panel>

              <Panel title="2. 图片生成">
                <label className="text-sm font-semibold text-memoryText" htmlFor="avatar-material">
                  选择图片资料
                </label>
                <select
                  id="avatar-material"
                  value={selectedMaterialId}
                  onChange={(event) => setSelectedMaterialId(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-memoryLine/80 bg-white/74 px-4 py-3 text-sm text-memoryText outline-none focus:border-memoryAccent focus:ring-4 focus:ring-memoryAccent/20"
                >
                  <option value="">暂无可用图片资料</option>
                  {imageMaterials.map((material) => (
                    <option key={material.id} value={material.id}>
                      {material.file_name || material.user_description || material.id}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleGenerateAvatar}
                  disabled={busyAction !== null || !selectedMaterialId}
                  className="mt-4 rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-2.5 text-sm font-semibold text-memoryText disabled:cursor-not-allowed disabled:text-memoryText/40"
                >
                  {busyAction === "generate" ? "正在生成..." : "生成 mock 3D 形象"}
                </button>
              </Panel>

              <Panel title="3. 动作与口型">
                <p className="text-sm leading-7 text-memoryText/70">
                  预览包含待机、眨眼、微笑和点头；口型测试使用简化 audio envelope 控制嘴部开合。
                </p>
                <button
                  type="button"
                  onClick={handleMouthTest}
                  className="mt-4 rounded-2xl border border-memoryLine/80 bg-white/72 px-4 py-2.5 text-sm font-semibold text-memoryText"
                >
                  测试口型同步
                </button>
              </Panel>
            </section>
          </div>
        </div>
      ) : null}
      </MemoryContainer>
    </MemoryShell>
  );
}

async function loadAvatarPage(personaId: string): Promise<{
  persona: PersonaRead;
  config: AvatarConfigResponse;
  imageMaterials: SourceMaterialRead[];
}> {
  const [persona, config, materials] = await Promise.all([
    getPersona(personaId),
    getAvatarConfig(personaId),
    listMaterials(personaId)
  ]);
  return {
    persona,
    config,
    imageMaterials: materials.filter((material) => material.file_type === "image")
  };
}

function SignedOutState() {
  return (
    <GlassPanel className="mt-8 max-w-3xl">
      <h2 className="font-serif text-2xl font-semibold text-memoryText">需要先进入记忆空间</h2>
      <p className="mt-2 max-w-2xl text-sm leading-7 text-memoryText/70">
        可以免注册体验外婆示例，或登录已有账号查看私有纪念形象。
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        <DemoEntry label="立即体验示例" />
        <Link
          href={ROUTES.login}
          className="rounded-2xl border border-memoryLine/80 bg-white/72 px-5 py-3 text-sm font-semibold text-memoryText shadow-soft"
        >
          登录已有账号
        </Link>
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
      <dd className="mt-1 break-all leading-6 text-memoryText">{value || "未设置"}</dd>
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
