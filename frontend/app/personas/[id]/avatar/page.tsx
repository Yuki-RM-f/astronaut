"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { UploadCloud } from "lucide-react";
import { AvatarStage } from "@/src/components/AvatarStage";
import type { AvatarModelLoadState } from "@/src/components/AvatarPreview";
import {
  PageTitle,
  StarNav,
  StarPanel,
  StarShell
} from "@/src/components/StarSite";
import { PersonaBackLink } from "@/src/components/PersonaBackLink";
import {
  avatarModelSummary,
  avatarStatusLabel,
  AvatarConfigResponse,
  getAvatarConfig,
  getAvatarDisplaySource,
  hasRenderableAvatarModel,
  uploadAvatarModel
} from "@/src/lib/avatar";
import { ensureDemoSession } from "@/src/lib/auth";
import { getPersona, PersonaRead } from "@/src/lib/persona";

type PageState = "loading" | "ready" | "error";
type BusyAction = "upload" | null;

export default function PersonaAvatarPage() {
  const params = useParams();
  const personaId = useMemo(() => {
    const rawId = params.id;
    return Array.isArray(rawId) ? rawId[0] : rawId;
  }, [params.id]);
  const [state, setState] = useState<PageState>("loading");
  const [persona, setPersona] = useState<PersonaRead | null>(null);
  const [config, setConfig] = useState<AvatarConfigResponse | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const [modelLoadState, setModelLoadState] = useState<AvatarModelLoadState>("idle");
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

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setNotice(null);
    setError(null);
  }

  async function handleUpload() {
    if (!personaId || !selectedFile) {
      setError("需要先选择一个 GLB 模型文件。");
      return;
    }
    if (!selectedFile.name.toLowerCase().endsWith(".glb")) {
      setError("当前只支持上传 .glb 模型文件。");
      return;
    }

    setBusyAction("upload");
    setNotice(null);
    setError(null);
    try {
      const nextConfig = await uploadAvatarModel(personaId, selectedFile);
      setConfig(nextConfig);
      setSelectedFile(null);
      setModelLoadState("loading");
      setNotice("GLB 模型已上传，正在加载预览。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "无法上传 GLB 模型。");
    } finally {
      setBusyAction(null);
    }
  }

  const selectedModel = config?.selected_avatar_model ?? null;
  const selectedModelIsRenderable = hasRenderableAvatarModel(selectedModel);

  return (
    <StarShell>
      <StarNav />
      <main className="mx-auto w-full max-w-7xl px-5 pb-12 sm:px-8 lg:px-10">
        {personaId ? <PersonaBackLink personaId={personaId} /> : null}

        <PageTitle
          className="mt-6"
          title={persona ? `${persona.name}的 GLB 数字人` : "TA 的 GLB 数字人"}
          subtitle="上传一个自包含 GLB 模型后，这里和对话页右侧会展示同一个数字人模型。"
        />

        {state === "loading" ? <Notice text="正在加载形象设置..." /> : null}
        {state === "error" ? <Notice text={error ?? "无法加载形象设置。"} /> : null}

        {state === "ready" && config ? (
          <div className="mt-8 grid gap-6">
            <AvatarStage
              personaName={persona?.name ?? "TA"}
              source={getAvatarDisplaySource(config)}
              onModelLoadStateChange={setModelLoadState}
              className="order-3 border-starGold/18 lg:order-1"
              subtitle="上传 GLB 模型后，对话页、遗憾对话室和心愿延续页会使用同一个数字人展示。"
            />

            <div className="order-2 grid gap-6 lg:order-2 lg:grid-cols-[0.85fr_1.15fr]">
              <StarPanel className="p-5">
                <h2 className="font-serif text-2xl font-bold text-starGold">
                  当前状态：{avatarStatusLabel(config.avatar_status)}
                </h2>
                <p className="mt-3 rounded-2xl border border-white/8 bg-white/6 p-3 text-sm font-semibold leading-7 text-starMist/74">
                  {modelProcessText(modelLoadState, selectedModelIsRenderable)}
                </p>
                <dl className="mt-5 grid gap-4 text-sm">
                  <Detail
                    label="选中形象"
                    value={
                      selectedModelIsRenderable && selectedModel
                        ? avatarModelSummary(selectedModel)
                        : "未设置"
                    }
                  />
                  <Detail label="形象记录" value={`${config.avatar_models.length}`} />
                  <Detail label="模型地址" value={selectedModel?.model_url ?? "未上传"} />
                </dl>
              </StarPanel>

              <section className="grid gap-5">
                {error ? <Alert tone="error" text={error} /> : null}
                {notice ? <Alert tone="success" text={notice} /> : null}

                <StarPanel className="p-5">
                  <h2 className="font-serif text-2xl font-bold text-starGold">
                    上传 GLB 模型
                  </h2>
                  <p className="mt-3 text-sm font-semibold leading-7 text-starMist/72">
                    请选择已经准备好的自包含 .glb 文件。上传后会保存为当前选中数字人模型。
                  </p>
                  <label className="mt-5 block">
                    <span className="text-sm font-bold text-starMist/78">GLB 文件</span>
                    <input
                      type="file"
                      accept=".glb,model/gltf-binary"
                      onChange={handleFileChange}
                      className="mt-2 block w-full rounded-2xl border border-starGold/16 bg-indigo-950/32 px-4 py-3 text-sm font-bold text-starCream file:mr-4 file:rounded-full file:border-0 file:bg-starGold file:px-4 file:py-2 file:text-sm file:font-black file:text-violet-950"
                    />
                  </label>
                  {selectedFile ? (
                    <p className="mt-3 text-sm font-semibold text-starMist/64">
                      已选择：{selectedFile.name}
                    </p>
                  ) : null}
                  <button
                    type="button"
                    onClick={handleUpload}
                    disabled={busyAction !== null || !selectedFile}
                    className="star-button mt-5 gap-2 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <UploadCloud className="h-4 w-4" aria-hidden="true" />
                    {busyAction === "upload" ? "正在上传..." : "上传 GLB 模型"}
                  </button>
                </StarPanel>
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
}> {
  const [persona, config] = await Promise.all([
    getPersona(personaId),
    getAvatarConfig(personaId)
  ]);
  return { persona, config };
}

function modelProcessText(state: AvatarModelLoadState, hasModel: boolean): string {
  if (!hasModel) {
    return "尚未上传 GLB 模型。上传成功后会在上方预览区加载并展示。";
  }
  if (state === "loading") {
    return "模型加载中，请稍候。";
  }
  if (state === "ready") {
    return "模型加载成功，当前 GLB 已作为这个人物的数字人展示。";
  }
  if (state === "error") {
    return "模型加载失败。请确认 GLB 文件完整，或重新上传一个可打开的模型。";
  }
  return "已保存 GLB 模型，正在准备预览。";
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
