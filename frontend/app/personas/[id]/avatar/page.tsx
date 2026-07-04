"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { type ReactNode, useEffect, useMemo, useState } from "react";
import { Sparkles } from "lucide-react";
import { AvatarStage } from "@/src/components/AvatarStage";
import {
  PageTitle,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import {
  avatarModelSummary,
  avatarStatusLabel,
  avatarStyleLabel,
  AvatarConfigResponse,
  AvatarStyle,
  buildDefaultAvatarPayload,
  buildGenerateAvatarPayload,
  generateAvatar,
  getAvatarConfig,
  getAvatarDisplaySource,
  hasRenderableAvatarModel,
  selectDefaultAvatar
} from "@/src/lib/avatar";
import { ensureDemoSession } from "@/src/lib/auth";
import { listMaterials, SourceMaterialRead } from "@/src/lib/materials";
import { getPersona, PersonaRead } from "@/src/lib/persona";
import { ROUTES } from "@/src/lib/routes";

type PageState = "loading" | "ready" | "error";

export default function PersonaAvatarPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("loading");
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
    if (!personaId) {
      setError("缺少人物 ID。");
      setState("error");
      return;
    }

    let isCurrent = true;
    setState("loading");
    setError(null);

    ensureDemoSession()
      .then(() => loadAvatarPage(personaId))
      .then((loaded) => {
        if (!isCurrent) {
          return;
        }
        setPersona(loaded.persona);
        setConfig(loaded.config);
        setImageMaterials(loaded.imageMaterials);
        setSelectedMaterialId(loaded.imageMaterials[0]?.id ?? "");
        const selectedStyle = loaded.config.selected_avatar_model?.style;
        setStyle(isAvatarStyle(selectedStyle) ? selectedStyle : "memorial");
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
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-12 sm:px-8 lg:px-10">
        <div className="flex flex-wrap items-center gap-3 text-sm font-bold text-starGold">
          <Link href={personaId ? ROUTES.personaDetail(personaId) : ROUTES.dashboard}>
            返回星星
          </Link>
          {personaId ? <Link href={ROUTES.personaChat(personaId)}>进入对话</Link> : null}
          {personaId ? <Link href={ROUTES.personaUploads(personaId)}>上传图片</Link> : null}
        </div>

        <PageTitle
          className="mt-6"
          title={persona ? `${persona.name}的纪念形象预览` : "TA 的纪念形象预览"}
          subtitle="这里仅展示默认纪念形象、图片生成任务和简化动作测试，不声明真实 3D 数字人能力。"
        />

        {state === "loading" ? <Notice text="正在加载形象设置..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载形象设置。"} /> : null}

        {state === "ready" && config ? (
          <div className="mt-8 grid gap-6">
            <AvatarStage
              personaName={persona?.name ?? "TA"}
              source={getAvatarDisplaySource(config)}
              mouthActive={mouthTest}
              className="border-starGold/18"
              subtitle="生成或选择形象后，对话页右侧会直接替换为当前数字人预览。"
            />

            <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
              <StarPanel className="p-5">
                <h2 className="font-serif text-2xl font-bold text-starGold">
                  当前状态：{avatarStatusLabel(config.avatar_status)}
                </h2>
                <p className="mt-3 rounded-2xl border border-white/8 bg-white/6 p-3 text-sm font-semibold leading-7 text-starMist/74">
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
                  <Detail label="模型地址" value={selectedModel?.model_url ?? "未生成"} />
                </dl>
              </StarPanel>

              <section className="grid gap-5">
                {error ? <Alert tone="error" text={error} /> : null}
                {notice ? <Alert tone="success" text={notice} /> : null}

                <Panel title="1. 选择风格">
                  <select
                    value={style}
                    onChange={(event) => setStyle(event.target.value as AvatarStyle)}
                    className={inputClass}
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
                    className={primaryButtonClass}
                  >
                    {busyAction === "default" ? "正在设置..." : "选择默认纪念形象"}
                  </button>
                </Panel>

                <Panel title="2. 图片生成">
                  <label className="text-sm font-bold text-starMist/78" htmlFor="avatar-material">
                    选择图片资料
                  </label>
                  <select
                    id="avatar-material"
                    value={selectedMaterialId}
                    onChange={(event) => setSelectedMaterialId(event.target.value)}
                    className={`${inputClass} mt-2`}
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
                    className={secondaryButtonClass}
                  >
                    {busyAction === "generate" ? "正在生成..." : "生成 mock 3D 形象"}
                  </button>
                </Panel>

                <Panel title="3. 动作与口型">
                  <p className="text-sm font-semibold leading-7 text-starMist/70">
                    预览包含待机、眨眼、微笑和点头；口型测试使用简化 audio envelope 控制嘴部开合。
                  </p>
                  <button type="button" onClick={handleMouthTest} className={secondaryButtonClass}>
                    <Sparkles className="h-4 w-4" aria-hidden="true" />
                    测试口型同步
                  </button>
                </Panel>
              </section>
            </div>
          </div>
        ) : null}
      </main>
    </StarShell>
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
      <dd className="mt-1 break-all leading-6 text-starCream">{value || "未设置"}</dd>
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

function isAvatarStyle(value: string | null | undefined): value is AvatarStyle {
  return value === "semi_realistic" || value === "cartoon" || value === "memorial";
}

const inputClass = "star-input text-sm";
const primaryButtonClass = "star-button mt-4 min-w-32 disabled:opacity-60";
const secondaryButtonClass =
  "mt-4 inline-flex items-center justify-center gap-2 rounded-full border border-starGold/22 bg-starGold/10 px-4 py-2.5 text-sm font-bold text-starCream transition hover:bg-starGold/16 disabled:cursor-not-allowed disabled:opacity-35";
